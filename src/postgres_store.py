"""PostgreSQL adapter for the monitoring repository's fixed SQL statements.

The dedicated sentinel schema is installed by migrations, never by web requests.
Advisory transaction locking preserves the pilot's serial state transitions across
serverless instances. It can be narrowed to site-level locks after load testing.
"""
import os
from contextlib import contextmanager


class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(row) for row in self.cursor.fetchall()]


class Database:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        if sql == 'BEGIN IMMEDIATE':
            return Cursor(self.connection.execute('SELECT pg_advisory_xact_lock(73638421)'))
        sql = sql.replace('?', '%s')
        if sql.startswith('INSERT OR IGNORE '):
            sql = sql.replace('INSERT OR IGNORE ', 'INSERT ', 1) + ' ON CONFLICT DO NOTHING'
        returning = sql.startswith('INSERT INTO incidents(')
        if returning:
            sql += ' RETURNING id'
        cursor = self.connection.execute(sql, tuple(int(p) if isinstance(p, bool) else p for p in parameters))
        return Cursor(cursor, cursor.fetchone()['id'] if returning else None)


@contextmanager
def connect():
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10, row_factory=dict_row, prepare_threshold=None) as connection:
        connection.execute("SET LOCAL search_path TO sentinel")
        connection.execute("SET LOCAL statement_timeout = '15s'")
        yield Database(connection)
