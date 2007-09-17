#!/usr/bin/python

import os, sys

import settings, group

def fix_index(g):
    if not g.lockfile.trylock():
        print g.name + " locked"
        return

    try:
        index = g.load_eval("index", {})

        # XXX might need to generate index if it didn't exist
        g.saferemove("index")

        actual_arts = set(g.article_numbers())

        # remove index entries for missing articles
        for (id, art) in index.items():
            if art not in actual_arts:
                print "Removing index entry for missing article %s" % art
                del index[id]

        # add missing index entries:
        for art in actual_arts.difference(index.values()):
            print "Adding index entry for article %s" % art
            index[g.article(art).entry['message_id']] = art

        g.save("index", repr(index))
    finally:
        g.lockfile.unlock()

for arg in sys.argv[1:]:
    fix_index(group.Group(arg))
