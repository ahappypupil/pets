"""规则引擎 R1–R15：纯函数，不 import Flask、不碰 DB、不读系统时间。

所有函数接收 GameState 与参数，返回 Ok(value) / Err(code, message)。
"""
from .state import Ok, Err, PetStatus


def form_of(feed_count, K):
    """形态判定：T1=ceil(K/3), T2=ceil(2K/3)。"""
    if feed_count >= K:
        return PetStatus.ADULT
    t1 = (K + 2) // 3
    t2 = (2 * K + 2) // 3
    if feed_count >= t2:
        return PetStatus.ADULT
    if feed_count >= t1:
        return PetStatus.JUVENILE
    return PetStatus.EGG


def is_graduation(feed_count, K):
    return feed_count >= K


# ---- R1–R4 奖项 ----
def can_claim(s, award):
    """校验孩子能否领取/申请某奖项。"""
    if not award.enabled:
        return Err("AWARD_DISABLED", "这个奖项暂时不能领啦")
    used = s.today_claims.get(award.id, 0)
    if used >= award.daily_cap:
        return Err("DAILY_CAP", "今天这个奖项已经领过啦，明天再来吧")
    return Ok()


# ---- R7–R9 兑换 ----
def can_exchange(s, milk, cookie, rate, stock_cap):
    """返回所需积分；R7 汇率、R9 库存上限。"""
    if milk < 0 or cookie < 0 or (milk + cookie) == 0:
        return Err("INVALID_QTY", "请先选择要换的食物")
    if milk > stock_cap or cookie > stock_cap:
        return Err("STOCK_CAP", f"每种食物最多存 {stock_cap} 份哦")
    cost = (milk + cookie) // rate
    if (milk + cookie) % rate != 0:
        return Err("NOT_DIVISIBLE", f"{rate} 份食物才能换 1 个积分，请调整数量")
    if s.points < cost:
        return Err("INSUFFICIENT_POINTS", f"还差 {cost - s.points} 个积分")
    return Ok(cost)


def recommend_exchange(s, rate, stock_cap):
    """R10：按当前配方比例，在库存上限内尽可能花光积分换食物。

    可花积分 = min(积分余额, 剩余库存空间 // rate)，总份数必为 rate 的整数倍；
    再按配方比例把份数分给牛奶/饼干，某一侧超出空间的部分挪给另一侧。
    返回的方案满足 can_exchange 的全部约束。
    """
    if not s.species or not s.pet:
        return None
    rate = max(1, rate)
    fm, fc = s.species.formula_milk, s.species.formula_cookie
    room_milk = max(0, stock_cap - s.stock.milk)
    room_cookie = max(0, stock_cap - s.stock.cookie)
    # 积分余额与库存空间双重约束下的最大可花积分
    cost = min(s.points, (room_milk + room_cookie) // rate)
    total = cost * rate
    if total <= 0:
        return {"milk": 0, "cookie": 0, "cost": 0, "need_points": 0}
    milk = total * fm // (fm + fc)
    cookie = total - milk
    # 收敛到各自剩余空间：total <= 空间总和，故溢出只可能有一侧且不会丢份数
    if milk > room_milk:
        cookie += milk - room_milk
        milk = room_milk
    if cookie > room_cookie:
        milk += cookie - room_cookie
        cookie = room_cookie
    return {"milk": milk, "cookie": cookie, "cost": cost, "need_points": 0}


# ---- R11 喂食校验 ----
def can_feed(s):
    if s.pet is None or s.species is None:
        return Err("NO_PET", "还没有宠物哦")
    if s.pet.status == PetStatus.GRADUATED:
        return Err("PET_GRADUATED", "这位宠物已经毕业啦")
    lack = []
    if s.stock.milk < s.species.formula_milk:
        lack.append(f"还差 {s.species.formula_milk - s.stock.milk} 瓶牛奶")
    if s.stock.cookie < s.species.formula_cookie:
        lack.append(f"还差 {s.species.formula_cookie - s.stock.cookie} 块饼干")
    if lack:
        return Err("FOOD_LACK", "，".join(lack))
    return Ok()


def apply_feed(s):
    """R12/R13：纯计算，返回新库存、新次数、新形态、是否毕业。不写库。"""
    chk = can_feed(s)
    if not chk.ok:
        return chk
    K = s.species.feed_times
    new_feed_count = s.pet.feed_count + 1
    return Ok({
        "milk_used": s.species.formula_milk,
        "cookie_used": s.species.formula_cookie,
        "new_milk": s.stock.milk - s.species.formula_milk,
        "new_cookie": s.stock.cookie - s.species.formula_cookie,
        "new_feed_count": new_feed_count,
        "new_status": form_of(new_feed_count, K).value,
        "graduated": is_graduation(new_feed_count, K),
    })


def next_species(species, chain):
    """返回下一阶物种；终阶返回 None。"""
    if not species or species.next_species_id is None:
        return None
    for sp in chain:
        if sp.id == species.next_species_id:
            return sp
    return None
