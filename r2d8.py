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
logging.getLogger("requests").setLevel(logging.WARNING)

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

common_abbrv = {
    'Dead of Winter': 'Dead of Winter: A Crossroads Game',
    'Pathfinder': 'Pathfinder Adventure Card Game: Rise of the Runelords - Base Set'
}

def handle_getinfo(comment, bgg):
    bolded = [m.group(1).encode('utf-8') for m in re.finditer('\*\*([^\*]+)\*\*', comment.body)]
    games = []
    not_found = []
    min_mode = False

    for game_name in bolded:
        if game_name in common_abbrv.keys():
            game_name = common_abbrv[game_name]

        log.info('asking BGG for info on {}'.format(game_name))
        try:
            games_of_this_name = []
            for title in bgg.search(game_name):
                if title.type == 'boardgame':
                    if title.name == game_name:
                        # search returns a game even if the alternate game name is the name.
                        tmp_game = bgg.game(name=None, game_id=title.id)
                        if tmp_game.name.encode('utf-8') == game_name:
                            games_of_this_name.append(bgg.game(name=None, game_id=title.id))

            games_of_this_name.sort(key=lambda g: g.year, reverse=True)
            games += games_of_this_name

        except boardgamegeek.exceptions.BoardGameGeekError:
            log.error('Error getting info from BGG on {}'.format(game_name))
            continue

    # we now have all the games. 
    min_mode = True if len(games) > 6 else False
    not_found = list(set(bolded) - set([game.name for game in games]))
    not_found = [g for g in not_found if g not in common_abbrv.keys()]

    if not_found:
        log.debug('not found: {}'.format(', '.join(not_found)))

    infos = []
    for game in games:                            
        log.debug('found game {} ({})'.format(game.name.encode('utf-8'), game.year))
        if min_mode:
            info = (' * [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    ' ({}) by {}'.format(game.name.encode('utf-8'), game.id, game.year,
                                          ', '.join(getattr(game, 'designers', 'Unknown')).encode('utf-8')))
        else:
            info = ('Details about [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    ' ({}) by {}\n\n'.format(game.name.encode('utf-8'), game.id, game.year,
                                          ', '.join(getattr(game, 'designers', 'Unknown')).encode('utf-8')))
            data = ', '.join(getattr(game, 'mechanics', 'not listed'))
            info += ' * Mechanics: {}\n'.format(data.encode('utf-8'))
            people = 'people' if game.users_rated > 1 else 'person'
            info += ' * Average rating is {}; rated by {} {}\n'.format(
                game.rating_average, game.users_rated, people)
            data = ', '.join(['{}: {}'.format(r['friendlyname'], r['value']) for r in game.ranks])
            info += ' * {}\n\n'.format(data)

        log.debug('adding info: {}'.format(info))
        infos.append(info)

    if not_found:
        infos.append('Bolded items not found at BGG: {}\n\n'.format(', '.join(not_found)))

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
    p.add_argument('-C', '--cache', help='path tp SQL file used for cache.')
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

    reddit = praw.Reddit('{} - boardgame util bot, v 0.1'.format(bot_name))
    reddit.login(username=user, password=password)
    subreddit = reddit.get_subreddit(args.subreddit)

    if path.exists(args.config):
        conf = yaml.safe_load(file(args.config, 'r'))
        log.info('read in config {}'.format(args.config))
    else:
        conf = {}
        conf['scanned_comments'] = []

    if args.cache:
        bgg = BGG(cache='sqlite://{}?ttl=86400'.format(args.cache))
    else:
        bgg = BGG()

    attn = '!{} getinfo'.format(bot_name)
    while True:
        try:
            # for comment in subreddit.get_comments(limit=None):
            for comment in praw.helpers.comment_stream(reddit, args.subreddit, limit=None):
                cid = comment.id.encode('utf-8')
                log.debug('read comment {}'.format(cid))
                if cid not in conf['scanned_comments']:
                    log.info('scanning comment {}{}'.format(comment.link_url.encode('utf-8'), cid))
                    conf['scanned_comments'].append(cid)
                    if attn in comment.body.lower():
                        if '[deleted]' == comment.link_author.encode('utf-8'):
                            log.debug('skipping deleted comment')
                        else:
                            log.debug('executing getinfo')
                            handle_getinfo(comment, bgg)

                # this may be a bad idea, but when else to save state?
                with open(args.config, 'w') as fd:
                    log.debug('writing config file')
                    fd.write(yaml.dump(conf, default_flow_style=True))

        except (praw.errors.APIException,
                praw.errors.ClientException,
                requests.HTTPError) as e:
            log.error('Caught exception: {}'.format(e))
