from flask import request
from sqlops import auto_rollback
from page_view import DbTree, PageInfo, toc_cols_str

class DbEditPage(DbTree):
    @staticmethod
    def _put_current_node(c, page_id, page_info):
        c.execute('SELECT {} FROM toc WHERE id = ?'.format(toc_cols_str),
                  (page_id,))
        page_info.load_tree_row(c.fetchone())

    def get_page_info(self, slur):
        return self._get_page_info(slur, DbEditPage._put_current_node)

    def append(self, slur, content):
        with self.auto_rollback() as c:
            page_id = Db.check_page_id(c, slur)

            c.execute("""
            INSERT INTO content (parent_id, next_id, content)
            VALUES (?, NULL, ?)
            """, (page_id, content))

            c.execute("""
            UPDATE content SET next_id = last_insert_rowid()
            WHERE id != last_insert_rowid() AND next_id IS NULL
            """)

    @staticmethod
    def _check_is_front(c, page_id, paragraph_id):
        c.execute("""
        SELECT first_content_id FROM toc
        WHERE id = ? AND
        (SELECT parent_id FROM content where id = ?) = ?
        """, (page_id, paragraph_id, page_id))
        row = c.fetchone()
        # also checks if row exists, and the if the parent is correct
        if not row:
            raise IntegrityError('Row DNE')

        return row[0] == paragraph_id

    def delete_paragraph(self, slur, paragraph_id):
        with self.auto_rollback() as c:
            page_id = Db.check_page_id(c, slur)
            is_front = Db._check_is_front(c, page_id, paragraph_id)
            if is_front:
                # front = current.next
                c.execute("""
                UPDATE toc SET first_content_id = (
                    SELECT next_id FROM content WHERE id = ?
                ) WHERE id = ?
                """, (paragraph_id, page_id))
            else:
                # prev.next = current.next
                c.execute("""
                UPDATE content SET next_id = (
                    SELECT next_id FROM content WHERE id = ?
                ) WHERE next_id = ?
                """, (paragraph_id, paragraph_id))
            # delete current
            c.execute('DELETE FROM content WHERE id = ?', (paragraph_id,))

    @staticmethod
    def _insert_par_node(c, parent_id, next_id, content):
        c.execute("""
        INSERT INTO content (parent_id, next_id, content)
        VALUES (?, ?, ?)
        """, (parent_id, next_id, content))

    def insert_paragraph(self, slur, after_content_id, content):
        with auto_rollback() as c:
            if after_content_id == -1:
                # at the front
                row = Db._fetch_page_row(c, slur)
                Db._insert_par_node(c,
                                    row['id'],
                                    row['first_content_id'],
                                    content)
                c.execute("""
                UPDATE toc SET first_content_id = last_insert_rowid()
                WHERE id = ?
                """, (row['id'],))
            else:
                # check if id exists
                c.execute('SELECT parent_id, next_id FROM content WHERE id = ?',
                          (after_content_id,))
                row = c.fetchone()
                if not row:
                    raise IntegrityError('Content ID not found')

                Db._insert_par_node(c, row[0], row[1], content)
                c.execute("""
                UPDATE content SET next_id = last_insert_rowid()
                WHERE id = ?
                """, (after_content_id,))

def handle_get(app):
    slur = request.args.get(':')
    with DbEditPage(app.config['db_uri']) as db:
        page_info = db.get_page_info(slur)

    title = 'Editing %s' % page_info.title
    return render_template('edit.html', title=title)

def handle_post(app):
    pass
