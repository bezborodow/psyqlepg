import re
from psycopg import sql
from psycopg.rows import namedtuple_row
from enum import Enum
from dataclasses import dataclass


class TableInfo:
    def __init__(self, table):
        self.table = table


    def unique_indices(self, conn):
        '''
        Search for unique keys (except for primary keys.)

        https://www.postgresql.org/docs/current/functions-info.html
        '''

        cur = conn.cursor()
        cur.row_factory = namedtuple_row

        # The indexdef is an array of column names on the unique index.
        # The relname is the name of the unique index.
        query = '''
            select idx.relname,
                    json_agg(pg_catalog.pg_get_indexdef(a.attrelid, a.attnum, true)) indexdef
            from pg_catalog.pg_attribute a
            join pg_class idx on idx.oid = a.attrelid
            join pg_index pgi on pgi.indexrelid = idx.oid
            join pg_namespace insp on insp.oid = idx.relnamespace
            join pg_class tbl on tbl.oid = pgi.indrelid
            join pg_namespace tnsp on tnsp.oid = tbl.relnamespace
            where a.attnum > 0
                and not a.attisdropped
                and tnsp.nspname = 'public'
                and pgi.indisunique
                and not pgi.indisprimary
                and tbl.relname = %s
            group by idx.relname
        '''
        cur.execute(query, [self.table.table])

        indices = {}
        while (att := cur.fetchone()):
            indices[att.relname] = att.indexdef

        return indices


class ComparisonOperator(Enum):
    '''
    Comparison Operators

    https://www.postgresql.org/docs/current/functions-comparison.html
    '''
    LESS_THAN = 1
    GREATER_THAN = 2
    LESS_THAN_OR_EQUAL_TO = 3
    GREATER_THAN_OR_EQUAL_TO = 4
    EQUAL_TO = 5
    NOT_EQUAL_TO = 6


    def __str__(self):
        o = ('<', '>', '<=', '>=', '=', '!=')
        return o[self.value - 1]


    def __format__(self, spec):
        return self.__str__(self)


class Where:
    def __init__(self, name=None, value=None):
        self.params = []
        self.args = []
        if (name):
            self.append(name, value)


    def append(self, name,
               value=None,
               operator=ComparisonOperator.EQUAL_TO):

        if type(operator) is not ComparisonOperator:
            raise ValueError('Invalid comparison operator.')

        if isinstance(name, sql.Composable):
            self.params.append(name)
        else:
            self.params.append(sql.SQL('{} ' + str(operator) + ' %s').format(sql.Identifier(name)))
            self.args.append(value)
        return self


    def clause(self, or_clause=False):
        if not self.params:
            return sql.SQL('true').format()

        if or_clause:
            return sql.SQL('{params}').format(
                params=sql.SQL(' or ').join(self.params))

        return sql.SQL('{params}').format(
            params=sql.SQL(' and ').join(self.params))


    def as_string(self, context):
        return self.clause().as_string(context)


class List:
    def __init__(self, value=None):
        self.params = []
        self.args = []
        if (value):
            self.append(value)


    def append(self, value):
        if isinstance(value, sql.Composable):
            self.params.append(value)
        elif isinstance(value, list):
            for v in value:
                self.append(v)
        else:
            self.params.append(sql.SQL('%s'))
            self.args.append(value)
        return self


    def clause(self):
        return sql.SQL('{params}').format(
            params=sql.SQL(', ').join(self.params))


    def as_string(self, context):
        return self.clause().as_string(context)


def key_search(primary_key, identifier):
    '''
    Generate a where clause to search by primary key.
    Allows composite indices to be passed as a tuple.
    '''
    where = Where()
    if type(primary_key) is tuple and type(identifier) is tuple:
        for k, v in dict(zip(primary_key, identifier)).items():
            where.append(k, v)
    else:
        where.append(primary_key, identifier)

    return where


def selectone(conn, table, primary_key, identifier):
    where = key_search(primary_key, identifier)
    query = sql.SQL('''
        select *
        from {table}
        where {where}
        limit 1
    ''').format(
            table=sql.Identifier(table),
            where=where.clause())

    cur = conn.execute(query, where.args)
    return cur.fetchone()


def selectall(conn, table, where=Where(), order_by=None):
    if (order_by):
        query = sql.SQL('''
            select *
            from {table}
            where {where}
            order by {order_by}
        ''').format(
                where=where.clause(),
                table=sql.Identifier(table),
                order_by=sql.Identifier(order_by))
    else:
        query = sql.SQL('''
            select *
            from {table}
            where {where}
        ''').format(
                where=where.clause(),
                table=sql.Identifier(table))

    cur = conn.execute(query, where.args)
    return cur.fetchall()


def insert(conn, table, **kwargs):
    query = sql.SQL('''
        insert into {table} ({fields})
        values ({values})
        returning *
    ''').format(
            table=sql.Identifier(table),
            fields=sql.SQL(', ').join(map(sql.Identifier, kwargs)),
            values=sql.SQL(', ').join(sql.Placeholder() * len(kwargs)))

    cur = conn.execute(query, list(kwargs.values()))
    return cur.fetchone()


def update(conn, table, primary_key, identifier, **kwargs):
    params = []
    values = []
    for col, value in kwargs.items():
        if not isinstance(value, sql.Composable):
            values.append(value)
            value = sql.Placeholder()

        params.append(sql.SQL('{} = {}').format(
            sql.Identifier(col),
            value))

    where = key_search(primary_key, identifier)
    query = sql.SQL('''
        update {table}
        set {params}
        where {where}
        returning *
    ''').format(
            table=sql.Identifier(table),
            params=sql.SQL(', ').join(params),
            where=where.clause())

    return conn.execute(query, [*values, *where.args])


def delete(conn, table, primary_key, identifier):
    where = key_search(primary_key, identifier)
    query = sql.SQL('''
        delete from {table}
        where {where}
        returning *
    ''').format(
            table=sql.Identifier(table),
            where=where.clause())

    return conn.execute(query, where.args)


def load_queries(filename):
    with open(filename) as file:
        name = None
        queries = {}

        for line in file:
            p = re.compile('-- *#([a-z][a-z0-9_]*)', re.IGNORECASE)

            if (m := p.search(line)):
                name = m.group(1)
            elif name is not None:
                if name not in queries:
                    queries[name] = line
                else:
                    queries[name] += line

        return queries


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
