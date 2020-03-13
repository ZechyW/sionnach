"""
Logging configuration
"""
import datetime
import logging

from sionnach import config


def get_gmt8(timestamp):
    """
    Returns a struct_time for the given time in SGT (GMT+8)
    :param timestamp:
    :return:
    """
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.fromtimestamp(timestamp, tz=tz).timetuple()


def logger(name):
    return logging.getLogger(name)


# On import, configure the root logger (which will affect subsequent logger calls)
root_logger = logging.getLogger()
if config.debug:
    root_logger.setLevel(logging.DEBUG)
else:
    root_logger.setLevel(logging.INFO)

# Default message format
root_logger.handlers = []

formatter = logging.Formatter(
    # "[%(asctime)s] [%(levelname)s:%(name)s] %(message)s"
    "[%(asctime)s][%(name)15s][%(levelname)5s] %(message)s"
)
formatter.converter = get_gmt8
formatter.datefmt = "%Y-%m-%d %H:%M:%S"

console_handler = logging.StreamHandler()

console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)
