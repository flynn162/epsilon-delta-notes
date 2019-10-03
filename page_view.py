from flask import request, render_template, escape, Response, url_for
from parsing import compile_notes, Parser
from sidebar import compile_tree
from pathlib import Path
from sqlops import Db, is_valid_slug, slug_to_link, QueryBuilder, Tree, Content
from collections import deque
from datetime import datetime, timezone

tree_query_cte = str(QueryBuilder().forward().backward().upward().downward())

def row_to_link_tuple(row):
    if not row:
        return None
    elif row['unlisted']:
        return '...', 'unlisted:'
    else:
        return row['title'], slug_to_link(row['slug'])

def utc_to_local_with_title(unix_seconds):
    utc = datetime.utcfromtimestamp(unix_seconds).replace(tzinfo=timezone.utc)
    local = utc.astimezone(tz=None)
    display = local.strftime('%Y-%m-%d')
    title = '%s (%s)' % (display, local.tzname())
    return display, title

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
        self.unlisted = False

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
        self.unlisted = current_row['unlisted'] == 1

        if current_row['mtime'] is not None:
            self.mtime_str = utc_to_local_with_title(current_row['mtime'])

        self.tree = Tree(self.acc, self.page_id).into()
        self.path = self.compute_path()
        id_start = self.acc[self.page_id]['first_content_id']
        self.register_content_id(id_start)

class DbTree(Db):
    @staticmethod
    def _load_content(c, page_id, page_info):
        c.execute("""
        SELECT id, next_id, content FROM content WHERE parent_id = ?
        """, (page_id,))
        for row in c.fetchall():
            page_info.load_content_row(row)

    def get_page_info(self, slug):
        result = None
        with self.auto_rollback() as c:
            page_id = Db.check_page_id(c, slug)
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

class DbTitle(Db):
    def put_titles_in(self, parser_acc):
        unproc = list(parser_acc.unprocessed_slugs())
        if not unproc:
            return
        query = 'SELECT slug, title FROM toc WHERE slug in ({})'.format(
            ','.join(map(lambda _: '?', unproc))
        )
        with self.auto_rollback() as c:
            c.execute(query, unproc)
            for row in c:
                parser_acc.put_title(row[0], row[1])

def handle(app_config):
    slug = request.args.get(':')
    if not slug:
        return '<meta http-equiv="refresh" content="2; url=?:=home"> redirect'
    if not is_valid_slug(slug):
        return 'Invalid page ID'

    with DbTree(app_config['db_uri']) as db:
        page_info = db.get_page_info(slug)

    tree_html = compile_tree(page_info.tree)
    parser = Parser(slug)
    ast_list = [parser.parse_string(string, content_id)
                for string, content_id in page_info.content_pair_iter()]
    with DbTitle(app_config['db_uri']) as db:
        db.put_titles_in(parser.acc)
    notes_html_list = (compile_notes(cons, parser.acc) for cons in ast_list)

    # use the "directory" part only
    page_info.path.pop()

    return render_template(
        'view.html',
        title=page_info.title,
        nav_edit=url_for('edit') + slug_to_link(slug),
        unlisted=page_info.unlisted,
        directory_of_page=page_info.path,
        prev_article=page_info.prev,
        next_article=page_info.next,
        mtime_str=page_info.mtime_str,
        sidebar_html=tree_html,
        notes_html_list=notes_html_list
    )
