import sqlite3
from sqlite3 import DatabaseError, IntegrityError
from pathlib import Path
from functools import wraps

res_dir = Path(__file__).absolute().parent

def auto_rollback(func):
    @wraps(func)
    def result(self, *args, **kwargs):
        c = self.conn.cursor()
        c.execute('BEGIN')
        try:
            ret = func(self, c, *args, **kwargs)
            c.execute('COMMIT')
            return ret
        except DatabaseError as e:
            c.execute('ROLLBACK')
            raise e from e

    return result

class Db:
    def __init__(self, address):
        self.conn = sqlite3.connect(address, isolation_level=None)
        c = self.conn.cursor()
        c.execute('PRAGMA foreign_keys = ON')

    def create_tables(self):
        with open(res_dir / 'schema.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        c = self.conn.cursor()
        c.executescript(schema_sql)

    def import_test_data(self):
        with open(res_dir / 'test_data.sql', 'r', encoding='utf-8') as f:
            test_data_sql = f.read()
        c = self.conn.cursor()
        c.executescript(test_data_sql)

    def execute(self, stmt):
        c = self.conn.cursor()
        for row in c.execute(stmt):
            print(repr(row))

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @staticmethod
    def _fetch_page_fmt(c, slur, fmt):
        c.execute('SELECT %s FROM toc WHERE slur = ?' % fmt, (slur,))
        row = c.fetchone()
        if not row:
            raise IntegrityError('No such page')
        return row

    @staticmethod
    def _fetch_page_row(c, slur):
        names = ('id', 'parent_id', 'next_id', 'first_content_id')
        row = Db._fetch_page_fmt(c, slur, ','.join(names))
        result = {}
        for i, n in enumerate(names):
            result[n] = row[i]
        return result

    @staticmethod
    def check_page_id(c, slur):
        return Db._fetch_page_fmt(c, slur, 'id')[0]

db = None
if __name__ == '__main__':
    db = Db(':memory:')
    db.create_tables()
    db.import_test_data()
