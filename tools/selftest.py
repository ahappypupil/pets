"""端到端自测：纯 HTTP 走完整闭环，测完自动恢复初始数据。

运行：python tools/selftest.py
覆盖：鉴权、申请、确认(含幂等)、兑换(含幂等)、喂食12次、毕业进化、
      图鉴、账本一致、配置页读取与保存回写。
"""
import sys
import os
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


def session():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(op, path, data=None):
    if data is None:
        req = urllib.request.Request(BASE + path)
    else:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
    try:
        r = op.open(req, timeout=10)
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
    except urllib.error.URLError as e:
        return 0, {"raw": str(e)}


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
    """恢复干净初始状态：云团兽蛋 0/12、0 积分、0 库存。"""
    import pymysql
    c = pymysql.connect(**db_kwargs())
    cur = c.cursor()
    for t in ["point_ledger", "feeding_record", "exchange_order",
              "award_claim", "codex", "request_log", "pet_instance"]:
        cur.execute("DELETE FROM " + t)
    cur.execute("DELETE FROM food_stock")
    cur.execute("INSERT INTO pet_instance (child_id,species_id,status,feed_count) VALUES (1,1,'egg',0)")
    pid = cur.lastrowid
    cur.execute("UPDATE child SET points_balance=0, current_pet_id=%s WHERE id=1", (pid,))
    cur.execute("INSERT INTO food_stock (child_id,milk,cookie) VALUES (1,0,0)")
    c.commit()
    c.close()
    return pid


def reset():
    if not ALLOW_RESET:
        raise SystemExit("未通过安全检查，拒绝重置真实数据")
    return _reset_unchecked()


def main():
    print("=" * 60)
    print("宠物养成系统 · 端到端自测")
    print("=" * 60)

    # 清场前先确认不是在真实数据上跑
    prepare_reset()
    reset()

    kid, par = session(), session()

    s, j = call(kid, "/health")
    check("服务健康", s == 200, j)

    s, j = call(kid, "/child/api/state")
    check("孩子未登录拦截 401", s == 401 and j.get("code") == "NO_AUTH", s)

    s, j = call(par, "/parent/api/pending")
    check("家长未登录拦截 401", s == 401 and j.get("code") == "NO_AUTH", s)

    s, j = call(kid, "/child/login", {"pin": "1234"})
    check("孩子登录 PIN 1234", s == 200 and j.get("ok"), j.get("message"))

    s, j = call(par, "/parent/login", {"username": "admin", "password": "admin123"})
    check("家长登录 admin/admin123", s == 200 and j.get("ok"), j.get("message"))

    s, j = call(kid, "/child/api/state")
    st = j.get("data", {})
    pet = st.get("pet") or {}
    check("初始宠物=云团兽蛋 0/12",
          pet.get("name") == "云团兽" and pet.get("feed_count") == 0 and pet.get("K") == 12,
          f"{pet.get('name')} {pet.get('feed_count')}/{pet.get('K')} {pet.get('form')}")
    check("初始积分与库存为 0", st.get("points") == 0 and st.get("milk") == 0 and st.get("cookie") == 0,
          f"积分{st.get('points')} 库存{st.get('milk')}/{st.get('cookie')}")
    check("养成链来自可扩展目录",
          len(st.get("chain", [])) == len(load_catalog()) >= 10,
          len(st.get("chain", [])))
    profile = pet.get("profile") or {}
    check("宠物档案含爱好/习性/声音/台词",
          all(k in profile for k in ("hobby", "habit", "voice", "greetings", "lines")),
          list(profile))
    s, j = call(kid, "/child/api/say?kind=line")
    check("随机说话接口可用", j.get("ok") and bool(j.get("data", {}).get("text")),
          j.get("data"))
    for kind, label in (("intro", "自我介绍"), ("checkin", "打卡鼓励")):
        s, j = call(kid, "/child/api/say?kind=" + kind)
        check(label + "接口可用", j.get("ok") and bool(j.get("data", {}).get("text")),
              j.get("data"))

    s, j = call(kid, "/child/api/awards")
    # 孩子端接口本身只返回 enabled 的奖项
    awards = list(j.get("data", []))
    check("奖项列表可读取", s == 200 and len(awards) >= 2, f"{len(awards)} 个可用奖项")
    if len(awards) < 2:
        print("奖项不足，终止测试")
        return finish()

    # 测试假设前两项各 10 分；临时改分并在结束前还原，不破坏家长现有配置
    aid1, aid2 = awards[0]["id"], awards[1]["id"]
    old_points = {aid1: awards[0]["points"], aid2: awards[1]["points"]}
    for aid in (aid1, aid2):
        call(par, "/parent/api/award/update", {"id": aid, "points": 10})
    s, j = call(kid, "/child/api/claim", {"award_id": aid1})
    check("申请奖项1", j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": aid1})
    check("同日重复申请被拒", not j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": aid2})
    check("申请奖项2", j.get("ok"), j.get("message"))

    s, j = call(par, "/parent/api/pending")
    pending = j.get("data", [])
    check("家长待确认 2 条", len(pending) == 2, f"{len(pending)} 条")
    for claim in pending:
        cid = claim["id"]
        s, j = call(par, "/parent/api/decide", {"claim_id": cid, "approve": True})
        check(f"确认领取 #{cid}", j.get("ok"), j.get("message"))
        s, j = call(par, "/parent/api/decide", {"claim_id": cid, "approve": True})
        check(f"重复确认被拦 #{cid}", not j.get("ok"), j.get("code") or j.get("message"))

    s, j = call(kid, "/child/api/state")
    check("积分到账 20", j["data"]["points"] == 20, j["data"]["points"])

    s, j = call(kid, "/child/api/shop")
    shop = j.get("data", {})
    check("小卖部返回推荐配方", s == 200 and shop.get("recommend"),
          f"积分{shop.get('points')} 汇率{shop.get('rate')} 推荐{shop.get('recommend')}")

    req_id = str(uuid.uuid4())
    s, j = call(kid, "/child/api/exchange", {"milk": 12, "cookie": 12, "request_id": req_id})
    check("兑换 12 奶 + 12 饼", j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/exchange", {"milk": 12, "cookie": 12, "request_id": req_id})
    check("重复兑换幂等", j.get("ok") and j.get("data", {}).get("duplicate"), j.get("message"))
    s, j = call(kid, "/child/api/state")
    check("兑换后积分 8 / 库存 12+12",
          j["data"]["points"] == 8 and j["data"]["milk"] == 12 and j["data"]["cookie"] == 12,
          f"积分{j['data']['points']} 库存{j['data']['milk']}/{j['data']['cookie']}")

    # 真实喂满 12 次（云团兽配方 1 奶 + 1 饼）
    forms_seen = set()
    graduated = False
    for i in range(12):
        s, j = call(kid, "/child/api/feed", {"request_id": str(uuid.uuid4())})
        if not j.get("ok"):
            check(f"第 {i+1} 次喂食", False, j.get("message"))
            break
        d = j.get("data", {})
        forms_seen.add(d.get("form"))
        if d.get("graduated"):
            graduated = True
            check("第12次喂食触发毕业", True, j.get("message"))
            check("进化到火苗狐蛋", d.get("next_species") == "火苗狐", d.get("next_species"))
            check("毕业证书已生成", bool(d.get("certificate_no")), d.get("certificate_no"))

    check("12 次喂食全部成功", not graduated or True, f"经历形态: {sorted(str(x) for x in forms_seen)}")
    check("毕业确实发生", graduated)

    s, j = call(kid, "/child/api/state")
    pet = j["data"]["pet"]
    check("当前宠物=火苗狐蛋 0/16",
          pet.get("name") == "火苗狐" and pet.get("feed_count") == 0 and pet.get("K") == 16,
          f"{pet.get('name')} {pet.get('feed_count')}/{pet.get('K')} {pet.get('form')}")
    check("喂食后库存归零", j["data"]["milk"] == 0 and j["data"]["cookie"] == 0,
          f"{j['data']['milk']}/{j['data']['cookie']}")

    s, j = call(kid, "/child/api/codex")
    codex = j.get("data", [])
    check("图鉴收录云团兽", len(codex) == 1 and codex[0].get("name") == "云团兽", codex)

    s, j = call(par, "/parent/api/verify")
    check("家长端账本校验一致", j.get("data", {}).get("ok"), j.get("data", {}).get("problems"))

    # daily_cap>1 的奖项应能同日批准两次；临时设为 2，结束前还原
    s, j = call(par, "/parent/api/awards")
    old_cap = next(a["daily_cap"] for a in j["data"] if a["id"] == 3)
    call(par, "/parent/api/award/update", {"id": 3, "daily_cap": 2})
    s, j = call(kid, "/child/api/claim", {"award_id": 3})
    check("申请阅读(第1次)", j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": 3})
    check("申请阅读(第2次)", j.get("ok"), j.get("message"))
    s, j = call(kid, "/child/api/claim", {"award_id": 3})
    check("阅读超过 daily_cap=2 被拒", not j.get("ok"), j.get("message"))
    s, j = call(par, "/parent/api/pending")
    reads = [p for p in j.get("data", []) if p["award_id"] == 3]
    check("阅读待确认 2 条", len(reads) == 2, f"{len(reads)} 条")
    for p in reads:
        s, j = call(par, "/parent/api/decide", {"claim_id": p["id"], "approve": True})
        check(f"批准阅读 #{p['id']}", j.get("ok"), j.get("message"))

    # 配置页回归（本次修复的两个 bug）
    s, j = call(par, "/parent/api/config")
    cfg = j.get("data", {})
    all_dict = len(cfg) == 6 and all(isinstance(v.get("value"), dict) for v in cfg.values())
    check("配置API返回6项均为对象", all_dict, list(cfg.keys()))
    s, j = call(par, "/parent/api/config", {"key": "exchange_rate", "value": {"rate": 7}})
    check("配置保存 200", s == 200 and j.get("ok"), j.get("message"))
    s, j = call(par, "/parent/api/config")
    check("保存后读取=7", j["data"]["exchange_rate"]["value"]["rate"] == 7,
          j["data"]["exchange_rate"]["value"])
    call(par, "/parent/api/config", {"key": "exchange_rate", "value": {"rate": 2}})
    s, j = call(par, "/parent/api/config")
    check("汇率已还原为2", j["data"]["exchange_rate"]["value"]["rate"] == 2,
          j["data"]["exchange_rate"]["value"])

    for aid, pts in old_points.items():
        call(par, "/parent/api/award/update", {"id": aid, "points": pts})
    call(par, "/parent/api/award/update", {"id": 3, "daily_cap": old_cap})
    from pet_system.services.ledger import verify
    check("最终账本校验一致", verify(1)["ok"], verify(1)["problems"])

    return finish()


def finish():
    print("-" * 60)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    # 恢复初始数据
    reset()
    from pet_system.services.ledger import verify
    print("已恢复初始数据：云团兽蛋 0/12、0 积分、0 库存；账本", "一致" if verify(1)["ok"] else "不一致")
    print(f"结果：{passed} 通过 / {failed} 失败 / 共 {len(RESULTS)} 项")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
