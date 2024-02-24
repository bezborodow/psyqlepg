from dataclasses import dataclass
from .table_info import TableInfo
from .where import Where, ComparisonOperator
from .util import selectone, selectall, insert, update, delete, load_queries


class MetaTable(type):
    @property
    def info(cls):
        return TableInfo(cls)


# https://docs.python.org/3/library/dataclasses.html
@dataclass
class Table(metaclass=MetaTable):
    table: str # TODO rename to table_name
    primary_key: str | tuple[str]
    columns: dict # TODO dict of objects of type Column.
    queryfile: str
    queries = None


    @classmethod
    def get(cls, conn, identifier, key=None):
        return selectone(conn, cls.table, key or cls.primary_key, identifier)


    @classmethod
    def find(cls, conn, where=Where(), order_by=None):
        return selectall(conn, cls.table, where, order_by or cls.order_by)


    @classmethod
    def insert(cls, conn, **kwargs):
        return insert(conn, cls.table, **kwargs)


    @classmethod
    def update(cls, conn, identifier, key=None, **kwargs):
        return update(conn, cls.table, key or cls.primary_key, identifier, **kwargs)


    @classmethod
    def delete(cls, conn, identifier, key=None):
        return delete(conn, cls.table, key or cls.primary_key, identifier)


    @classmethod
    def query(cls, query_name):
        if cls.queries is None:
            cls.queries = load_queries(cls.queryfile)
        return cls.queries[query_name]


    @classmethod
    def queryone(cls, conn, query_name, params=None, **kwargs):
        query = cls.query(query_name)
        cur = conn.execute(query, params, **kwargs)
        return cur.fetchone()


    @classmethod
    def queryall(cls, conn, query_name, params=None, **kwargs):
        query = cls.query(query_name)
        cur = conn.execute(query, params, **kwargs)
        return cur.fetchall()
