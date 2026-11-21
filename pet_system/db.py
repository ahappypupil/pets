"""数据库连接、事务上下文、初始化。

每次事务新建一个连接（家用低并发，简单可靠），用完归还池/关闭。
写事务统一 START TRANSACTION + SELECT ... FOR UPDATE 锁行。
"""
from contextlib import contextmanager
import pymysql
from .config import db_kwargs, DBConfig


def connect(database=None):
    return pymysql.connect(**db_kwargs(database))


@contextmanager
def get_conn():
    """普通连接（自动提交关闭）。"""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction():
    """写事务上下文：yield 一个 DictCursor；异常回滚，正常提交。"""
    conn = connect()
    try:
        conn.begin()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """首次运行时执行 schema.sql 与 seed.sql（幂等，重复执行安全）。"""
    base = __import__("os").path.dirname(__import__("os").path.dirname(__file__))
    root_conn = pymysql.connect(
        host=DBConfig.HOST, port=DBConfig.PORT, user=DBConfig.USER,
        password=DBConfig.PASSWORD, charset=DBConfig.CHARSET, autocommit=True,
    )
    cur = root_conn.cursor()
    for rel in ("schema.sql", "config/seed.sql"):
        path = __import__("os").path.join(base, rel)
        sql = open(path, encoding="utf-8").read()
        for raw in sql.split(";"):
            lines = [l for l in raw.strip().splitlines()
                     if l.strip() and not l.strip().startswith("--")]
            if lines:
                cur.execute("\n".join(lines))
    root_conn.close()


def fetch_all(sql, args=None):
    with get_conn() as c:
        with c.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, args or ())
            return cur.fetchall()


def fetch_one(sql, args=None):
    with get_conn() as c:
        with c.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql, args or ())
            return cur.fetchone()
