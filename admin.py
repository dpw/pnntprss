#!/usr/bin/python
#
# An administration tool for pnntprss.  Currently can only display
# group data.

import sys, time, optparse

import group, guessfeedurl, english

props = [('href', 'Feed URI'),
         ('link', 'Feed homepage URI'),
         ('interval', 'Poll interval', english.describe_interval),
         ('lastpolled', 'Last successful poll time',
          lambda s: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s))),
         ('article_lifetime', 'Article lifetime', english.describe_interval)]

def display_group(g):
    """Print the properties of the given group in a readable form."""
    config = g.config
    for prop in props:
        if prop[0] in config:
            func = lambda x: x
            if len(prop) == 3:
                func = prop[2]

            print prop[1] + ':', func(config[prop[0]])


def error(msg):
    print >>sys.stderr, msg
    sys.exit(1)

parser = optparse.OptionParser()
parser.add_option('-a', '--add-group', action='store_true')
parser.add_option('-u', '--uri')
parser.add_option('-l', '--article-lifetime')
(opts, args) = parser.parse_args()

config = {}

if opts.uri:
    print >>sys.stderr, "Checking feed..."
    config['href'] = guessfeedurl.guess_feed_url(opts.uri)
    if config['href'] is None:
        error("Could not find a valid feed at %s" % opts.uri)
elif opts.article_lifetime:
    config['article_lifetime'] = english.parse_interval(opts.article_lifetime)

if opts.add_group:
    if len(args) != 1:
        error("There should be exactly one group name")
    if opts.uri is None:
        error("Feed URI not specified")
    group.create_group(args[0], config)
elif config:
    for arg in args:
        g = group.load_group(arg)
        g.config.update(config)
        g.save_config()
elif len(args) == 0:
    # with no args, list all groups
    for g in group.groups():
        print g.name
else:
    # display specified groups
    for arg in args:
        display_group(group.load_group(arg))
