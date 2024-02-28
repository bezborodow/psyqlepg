import re
from psycopg import sql
from .where import Where, ComparisonOperator


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
    if type(where) is tuple:
        where_tuple = where
        where = Where()
        where.append(*where_tuple)
    if type(where) is list:
        where_list = where
        where = Where()
        for w in where_list:
            if type(w) is tuple:
                where.append(*w)

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
