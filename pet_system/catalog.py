"""宠物目录：config/pets.json 是唯一可扩展清单，同步到 pet_species 表。

新增一种怪兽只需在 JSON 里追加一项（id/tier 唯一、next 指向下一项 id），
然后执行 `python -m pet_system.catalog` 或重启服务；旧库会自动补列并同步。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "config", "pets.json")


def load_catalog(path=None):
    """读取并校验目录，返回按 tier 排序的条目列表。"""
    with open(path or CATALOG_PATH, encoding="utf-8") as f:
        items = json.load(f)
    ids = [x["id"] for x in items]
    tiers = [x["tier"] for x in items]
    if len(ids) != len(set(ids)) or len(tiers) != len(set(tiers)):
        raise ValueError("宠物目录里 id / tier 不能重复")
    for x in items:
        nxt = x.get("next")
        if nxt is not None and nxt not in ids:
            raise ValueError(f"宠物 {x['name']} 的 next={nxt} 不在目录中")
        p = x.get("profile") or {}
        for field in ("hobby", "habit", "motion", "voice"):
            if field not in p:
                raise ValueError(f"宠物 {x['name']} 缺少 profile.{field}")
        if not p.get("greetings") or not p.get("lines") or not p.get("checkins"):
            raise ValueError(f"宠物 {x['name']} 至少需要一句问候、一句鼓励语和一句打卡语")
    return sorted(items, key=lambda x: x["tier"])


def profile_of(item):
    return item.get("profile") or {}


def ensure_schema(cur):
    """老库兼容：没有 profile_json 列时补上。"""
    cur.execute(
        "SELECT COUNT(*) AS n FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='pet_species' "
        "AND COLUMN_NAME='profile_json'"
    )
    if not cur.fetchone()["n"]:
        cur.execute(
            "ALTER TABLE pet_species ADD COLUMN profile_json JSON DEFAULT NULL "
            "COMMENT '档案：出处/爱好/习性/声音/台词/动画'"
        )


def sync_catalog(cur, path=None, force=False, refresh_profiles=False):
    """插入缺失物种、补空档案、按目录重连养成链；返回新增数量。

    不覆盖家长已改过的配方/次数；force=True 覆盖全部字段，
    refresh_profiles=True 只刷新档案（台词/叫声/爱好等）。
    """
    items = load_catalog(path)
    cur.execute("SELECT id, profile_json FROM pet_species")
    existing = {r["id"]: r for r in cur.fetchall()}
    added = 0
    for x in items:
        profile = json.dumps(profile_of(x), ensure_ascii=False)
        if x["id"] not in existing:
            cur.execute(
                "INSERT INTO pet_species "
                "(id,tier,name,egg_name,formula_milk,formula_cookie,feed_times,"
                "next_species_id,svg_key,profile_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (x["id"], x["tier"], x["name"], x["egg_name"],
                 x["formula_milk"], x["formula_cookie"], x["feed_times"],
                 x.get("next"), x["svg_key"], profile),
            )
            added += 1
        else:
            old = existing[x["id"]]["profile_json"]
            if force or refresh_profiles or not old or old in ("{}", "null"):
                cur.execute("UPDATE pet_species SET profile_json=%s WHERE id=%s",
                            (profile, x["id"]))
            if force:
                cur.execute(
                    "UPDATE pet_species SET tier=%s,name=%s,egg_name=%s,"
                    "formula_milk=%s,formula_cookie=%s,feed_times=%s,svg_key=%s WHERE id=%s",
                    (x["tier"], x["name"], x["egg_name"], x["formula_milk"],
                     x["formula_cookie"], x["feed_times"], x["svg_key"], x["id"]),
                )
        cur.execute("UPDATE pet_species SET next_species_id=%s WHERE id=%s",
                    (x.get("next"), x["id"]))
    return added


if __name__ == "__main__":
    import sys
    from .db import transaction

    force = "--force" in sys.argv
    refresh_profiles = "--refresh-profiles" in sys.argv
    with transaction() as cur:
        ensure_schema(cur)
        n = sync_catalog(cur, force=force, refresh_profiles=refresh_profiles)
    print(f"宠物目录已同步：新增 {n} 种，共 {len(load_catalog())} 种")
