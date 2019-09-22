import sqlite3
from pathlib import Path
import re
from contextlib import contextmanager
from collections import deque

res_dir = Path(__file__).absolute().parent
slug_re = re.compile('^[a-zA-Z0-9_\\-]{1,100}$')

toc_cols = ('id', 'parent_id', 'next_id', 'first_child_id', 'first_content_id',
            'slug', 'title', 'mtime', 'content_lock')
toc_cols_fullname = map(lambda s: 'toc.{0} as {0}'.format(s), toc_cols)

toc_cols_str = ', '.join(toc_cols)
toc_cols_fullname_str = ', '.join(toc_cols_fullname)

cte_template = """
{{name}} (n, {0}) AS (
SELECT 0 as n, {1} FROM toc WHERE id = :id
UNION ALL
SELECT n + 1, {1} FROM toc
INNER JOIN {{name}} ON {{comp}}
WHERE n < {{N}}
)""".format(toc_cols_str, toc_cols_fullname_str)

class QueryBuilder:
    def __init__(self):
        self.current_i = -1
        self.tables = []

    def get_name(self):
        self.current_i += 1
        return 'cte_%d' % self.current_i

    def _append_fmt(self, fmt_str, N):
        name = self.get_name()
        self.tables.append(cte_template.format(
            name=name,
            comp=fmt_str.format(name),
            N=N
        ))

    def forward(self):
        self._append_fmt('{}.next_id = toc.id', 5)
        return self

    def backward(self):
        self._append_fmt('toc.next_id = {}.id', 5)
        return self

    def upward(self):
        self._append_fmt('{}.parent_id = toc.id', 10)
        return self

    def downward(self):
        self._append_fmt('toc.parent_id = {}.id', 1)
        return self

    def __str__(self):
        selects = ['SELECT {} FROM cte_{}'.format(toc_cols_str, i)
                   for i in range(len(self.tables))]

        return 'WITH {} \n {}'.format(
            ','.join(self.tables),
            '\n UNION '.join(selects)
        )

class TreeNode:
    def __init__(self, title, slug, children=None, selected=False):
        self.title = title
        self.slug = slug
        self.children = children
        self.selected = selected

    def __repr__(self):
        return '<TreeNode selected=%r title=%r slug=%r children=%r>' % (
            self.selected,
            self.title,
            self.slug,
            self.children
        )

    def append(self, child):
        if self.children is None:
            self.children = deque()
        self.children.append(child)

    def prepend(self, child):
        if self.children is None:
            self.children = deque()
        self.children.appendleft(child)

    def link(self):
        return slug_to_link(self.slug)

class Tree:
    def __init__(self, rows, page_id):
        self.rows = rows
        self.page_id = page_id

    def __contains__(self, element):
        if element is None:
            return False
        else:
            return element in self.rows

    def get(self, key, default=None):
        if key is None:
            return default
        else:
            return self.rows.get(key, default)

    def into(self):
        # start from the top
        top_level_rows = filter(lambda r: r['parent_id'] not in self,
                                self.rows.values())
        # root
        root = TreeNode(None, None)
        self.make_children(top_level_rows, root)
        return root

    def iterate_children(self, parent_row):
        front_row = self.get(parent_row['first_child_id'])
        while front_row is not None:
            yield front_row
            front_row = self.get(front_row['next_id'])

    def make_children(self, current_rows, acc):
        last_row = None
        for row in current_rows:
            last_row = row
            children = self.iterate_children(row)
            node = TreeNode(row['title'],
                            row['slug'],
                            selected=(row['id'] == self.page_id))
            self.make_children(children, node)
            acc.append(node)
        # detect broken linked list
        # we can have no child at all, so we need to check if last_row is None
        if last_row and last_row['next_id']:
            acc.append(TreeNode(None, '...'))

class Content:
    def __init__(self):
        self.content_rows = {}
        self.content_id = None

    def register_content_id(self, content_id):
        self.content_id = content_id

    def load_content_row(self, row):
        self.content_rows[row['id']] = row

    def content_row_iter(self):
        if self.content_id is None:
            return

        current = self.content_rows[self.content_id]
        while current is not None:
            yield current
            next_id = current['next_id']
            if next_id is not None:
                current = self.content_rows[next_id]
            else:
                current = None

    def content_list_iter(self):
        return map(lambda r: r['content'], self.content_row_iter())

    def content_id_iter(self):
        return map(lambda r: r['id'], self.content_row_iter())

    def content_pair_iter(self):
        return zip(self.content_list_iter(), self.content_id_iter())

def is_valid_slug(slug):
    return slug_re.match(slug)

def slug_to_link(slug):
    return '?:=%s' % slug

class PageNotFoundError(sqlite3.DatabaseError):
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
        with open(str(res_dir / 'schema.sql'), 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        c = self.conn.cursor()
        c.executescript(schema_sql)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @staticmethod
    def check_page_id(c, slug):
        c.execute('SELECT id, slug FROM toc WHERE slug = ?', (slug,))
        row = c.fetchone()
        if not row:
            raise PageNotFoundError(slug)
        return row[0]
