import logging, logging.handlers, os, os.path
from piccolo.config import LOGGING
from piccolo.commands.colors import *

class ColorFormatter(logging.Formatter):
    def format(self, record):
        formatted = logging.Formatter.format(self, record)
        if record.levelno <= logging.DEBUG:
            output = formatted
        elif record.levelno <= logging.INFO:
            output = cyan(formatted)
        elif record.levelno <= logging.WARNING:
            output = yellow(formatted)
        elif record.levelno <= logging.ERROR:
            output = red(formatted)
        else:
            output = white(magentabg(formatted))
        return output

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create file handler and set to warning
fh = logging.handlers.RotatingFileHandler(
    os.path.join(LOGGING['directory'], 'piccolo.log'),
    maxBytes=LOGGING['max_size']*1024*1024, # convert megabytes -> bytes
    backupCount=LOGGING['retain_count'])
fh.setLevel(logging.WARNING)

# create formatters
color_formatter = ColorFormatter(bright('[%(levelname)s]') + ' %(message)s')
plain_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s')

# add formatters to handlers
ch.setFormatter(color_formatter)
fh.setFormatter(plain_formatter)

# add ch, fh to logger
logger.addHandler(ch)
logger.addHandler(fh)