#!/usr/bin/env python
# Wait for postgres to be up, then create the database if it does not exist.
# Used by entrypoint.sh, reads the same SQL_* environment variables as settings.py

import os
import sys
import time

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

database = os.environ.get("SQL_DATABASE")
conn_args = dict(
    user=os.environ.get("SQL_USER"),
    password=os.environ.get("SQL_PASSWORD"),
    host=os.environ.get("SQL_HOST", "localhost"),
    port=os.environ.get("SQL_PORT", "5432"),
)
wait_seconds = int(os.environ.get("SQL_WAIT_SECONDS", "60"))


def connect(dbname):
    return psycopg2.connect(dbname=dbname, connect_timeout=5, **conn_args)


# Wait for the server, the database container can take a few seconds to start
deadline = time.time() + wait_seconds
while True:
    try:
        con = connect(database)
        con.close()
        sys.exit(0)  # Database exists and we can log into it
    except psycopg2.OperationalError as e:
        error = str(e)
    if 'does not exist' in error:
        break
    if time.time() > deadline:
        print('Unable to connect to postgres at {host}:{port}: {error}'.format(error=error.strip(), **conn_args))
        sys.exit(1)
    print('Waiting for postgres...')
    time.sleep(2)

print('Creating database {}'.format(database))
try:
    con = connect('postgres')
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with con.cursor() as cur:
        cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    con.close()
except psycopg2.DatabaseError as e:
    print('Error creating database: {}'.format(e))
    sys.exit(1)
