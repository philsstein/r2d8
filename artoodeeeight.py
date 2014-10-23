import argparse
import praw
import requests
import logging
import re
from HTMLParser import HTMLParser
from time import sleep

from argParseLog import addLoggingArgs, handleLoggingArgs
from BotConfig import UID, PASSWD
from BotDatabase import BotDatabase
from CommentHandler import CommentHandler

log = logging.getLogger(__name__)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument(u'-d', u'--database', help=u'The bot database. Default is {}-bot.db'.format(UID),
                    default=u'{}-bot.db'.format(UID))
    ap.add_argument(u'-u', u'--uid', help=u'The Reddit user ID to run the bot as. '
                    u'Default is {}'.format(UID))
    addLoggingArgs(ap)
    args = ap.parse_args()
    handleLoggingArgs(args)

    UID = args.uid if args.uid else UID

    hp = HTMLParser()

    # quiet requests
    logging.getLogger(u"requests").setLevel(logging.WARNING)

    log.info(u'connecting to reddit with uid {}'.format(UID))
    reddit = praw.Reddit(u'{} bot for linking to boardgame information, v 0.1. '
                         u'/u/phil_s_stein see /r/{}'.format(UID, UID))
    log.info(u'Connected. Logging in as {}'.format(UID))
    reddit.login(username=UID, password=PASSWD)
    log.info(u'Logged in.')
    
    bdb = BotDatabase(args.database)
    log.info(u'Bot database opened/created.')
    ch = CommentHandler(UID, bdb)
    log.info(u'Comment/notification handler created.')
    botcmds = re.compile(u'/u/{}\s(\w+)'.format(UID, UID), re.IGNORECASE)
    cmdmap = {
        u'getinfo': ch.getInfo,
        u'repair': ch.repairComment,
        u'xyzzy': ch.xyzzy,
        u'alias': ch.alias,
        u'getaliases': ch.getaliases,
        u'getparentinfo': ch.getParentInfo
    }
    log.info(u'Waiting for new PMs and/or notifications.')
    while True:
        try:
            for comment in list(reddit.get_mentions()) + list(reddit.get_unread()):
                # log.debug(u'got {}'.format(comment.id))
                if not bdb.comment_exists(comment):
                    bdb.add_comment(comment)
                    for cmd in [c.lower() for c in botcmds.findall(comment.body)]:
                        if cmd in cmdmap:
                            comment.body = hp.unescape(comment.body)
                            cmdmap[cmd](comment)
                        else:
                            log.info(u'Got unknown command: {}'.format(cmd))

        except Exception as e:
            log.error(u'Caught exception: {}'.format(e))

        # get_mentions is non-blocking
        sleep(5)
