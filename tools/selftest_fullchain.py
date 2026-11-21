"""全链路自测：从云团兽蛋一路养到星辰龙毕业（5 阶 102 次喂食）。

运行：python tools/selftest_fullchain.py（需先启动服务）
所有业务操作走 HTTP；仅通过家长 API 临时调大 daily_cap 以在单日备足积分，
测完恢复配置并 reset 数据。
"""
import sys
import os
import json
import uuid
import urllib.request
import urllib.error
import http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pet_system.config import db_kwargs  # noqa: E402

BASE = "http://127.0.0.1:5000"
RESULTS = []
CHAIN = [
    ("云团兽", "棉花蛋", 1, 1, 12),
    ("火苗狐", "暖焰蛋", 2, 1, 16),
    ("星角鹿", "星屑蛋", 2, 2, 20),
    ("海雾鲸", "潮汐蛋", 3, 2, 24),
    ("星辰龙", "星河蛋", 3, 3, 30),
]


def session():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(op, path, data=None):
    if data is None:
        req = urllib.request.Request(BASE + path)
    else:
        req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        r = op.open(req, timeout=15)
        body = r.read().decode()
        try:
            return r.status, json.loads(body)
        except ValueError:
            return r.status, {"raw": body[:120]}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {"raw": body[:120]}


def check(name, cond, detail=""):
    ok = bool(cond)
    RESULTS.append((name, ok, detail))
    print(("  [OK]   " if ok else "  [FAIL] ") + name + (("  -> " + str(detail)) if detail else ""))


def reset():
    import pymysql
    c = pymysql.connect(**db_kwargs())
    cur = c.cursor()
    for t in ["point_ledger", "feeding_record", "exchange_order", "award_claim",
              "codex", "request_log", "pet_instance"]:
        cur.execute("DELETE FROM " + t)
    cur.execute("DELETE FROM food_stock")
    cur.execute("INSERT INTO pet_instance (child_id,species_id,status,feed_count) VALUES (1,1,'egg',0)")
    pid = cur.lastrowid
    cur.execute("UPDATE child SET points_balance=0, current_pet_id=%s WHERE id=1", (pid,))
    cur.execute("INSERT INTO food_stock (child_id,milk,cookie) VALUES (1,0,0)")
    c.commit()
    c.close()


def set_daily_cap(par, award_id, cap):
    return call(par, "/parent/api/award/update", {"id": award_id, "daily_cap": cap})


def main():
    print("=" * 64)
    print("宠物养成系统 · 全链路自测（5 阶 102 次喂食 → 终阶毕业）")
    print("=" * 64)
    reset()
    kid, par = session(), session()
    call(kid, "/child/login", {"pin": "1234"})
    call(par, "/parent/login", {"username": "admin", "password": "admin123"})

    # 临时调大 award10 的每日额度，单日备足 226 积分
    set_daily_cap(par, 10, 20)
    s, j = call(kid, "/child/api/state")
    check("初始状态云团兽蛋", j["data"]["pet"]["name"] == "云团兽" and j["data"]["pet"]["feed_count"] == 0)

    earned = 0
    for i in range(12):  # 12 × 20 = 240 分，足够 226 分
        s, j = call(kid, "/child/api/claim", {"award_id": 10})
        if not j.get("ok"):
            check(f"申请挑战奖 #{i+1}", False, j.get("message"))
            break
        earned += 1
    s, j = call(par, "/parent/api/pending")
    claims = [c for c in j["data"] if c["award_id"] == 10]
    check(f"申请挑战奖 {earned} 次", earned == 12, earned)
    check(f"待确认 {earned} 条", len(claims) == 12, len(claims))
    for c in claims:
        s, j = call(par, "/parent/api/decide", {"claim_id": c["id"], "approve": True})
        if not j.get("ok"):
            check(f"批准 #{c['id']}", False, j.get("message"))
    set_daily_cap(par, 10, 1)  # 恢复默认额度

    s, j = call(kid, "/child/api/state")
    check("积分到账 240", j["data"]["points"] == 240, j["data"]["points"])

    total_feeds = 0
    for idx, (name, egg_name, fm, fc, K) in enumerate(CHAIN, 1):
        # 兑换该阶所需全部食物（分多次，每次不超过 cap=99 且份数能被2整除）
        need_milk, need_cookie = fm * K, fc * K
        while need_milk > 0 or need_cookie > 0:
            batch_m = min(need_milk, 90)
            batch_c = min(need_cookie, 90)
            # 保持总数为偶数（rate=2）
            if (batch_m + batch_c) % 2:
                if batch_m > batch_c:
                    batch_m -= 1
                else:
                    batch_c -= 1
            s, j = call(kid, "/child/api/exchange", {
                "milk": batch_m, "cookie": batch_c, "request_id": str(uuid.uuid4())})
            if not j.get("ok"):
                check(f"第{idx}阶兑换 {batch_m}+{batch_c}", False, j.get("message"))
                break
            need_milk -= batch_m
            need_cookie -= batch_c

        s, j = call(kid, "/child/api/state")
        pet = j["data"]["pet"]
        check(f"第{idx}阶投喂前：{name} {pet['feed_count']}/{K} 库存 {j['data']['milk']}+{j['data']['cookie']}",
              pet["name"] == name and pet["feed_count"] == 0
              and j["data"]["milk"] >= fm * K and j["data"]["cookie"] >= fc * K,
              f"{pet['name']} {pet['feed_count']}/{pet['K']} 库存{j['data']['milk']}/{j['data']['cookie']}")

        forms = set()
        for n in range(K):
            s, j = call(kid, "/child/api/feed", {"request_id": str(uuid.uuid4())})
            if not j.get("ok"):
                check(f"{name} 第{n+1}次喂食", False, j.get("message"))
                break
            d = j["data"]
            forms.add(d.get("form"))
            total_feeds += 1
            if n + 1 == K:
                check(f"{name} 第{K}次毕业", d.get("graduated"), j.get("message"))
                if idx < len(CHAIN):
                    nxt_name, nxt_egg = CHAIN[idx][0], CHAIN[idx][1]
                    check(f"进化为{nxt_egg}（{nxt_name}）", d.get("next_species") == nxt_name,
                          d.get("next_species"))
                else:
                    check("终阶毕业无下一阶", d.get("next_species") is None, d.get("next_species"))
                    check("终阶毕业有证书", bool(d.get("certificate_no")), d.get("certificate_no"))

        check(f"{name} 经历三形态", len(forms) == 3, sorted(str(f) for f in forms))

    check("累计喂食 102 次", total_feeds == 102, total_feeds)

    s, j = call(kid, "/child/api/state")
    check("终阶后无当前宠物", j["data"]["pet"] is None, j["data"]["pet"])
    s, j = call(kid, "/child/api/codex")
    codex = j.get("data", [])
    check("图鉴集齐 5 阶", len(codex) == 5, [c["name"] for c in codex])
    check("图鉴顺序正确", [c["name"] for c in codex] == [c[0] for c in CHAIN],
          [c["name"] for c in codex])

    s, j = call(par, "/parent/api/verify")
    check("全链路账本一致", j.get("data", {}).get("ok"), j.get("data", {}).get("problems"))

    # 异常分支
    s, j = call(kid, "/child/api/state")
    pts_left = j["data"]["points"]
    check("终阶后剩余积分=240-226=14", pts_left == 14, pts_left)
    s, j = call(kid, "/child/api/exchange", {"milk": 4, "cookie": 4, "request_id": str(uuid.uuid4())})
    check("兑换4+4消耗4积分(8份÷汇率2)", j.get("ok") and j["data"].get("cost") == 4,
          f"{j.get('message')} cost={j.get('data', {}).get('cost')}")
    s, j = call(kid, "/child/api/state")
    check("兑换后积分=10", j["data"]["points"] == 10, j["data"]["points"])
    s, j = call(kid, "/child/api/exchange", {"milk": 90, "cookie": 90, "request_id": str(uuid.uuid4())})
    check("积分不足时兑换失败", not j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/feed", {"request_id": str(uuid.uuid4())})
    check("无宠物时喂食失败", not j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": 5})  # 自动通过类，当天未领过
    check("终阶后仍可申请奖项", j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": 3})  # 需家长批准
    check("申请需批准奖项成功", j.get("ok"), j.get("message"))
    s, j = call(par, "/parent/api/pending")
    p3 = [c for c in j["data"] if c["award_id"] == 3]
    if p3:
        s, j = call(par, "/parent/api/decide", {"claim_id": p3[0]["id"], "approve": False})
        check("驳回申请成功", j.get("ok"), j.get("message"))
        s, j = call(kid, "/child/api/claim", {"award_id": 3})
        check("驳回后额度释放可再申请", j.get("ok"), j.get("message"))

    return finish()


def finish():
    print("-" * 64)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    reset()
    from pet_system.services.ledger import verify
    print("已恢复初始数据：云团兽蛋 0/12、0 积分、0 库存；账本", "一致" if verify(1)["ok"] else "不一致")
    print(f"结果：{passed} 通过 / {failed} 失败 / 共 {len(RESULTS)} 项")
    print("=" * 64)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
