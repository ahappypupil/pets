"""唯一允许出现 SQL 的模块。所有读写都通过这里，映射成领域对象。"""
import json
import pymysql
from datetime import date
from ..domain.state import (Award, PetSpecies, PetInstance, Stock, GameState)


# ---------- 配置 ----------
def get_config(cur, key, default=None):
    cur.execute("SELECT value_json FROM app_config WHERE config_key=%s", (key,))
    row = cur.fetchone()
    if not row:
        return default
    val = row["value_json"]
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val) if val else default


def set_config(cur, key, value, operator=None):
    cur.execute("SELECT value_json FROM app_config WHERE config_key=%s", (key,))
    old = cur.fetchone()
    old_json = None
    if old:
        ov = old["value_json"]
        old_json = ov if isinstance(ov, (dict, list)) else (json.loads(ov) if ov else None)
    new_json = json.dumps(value, ensure_ascii=False)
    cur.execute(
        "INSERT INTO app_config (config_key,value_json,updated_by) VALUES (%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE value_json=VALUES(value_json), updated_by=VALUES(updated_by)",
        (key, new_json, operator),
    )
    cur.execute(
        "INSERT INTO config_audit (config_key,old_json,new_json,operator) VALUES (%s,%s,%s,%s)",
        (key, json.dumps(old_json, ensure_ascii=False) if old_json else None, new_json, operator),
    )


# ---------- 领域对象映射 ----------
def _to_award(r):
    return Award(id=r["id"], name=r["name"], points=r["points"],
                 daily_cap=r["daily_cap"], need_approval=bool(r["need_approval"]),
                 enabled=bool(r["enabled"]), source_type=r["source_type"],
                 category=r["category"], exclusive_group=r["exclusive_group"])


def _profile(r):
    val = r.get("profile_json")
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val:
        try:
            return json.loads(val)
        except ValueError:
            return {}
    return {}


def _to_species(r):
    return PetSpecies(id=r["id"], tier=r["tier"], name=r["name"],
                      egg_name=r["egg_name"], formula_milk=r["formula_milk"],
                      formula_cookie=r["formula_cookie"], feed_times=r["feed_times"],
                      next_species_id=r["next_species_id"], svg_key=r["svg_key"],
                      profile=_profile(r))


def _to_pet(r):
    if not r:
        return None
    return PetInstance(id=r["id"], child_id=r["child_id"], species_id=r["species_id"],
                       status=r["status"], feed_count=r["feed_count"])


def all_awards(cur, enabled_only=True):
    sql = "SELECT * FROM award"
    if enabled_only:
        sql += " WHERE enabled=1"
    sql += " ORDER BY sort_order, id"
    cur.execute(sql)
    return [_to_award(r) for r in cur.fetchall()]


def all_species(cur):
    cur.execute("SELECT * FROM pet_species ORDER BY tier")
    return [_to_species(r) for r in cur.fetchall()]


def get_species(cur, species_id):
    cur.execute("SELECT * FROM pet_species WHERE id=%s", (species_id,))
    r = cur.fetchone()
    return _to_species(r) if r else None


# ---------- 加载游戏状态（事务内，配合 FOR UPDATE） ----------
def load_state(cur, child_id, lock=False):
    suffix = " FOR UPDATE" if lock else ""
    cur.execute("SELECT points_balance FROM child WHERE id=%s" + suffix, (child_id,))
    child = cur.fetchone()
    if not child:
        return None
    points = child["points_balance"]

    cur.execute("SELECT milk, cookie FROM food_stock WHERE child_id=%s", (child_id,))
    stock_row = cur.fetchone() or {"milk": 0, "cookie": 0}
    stock = Stock(milk=stock_row["milk"], cookie=stock_row["cookie"])

    cur.execute("SELECT * FROM pet_instance WHERE id=(SELECT current_pet_id FROM child WHERE id=%s)", (child_id,))
    pet = _to_pet(cur.fetchone())
    species = get_species(cur, pet.species_id) if pet else None

    cur.execute(
        "SELECT award_id, COUNT(*) c FROM award_claim "
        "WHERE child_id=%s AND claim_date=%s AND status IN ('pending','approved') GROUP BY award_id",
        (child_id, date.today()),
    )
    today_claims = {r["award_id"]: r["c"] for r in cur.fetchall()}

    from datetime import datetime
    return GameState(child_id=child_id, points=points, stock=stock, pet=pet,
                     species=species, today_claims=today_claims, now=datetime.now())


# ---------- 积分与流水 ----------
def add_points(cur, child_id, delta, type_, ref_type, ref_id, operator=None, note=None):
    suffix = " FOR UPDATE" if type_ in ("earn", "spend") else ""
    cur.execute("SELECT points_balance FROM child WHERE id=%s" + suffix, (child_id,))
    new_balance = cur.fetchone()["points_balance"] + delta
    if new_balance < 0:
        raise ValueError("余额不足，不能为负")
    cur.execute("UPDATE child SET points_balance=%s WHERE id=%s", (new_balance, child_id))
    cur.execute(
        "INSERT INTO point_ledger (child_id,type,delta,balance_after,ref_type,ref_id,operator,note) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (child_id, type_, delta, new_balance, ref_type, ref_id, operator, note),
    )
    return new_balance


# ---------- 幂等 ----------
def claim_request(cur, request_id):
    """返回 True 表示首次请求；False 表示已处理过。"""
    cur.execute(
        "INSERT IGNORE INTO request_log (request_id) VALUES (%s)", (request_id,)
    )
    return cur.rowcount == 1


# ---------- 图鉴 ----------
def add_codex(cur, child_id, species, feed_count, milk_used, cookie_used):
    from datetime import datetime
    cert_no = f"PET-{child_id}-{species.tier}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cur.execute(
        "INSERT INTO codex (child_id,species_id,first_graduated_at,total_feedings,milk_used,cookie_used,certificate_no) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (child_id, species.id, datetime.now(), feed_count, milk_used, cookie_used, cert_no),
    )
    return cert_no
