#!/usr/bin/python

import sys

import group

def wipe(group):
    (lo, hi, count) = group.article_range()
    for art in range(lo, hi+1):
        group.saferemove(str(art))

    group.saferemove('index')

    config = group.config
    newconfig = {}
    for k in ['href']:
        newconfig[k] = config[k]

    group.save("config", repr(newconfig))

wipe(group.Group(sys.argv[1]))
