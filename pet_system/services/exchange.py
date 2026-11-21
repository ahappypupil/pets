"""兑换服务：积分换食物，含幂等。"""
from ..domain.rules import can_exchange, recommend_exchange
from ..domain.state import Ok, Err
from ..db import transaction
from ..repo import store


def _settings(cur):
    rate = int(store.get_config(cur, "exchange_rate", {}).get("rate", 2))
    cap = int(store.get_config(cur, "stock_cap", {}).get("cap", 99))
    return rate, cap


def shop_view(child_id):
    with transaction() as cur:
        state = store.load_state(cur, child_id)
        rate, cap = _settings(cur)
        plan = recommend_exchange(state, rate)
    return {
        "points": state.points,
        "milk": state.stock.milk,
        "cookie": state.stock.cookie,
        "rate": rate,
        "cap": cap,
        "recommend": plan,
    }


def exchange(child_id, milk, cookie, request_id):
    with transaction() as cur:
        # R8 幂等
        if not store.claim_request(cur, request_id):
            return Ok({"message": "这笔兑换已经办好啦", "duplicate": True})
        state = store.load_state(cur, child_id, lock=True)
        rate, cap = _settings(cur)
        chk = can_exchange(state, milk, cookie, rate, cap)
        if not chk.ok:
            return chk
        cost = chk.value
        cur.execute(
            "UPDATE food_stock SET milk=milk+%s, cookie=cookie+%s WHERE child_id=%s",
            (milk, cookie, child_id),
        )
        cur.execute(
            "INSERT INTO exchange_order (child_id,points_spent,milk_qty,cookie_qty,request_id) "
            "VALUES (%s,%s,%s,%s,%s)", (child_id, cost, milk, cookie, request_id),
        )
        order_id = cur.lastrowid
        store.add_points(cur, child_id, -cost, "spend", "exchange_order", order_id,
                         note=f"兑换 {milk} 牛奶 + {cookie} 饼干")
        return Ok({"cost": cost, "milk": milk, "cookie": cookie,
                   "message": f"换好啦！花了 {cost} 积分"})
