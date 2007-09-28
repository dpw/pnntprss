#!/usr/bin/python
#
# Create a new group, subscribing to its feed.
#
# This functionality should be rolled into admin.py

import sys, os, os.path

import group, guessfeedurl

if len(sys.argv) < 3:
    print sys.argv[0] + " <group name> <feed url>"
else:
    (name, url) = sys.argv[1:]
    url = guessfeedurl.guess_feed_url(url)
    if url:
        print "Using feed url " + url
    
        path = group.group_path(name)
        if not os.path.isdir(path):
            os.mkdir(path)

        g = group.Group(name)
        g.lockfile.trylock()
        g.config['href'] = url
        g.save_config()
        g.lockfile.unlock()
    else:
        print "Couldn't find feed url"
