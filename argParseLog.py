import logging

log = logging.getLogger(__name__)


def handleLoggingArgs(args):
    logLevels = {
       u'none': 100,
       u'all': 0,
       u'debug': logging.DEBUG,
       u'info': logging.INFO,
       u'warning': logging.WARNING,
       u'error': logging.ERROR,
       u'critical': logging.CRITICAL
    }
    log_format = u'%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    log_datefmt = u'%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format, datefmt=log_datefmt,
                        level=logLevels[args.loglevel])


def addLoggingArgs(ap):
    ap.add_argument("-l", "--loglevel", dest="loglevel",
                    help="The level at which to log. Must be one of "
                    "none, debug, info, warning, error, or critical. Default is none. ("
                    "This is mostly used for debugging.)",
                    default='none', choices=['none', u'all', u'debug', u'info', u'warning',
                                             u'error', u'critical'])
