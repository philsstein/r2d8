#!/usr/bin/env python

import logging
import re
import yaml
from urllib2 import quote
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
        self._header = u'*^({} issues a series of sophisticated bleeps and whistles...)*\n\n'.format(self._botname)
        self._footer = (u'\n\n'
                        u'-------------\n'
                        u'^({} is a bot. Looks a little like a trash can, but you shouldn\'t hold that against him.) '
                        u'[^Submit ^questions, ^abuse, ^and ^bug ^reports ^here.](/r/r2d8)'.format(self._botname))

        dbpath = pjoin(getcwd(), u'{}-bgg.db'.format(self._botname))
        self._bgg = BGG(cache=u'sqlite://{}?ttl=86400'.format(dbpath))

    def _getInfoResponseBody(self, comment, mode=None):
        body = comment.body
        bolded = re.findall(u'\*\*([^\*]+)\*\*', body)

        if not bolded:
            log.warn(u'Got getinfo command, but nothing is bolded. Ignoring comment.')
            log.debug(u'comment was: {}'.format(body))
            return

        # convert aliases to real names. It may be better to do this after we don't find the 
        # game. Oh, well.
        for i in xrange(len(bolded)):
            real_name = self._botdb.get_name_from_alias(bolded[i])
            if real_name:
                bolded[i] = real_name
    
        # filter out dups.
        bolded = list(set(bolded))

        games = []
        not_found = []

        if comment.subreddit.display_name.lower() == u'boardgamescirclejerk':
            cjgames = [
                [u'Dead of Winter: A Crossroads Game'],
                [u'Ginkgopolis'],
                [u'Machi Koro']
            ]
            old_bolded = set(bolded) ^ set(cjgames)
            bolded = choice(cjgames)

        seen = set()
        for game_name in bolded:
            log.info(u'asking BGG for info on {}'.format(game_name))
            try:
                game = self._bgg.game(game_name)
                if game:
                    if not game.name in seen:
                        games.append(self._bgg.game(game_name))
                    # don't add dups. This can happen when the same game is calledby two valid
                    # names in a post. 
                    seen.add(game.name)   
                else:
                    not_found.append(game_name)

    
            except boardgamegeek.exceptions.BoardGameGeekError:
                log.error(u'Error getting info from BGG on {}'.format(game_name))
                continue
    
        # we now have all the games. 
        mode = u'short' if len(games) > 6 else mode
        # not_found = list(set(bolded) - set([game.name for game in games]))

        if comment.subreddit.display_name.lower() == u'boardgamescirclejerk':
            not_found = old_bolded

        if not_found:
            log.debug(u'not found: {}'.format(u', '.join(not_found)))

        if games:
            log.debug(u'Found games {}'.format(u','.join([u'{} ({})'.format(
                game.name, game.year) for game in games])))
        else:
            log.warn(u'Found no games in comment {}'.format(comment.id))

        # get the information for each game in a nice tidy list of strings.
        # get the mode if given. Can be short or long or normal. Default is normal.
        if not mode:
            m = re.search(u'getinfo\s(\w+)', body, flags=re.IGNORECASE)
            if m:
                mode = m.group(1).lower() if m.group(1).lower() in [u'short', u'long'] else mode

        if mode == u'short':
            infos = self._getShortInfos(games)
        elif mode == u'long':
            infos = self._getLongInfos(games)
        else:
            infos = self._getStdInfos(games)

        # append not found string if we didn't find a bolded string.
        if not_found:
            not_found = [u'[{}](http://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q={}&B1=Go)'.format(
                n, quote(n)) for n in not_found]
            if mode == u'short':
                infos.append(u'\n\n-----\nBolded items not found at BGG (click to search): {}\n\n'.format(
                   u', '.join(not_found)))
            else:
                infos.append(u'Bolded items not found at BGG (click to search): {}\n\n'.format(u', '.join(not_found)))

        response = None
        if len(infos):
            if mode == u'short':
                response = self._header + u'\n'.join([i for i in infos]) + self._footer
            else:
                response = self._header + u'-----\n'.join([i for i in infos]) + self._footer

        return response

    def getInfo(self, comment, replyTo=None, mode=None):
        '''Reply to comment with game information. If replyTo isot given reply to original else
        reply to given comment.'''
        response = self._getInfoResponseBody(comment, mode)
        if response:
            if replyTo:
                replyTo.reply(response)
            else:
                comment.reply(response)
            log.info(u'Replied to info request for comment {}'.format(comment.id))
        else:
            log.warn(u'Did not find anything to reply to in comment'.format(comment.id))

    def _getShortInfos(self, games):
        infos = list()
        for game in games:
            if game.min_players == game.max_players:
                players = '{} p'.format(game.min_players)
            else:
                players = '{}-{} p'.format(game.min_players, game.max_players)

            info = (u' * Details for [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    u' ({}) by {}. {}; {} mins'.format(
                        game.name, game.id, game.year, u', '.join(getattr(game, u'designers', u'Unknown')),
                        players, game.playing_time))
            infos.append(info)

        return infos

    def _getStdInfos(self, games):
        infos = list()
        for game in games:
            if game.min_players == game.max_players:
                players = '{} player{}'.format(game.min_players, 's' if game.min_players != 1 else '')
            else:
                players = '{}-{} players'.format(game.min_players, game.max_players)

            info = (u'Details for [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    u' ({}) by {}. {}; {} minutes\n\n'.format(
                        game.name, game.id, game.year, u', '.join(getattr(game, u'designers', u'Unknown')),
                        players, game.playing_time))
            data = u', '.join(getattr(game, u'mechanics', u''))
            if data:
                info += u' * Mechanics: {}\n'.format(data)
            people = u'people' if game.users_rated > 1 else u'person'
            info += u' * Average rating is {}; rated by {} {}\n'.format(
                game.rating_average, game.users_rated, people)
            data = u', '.join([u'{}: {}'.format(r[u'friendlyname'], r[u'value']) for r in game.ranks])
            info += u' * {}\n\n'.format(data)
    
            log.debug(u'adding info: {}'.format(info))
            infos.append(info)
   
        return infos

    def _getLongInfos(self, games):
        infos = list()
        for game in games:
            info = (u'Details about [**{}**](http://boardgamegeek.com/boardgame/{}) '
                    u' ({}) by {}'.format(game.name, game.id, game.year,
                                             u', '.join(getattr(game, u'designers', u'Unknown'))))
            info += u', {} - {} players, {} minutes\n\n'.format(game.min_players, game.max_players,
                                                             game.playing_time)
            data = u', '.join(getattr(game, u'mechanics', u''))
            if data:
                info += u' * Mechanics: {}\n'.format(data)
            people = u'people' if game.users_rated > 1 else u'person'
            info += u' * Average rating is {}; rated by {} {}\n'.format(
                game.rating_average, game.users_rated, people)
            data = u', '.join(['{}: {}'.format(r[u'friendlyname'], r[u'value']) for r in game.ranks])
            info += u' * {}\n\n'.format(data)
   
            info += u'Description:\n\n{}\n\n'.format(game.description)

            log.debug(u'adding info: {}'.format(info))
            infos.append(info)

        return infos

    def repairComment(self, comment):
        '''Look for maps from missed game names to actual game names. If 
        found repair orginal comment.'''
        # 
        # The repair is done by replacing the new games names with the old (wrong)
        # games names in the original /u/r2d8 response, then recreating the entire
        # post by regenerating it with the new (fixed) bolded game names. The just replacing
        # the orginal response with the new one.
        #
        log.debug(u'Got repair response, id {}'.format(comment.id))

        if comment.is_root:
            # error here - this comment should be in response to a u/r2d8 comment.
            log.info(u'Got a repair comment as root, ignoring.')
            return

        parent = comment.reddit_session.get_info(thing_id=comment.parent_id)
        if parent.author.name != self._botname:
            log.info(u'Parent of repair comment is not authored by the bot, ignoring.')
            return 

        # Look for patterns of **something**=**somethingelse**. This line creates a dict 
        # of something: somethingelse for each one pattern found. 
        repairs = {match[0]: match[1] for match in re.findall(
            u'\*\*([^\*]+)\*\*=\*\*([^\*]+)\*\*', comment.body)}
        
        pbody = parent.body
        for wrongName, repairedName in repairs.iteritems():
            # check to see if it's actually a game.
            log.info(u'Repairing {} --> {}'.format(wrongName, repairedName))
            alias = self._botdb.get_name_from_alias(repairedName)
            tmp_name = alias if alias else repairedName
            tmp_game = self._bgg.game(tmp_name)  # with caching it's ok to check twice
            if tmp_game:
                # In the parent body we want to replace [NAME](http://... with **NAME**(http://
                pbody = pbody.replace(u'[' + wrongName + u']', u'**' + tmp_name + u'**')
            else:
                log.info(u'{} seems to not be a game name according to BGG, ignoring.'.format(tmp_name))

        # Now re-bold the not found strings so they are re-searched or re-added to the not found list.
        for nf in re.findall(u'\[([\w|\s]+)]\(http://boardgamegeek.com/geeksearch.php', pbody):
            pbody += u' **{}**'.format(nf)

        # now re-insert the original command to retain the mode. 
        grandparent = parent.reddit_session.get_info(thing_id=parent.parent_id)
        modes = list()
        if not grandparent:
            log.error(u'Cannot find original GP post. Assuming normal mode.')
        else:
            modes = re.findall(u'[getparent|get]info\s(\w+)', grandparent.body)

        if modes:
            log.debug(u'Recreating {} mode from the GP.'.format(modes[0]))
            pbody += u' /u/{} getinfo {}'.format(self._botname, modes[0])
        else:
            pbody += u' /u/{} getinfo'.format(self._botname)

        parent = parent.edit(pbody)
        new_reply = self._getInfoResponseBody(parent)

        # should check for Editiable class somehow here. GTL
        log.debug(u'Replacing bot comment {} with: {}'.format(parent.id, new_reply))
        parent.edit(new_reply)

    def xyzzy(self, comment):
        comment.reply(u'Nothing happens.')

    def getParentInfo(self, comment):
        '''Allows others to call the bot to getInfo for parent posts.'''
        log.debug(u'Got getParentInfo comment in id {}'.format(comment.id))

        if comment.is_root:
            # error here - this comment should be in response to a u/r2d8 comment.
            log.info(u'Got a repair comment as root, ignoring.')
            return
    
        m = re.search(u'getparentinfo\s(\w+)', comment.body, re.IGNORECASE)
        mode = None
        if m:
            mode = u'short' if m.group(1).lower() == u'short' else u'long'

        parent = comment.reddit_session.get_info(thing_id=comment.parent_id)
        self.getInfo(parent, comment, mode)

    def alias(self, comment):
        '''add an alias to the database.'''
        if not self._botdb.is_admin(comment.author.name):
            log.info(u'got alias command from non admin {}, ignoring.'.format(
                comment.author.name))
            return

        response = u'executing alias command.\n\n'
        for match in re.findall(u'\*\*([^\*]+)\*\*=\*\*([^\*]+)\*\*', comment.body):
            mess = u'Adding alias to database: "{}" = "{}"'.format(match[0], match[1])
            log.info(mess)
            response += mess + u'\n\n'
            self._botdb.add_alias(match[0], match[1])

        comment.reply(response)

    def getaliases(self, comment):
        aliases = self._botdb.aliases()
        response = u'Current aliases:\n\n'
        for name, alias in sorted(aliases, key=lambda g: g[1]):
            response += u' * {} = {}\n'.format(alias, name)

        log.info(u'Responding to getalaises request with {} aliases'.format(len(aliases)))
        comment.reply(response)
