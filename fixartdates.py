#!/usr/bin/python

import os, sys, time

import settings, group

def fix_index(g):
    if not g.lockfile.trylock():
        print g.name + " locked"
        return

    try:
        for art in g.articles():
            if 'feed_updated_parsed' not in art.entry:
                stat = os.stat(g.group_file(art.num))
                art.entry['feed_updated_parsed'] = time.gmtime(stat.st_mtime)
                print "Fixing %s (%s)" % (art.message_id(), art.num)
                g.save(str(art.num), repr(art.entry))
    finally:
        g.lockfile.unlock()

for arg in sys.argv[1:]:
    fix_index(group.Group(arg))
