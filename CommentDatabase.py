import sqlite3
import logging

log = logging.getLogger(__name__)

class CommentDatabase(object):
    def __init__(self, path):
        super(CommentDatabase, self).__init__()
        self._connection = sqlite3.connect(path)

        stmt = 'SELECT name FROM sqlite_master WHERE type="table" AND name="comments"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            self._connection.execute('CREATE table comments (id text)')
            self._connection.commit()

    def add_comment(self, comment):
        self._connection.execute('INSERT INTO comments VALUES("{}")'.format(comment.id))
        self._connection.commit()

    def comment_exists(self, comment):
        cmd = 'SELECT COUNT(*) from comments where id="{}"'.format(comment.id)
        count = self._connection.execute(cmd).fetchall()[0]
        return count and count[0] > 0
