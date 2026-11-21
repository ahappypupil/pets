"""规则引擎纯函数单测：不连数据库。运行：python -m unittest tests.test_rules"""
import unittest
from datetime import datetime
from pet_system.domain.rules import (form_of, is_graduation, can_claim,
                                      can_exchange, can_feed, apply_feed, next_species)
from pet_system.domain.state import (Stock, GameState, PetInstance, PetSpecies, Award)


def make_state(feed_count=0, milk=9, cookie=9, points=10, K=12):
    pet = PetInstance(id=1, child_id=1, species_id=1, status="egg", feed_count=feed_count)
    sp = PetSpecies(id=1, tier=1, name="云团兽", egg_name="棉花蛋",
                    formula_milk=1, formula_cookie=1, feed_times=K,
                    next_species_id=2, svg_key="cloud_beast")
    return GameState(child_id=1, points=points, stock=Stock(milk, cookie),
                     pet=pet, species=sp, today_claims={}, now=datetime.now())


class TestForm(unittest.TestCase):
    # 设计文档第 5.2 节形态表逐格断言
    CASES = [
        (12, 4, 8), (16, 6, 11), (20, 7, 14), (24, 8, 16), (30, 10, 20),
    ]
    def test_thresholds(self):
        for K, t1, t2 in self.CASES:
            self.assertEqual(form_of(0, K).value, "egg")
            self.assertEqual(form_of(t1 - 1, K).value, "egg")
            self.assertEqual(form_of(t1, K).value, "juvenile")
            self.assertEqual(form_of(t2 - 1, K).value, "juvenile")
            self.assertEqual(form_of(t2, K).value, "adult")
            self.assertEqual(form_of(K, K).value, "adult")

    def test_graduation(self):
        self.assertFalse(is_graduation(11, 12))
        self.assertTrue(is_graduation(12, 12))
        self.assertTrue(is_graduation(13, 12))


class TestAward(unittest.TestCase):
    def test_daily_cap(self):
        aw = Award(id=1, name="作业", points=10, daily_cap=1,
                   need_approval=True, enabled=True, source_type="manual")
        s = make_state()
        self.assertTrue(can_claim(s, aw).ok)
        s2 = GameState(**{**s.__dict__, "today_claims": {1: 1}})
        self.assertFalse(can_claim(s2, aw).ok)

    def test_disabled(self):
        aw = Award(id=1, name="作业", points=10, daily_cap=1,
                   need_approval=True, enabled=False, source_type="manual")
        self.assertFalse(can_claim(make_state(), aw).ok)


class TestExchange(unittest.TestCase):
    def test_rate(self):
        self.assertEqual(can_exchange(make_state(points=10), 1, 1, 2, 99).value, 1)
        self.assertFalse(can_exchange(make_state(points=10), 1, 0, 2, 99).ok)  # 不整除
        self.assertFalse(can_exchange(make_state(points=0), 1, 1, 2, 99).ok)   # 积分不足

    def test_stock_cap(self):
        self.assertFalse(can_exchange(make_state(points=100), 100, 0, 2, 99).ok)


class TestFeed(unittest.TestCase):
    def test_food_lack(self):
        s = make_state(milk=0, cookie=5)
        self.assertFalse(can_feed(s).ok)
        r = apply_feed(s)
        self.assertFalse(r.ok)

    def test_apply(self):
        s = make_state(feed_count=11, milk=2, cookie=2)
        r = apply_feed(s)
        self.assertTrue(r.ok)
        self.assertTrue(r.value["graduated"])
        self.assertEqual(r.value["new_feed_count"], 12)
        self.assertEqual(r.value["new_milk"], 1)

    def test_next_species(self):
        chain = [
            PetSpecies(1, 1, "云团兽", "棉花蛋", 1, 1, 12, 2, "a"),
            PetSpecies(2, 2, "火苗狐", "暖焰蛋", 2, 1, 16, None, "b"),
        ]
        self.assertEqual(next_species(chain[0], chain).name, "火苗狐")
        self.assertIsNone(next_species(chain[1], chain))


if __name__ == "__main__":
    unittest.main()
