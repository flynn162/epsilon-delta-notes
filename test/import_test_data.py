#!/usr/bin/env python3

from pathlib import Path
import sys
import glob

res_dir = Path(__file__).absolute().parent.parent
sys.path.append(str(res_dir))

import sqlops

class DbTest(sqlops.Db):
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

db = None

def prepare(uri):
    """Create tables and import test data"""
    global db
    db = DbTest(uri)
    db.create_tables()
    db.import_test_data()

if __name__ == '__main__':
    db_path = res_dir / 'test/test.db'
    if db_path.is_file():
        answer = input('Would you like to delete %s and make a new test DB? '
                       % db_path)
        if answer.lower().startswith('y'):
            db_path.unlink()
            print('Deleted the file.')
        else:
            print('Not doing anything...')
            sys.exit(1)
    prepare(str(db_path))
    db.close()
    print('New DB created at %s' % db_path)
