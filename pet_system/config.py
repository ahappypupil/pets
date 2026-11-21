"""配置加载：数据库连接只从 .env 读；业务配置从 MySQL 的 app_config 读。"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass


def _load_dotenv_fallback():
    """没有 python-dotenv 时手动解析 .env。"""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv_fallback()


class DBConfig:
    HOST = os.getenv("DB_HOST", "127.0.0.1")
    PORT = int(os.getenv("DB_PORT", "3306"))
    USER = os.getenv("DB_USER", "root")
    PASSWORD = os.getenv("DB_PASSWORD", "")
    NAME = os.getenv("DB_NAME", "pets")
    CHARSET = "utf8mb4"


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"


def db_kwargs(database=None):
    return dict(
        host=DBConfig.HOST,
        port=DBConfig.PORT,
        user=DBConfig.USER,
        password=DBConfig.PASSWORD,
        database=database or DBConfig.NAME,
        charset=DBConfig.CHARSET,
        autocommit=False,
    )
