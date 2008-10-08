#!/usr/bin/python

import os, sys

import settings, group

def fix_index(g):
    if not g.lockfile.trylock():
        print g.name + " locked"
        return

    try:
        print "Examining " + g.name
        id_to_arts = {}
        for art in g.article_numbers():
            id = g.article(art).entry['message_id']
            id_to_arts.setdefault(id, set()).add(art)

        index = {}
        dangling_arts = []
        for id in id_to_arts:
            arts = sorted(id_to_arts[id])
            index[id] = arts[0]
            dangling_arts.extend(arts[1:])

        if dangling_arts:
            print "Renaming %d dangling articles" % len(dangling_arts)
            for art in dangling_arts:
                art = str(art)
                os.rename(g.group_file(art), g.group_file("dangling-"+art))

        g.save("index", repr(index))
    finally:
        g.lockfile.unlock()

for arg in sys.argv[1:]:
    fix_index(group.Group(arg))
