from psycopg import sql
import re


class Where:
    def __init__(self, name=None, value=None):
        self.params = []
        self.args = []
        if (name):
            self.append(name, value)


    def append(self, name, value=None):
        if isinstance(name, sql.Composable):
            self.params.append(name)
        else:
            self.params.append(sql.SQL('{} = %s').format(sql.Identifier(name)))
            self.args.append(value)
        return self

    def clause(self):
        if not self.params:
            return sql.SQL('true').format()

        return sql.SQL('{params}').format(
            params=sql.SQL(' and ').join(self.params))


    def as_string(self, context):
        return self.clause().as_string(context)


def selectone(conn, table, primary_key, identifier):
    query = sql.SQL('''
        select *
        from {table}
        where {primary_key} = %s
        limit 1
    ''').format(
            table=sql.Identifier(table),
            primary_key=sql.Identifier(primary_key))

    cur = conn.execute(query, [identifier])
    return cur.fetchone()


def selectall(conn, table, where=Where()):
    query = sql.SQL('''
        select *
        from {table}
        where {where}
    ''').format(
            where=where.clause(),
            table=sql.Identifier(table))

    cur = conn.execute(query, where.args)
    return cur.fetchall()


def insert(conn, table, primary_key, **kwargs):
    query = sql.SQL('''
        insert into {table} ({fields})
        values ({values})
        returning {primary_key} as id
    ''').format(
            table=sql.Identifier(table),
            fields=sql.SQL(', ').join(map(sql.Identifier, kwargs)),
            values=sql.SQL(', ').join(sql.Placeholder() * len(kwargs)),
            primary_key=sql.Identifier(primary_key))

    cur = conn.execute(query, list(kwargs.values()))
    return cur.fetchone().id


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

    query = sql.SQL('''
        update {table}
        set {params}
        where {primary_key} = %s
    ''').format(
            table=sql.Identifier(table),
            params=sql.SQL(', ').join(params),
            primary_key=sql.Identifier(primary_key))

    return conn.execute(query, [*values, identifier])


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


class Table:
    queries = None

    @classmethod
    def get(cls, conn, identifier, key=None):
        return selectone(conn, cls.table, key or cls.primary_key, identifier)

    @classmethod
    def find(cls, conn, where=Where()):
        return selectall(conn, cls.table, where)

    @classmethod
    def insert(cls, conn, **kwargs):
        return insert(conn, cls.table, cls.primary_key, **kwargs)

    @classmethod
    def update(cls, conn, identifier, key=None, **kwargs):
        return update(conn, cls.table, key or cls.primary_key, identifier, **kwargs)

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
