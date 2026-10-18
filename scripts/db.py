"""Small PyMySQL adapter, vendored locally; no service imports another service."""
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
from uuid import UUID
import pymysql

JSON_COLUMNS = {'request_body', 'response_body', 'failure_body'}


def parameters(values):
    return tuple(str(v) if isinstance(v, UUID) else v for v in values)


def normalize(row):
    if row is None:
        return None
    return {key: json.loads(value) if key in JSON_COLUMNS and isinstance(value, str) else value
            for key, value in row.items()}


class Cursor:
    def __init__(self, raw):
        self.raw = raw
        self.rowcount = raw.rowcount

    def fetchone(self):
        return normalize(self.raw.fetchone())

    def fetchall(self):
        return [normalize(row) for row in self.raw.fetchall()]


class Connection:
    def __init__(self, values, *, autocommit=False):
        self.namespace = values['DB_NAME']
        self.raw = pymysql.connect(
            host=values.get('DB_HOST', '127.0.0.1'), port=int(values.get('DB_PORT', 3306)),
            user=values['DB_USER'], password=values['DB_PASSWORD'], database=values['DB_NAME'],
            charset='utf8mb4', autocommit=autocommit,
            connect_timeout=int(values.get('DB_CONNECT_TIMEOUT_SECONDS', 5)),
            cursorclass=pymysql.cursors.DictCursor,
        )
        # A key/booking lock may be acquired after a prior SELECT. READ COMMITTED
        # ensures the next lookup sees the preceding owner's committed result.
        self.execute('SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')
        self.execute("SET time_zone='+00:00'")
        self.locks = []
        self.savepoint = 0

    def execute(self, statement, values=()):
        cursor = self.raw.cursor()
        cursor.execute(statement, parameters(values))
        return Cursor(cursor)

    def lock_name(self, name):
        return hashlib.sha256((self.namespace + ':' + name).encode()).hexdigest()

    def try_lock(self, name, timeout=0):
        token = self.lock_name(name)
        acquired = self.execute('SELECT GET_LOCK(%s,%s) AS acquired', (token, timeout)).fetchone()['acquired']
        if acquired == 1:
            self.locks.append(token)
            return True
        return False

    def lock(self, name, timeout=15):
        if not self.try_lock(name, timeout):
            raise pymysql.OperationalError(1205, 'A concurrent operation is still in progress; retry the same request key.')

    def release_lock(self, name):
        token = self.lock_name(name)
        if token in self.locks:
            self.execute('SELECT RELEASE_LOCK(%s)', (token,))
            self.locks.remove(token)

    @contextmanager
    def transaction(self):
        self.savepoint += 1
        name = 'effect_' + str(self.savepoint)
        self.execute('SAVEPOINT ' + name)
        try:
            yield self
        except BaseException:
            self.execute('ROLLBACK TO SAVEPOINT ' + name)
            self.execute('RELEASE SAVEPOINT ' + name)
            raise
        else:
            self.execute('RELEASE SAVEPOINT ' + name)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.raw.commit()
            else:
                self.raw.rollback()
        finally:
            # Closing the connection releases all GET_LOCK locks, including on
            # failures. This happens after the local transaction has ended.
            self.raw.close()


def json_document(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
