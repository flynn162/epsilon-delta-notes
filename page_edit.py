from sqlops import Db, auto_rollback

TRASH = '.trash'

class DbEditPage(Db):
    @auto_rollback
    def append(self, c, slur, content):
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

    @auto_rollback
    def delete_paragraph(self, c, slur, paragraph_id):
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

    @auto_rollback
    def insert_paragraph(self, c, slur, after_content_id, content):
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

class DbEditTree(Db):
    def create_trash_if_dne(self):
        pass

    @auto_rollback
    def delete_page(self, c, slur):
        # TODO: recursively delete branches in the tree
        raise DatabaseError("Not yet implemented")

        row = Db._fetch_page_row(c, slur)
        c.execute('DELETE FROM toc WHERE id = ?',
                    (row['id'],))
        c.execute('DELETE FROM content WHERE parent_id = ?',
                    (row['first_content_id'],))

    def recycle_page(self, slur):
        raise Exception("Not yet implemented")
