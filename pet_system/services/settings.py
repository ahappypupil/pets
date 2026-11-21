"""配置服务：家长改配置走这里，写审计，改完失效缓存。"""
import json

from ..db import transaction
from ..repo import store


def get_all():
    with transaction() as cur:
        cur.execute("SELECT config_key, value_json, description, updated_at FROM app_config ORDER BY config_key")
        rows = cur.fetchall()
    out = {}
    for r in rows:
        val = r["value_json"]
        # PyMySQL 对 MySQL JSON 列返回的是字符串，需反序列化成对象交给前端
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (ValueError, TypeError):
                pass
        out[r["config_key"]] = {"value": val, "description": r["description"], "updated_at": str(r["updated_at"])}
    return out


def update(key, value, operator="admin"):
    with transaction() as cur:
        store.set_config(cur, key, value, operator)
    return True


def list_awards_admin():
    with transaction() as cur:
        cur.execute("SELECT * FROM award ORDER BY sort_order, id")
        return cur.fetchall()


def update_award(award_id, fields, operator="admin"):
    allowed = ["name", "points", "daily_cap", "need_approval", "enabled", "category", "sort_order", "icon"]
    sets, args = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k}=%s")
            args.append(fields[k])
    if not sets:
        return False
    args.append(award_id)
    with transaction() as cur:
        cur.execute(f"UPDATE award SET {','.join(sets)} WHERE id=%s", args)
    return True
