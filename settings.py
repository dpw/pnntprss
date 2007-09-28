# pnntprss global settings

import os, os.path

# The base directory of pnntprss data
base_dir = os.path.join(os.environ['HOME'], ".pnntprss")

# The directory containing group data
groups_dir = os.path.join(base_dir, "groups")

# default feed polling interval
feed_poll_interval = 1800

# how long an article lives for.  may be overridden in group config.
# None means forever
article_lifetime = None

# user-agent string
user_agent = "pnntprss/0.01 +http://david.wragg.org/pnntprss/"

# how many feeds to retrieve concurrently when polling all feeds
feed_poll_concurrency = 4

# Logging settings
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=os.path.join(base_dir, "log"))

def log_to_stderr():
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger('').addHandler(console)

def get_logger(name):
    return logging.getLogger(name)

