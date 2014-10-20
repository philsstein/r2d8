import argparse
import praw
import requests
import logging
import re
from time import sleep

from argParseLog import addLoggingArgs, handleLoggingArgs
from BotConfig import UID, PASSWD
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

    # quiet requests
    logging.getLogger("requests").setLevel(logging.WARNING)

    log.info('connecting to reddit with uid {}'.format(UID))
    reddit = praw.Reddit('{} bot for linking to boardgame information, v 0.1. '
                         '/u/phil_s_stein see /r/{}'.format(UID, UID))
    log.info('Connected. Logging in as {}'.format(UID))
    reddit.login(username=UID, password=PASSWD)
    log.info('Logged in.')
    
    bdb = BotDatabase(args.database)
    log.info('Bot database opened/created.')
    ch = CommentHandler(UID, bdb)
    log.info('Comment/notification handler created.')
    botcmds = re.compile('/u/{}\s(\w+)'.format(UID, UID))
    cmdmap = {
        'getinfo': ch.getInfo,
        'repair': ch.repairComment,
        'xyzzy': ch.xyzzy,
        'alias': ch.alias,
        'getparentinfo': ch.getParentInfo
    }
    log.info('Waiting for new PMs and/or notifications.')
    while True:
        try:
            # for comment in reddit.get_mentions():
            for comment in list(reddit.get_mentions()) + list(reddit.get_unread()):
                # log.debug('got {}'.format(comment.id))
                if not bdb.comment_exists(comment):
                    bdb.add_comment(comment)
                    for cmd in botcmds.findall(comment.body):
                        if cmd in cmdmap:
                            cmdmap[cmd](comment)
                        else:
                            log.info('Got unknown command: {}'.format(cmd))

        except Exception as e:
           log.error('Caught exception: {}'.format(e))

        # get_mentions is non-blocking
        sleep(5)
