#!/usr/bin/python
#
# An administration tool for pnntprss.  Currently can only display
# group data.

import sys, time, optparse, settings, update
from HTMLParser import HTMLParser

import group, english

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

# prefer atom links
class LinkParser(HTMLParser):
    type_goodness = {'application/rss+xml':1, 'application/atom+xml':2}

    def reset(self):
        HTMLParser.reset(self)
        self.href = None
        self.goodness = 0
        self.inbody = False

    def handle_starttag(self, tag, attrs):
        if not self.inbody and tag == 'link':
            a = dict(attrs)
            if a.get('rel') == 'alternate' and 'href' in a:
                goodness = LinkParser.type_goodness.get(a.get('type'), 0)
                if goodness > self.goodness:
                    self.goodness = goodness
                    self.href = a['href']
        else:
            if tag == 'body':
                self.inbody = True
        
        HTMLParser.handle_starttag(self, tag, attrs)

def find_feed(href, guess=True):
    import urllib2, urllib, urlparse, cStringIO, feedparser

    req = urllib2.Request(href)
    req.add_header('User-Agent', settings.user_agent)
    usock = urllib2.urlopen(req)
    content = usock.read()
    headers = usock.info()
    usock.close()

    # try to parse as a feed
    feed = None
    err = None
    try:
        feed = feedparser.parse(urllib.addinfourl(cStringIO.StringIO(content),
                                                  headers, href))
        if not feed.version:
            # doesn't look like a real feed
            feed = None
    except:
        err = sys.exc_info()

    if feed is None and guess:
        # try feed autodiscovery
        parser = LinkParser()
        try:
            parser.feed(content)
        except:
            pass
            #err = sys.exc_info()

        if parser.href:
            return find_feed(urlparse.urljoin(href, parser.href), guess=False)

    if feed is None and err:
        raise err[0], err[1], err[2]

    return feed

parser = optparse.OptionParser()
parser.add_option('-a', '--add-group', action='store_true')
parser.add_option('-d', '--delete-group', action='store_true')
parser.add_option('-u', '--uri')
parser.add_option('-l', '--article-lifetime')
(opts, args) = parser.parse_args()

config = {}
if opts.article_lifetime:
    config['article_lifetime'] = english.parse_interval(opts.article_lifetime)

if opts.uri:
    if len(args) != 1:
        error("There should be exactly one group name")

    feed = find_feed(opts.uri)
    if feed:
        config['href'] = feed['href']
        if opts.add_group:
            g = group.NewGroup(args[0], config)
            failed = True
            try:
                update.update_group_from_feed(g, feed)
                failed = False
                g.create()
            finally:
                if failed:
                    g.delete()
        else:
            g = group.Group(args[0])
            g.lockfile.lock()
            try:
                g.config.update(config)
                update.update_group_from_feed(g, feed)
            finally:
                g.lockfile.unlock()
    else:
        error("Could not find a valid feed at %s" % opts.uri)
elif opts.add_group:
    error("Feed URI not specified")
elif opts.delete_group:
    # delete groups
    for arg in args:
        g = group.Group(arg)
        g.delete()
elif config:
    # update groups
    for arg in args:
        g = group.Group(arg)
        g.lockfile.lock()
        try:
            g.config.update(config)
            g.save_config()
        finally:
            g.lockfile.unlock()
elif len(args) == 0:
    # with no args, list all groups
    for g in group.groups():
        print g.name
else:
    # display specified groups
    for arg in args:
        display_group(group.Group(arg))
