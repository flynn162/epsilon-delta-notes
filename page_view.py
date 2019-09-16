from flask import request, render_template, escape, Response
from parser import compile_notes, Parser
from sidebar import compile_tree
from pathlib import Path
from sqlops import Db, is_valid_slur, slur_to_link, QueryBuilder, Tree, Content
from collections import deque
import datetime

tree_query_cte = str(QueryBuilder().forward().backward().upward().downward())

def row_to_link_tuple(row):
    if not row:
        return None
    else:
        return row['title'], slur_to_link(row['slur'])

class PageInfo(Content):
    def __init__(self, page_id):
        super().__init__()
        self.acc = {}
        self.page_id = page_id

        self.content_lock = None
        self.tree = None
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

    def compute(self):
        current_row = self.acc[self.page_id]
        self.next = row_to_link_tuple(self.acc.get(current_row['next_id']))
        self.title = current_row['title']

        if current_row['mtime'] is not None:
            self.mtime_str = datetime.utcfromtimestamp(current_row['mtime']) \
                                     .strptime('%Y-%m-%d')

        self.tree = Tree(self.acc, self.page_id).into()
        self.path = self.compute_path()
        id_start = self.acc[self.page_id]['first_content_id']
        self.content_list = self.content_list_iter(id_start)

class DbTree(Db):
    @staticmethod
    def _load_content(c, page_id, page_info):
        c.execute("""
        SELECT id, next_id, content FROM content WHERE parent_id = ?
        """, (page_id,))
        for row in c.fetchall():
            page_info.load_content_row(row)

    def get_page_info(self, slur):
        result = None
        with self.auto_rollback() as c:
            page_id = Db.check_page_id(c, slur)
            result = PageInfo(page_id)
            self.populate_page_info(c, page_id, result)
        result.compute()
        return result

    def get_tree_cte(self):
        return tree_query_cte

    def populate_page_info(self, c, page_id, page_info):
        """Get all page content, and part of the tree"""
        # adjacent articles
        c.execute(self.get_tree_cte(), {'id': page_id})
        # convert rows into dict
        for row in c.fetchall():
            page_info.load_tree_row(row)
        # load content
        DbTree._load_content(c, page_id, page_info)

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
