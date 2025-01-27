from database import config
import sqlalchemy as sa
import logging


logging.basicConfig()
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

_engine: sa.engine.Engine = None


def init_sqlalchemy_engine():
    global _engine
    if _engine is None:
        _engine = sa.create_engine(
            config.sqlalchemy_url,
            pool_timeout=None,
            isolation_level="READ COMMITTED"
        )


def get_session():
    global _engine
    return sa.orm.Session(_engine, expire_on_commit=False)


def validate_table_name(table_name):
    if not table_name.isidentifier():
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name
