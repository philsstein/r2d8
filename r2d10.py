#!/usr/bin/env python

import logging
import argparse
import praw
import re
from time import sleep
from AccountDetails import UID, PASS
from boardgamegeek import BoardGameGeek as BGG

log = logging.getLogger('r2d6')

def set_log_level(arg):
    logLevels = {
        'none': 100,
        'all': 0,
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    log_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    log_datefmt = '%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format, datefmt=log_datefmt,
                        level=logLevels[args.loglevel])


bot_name = 'r2d10'

header = '''
*^({} issues a series of sophisticated beeps and whistles...)*

'''.format(bot_name)

footer = '''

-------------
^({} is a bot. A helpful bot. Looks a little like a trash can, but you shouldn't hold that against him.)
'''.format(bot_name)

def handle_link(comment):
    bgg = BGG()
    infos = []
    for m in re.finditer('\*\*(\w+)\*\*', comment.body):
        log.debug('looking for game {}'.format(m.group(1)))
        game = bgg.game(m.group(1))
        if game:
            info = 'Details about [**{}**](http://boardgamegeek.com/boardgame/{}):'.format(
                game.name, game.id)
            info += '\n\n'
            info += ' * Released in {}\n'.format(game.year)
            data = ', '.join(getattr(game, 'designers', 'Unknown'))
            info += ' * Designed by {}\n'.format(data)
            data = ', '.join(getattr(game, 'mechanics', 'not listed'))
            info += ' * Mechanics: {}\n'.format(data)
            info += ' * Average rating is {}; rated by {} people\n'.format(
                game.users_rated, game.rating_average)
            for rank in game.ranks:
                info += ' * {}: {}\n'.format(rank['friendlyname'], rank['value'])
            info += ('\nMore information can be found on the [{}\'s page on BGG]'
                     '(http://boardgamegeek.com/boardgame/{})'.format(game.name, game.id))
            info += '\n\n'
            log.debug('adding info: {}'.format(info))
            infos.append(info)

    if not len(infos):
        infos.append('I could not find any games in **bolded** text. Sorry.')

    comment.reply(header + '-----\n'.join([i for i in infos]) + footer)


def handle_xyzzy(comment):
    comment.reply(header + 'Nothing happens.' + footer)


def handle_help(comment):
    pass

if __name__ == "__main__":
    p = argparse.ArgumentParser(prog='r2d6')
    p.add_argument("-u", "--user", help='Reddit account to run the bot as.')
    p.add_argument("-p", "--password", help='password for reddit account')
    p.add_argument('-s', '--subreddit', help='Subreddit to listen to. Can be specified'
                   ' multiple times. Default is "boardgames"', default='boardgames')
    p.add_argument("-l", "--loglevel", dest="loglevel",
                    help="The level at which to log. Must be one of "
                    "none, debug, info, warning, error, or critical. Default is none. ("
                    "This is mostly used for debugging.)",
                    default='none', choices=['none', 'all', 'debug', 'info', 'warning',
                                             'error', 'critical'])
    args = p.parse_args()

    set_log_level(args.loglevel)

    user = args.user if args.user else UID
    password = args.password if args.password else PASS

    commands = {
        'link': handle_link,
        'help': handle_help,
        'xyzzy': handle_xyzzy,
    }

    reddit = praw.Reddit('{} - boardgame util bot, v 0.1'.format(bot_name))
    reddit.login(username=user, password=password)
    subreddit = reddit.get_subreddit(args.subreddit)

    scanned_comments = []
    attn = '!{}'.format(bot_name)
    while True:
        for comment in subreddit.get_comments():
            log.debug('read comment {}: {}'.format(comment.id, comment.body[:20]))
            if comment.id not in scanned_comments:
                log.debug('scanning comment {}: {}'.format(comment.id, comment.body[:20]))
                scanned_comments.append(comment.id)
                if attn in comment.body.lower():
                    cmd = comment.body[comment.body.find(attn):].split()[1]
                    log.debug('found command {}'.format(cmd))
                    if cmd in commands.keys():
                        log.debug('executing cmd {}'.format(cmd))
                        commands[cmd](comment)

        sleep(30)

