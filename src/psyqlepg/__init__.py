from psycopg import sql


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


def selectall(conn, table, where):
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


class Table:
    @classmethod
    def get(cls, conn, identifier, key = None):
        return selectone(conn, cls.table, key or cls.primary_key, identifier)

    @classmethod
    def fetch(cls, conn, where):
        return selectall(conn, cls.table, where)
