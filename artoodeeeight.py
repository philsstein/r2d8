import argparse
import logging
import re

from argParseLog import addLoggingArgs, handleLoggingArgs
from RedditBot import RedditBot
from BotConfig import UID, PASSWD, subreddits
from BotDatabase import BotDatabase
from CommentHandler import CommentHandler

log = logging.getLogger(__name__)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '--database', help='The bot database. Default is {}-bot.db'.format(UID),
                    default='{}-bot.db'.format(UID))
    ap.add_argument('-u', '--uid', help='The Reddit user ID to run the bot as. '
                    'Default is {}'.format(UID))
    addLoggingArgs(ap)
    args = ap.parse_args()
    handleLoggingArgs(args)

    UID = args.uid if args.uid else UID

    logging.getLogger("requests").setLevel(logging.WARNING)

    rb = RedditBot(UID, '{} bot for linking to boardgame information, v 0.1. '
                   ' /u/phil_s_stein /r/{}'.format(UID, UID), UID, PASSWD)
    rb.connect()

    bdb = BotDatabase(args.database)
    ch = CommentHandler(rb, bdb)
    # find "!rd28 cmd" and "/u/r2d8 cmd"
    botcmds = re.compile('[!|/u/]{}\s(\w+)'.format(UID, UID))
    cmdmap = {
        'getinfo': ch.getInfo,
        'repair': ch.repairComment,
        'xyzzy': ch.xyzzy
    }
    while True:
        try:
            for comment in rb.get_comments_to_scan(subreddits=subreddits, mentions=True):
                if not bdb.comment_exists(comment):
                    bdb.add_comment(comment)
                    # there is probably a better way to find [deleted] comment.
                    if getattr(comment, 'link_author', None):    
                        if '[deleted]' == comment.link_author.encode('utf-8'):
                            continue
                    for cmd in botcmds.findall(comment.body):
                        if cmd in cmdmap:
                            cmdmap[cmd](comment)
                        else:
                            log.info('Got unknown command: {}'.format(cmd))

        except Exception as e:
            log.error('Caught exception: {}'.format(e))
