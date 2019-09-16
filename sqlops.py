import sqlite3
from sqlite3 import DatabaseError, IntegrityError
from pathlib import Path
import re
from contextlib import contextmanager
import glob

res_dir = Path(__file__).absolute().parent
slur_re = re.compile('^[a-zA-Z0-9_\\-]{1,100}$')

def is_valid_slur(slur):
    return slur_re.match(slur)

def slur_to_link(slur):
    return '?:=%s' % slur

class PageNotFoundError(DatabaseError):
    pass

class Db:
    def __init__(self, address):
        self.conn = sqlite3.connect(address, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('PRAGMA foreign_keys = ON')

    @contextmanager
    def auto_rollback(self):
        c = self.conn.cursor()
        c.execute('BEGIN')
        try:
            yield c
            c.execute('COMMIT')
        except Exception as e:
            c.execute('ROLLBACK')
            raise e from e

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
    def check_page_id(c, slur):
        c.execute('SELECT id, slur FROM toc WHERE slur = ?', (slur,))
        row = c.fetchone()
        if not row:
            raise PageNotFoundError(slur)
        return row[0]

db = None
if __name__ == '__main__':
    db = Db(str(res_dir / 'test/test.db'))
    db.create_tables()
    db.import_test_data()
