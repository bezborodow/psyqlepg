from psycopg.rows import namedtuple_row


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

