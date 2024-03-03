# Configure the test suite from the env variables.

import os

dbname = os.environ.get('PSYQLEPG_TESTDB', 'psyqlepg_test')
dbhost = os.environ.get('PSYQLEPG_TESTDB_HOST', os.environ.get('PGHOST'))
dbport = os.environ.get('PSYQLEPG_TESTDB_PORT', os.environ.get('PGPORT'))
dbuser = os.environ.get('PSYQLEPG_TESTDB_USER', os.environ.get('PGUSER'))
dbpass = os.environ.get('PSYQLEPG_TESTDB_PASSWORD', os.environ.get('PGPASSWORD'))

# Construct a DSN to connect to the test database.
dsn = f'dbname={dbname}'
if dbhost is not None:
    dsn += f' host={dbhost}'
if dbport is not None:
    dsn += f' port={dbport}'
if dbuser is not None:
    dsn += f' user={dbuser}'
if dbpass is not None:
    dsn += f' password={dbpass}'
