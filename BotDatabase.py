import sqlite3
import logging

log = logging.getLogger(__name__)

class BotDatabase(object):
    def __init__(self, path):
        super(BotDatabase, self).__init__()
        self._connection = sqlite3.connect(path)

        stmt = u'SELECT name FROM sqlite_master WHERE type="table" AND name="comments"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info(u'Creating comments table.')
            self._connection.execute(u'CREATE table comments (id text)')

        stmt = u'SELECT name FROM sqlite_master WHERE type="table" AND name="aliases"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info(u'Creating aliases table.')
            self._connection.execute(u'CREATE table aliases (gamename text, alias text)')

            # known aliases
            gameNameMap = {
                u'Dead of Winter': u'Dead of Winter: A Crossroads Game',
                u'Pathfinder': u'Pathfinder Adventure Card Game: Rise of the Runelords - Base Set',
                u'Descent 2': u'Descent: Journeys in the Dark (Second Edition)',
                u'Seven Wonders': u'7 Wonders',
                u'Caverna': u'Caverna: The Cave Farmers'
            }

            for a, g in gameNameMap.iteritems():
                log.info(u'adding alias {} == {} to database'.format(a, g))
                self.add_alias(a, g)

        stmt = u'SELECT name FROM sqlite_master WHERE type="table" AND name="bot_admins"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info(u'Creating bot_admins table.')
            self._connection.execute(u'CREATE table bot_admins (ruid text)')
            for a in ['phil_s_stein', u'timotab']:
                log.info(u'Adding {} as admin'.format(a))
                self._connection.execute(u'INSERT INTO bot_admins VALUES (?)', (a,))

        stmt = u'SELECT name FROM sqlite_master WHERE type="table" AND name="ignore"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            self._connection.execute(u'CREATE table ignore (uid text)')
            log.info('Created ignore table.')
            pass

        self._connection.commit()

    def add_comment(self, comment):
        log.debug(u'adding comment {} to database'.format(comment.id))
        comment.mark_as_read()
        self._connection.execute(u'INSERT INTO comments VALUES(?)', (comment.id,))
        self._connection.commit()

    def comment_exists(self, comment):
        cmd = u'SELECT COUNT(*) FROM comments WHERE id=?'
        count = self._connection.execute(cmd, (comment.id,)).fetchall()[0]
        return count and count[0] > 0

    def add_alias(self, alias, name):
        gname = self.get_name_from_alias(alias)
        if not gname:
            self._connection.execute(u'INSERT INTO aliases VALUES (?, ?)', (name, alias))
            self._connection.commit()

    def get_name_from_alias(self, name):
        cmd = u'SELECT gamename FROM aliases where alias=?'
        rows = self._connection.execute(cmd, (name,)).fetchall()
        return rows[0][0] if rows else None

    def aliases(self):
        cmd = u'SELECT * FROM aliases' 
        rows = self._connection.execute(cmd).fetchall()
        return [] if not rows else rows

    def is_admin(self, uid):
        cmd = u'SELECT COUNT(ruid) FROM bot_admins where ruid=?'
        rows = self._connection.execute(cmd, (uid,)).fetchall()
        if not rows:
            return False

        return False if rows[0][0] == 0 else True

    def ignore_user(self, uid):
        cmd = u'SELECT COUNT(uid) FROM ignore where uid=?'
        rows = self._connection.execute(cmd, (uid,)).fetchall()
        if not rows:
            return False

        return False if rows[0][0] == 0 else True
