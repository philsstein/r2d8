#!/usr/bin/env python

import logging
import re
import yaml
from random import choice
from os import getcwd
from os.path import join as pjoin
from boardgamegeek import BoardGameGeek as BGG
import boardgamegeek

log = logging.getLogger(__name__)


class CommentHandler(object):
    def __init__(self, UID, botdb):
        self._botdb = botdb
        self._botname = UID
        self._header = '*^({} issues a series of sophisticated bleeps and whistles...)*\n\n'.format(self._botname)
        self._footer = ('\n\n'
                        '-------------\n'
                        '^({} is a bot. Looks a little like a trash can, but you shouldn\'t hold that against him.)'
                        '[^Submit ^questions, ^abuse, ^and ^bug ^reports ^here.](/r/r2d8)'.format(self._botname))

        self._gameNameMap = {
            'Dead of Winter': 'Dead of Winter: A Crossroads Game',
            'Pathfinder': 'Pathfinder Adventure Card Game: Rise of the Runelords - Base Set',
            'Descent 2': 'Descent: Journeys in the Dark (Second Edition)',
            'Seven Wonders': '7 Wonders',
            'Caverna': 'Caverna: The Cave Farmers'
        }

        dbpath = pjoin(getcwd(), '{}-bgg.db'.format(self._botname))
        self._bgg = BGG(cache='sqlite://{}?ttl=86400'.format(dbpath))

    def getInfo(self, comment):
        body = comment.body.encode('utf-8')
        bolded = [b for b in re.findall('\*\*([^\*]+)\*\*', body)]

        if not bolded:
            log.warn('Got getinfo command, but nothing is bolded. Ignoring comment.')
            log.debug('comment was: {}'.format(body))
            return

        # filter out dups.
        bolded = list(set(bolded))
        games = []
        not_found = []

        if comment.subreddit.display_name.lower() == 'boardgamescirclejerk':
            old_bolded = bolded[:]
            bolded = choice([
                ['Dead of Winter: A Crossroads Game'],
                ['Ginkgopolis'],
                ['Machi Koro']
            ])

        for game_name in bolded:
            if game_name in self._gameNameMap.keys():
                game_name = self._gameNameMap[game_name]
    
            log.info('asking BGG for info on {}'.format(game_name))
            try:
                games_of_this_name = []
                for title in self._bgg.search(game_name):
                    if title.type == 'boardgame':
                        if title.name == game_name:
                            # search returns a game even if the alternate game name is the name.
                            tmp_game = self._bgg.game(name=None, game_id=title.id)
                            if tmp_game.name.encode('utf-8') == game_name:
                                games_of_this_name.append(self._bgg.game(name=None,
                                                                         game_id=title.id))
   
                if games_of_this_name:
                    games_of_this_name.sort(key=lambda g: g.year, reverse=True)
                    games += games_of_this_name
    
            except boardgamegeek.exceptions.BoardGameGeekError:
                log.error('Error getting info from BGG on {}'.format(game_name))
                continue
    
        # we now have all the games. 
        mode = 'short' if len(games) > 6 else None
        not_found = list(set(bolded) - set([game.name for game in games]))
        not_found = [g for g in not_found if g not in self._gameNameMap.keys()]

        if comment.subreddit.display_name.lower() == 'boardgamescirclejerk':
            not_found = old_bolded[:]

        if not_found:
            log.debug('not found: {}'.format(', '.join(not_found)))

        if games:
            log.debug('Found games {}'.format(','.join(['{} ({})'.format(
                game.name.encode('utf-8'), game.year) for game in games])))
        else:
            log.warn('Found no games in comment {}'.format(comment.id))
            return 

        # get the information for each game in a nice tidy list of strings.
        # get the mode if given. Can be short or long or normal. Default is normal.
        m = re.search('getinfo\s(\w+)', body)
        if m:
            mode = m.group(1) if m.group(1) in ['short', 'long'] else mode

        if mode == 'short':
            infos = self._getShortInfos(games)
        elif mode == 'long':
            infos = self._getLongInfos(games)
        else:
            infos = self._getStdInfos(games)

        # append not found string if we didn't find a bolded string.
        if not_found:
            not_found = ['[{}](http://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q={}&B1=Go)'.format(
                n, n) for n in not_found]
            if mode == 'short':
                infos.append('\n\n-----\nBolded items not found at BGG: {}\n\n'.format(
                    ', '.join(not_found)))
            else:
                infos.append('Bolded items not found at BGG: {}\n\n'.format(', '.join(not_found)))

        if len(infos):
            if mode == 'short':
                comment.reply(self._header + '\n'.join([i for i in infos]) + self._footer)
            else:
                comment.reply(self._header + '-----\n'.join([i for i in infos]) + self._footer)

            log.info('Replied to info request for comment {}'.format(comment.id))

    def _getShortInfos(self, games):
        infos = list()
        for game in games:                            
            infos.append(' * [**{}**](http://boardgamegeek.com/boardgame/{}) '
                         ' ({}) by {}'.format(game.name.encode('utf-8'), game.id, game.year,
                                              ', '.join(getattr(game, 'designers', 'Unknown')).encode('utf-8')))
        return infos

    def _getStdInfos(self, games):
        infos = list()
        for game in games:
            info = ('Details for [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    ' ({}) by {}\n\n'.format(game.name.encode('utf-8'), game.id, game.year,
                                             ', '.join(getattr(game, 'designers', 'Unknown')).encode('utf-8')))
            data = ', '.join(getattr(game, 'mechanics', ''))
            if data:
                info += ' * Mechanics: {}\n'.format(data.encode('utf-8'))
            people = 'people' if game.users_rated > 1 else 'person'
            info += ' * Average rating is {}; rated by {} {}\n'.format(
                game.rating_average, game.users_rated, people)
            data = ', '.join(['{}: {}'.format(r['friendlyname'], r['value']) for r in game.ranks])
            info += ' * {}\n\n'.format(data)
    
            log.debug('adding info: {}'.format(info))
            infos.append(info)
    
        return infos

    def _getLongInfos(self, games):
        infos = list()
        for game in games:
            info = ('Details about [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    ' ({}) by {}\n\n'.format(game.name.encode('utf-8'), game.id, game.year,
                                             ', '.join(getattr(game, 'designers', 'Unknown')).encode('utf-8')))
            data = ', '.join(getattr(game, 'mechanics', ''))
            if data:
                info += ' * Mechanics: {}\n'.format(data.encode('utf-8'))
            people = 'people' if game.users_rated > 1 else 'person'
            info += ' * Average rating is {}; rated by {} {}\n'.format(
                game.rating_average, game.users_rated, people)
            data = ', '.join(['{}: {}'.format(r['friendlyname'], r['value']) for r in game.ranks])
            info += ' * {}\n\n'.format(data)
   
            info += 'Description:\n\n{}\n\n'.format(game.description.encode('utf-8'))

            log.debug('adding info: {}'.format(info))
            infos.append(info)

        return infos

    def repairComment(self, comment):
        commet.reply('not yet implemented')

    def xyzzy(self, comment):
        comment.reply('Nothing happens.')

