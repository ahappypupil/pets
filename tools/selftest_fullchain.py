"""全链路自测：按 config/pets.json 的目录从头养到终阶毕业。

运行：python tools/selftest_fullchain.py（需先启动服务）
物种数量、配方、喂食次数都从目录读取；所有业务操作走 HTTP，
仅通过家长 API 临时调大 daily_cap 以在单日备足积分，测完恢复并 reset。
"""
import sys
import os
import math
import json
import uuid
import datetime
import urllib.request
import urllib.error
import http.cookiejar

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pet_system.config import db_kwargs  # noqa: E402
from pet_system.catalog import load_catalog  # noqa: E402

BASE = "http://127.0.0.1:5000"
RESULTS = []
CHAIN = [(x["name"], x["egg_name"], x["formula_milk"],
          x["formula_cookie"], x["feed_times"]) for x in load_catalog()]
TOTAL_FEEDS = sum(x[4] for x in CHAIN)
POINTS_NEEDED = sum((x[2] + x[3]) * x[4] for x in CHAIN) // 2  # 汇率 2
CLAIMS = math.ceil(POINTS_NEEDED / 20)  # 挑战奖每次 20 分
EARNED = CLAIMS * 20


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


ALLOW_RESET = False
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
VOLATILE = ["pet_instance", "codex", "point_ledger", "feeding_record",
            "exchange_order", "award_claim"]


def snapshot():
    """清空前把业务表存成 JSON，便于误操作时找回。"""
    import pymysql
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, "selftest_backup_" +
                        datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    data = {}
    c = pymysql.connect(**db_kwargs())
    cur = c.cursor(pymysql.cursors.DictCursor)
    for t in ["child", "pet_instance", "food_stock", "codex", "point_ledger",
              "feeding_record", "exchange_order", "award_claim", "request_log",
              "app_config", "award"]:
        cur.execute("SELECT * FROM " + t)
        data[t] = cur.fetchall()
    c.close()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return path


def prepare_reset():
    """库里有真实数据时默认拒绝清空；显式授权后才备份并继续。"""
    global ALLOW_RESET
    import pymysql
    c = pymysql.connect(**db_kwargs())
    cur = c.cursor()
    nonempty = {}
    for t in VOLATILE:
        cur.execute("SELECT COUNT(*) FROM " + t)
        n = cur.fetchone()[0]
        if n:
            nonempty[t] = n
    c.close()
    allowed = "--reset-data" in sys.argv or os.environ.get("PET_SELFTEST_RESET") == "1"
    if nonempty and not allowed:
        raise SystemExit(
            "检测到库中已有真实数据：" + str(nonempty) +
            "。自测默认拒绝清空；确认要清库重跑请加 --reset-data "
            "或设置 PET_SELFTEST_RESET=1（会先备份到 logs/）。"
        )
    if nonempty:
        print("已备份原有数据到:", snapshot())
    ALLOW_RESET = True


def _reset_unchecked():
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


def reset():
    if not ALLOW_RESET:
        raise SystemExit("未通过安全检查，拒绝重置真实数据")
    return _reset_unchecked()


def set_daily_cap(par, award_id, cap):
    return call(par, "/parent/api/award/update", {"id": award_id, "daily_cap": cap})


def main():
    print("=" * 64)
    print(f"宠物养成系统 · 全链路自测（{len(CHAIN)} 阶 {TOTAL_FEEDS} 次喂食 → 终阶毕业）")
    print("=" * 64)
    prepare_reset()
    reset()
    kid, par = session(), session()
    call(kid, "/child/login", {"pin": "1234"})
    call(par, "/parent/login", {"username": "admin", "password": "admin123"})
    # 测试按每次 20 分计算；临时改分并在结束前还原，不覆盖家长配置
    s, j = call(par, "/parent/api/awards")
    old_points = next(a["points"] for a in j["data"] if a["id"] == 10)
    call(par, "/parent/api/award/update", {"id": 10, "points": 20})

    # 临时调大 award10 的每日额度，单日备足 POINTS_NEEDED 积分
    set_daily_cap(par, 10, CLAIMS)
    s, j = call(kid, "/child/api/state")
    check("初始状态云团兽蛋", j["data"]["pet"]["name"] == "云团兽" and j["data"]["pet"]["feed_count"] == 0)
    check(f"目录含 {len(CHAIN)} 种宠物", len(j["data"]["chain"]) == len(CHAIN),
          len(j["data"]["chain"]))
    profile = j["data"]["pet"].get("profile") or {}
    check("宠物档案含爱好/习性/声音/台词",
          all(k in profile for k in ("hobby", "habit", "voice", "greetings", "lines")),
          list(profile))
    s, j = call(kid, "/child/api/say?kind=line")
    check("随机说话接口可用", j.get("ok") and bool(j["data"]["text"]), j.get("data"))
    for kind, label in (("intro", "自我介绍"), ("checkin", "打卡鼓励")):
        s, j = call(kid, "/child/api/say?kind=" + kind)
        check(label + "接口可用", j.get("ok") and bool(j["data"]["text"]), j.get("data"))

    earned = 0
    for i in range(CLAIMS):  # 每次 20 分，足够买完整条养成链的食物
        s, j = call(kid, "/child/api/claim", {"award_id": 10})
        if not j.get("ok"):
            check(f"申请挑战奖 #{i+1}", False, j.get("message"))
            break
        earned += 1
    s, j = call(par, "/parent/api/pending")
    claims = [c for c in j["data"] if c["award_id"] == 10]
    check(f"申请挑战奖 {earned} 次", earned == CLAIMS, earned)
    check(f"待确认 {earned} 条", len(claims) == CLAIMS, len(claims))
    for c in claims:
        s, j = call(par, "/parent/api/decide", {"claim_id": c["id"], "approve": True})
        if not j.get("ok"):
            check(f"批准 #{c['id']}", False, j.get("message"))
    set_daily_cap(par, 10, 1)  # 恢复默认额度

    s, j = call(kid, "/child/api/state")
    check(f"积分到账 {EARNED}", j["data"]["points"] == EARNED, j["data"]["points"])

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

    check(f"累计喂食 {TOTAL_FEEDS} 次", total_feeds == TOTAL_FEEDS, total_feeds)

    s, j = call(kid, "/child/api/state")
    check("终阶后无当前宠物", j["data"]["pet"] is None, j["data"]["pet"])
    s, j = call(kid, "/child/api/codex")
    codex = j.get("data", [])
    check(f"图鉴集齐 {len(CHAIN)} 阶", len(codex) == len(CHAIN), [c["name"] for c in codex])
    check("图鉴顺序正确", [c["name"] for c in codex] == [c[0] for c in CHAIN],
          [c["name"] for c in codex])

    s, j = call(par, "/parent/api/verify")
    check("全链路账本一致", j.get("data", {}).get("ok"), j.get("data", {}).get("problems"))

    # 异常分支
    s, j = call(kid, "/child/api/state")
    pts_left = j["data"]["points"]
    check(f"终阶后剩余积分={EARNED}-{POINTS_NEEDED}={EARNED - POINTS_NEEDED}",
          pts_left == EARNED - POINTS_NEEDED, pts_left)
    s, j = call(kid, "/child/api/exchange", {"milk": 4, "cookie": 4, "request_id": str(uuid.uuid4())})
    check("兑换4+4消耗4积分(8份÷汇率2)", j.get("ok") and j["data"].get("cost") == 4,
          f"{j.get('message')} cost={j.get('data', {}).get('cost')}")
    s, j = call(kid, "/child/api/state")
    check(f"兑换后积分={EARNED - POINTS_NEEDED - 4}",
          j["data"]["points"] == EARNED - POINTS_NEEDED - 4, j["data"]["points"])
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

    call(par, "/parent/api/award/update", {"id": 10, "points": old_points})
    return finish()


def finish():
    print("-" * 64)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    reset()
    from pet_system.services.ledger import verify
    print(f"已恢复初始数据：云团兽蛋 0/{CHAIN[0][4]}、0 积分、0 库存；账本",
          "一致" if verify(1)["ok"] else "不一致")
    print(f"结果：{passed} 通过 / {failed} 失败 / 共 {len(RESULTS)} 项")
    print("=" * 64)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
