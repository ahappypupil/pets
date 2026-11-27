"""喂食服务：核心闭环。喂食、形态变化、毕业与新蛋在同一事务。"""
import json
import random

from ..domain.rules import can_feed, apply_feed, next_species
from ..domain.state import Ok, Err, PetStatus
from ..db import transaction
from ..repo import store


def pet_view(child_id):
    with transaction() as cur:
        state = store.load_state(cur, child_id)
        chain = store.all_species(cur)
        if state.pet and state.species:
            K = state.species.feed_times
            from ..domain.rules import form_of
            form = form_of(state.pet.feed_count, K).value
        else:
            form, K = None, 0
    return {
        "child_id": child_id,
        "points": state.points,
        "milk": state.stock.milk,
        "cookie": state.stock.cookie,
        "pet": {
            "id": state.pet.id if state.pet else None,
            "name": state.species.name if state.species else None,
            "egg_name": state.species.egg_name if state.species else None,
            "tier": state.species.tier if state.species else 0,
            "svg_key": state.species.svg_key if state.species else None,
            "feed_count": state.pet.feed_count if state.pet else 0,
            "K": K,
            "form": form,
            "formula_milk": state.species.formula_milk if state.species else 0,
            "formula_cookie": state.species.formula_cookie if state.species else 0,
            "profile": (state.species.profile or {}) if state.species else {},
        } if state.pet else None,
        "chain": [{"id": s.id, "tier": s.tier, "name": s.name,
                   "svg_key": s.svg_key, "profile": s.profile or {}} for s in chain],
    }


CHECKIN_FALLBACK = [
    "完成今天的小任务，就回来点一下打卡吧！",
    "今天也坚持了一点点，记得给自己打个卡。",
    "打卡不是比赛，是给努力的自己点个赞。",
]


def say(child_id, kind="line", avoid=None):
    """按 kind 说话：greeting 问候 / intro 自我介绍 / line 鼓励 / checkin 打卡。"""
    with transaction() as cur:
        state = store.load_state(cur, child_id)
    if not state or not state.pet or not state.species:
        return Err("NO_PET", "还没有宠物哦")
    profile = state.species.profile or {}
    name = state.species.name

    if kind == "intro":
        bits = [f"我是{name}！"]
        if profile.get("hobby"):
            bits.append(f"我喜欢{profile['hobby']}。")
        if profile.get("habit"):
            bits.append(f"我习惯{profile['habit']}。")
        bits.append("今天也陪你一起加油！")
        text = "".join(bits)
    else:
        if kind == "greeting":
            pool = profile.get("greetings") or []
        elif kind == "line":
            pool = profile.get("lines") or []
        elif kind == "checkin":
            pool = profile.get("checkins") or CHECKIN_FALLBACK
        else:
            return Err("BAD_KIND", "不知道想让我说什么呀")
        if not pool:
            return Err("NO_LINES", "这位朋友还没学会说话呢")
        choices = [x for x in pool if x != avoid] or pool
        text = random.choice(choices)

    return Ok({
        "text": text,
        "voice": profile.get("voice") or {},
        "motion": profile.get("motion") or "float",
        "name": name,
        "kind": kind,
    })


def feed(child_id, request_id):
    with transaction() as cur:
        if not store.claim_request(cur, request_id):
            return Ok({"message": "这次喂食已经记过啦", "duplicate": True})
        state = store.load_state(cur, child_id, lock=True)
        outcome = apply_feed(state)
        if not outcome.ok:
            return outcome
        o = outcome.value
        cur.execute("UPDATE food_stock SET milk=%s, cookie=%s WHERE child_id=%s",
                    (o["new_milk"], o["new_cookie"], child_id))
        cur.execute("UPDATE pet_instance SET feed_count=%s, status=%s WHERE id=%s",
                    (o["new_feed_count"], o["new_status"], state.pet.id))
        cur.execute(
            "INSERT INTO feeding_record (pet_id,child_id,milk_used,cookie_used,feed_count_after,request_id) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (state.pet.id, child_id, o["milk_used"], o["cookie_used"], o["new_feed_count"], request_id),
        )
        result = {
            "new_feed_count": o["new_feed_count"],
            "K": state.species.feed_times,
            "form": o["new_status"],
            "milk": o["new_milk"],
            "cookie": o["new_cookie"],
            "graduated": o["graduated"],
        }
        if o["graduated"]:
            # 毕业分支：同事务内完成 图鉴 + 新蛋 + 切换当前宠物
            cur.execute("UPDATE pet_instance SET status='graduated', graduated_at=NOW() WHERE id=%s",
                        (state.pet.id,))
            cert = store.add_codex(cur, child_id, state.species, o["new_feed_count"],
                                   state.species.formula_milk * o["new_feed_count"],
                                   state.species.formula_cookie * o["new_feed_count"])
            chain = store.all_species(cur)
            nxt = next_species(state.species, chain)
            if nxt:
                # 注意：uk_pet_active 唯一约束，旧的已 graduated 让出名额
                cur.execute(
                    "INSERT INTO pet_instance (child_id,species_id,status,feed_count) "
                    "VALUES (%s,%s,'egg',0)", (child_id, nxt.id),
                )
                new_pet_id = cur.lastrowid
                cur.execute("UPDATE child SET current_pet_id=%s WHERE id=%s", (new_pet_id, child_id))
                result.update({
                    "next_species": nxt.name,
                    "next_svg_key": nxt.svg_key,
                    "certificate_no": cert,
                    "message": f"{state.species.name}毕业啦！{nxt.egg_name}出现啦！",
                })
            else:
                cur.execute("UPDATE child SET current_pet_id=NULL WHERE id=%s", (child_id,))
                result.update({"next_species": None, "certificate_no": cert,
                               "message": f"{state.species.name}毕业啦！图鉴全满，太厉害了！"})
        else:
            remain = state.species.feed_times - o["new_feed_count"]
            result["message"] = f"喂饱啦！还差 {remain} 次"
        return Ok(result)


def codex(child_id):
    with transaction() as cur:
        cur.execute(
            "SELECT c.species_id, s.name, s.tier, s.svg_key, s.profile_json, "
            "c.first_graduated_at, c.total_feedings, c.certificate_no "
            "FROM codex c JOIN pet_species s ON s.id=c.species_id "
            "WHERE c.child_id=%s ORDER BY s.tier", (child_id,)
        )
        rows = []
        for r in cur.fetchall():
            raw = r.pop("profile_json", None)
            if isinstance(raw, str) and raw:
                try:
                    r["profile"] = json.loads(raw)
                except ValueError:
                    r["profile"] = {}
            else:
                r["profile"] = raw or {}
            rows.append(r)
        return rows
