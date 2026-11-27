"""领域数据结构与状态枚举（纯数据，无副作用）。"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PetStatus(str, Enum):
    EGG = "egg"
    JUVENILE = "juvenile"
    ADULT = "adult"
    GRADUATED = "graduated"


class LedgerType(str, Enum):
    EARN = "earn"
    SPEND = "spend"
    ADJUST = "adjust"


@dataclass(frozen=True)
class Result:
    ok: bool
    value: object = None
    code: str = ""
    message: str = ""


def Ok(value=None):
    return Result(True, value=value)


def Err(code, message):
    return Result(False, code=code, message=message)


@dataclass(frozen=True)
class Stock:
    milk: int
    cookie: int


@dataclass(frozen=True)
class Award:
    id: int
    name: str
    points: int
    daily_cap: int
    need_approval: bool
    enabled: bool
    source_type: str
    category: str = "学习"
    exclusive_group: str | None = None


@dataclass(frozen=True)
class PetSpecies:
    id: int
    tier: int
    name: str
    egg_name: str
    formula_milk: int
    formula_cookie: int
    feed_times: int
    next_species_id: int | None
    svg_key: str
    profile: dict | None = None


@dataclass(frozen=True)
class PetInstance:
    id: int
    child_id: int
    species_id: int
    status: str
    feed_count: int


@dataclass(frozen=True)
class GameState:
    child_id: int
    points: int
    stock: Stock
    pet: PetInstance | None
    species: PetSpecies | None
    today_claims: dict  # award_id -> 已通过次数
    now: datetime


@dataclass(frozen=True)
class ExchangePlan:
    milk: int
    cookie: int
    cost: int
    need_points: int
