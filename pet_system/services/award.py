"""奖项服务：孩子申请、家长确认/驳回/撤回、自动发放。"""
from datetime import date, datetime
from ..domain.rules import can_claim
from ..domain.state import Ok, Err
from ..db import transaction
from ..repo import store


def list_awards(child_id):
    with transaction() as cur:
        awards = store.all_awards(cur)
        store.load_state(cur, child_id)  # 拿到今日已领
        state = store.load_state(cur, child_id)
        cur.execute(
            "SELECT award_id, status, COUNT(*) c FROM award_claim "
            "WHERE child_id=%s AND claim_date=%s GROUP BY award_id,status",
            (child_id, date.today()),
        )
        claims = {}
        for r in cur.fetchall():
            claims.setdefault(r["award_id"], {})[r["status"]] = r["c"]
    with transaction() as cur:
        cur.execute("SELECT id, icon FROM award")
        icons = {r["id"]: r["icon"] for r in cur.fetchall()}
    out = []
    for a in awards:
        # pending 也占当日名额，避免孩子连点产生重复待确认；驳回后自动释放
        used = sum(claims.get(a.id, {}).values())
        out.append({
            "id": a.id, "name": a.name, "icon": icons.get(a.id), "points": a.points,
            "daily_cap": a.daily_cap, "need_approval": a.need_approval,
            "category": a.category, "used": used,
            "remaining": max(0, a.daily_cap - used),
        })
    return out


def request_claim(child_id, award_id):
    """孩子申请（need_approval=0 的自动通过）。"""
    with transaction() as cur:
        cur.execute("SELECT * FROM award WHERE id=%s AND enabled=1", (award_id,))
        row = cur.fetchone()
        if not row:
            return Err("NOT_FOUND", "奖项不存在")
        award = {
            "id": row["id"], "name": row["name"], "points": row["points"],
            "daily_cap": row["daily_cap"], "need_approval": bool(row["need_approval"]),
            "enabled": bool(row["enabled"]), "source_type": row["source_type"],
            "category": row["category"], "exclusive_group": row["exclusive_group"],
        }
        state = store.load_state(cur, child_id, lock=True)
        # R3 互斥组
        if award["exclusive_group"]:
            cur.execute(
                "SELECT COUNT(*) AS c FROM award_claim c JOIN award a ON a.id=c.award_id "
                "WHERE c.child_id=%s AND c.claim_date=%s AND c.status='approved' "
                "AND a.exclusive_group=%s",
                (child_id, date.today(), award["exclusive_group"]),
            )
            if cur.fetchone()["c"] > 0:
                return Err("EXCLUSIVE", "同类奖项今天已经领过啦")
        chk = can_claim(state, type("A", (), award)())
        if not chk.ok:
            return chk
        if award["need_approval"]:
            cur.execute(
                "INSERT INTO award_claim (child_id,award_id,claim_date,status) VALUES (%s,%s,%s,'pending')",
                (child_id, award_id, date.today()),
            )
            return Ok({"status": "pending", "message": "已告诉爸爸妈妈啦，等确认后就加分"})
        # 自动通过
        cur.execute(
            "INSERT INTO award_claim (child_id,award_id,claim_date,status,approver_id) "
            "VALUES (%s,%s,%s,'approved',NULL)",
            (child_id, award_id, date.today()),
        )
        claim_id = cur.lastrowid
        store.add_points(cur, child_id, award["points"], "earn", "award_claim", claim_id,
                         note=f"自动通过：{award['name']}")
        return Ok({"status": "approved", "points": award["points"], "message": "太棒了，积分到账！"})


def pending_claims():
    with transaction() as cur:
        cur.execute(
            "SELECT c.id, c.child_id, c.award_id, c.claim_date, c.note, c.created_at, "
            "ch.name child_name, a.name award_name, a.points "
            "FROM award_claim c JOIN child ch ON ch.id=c.child_id "
            "JOIN award a ON a.id=c.award_id "
            "WHERE c.status='pending' ORDER BY c.created_at"
        )
        return cur.fetchall()


def decide_claim(claim_id, approve, admin_id, note=None):
    with transaction() as cur:
        cur.execute("SELECT * FROM award_claim WHERE id=%s", (claim_id,))
        claim = cur.fetchone()
        if not claim:
            return Err("NOT_FOUND", "申请不存在")
        if claim["status"] != "pending":
            return Err("ALREADY_HANDLED", "这条已经处理过啦")
        cur.execute(
            "UPDATE award_claim SET status=%s, approver_id=%s, note=%s WHERE id=%s AND status='pending'",
            ("approved" if approve else "rejected", admin_id, note, claim_id),
        )
        if cur.rowcount == 0:
            return Err("ALREADY_HANDLED", "这条已经处理过啦")
        if approve:
            cur.execute("SELECT points,name FROM award WHERE id=%s", (claim["award_id"],))
            aw = cur.fetchone()
            store.add_points(cur, claim["child_id"], aw["points"], "earn",
                             "award_claim", claim_id, operator="admin",
                             note=f"家长确认：{aw['name']}")
            return Ok({"points": aw["points"], "message": f"已通过，+{aw['points']} 积分"})
        return Ok({"message": "已驳回"})


def ledger(child_id, limit=50):
    with transaction() as cur:
        cur.execute(
            "SELECT type,delta,balance_after,note,created_at FROM point_ledger "
            "WHERE child_id=%s ORDER BY id DESC LIMIT %s", (child_id, limit)
        )
        return cur.fetchall()
