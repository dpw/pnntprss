import os, os.path

base_dir = os.path.join(os.environ['HOME'], ".pnntprss")
groups_dir = os.path.join(base_dir, "groups")

# default feed polling interval
feed_poll_interval = 1800

# how long an article lives for.  may be overridden in group config.
# None means forever
article_lifetime = None

import logging

logging.basicConfig(level=logging.INFO,
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

