import argparse
import logging
from os.path import join
from argParseLog import addLoggingArgs, handleLoggingArgs
from RedditBot import RedditBot
from BotConfig import UID, PASSWD, subreddits, botName
from CommentDatabase import CommentDatabase

log = logging.getLogger(__name__)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    addLoggingArgs(ap)
    args = ap.parse_args()
    handleLoggingArgs(args)

    logging.getLogger("requests").setLevel(logging.WARNING)
    rb = RedditBot(botName, '{} bot for linking to boardgame information, v 0.1'.format(botName),
                    UID, PASSWD)

    cdb = CommentDatabase(join('.', '{}-comments.db'.format(botName)))
    rb.connect()
    for comment in rb.get_comments_to_scan(subreddits=subreddits, mentions=True):
        # log.debug('  comment __dict__: {}'.format(comment.__dict__))
        if not cdb.comment_exists(comment):
            cdb.add_comment(comment)
            if comment.subject == 'username mention':
                log.info('got new username mention: {}'.format(comment.__dict__))
