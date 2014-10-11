import praw
import requests
import logging
import signal
from time import sleep
from Queue import Queue, Empty
from threading import Thread, Event

log = logging.getLogger(__name__)

def _redditBotSignalHandler(signum, frame):
    RedditBot._doexit = True

class RedditBot(object):
    _doexit = False
    def __init__(self, name, userAgent, uid, passwd):
        self.uid = uid
        self.passwd = passwd
        self.userAgent = userAgent
        self.name = name
        self.reddit = None

    def connect(self):
        if not self.reddit:
            log.info('connecting to reddit with uid {}'.format(self.uid))
            self.reddit = praw.Reddit(self.userAgent)
            self.reddit.login(username=self.uid, password=self.passwd)

    def UID(self):
        return self.uid

    def get_comments_to_scan(self, subreddits=None, mentions=True):
        '''get_comments_to_scan creates a number of threads to read comments from the 
        given subreddits and notifications of username mentions.'''
        # helper thread class to read from a single content generator
        class _consumer(Thread):
            def __init__(self, queue, waitTime, source, *source_args):
                super(_consumer, self).__init__()
                self._stop = Event()
                self._queue = queue
                self._source = source
                self._source_args = source_args
                self._sleep = waitTime
                self.exit = False

            def stop(self):
                self._stop.set()

            def run(self):
                while True:
                    for item in self._source(*self._source_args):
                        self._queue.put(item)
                        if self._stop.isSet():
                            return
                    if self._sleep:
                        sleep(self._sleep)
    
        queue = Queue()
        consumers = list()
        if subreddits:
            multi_reddits = self.reddit.get_subreddit('+'.join(subreddits))
            consumers.append(_consumer(queue, 0, praw.helpers.comment_stream, self.reddit, multi_reddits))
        
        if mentions:
            consumers.append(_consumer(queue, 2, self.reddit.get_mentions))

        if not consumers:
            log.error('RedditBot has nothing to scan for comments.')
            return

        # set up signal handling to cleanly stop threads.
        orig_signals = list()
        for s in [signal.SIGQUIT, signal.SIGINT]:
            orig_signals.append((s, signal.signal(s, _redditBotSignalHandler)))

        # start comsuming threads.
        for c in consumers:
            c.daemon = True
            c.start()

        while True:
            try:
                item = queue.get(block=False, timeout=2)
            except Empty:
                if RedditBot._doexit:
                    # reset signals then tell threads to exit and wait for them to do so.
                    for s in orig_signals:
                        signal.signal(s[0], s[1])

                    log.info('got signal, RedditBot and consume threads exiting.')
                    [c.stop() for c in consumers]
                    [c.join() for c in consumers]
                    break
                else:
                    continue
            
            # actually give the comment to the caller
            yield item


if __name__ == '__main__':
    '''Just dump comments from subreddits and user mentions to stdout.'''
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG)
    from BotConfig import UID, PASSWD, subreddits, botName
    rb = RedditBot(botName, '{} test v0.1'.format(botName), UID, PASSWD)
    rb.connect()
    for comment in rb.get_comments_to_scan(subreddits=subreddits, mentions=True):
        print('read item ({}): {}'.format(type(comment), comment))
