import unittest
import psycopg
from psycopg.rows import dict_row
from src.psyqlepg import Table
from .testconfig import dsn


class TableTest(Table):
    table = 'test'
    queryfile = 'tests/data/queries/test.sql'


class TestTable(unittest.TestCase):
    def test_table(self):
        self.assertEqual(1, 1)
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            conn.execute(TableTest.query('create'))
            row = TableTest.insert(
                    conn,
                    num=7,
                    data='Wololo')
            self.assertIsNot(None, row)
            row = TableTest.queryone(conn, 'get', [row['id']])
            self.assertIs(dict, type(row))
            self.assertEqual(7, row['num'])
            self.assertEqual(row['data'], 'Wololo')



if __name__ == '__main__':
    unittest.main()
