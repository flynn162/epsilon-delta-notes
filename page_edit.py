from flask import request, render_template, url_for
from page_view import DbTree, PageInfo, QueryBuilder
from functools import wraps
from sqlops import PageNotFoundError

db_query = str(QueryBuilder().upward())

def needs_page_id(func):
    @wraps(func)
    def result(self, *args, **kwargs):
        if self.page_id is None:
            raise RuntimeError('Needs to register first')
        else:
            return func(self, *args, **kwargs)
    return result

class EditPageDbReader(DbTree):
    @staticmethod
    def _put_current_node(c, page_id, page_info):
        c.execute(db_query, {'id': page_id})
        for row in c.fetchall():
            page_info.load_tree_row(row)

    def get_page_info(self, slur):
        return self._get_page_info(slur, DbEditPage._put_current_node)

class EditPageDbWriter(Db):
    def __init__(self, db_uri):
        super().__init__(db_uri)
        self.page_id = None

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
    slur = request.args.get(':')
    with EditPageDbReader(app.config['db_uri']) as db:
        page_info = db.get_page_info(slur)

    title = 'Editing %s' % page_info.title
    path = [(t, '{}{}'.format(url_for('view'), l))
            for (t, l) in page_info.path]
    return render_template('edit.html',
                           title=title,
                           article_title=page_info.title,
                           slur=slur,
                           path=path,
                           content_list=page_info.content_list,
                           content_lock=page_info.content_lock)

def handle_post(app):
    return str(request.form.getlist('text'))
