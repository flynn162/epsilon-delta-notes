from flask import request, render_template, escape, Response
from parser import compile_notes, Parser
from sidebar import TreeNode, compile_tree
from pathlib import Path
from sqlops import Db, is_valid_slur, slur_to_link
from collections import deque
import datetime

toc_cols = ('id', 'parent_id', 'next_id', 'first_child_id', 'first_content_id',
            'slur', 'title', 'mtime', 'content_lock')
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


tree_query_cte = str(QueryBuilder().forward().backward().upward().downward())

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
                            row['slur'],
                            selected=(row['id'] == self.page_id))
            self.make_children(children, node)
            acc.append(node)
        # detect broken linked list
        # we can have no child at all, so we need to check if last_row is None
        if last_row and last_row['next_id']:
            acc.append(TreeNode(None, '...'))

def row_to_link_tuple(row):
    if not row:
        return None
    else:
        return row['title'], slur_to_link(row['slur'])

class PageInfo:
    def __init__(self, page_id):
        self.acc = {}
        self.page_id = page_id
        self.content_rows = {}

        self.content_lock = None
        self.tree = None
        self.content_list = None
        self.path = None
        self.title = None
        self.mtime_str = None
        self.prev = None
        self.next = None

    def load_tree_row(self, row):
        if row['next_id'] == self.page_id:
            self.prev = row_to_link_tuple(item)
        if row['id'] == self.page_id:
            self.content_lock = row['content_lock']

        self.acc[row['id']] = row

    def load_content_row(self, row):
        self.content_rows[row['id']] = row

    def reverse_path_iter(self):
        row = self.acc[self.page_id]
        while row is not None:
            yield row_to_link_tuple(row)
            if row['parent_id'] is None:
                row = None
            else:
                row = self.acc.get(row['parent_id'])
                if row is None:
                    # broken tree
                    yield ('...', '#')

    def compute_path(self):
        iterator = self.reverse_path_iter()
        result = deque()
        for path_tuple in iterator:
            result.appendleft(path_tuple)
        return result

    def content_row_iter(self):
        id_start = self.acc[self.page_id]['first_content_id']
        if id_start is None:
            return

        current = self.content_rows[id_start]
        while current is not None:
            yield current['content']
            next_id = current['next_id']
            if next_id is not None:
                current = self.content_rows[next_id]
            else:
                current = None

    def compute(self):
        current_row = self.acc[self.page_id]
        self.next = row_to_link_tuple(self.acc.get(current_row['next_id']))
        self.title = current_row['title']

        if current_row['mtime'] is not None:
            self.mtime_str = datetime.utcfromtimestamp(current_row['mtime']) \
                                     .strptime('%Y-%m-%d')

        self.tree = Tree(self.acc, self.page_id).into()
        self.path = self.compute_path()
        self.content_list = self.content_row_iter()

class DbTree(Db):
    @staticmethod
    def _put_tree(c, page_id, page_info):
        # adjacent articles
        c.execute(tree_query_cte, {'id': page_id})
        # convert rows into dict
        for row in c.fetchall():
            page_info.load_tree_row(row)

    @staticmethod
    def _load_content(c, page_id, page_info):
        c.execute("""
        SELECT id, next_id, content FROM content WHERE parent_id = ?
        """, (page_id,))
        for row in c.fetchall():
            page_info.load_content_row(row)

    def get_page_info(self, slur):
        return self._get_page_info(slur, DbTree._put_tree)

    def _get_page_info(self, slur, tree_loader):
        result = None
        # transaction starts
        with self.auto_rollback() as c:
            # initialize PageInfo
            page_id = Db.check_page_id(c, slur)
            result = PageInfo(page_id)
            # put some tree content in it
            tree_loader(c, page_id, result)
            # put some page content in it
            DbTree._load_content(c, page_id, result)
        result.compute()
        return result

def handle(app):
    slur = request.args.get(':')
    if not slur:
        return '<meta http-equiv="refresh" content="2; url=?:=home"> redirect'
    if not is_valid_slur(slur):
        return 'Invalid page ID'

    with DbTree(app.config['db_uri']) as db:
        page_info = db.get_page_info(slur)

    tree_html = compile_tree(page_info.tree)
    notes_html_list = []
    for content in page_info.content_list:
        cons = Parser().parse_string(content)
        notes_html_list.append(compile_notes(cons))

    # use the "directory" part only
    page_info.path.pop()

    return render_template(
        'view.html',
        title=page_info.title,
        directory_of_page=page_info.path,
        prev_article=page_info.prev,
        next_article=page_info.next,
        sidebar_html=tree_html,
        notes_html_list=notes_html_list
    )
