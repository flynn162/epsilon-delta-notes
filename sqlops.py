import sqlite3
from sqlite3 import DatabaseError, IntegrityError
from pathlib import Path
from functools import wraps
import glob

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

    def _read_script(self):
        with open(res_dir / 'test/test_data.sql', 'r', encoding='utf-8') as f:
            test_data_sql = f.read()
        c = self.conn.cursor()
        c.executescript(test_data_sql)

    def _read_scrbl(self, folder, id_start, for_id):
        files = glob.glob(str(res_dir / folder / '*.scrbl'))
        content = []
        for i in range(len(files)):
            with open(res_dir / folder / ('%d.scrbl' % (i+1)), 'r') as f:
                content.append(f.read())
        c = self.conn.cursor()
        c.execute('BEGIN')
        for i, s in enumerate(content):
            next_id = i + id_start + 1 if i < len(content) - 1 else None
            c.execute("""
            INSERT INTO content (id, next_id, parent_id, content)
            VALUES (?, ?, ?, ?)
            """, (i + id_start, next_id, for_id, s))
        c.execute('COMMIT')

    def import_test_data(self):
        self._read_script()
        self._read_scrbl('test/units/', 100, 2)

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
    db = Db(str(res_dir / 'test/test.db'))
    db.create_tables()
    db.import_test_data()
