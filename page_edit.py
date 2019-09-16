from flask import request, render_template, url_for, redirect
from page_view import DbTree, QueryBuilder
from functools import wraps
from sqlops import PageNotFoundError, Content, is_valid_slug, slug_to_link
from sqlite3 import IntegrityError
from os import urandom
from base64 import b64encode
from diff import print_diff
import time

db_query = str(QueryBuilder().upward())

class ConcurrentEditError(IntegrityError):
    def __init__(self):
        super().__init__('Somebody changed the page when you were editing it')

def needs_page_id(func):
    @wraps(func)
    def result(self, *args, **kwargs):
        if self.page_id is None:
            raise RuntimeError('Needs to register first')
        else:
            return func(self, *args, **kwargs)
    return result

class EditPageDbReader(DbTree):
    def get_tree_cte(self):
        return db_query

class EditPageDbWriter(DbTree):
    def __init__(self, db_uri):
        super().__init__(db_uri)
        self.page_id = None
        self.content_list = None
        self.content_ids = None

    def handle_change(self, old_slug, new_slug, title, text_list, lock):
        with self.auto_rollback() as c:
            self.register(c, old_slug)
            self.check_and_change_lock(c, lock)
            self.change_metadata(c, new_slug, title)
            self.patch_page(c, self.generate_patch(text_list))

    def register(self, c, old_slug):
        c.execute('SELECT id, first_content_id FROM toc WHERE slug = ?',
                  (old_slug,))
        row = c.fetchone()
        if not row:
            raise PageNotFoundError(old_slug)
        self.page_id = row[0]
        content = Content()
        DbTree._load_content(c, self.page_id, content)
        self.content_list = content.content_list_iter(row[1])
        self.content_ids = content.content_id_iter(row[1])

    def check_and_change_lock(self, c, lock):
        if lock == '': lock = None
        c.execute('SELECT content_lock FROM toc WHERE id = ?', (self.page_id,))
        if c.fetchone()[0] != lock:
            raise ConcurrentEditError()
        new_lock = None
        while new_lock == lock:
            new_lock = b64encode(urandom(9), b'-_').decode('ascii')
        c.execute('UPDATE toc SET content_lock = ? WHERE id = ?',
                  (new_lock, self.page_id))

    @needs_page_id
    def change_metadata(self, c, new_slug, new_title):
        new_slug = new_slug.strip()
        if not is_valid_slug(new_slug):
            raise IntegrityError('Invalid slug')

        new_title = new_title.strip()
        if not new_title:
            raise IntegrityError('You need a title')

        c.execute("""
        UPDATE toc SET slug = ?, title = ?, mtime = ?
        WHERE id = ?
        """, (new_slug, new_title, self.page_id, int(time.time())))

    def generate_patch(self, text_list):
        filtered = filter(str.__len__, map(str.strip, text_list))
        return print_diff(list(self.content_list), list(filtered))

    def patch_page(self, c, patch):
        last_id = 'front'
        for action, operand in patch:
            if action == '+':
                self.insert_paragraph(c, last_id, operand)
                last_id = 'lastinsert'
            elif action == '-':
                self.delete_paragraph(c, next(self.content_ids))
                # don't update last_id, but still move on
            else:
                last_id = next(self.content_ids)

    @needs_page_id
    def append(self, c, content):
        c.execute("""
        INSERT INTO content (parent_id, next_id, content)
        VALUES (?, NULL, ?)
        """, (self.page_id, content))

        c.execute("""
        UPDATE content SET next_id = last_insert_rowid()
        WHERE id != last_insert_rowid() AND next_id IS NULL
        """)

    def _check_is_front(self, c, paragraph_id):
        c.execute("""
        SELECT first_content_id FROM toc
        WHERE id = ? AND
        (SELECT parent_id FROM content where id = ?) = ?
        """, (self.page_id, paragraph_id, self.page_id))
        row = c.fetchone()
        # also checks if row exists, and the if the parent is correct
        if not row:
            raise IntegrityError('Row DNE')

        return row[0] == paragraph_id

    @needs_page_id
    def delete_paragraph(self, c, paragraph_id):
        is_front = self._check_is_front(c, paragraph_id)
        if is_front:
            # front = current.next
            c.execute("""
            UPDATE toc SET first_content_id = (
                SELECT next_id FROM content WHERE id = ?
            ) WHERE id = ?
            """, (paragraph_id, self.page_id))
        else:
            # prev.next = current.next
            c.execute("""
            UPDATE content SET next_id = (
                SELECT next_id FROM content WHERE id = ?
            ) WHERE next_id = ?
            """, (paragraph_id, paragraph_id))
        # delete current
        c.execute('DELETE FROM content WHERE id = ?', (paragraph_id,))

    @needs_page_id
    def insert_paragraph(self, c, after_content_id, content):
        if after_content_id == 'front':
            self._insert_at_front(c, content)
        elif after_content_id == 'lastinsert':
            c.execute('SELECT last_insert_rowid()')
            self._insert(c, c.fetchone()[0], content)
        else:
            self._insert(c, after_content_id, content)

    def _insert_at_front(self, c, content):
        c.execute("""
        INSERT INTO content (parent_id, next_id, content) VALUES
        (:pid,
         (SELECT first_content_id FROM toc where id = :pid),
         :content)
        """, {'pid': self.page_id, 'content': content})

        c.execute("""
        UPDATE toc SET first_content_id = last_insert_rowid()
        WHERE id = ?
        """, (self.page_id,))

    def _insert(self, c, after_content_id, content):
        # check if id exists
        c.execute('SELECT parent_id, next_id FROM content WHERE id = ?',
                  (after_content_id,))
        row = c.fetchone()
        if not row:
            raise IntegrityError('after_content_id not found')

        c.execute("""
        INSERT INTO content (parent_id, next_id, content) VALUES
        (?, ?, ?)
        """, (row[0], row[1], content))

        c.execute("""
        UPDATE content SET next_id = last_insert_rowid()
        WHERE id = ?
        """, (after_content_id,))

def handle_get(app):
    slug = request.args.get(':')
    with EditPageDbReader(app.config['db_uri']) as db:
        page_info = db.get_page_info(slug)

    title = 'Editing %s' % page_info.title
    path = [(t, '{}{}'.format(url_for('view'), l))
            for (t, l) in page_info.path]
    return render_template('edit.html',
                           title=title,
                           article_title=page_info.title,
                           slug=slug,
                           path=path,
                           content_list=page_info.content_list,
                           content_lock=page_info.content_lock)

def handle_post(app):
    text_list = request.form.getlist('text')
    if request.form.get('button') != 'submit':
        return 'You are not submitting'

    with EditPageDbWriter(app.config['db_uri']) as db:
        db.handle_change(request.form.get('old_slug', ''),
                         request.form.get('new_slug', ''),
                         request.form.get('title', ''),
                         request.form.getlist('text'),
                         request.form.get('content_lock', ''))

    return redirect('{}{}'.format(url_for('view'),
                                  slug_to_link(request.form['new_slug'])))
