from psycopg.rows import namedtuple_row


class TableInfo:
    def __init__(self, table):
        self.table = table


    def unique_indices(self, conn):
        '''
        Return unique keys.
        '''

        cur = conn.cursor()
        cur.row_factory = namedtuple_row

        # The indexdef is an array of column names on the unique index.
        # The relname is the name of the unique index.
        #
        # https://www.postgresql.org/docs/current/functions-info.html
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
                and tbl.relname = %s
            group by idx.relname
        '''
        cur.execute(query, [self.table.table])

        indices = {}
        while (att := cur.fetchone()):
            indices[att.relname] = att.indexdef

        return indices


    def primary_key(self, conn):
        '''
        Retreive the primary key. This is either a string, or a tuple
        if the primary key is a composite key.
        '''

        # https://wiki.postgresql.org/wiki/Retrieve_primary_key_columns
        query = '''
            SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid
                    AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = 'tablename'::regclass
            AND    i.indisprimary;
        '''
        return NotImplemented # TODO


    def columns(self, conn):
        cur = conn.cursor()
        cur.row_factory = namedtuple_row
        query = '''
            select data_type, column_default, udt_name, column_name,
                    character_maximum_length, numeric_precision,
                    is_nullable = 'YES' as is_nullable,
                    is_self_referencing = 'YES' as is_self_referencing,
                    is_updatable = 'YES' as is_updatable
            from information_schema.columns
            where table_name = %s
                and table_schema = 'public';
        '''
        cur.execute(query, [self.table.table])
        columns = {}
        while column := cur.fetchone():
            columns[column.column_name] = column
        return columns
