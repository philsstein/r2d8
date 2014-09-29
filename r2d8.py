#!/usr/bin/env python

import logging
import argparse
import praw
import re
import yaml
import requests
from os import path
from sys import exit
from time import sleep
from AccountDetails import UID, PASS
from boardgamegeek import BoardGameGeek as BGG
import boardgamegeek

bot_name = 'r2d8'
log = logging.getLogger(bot_name)

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


header = '''
*^({} issues a series of sophisticated bleeps and whistles...)*

'''.format(bot_name)

footer = '''

-------------
^({} is a bot. Looks a little like a trash can, but you shouldn't hold that against him.)
[^Submit ^questions, ^abuse, ^and ^bug ^reports ^here.](/r/r2d8)
'''.format(bot_name)

def handle_getinfo(comment):
    bgg = BGG()
    infos = []
    gids = []
    game_iter = re.finditer('\*\*([^\*]+)\*\*', comment.body)
    game_count = sum(1 for _ in game_iter)
    min_mode = True if game_count >= 10 else False
    if min_mode:
        log.debug('in min mode {} games referenced'.format(game_count))
        infos.append('BGG Links for referenced games:\n\n')
    else:
        log.debug('in normal mode {} games referenced'.format(game_count))

    for m in re.finditer('\*\*([^\*]+)\*\*', comment.body):
        log.info('asking BGG for info on {}'.format(m.group(1)))
        try:
            titles = [title for title in bgg.search(m.group(1)) if title.type=='boardgame' and title.name == m.group(1)]
            log.debug('titles: {}'.format(titles))
            games = [bgg.game(name=None, game_id=t.id) for t in titles]
            games.sort(key=lambda g: g.year)
            games.reverse()
        except boardgamegeek.exceptions.BoardGameGeekError:
            log.error('Error getting info from BGG on {}'.format(m.group(1)))
            continue

        for game in games:                            
            if game.id not in gids:
                log.debug('found game {} ({})'.format(game.name.encode('utf-8'), game.year))
                if min_mode:
                    info = ' * [{}](http://boardgamegeek.com/boardgame/{})'.format(
                        game.name.encode('utf-8'), game.id)
                else:
                    info = 'Details about [**{}**](http://boardgamegeek.com/boardgame/{}):'.format(
                        game.name.encode('utf-8'), game.id)
                    info += '\n\n'
                    info += ' * Released in {}\n'.format(game.year)
                    data = ', '.join(getattr(game, 'designers', 'Unknown'))
                    info += ' * Designed by {}\n'.format(data.encode('utf-8'))
                    data = ', '.join(getattr(game, 'mechanics', 'not listed'))
                    info += ' * Mechanics: {}\n'.format(data.encode('utf-8'))
                    info += ' * Average rating is {}; rated by {} people\n'.format(
                        game.rating_average, game.users_rated)
                    for rank in game.ranks:
                        info += ' * {}: {}\n'.format(rank['friendlyname'], rank['value'])
                    info += ('\nMore information can be found on the [{} page on BGG]'
                             '(http://boardgamegeek.com/boardgame/{})'.format(game.name.encode('utf-8'), game.id))
                    info += '\n\n'

                log.debug('adding info: {}'.format(info))
                infos.append(info)
                gids.append(game.id)

    if len(infos):
        if not min_mode:
            comment.reply(header + '-----\n'.join([i for i in infos]) + footer)
        else:
            comment.reply(header + '\n'.join([i for i in infos]) + footer)

        log.info('Replied to info request for comment {}'.format(comment.id))


def handle_xyzzy(comment):
    comment.reply('Nothing happens.')


def handle_help(comment):
    pass

if __name__ == "__main__":
    p = argparse.ArgumentParser(prog='r2d6')
    p.add_argument("-u", "--user", help='Reddit account to run the bot as.')
    p.add_argument("-p", "--password", help='password for reddit account')
    p.add_argument('-s', '--subreddit', help='Subreddit to listen to. Can be specified'
                   ' multiple times. Default is "boardgames"', default='boardgames')
    p.add_argument('-c', '--config', help='Path to configuration/history file.', 
                   default=path.join('.', '{}.config'.format(bot_name)))
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
        'getinfo': handle_getinfo,
        'help': handle_help,
        'xyzzy': handle_xyzzy,
    }

    reddit = praw.Reddit('{} - boardgame util bot, v 0.1'.format(bot_name))
    reddit.login(username=user, password=password)
    subreddit = reddit.get_subreddit(args.subreddit)

    if path.exists(args.config):
        conf = yaml.safe_load(file(args.config, 'r'))
    else:
        conf = {}
        conf['scanned_comments'] = []

    attn = '!{}'.format(bot_name)
    while True:
        try:
            for comment in subreddit.get_comments(limit=None):
                cid = comment.id.encode('utf-8')
                log.debug('read comment {}'.format(cid))
                if cid not in conf['scanned_comments']:
                    log.info('scanning comment {}'.format(cid))
                    conf['scanned_comments'].append(cid)
                    if attn in comment.body.lower():
                        cmd = comment.body[comment.body.find(attn):].split()[1]
                        log.info('found command {}'.format(cmd))
                        if cmd in commands.keys():
                            log.debug('executing cmd {}'.format(cmd))
                            commands[cmd](comment)

        except (praw.errors.APIException,
                praw.errors.ClientException,
                requests.HTTPError) as e:
            log.error('Caught exception: {}'.format(e))

        # this may be a bad idea, but when else to save state?
        with open(args.config, 'w') as fd:
            fd.write(yaml.dump(conf, default_flow_style=True))

        sleep(60)

