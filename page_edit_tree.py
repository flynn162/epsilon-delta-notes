TRASH = '.trash'

class DbEditTree(Db):
    def create_trash_if_dne(self):
        raise DatabaseError("Not yet implemented")

    def delete_page(self, c, slug):
        # TODO: recursively delete branches in the tree
        raise DatabaseError("Not yet implemented")

        row = Db._fetch_page_row(c, slug)
        c.execute('DELETE FROM toc WHERE id = ?',
                    (row['id'],))
        c.execute('DELETE FROM content WHERE parent_id = ?',
                    (row['first_content_id'],))

    def recycle_page(self, slug):
        raise DatabaseError("Not yet implemented")
