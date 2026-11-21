"""账本一致性校验：余额、库存、图鉴三项。"""
from ..db import fetch_all, fetch_one


def verify(child_id):
    problems = []
    # 余额：SUM(delta) 应等于 child.points_balance
    c = fetch_one("SELECT points_balance FROM child WHERE id=%s", (child_id,))
    s = fetch_one("SELECT COALESCE(SUM(delta),0) total FROM point_ledger WHERE child_id=%s", (child_id,))
    if not c or not s or c["points_balance"] != s["total"]:
        problems.append(f"余额不一致：账面={c['points_balance'] if c else '?'} 流水={s['total'] if s else '?'}")

    # 库存：兑换总量 - 喂食总量 = 当前库存
    fd = fetch_one("SELECT COALESCE(SUM(milk_qty),0) milk, COALESCE(SUM(cookie_qty),0) cookie FROM exchange_order WHERE child_id=%s", (child_id,))
    ff = fetch_one("SELECT COALESCE(SUM(milk_used),0) milk, COALESCE(SUM(cookie_used),0) cookie FROM feeding_record WHERE child_id=%s", (child_id,))
    fs = fetch_one("SELECT milk, cookie FROM food_stock WHERE child_id=%s", (child_id,))
    if fd and ff and fs:
        if fd["milk"] - ff["milk"] != fs["milk"] or fd["cookie"] - ff["cookie"] != fs["cookie"]:
            problems.append(f"库存不一致：应为 {fd['milk']-ff['milk']}/{fd['cookie']-ff['cookie']}，实为 {fs['milk']}/{fs['cookie']}")

    # 图鉴：毕业数应等于图鉴条数
    g = fetch_one("SELECT COUNT(*) c FROM pet_instance WHERE child_id=%s AND status='graduated'", (child_id,))
    d = fetch_one("SELECT COUNT(*) c FROM codex WHERE child_id=%s", (child_id,))
    if g and d and g["c"] != d["c"]:
        problems.append(f"图鉴不一致：毕业={g['c']} 图鉴={d['c']}")

    return {"ok": len(problems) == 0, "problems": problems}
