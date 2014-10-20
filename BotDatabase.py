import sqlite3
import logging

log = logging.getLogger(__name__)

class BotDatabase(object):
    def __init__(self, path):
        super(BotDatabase, self).__init__()
        self._connection = sqlite3.connect(path)

        stmt = 'SELECT name FROM sqlite_master WHERE type="table" AND name="comments"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info('Creating comments table.')
            self._connection.execute('CREATE table comments (id text)')

        stmt = 'SELECT name FROM sqlite_master WHERE type="table" AND name="aliases"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info('Creating aliases table.')
            self._connection.execute('CREATE table aliases (gamename text, alias text)')

            # known aliases
            gameNameMap = {
                'Dead of Winter': 'Dead of Winter: A Crossroads Game',
                'Pathfinder': 'Pathfinder Adventure Card Game: Rise of the Runelords - Base Set',
                'Descent 2': 'Descent: Journeys in the Dark (Second Edition)',
                'Seven Wonders': '7 Wonders',
                'Caverna': 'Caverna: The Cave Farmers'
            }

            for g, a in gameNameMap.iteritems():
                log.info('adding alias {} == {} to database'.format(g, a))
                self.add_alias(g, a)

        stmt = 'SELECT name FROM sqlite_master WHERE type="table" AND name="bot_admins"'
        q = self._connection.execute(stmt).fetchall()
        if not q:
            log.info('Creating bot_admins table.')
            self._connection.execute('CREATE table bot_admins (ruid text)')
            for a in ['phil_s_stein', 'timotab']:
                log.info('Adding {} as admin'.format(a))
                self._connection.execute('INSERT INTO bot_admins VALUES (?)', (a,)) 

        self._connection.commit()

    def add_comment(self, comment):
        log.debug('adding comment {} to database'.format(comment.id))
        comment.mark_as_read()
        self._connection.execute('INSERT INTO comments VALUES(?)', (comment.id,))
        self._connection.commit()

    def comment_exists(self, comment):
        cmd = 'SELECT COUNT(*) FROM comments WHERE id=?'
        count = self._connection.execute(cmd, (comment.id,)).fetchall()[0]
        return count and count[0] > 0

    def add_alias(self, name, alias):
        self._connection.execute('INSERT INTO aliases VALUES (?, ?)', (name, alias))

    def get_alias(self, name):
        cmd = 'SELECT gamename FROM aliases where alias=?'
        rows = self._connection.execute(cmd, (name,)).fetchall()
        return rows[0] if rows else None

    def is_admin(self, uid):
        cmd = 'SELECT COUNT(ruid) FROM bot_admins where ruid=?'
        rows = self._connection.execute(cmd, (uid,)).fetchall()
        return False if rows[0] == 0 else True

