#!/usr/bin/python
#
# An administration tool for pnntprss.  Currently can only display
# group data.

import sys, time
import group

def english_interval(val):
    """Convert an interval expressed as a number of seconds to a
    human-readable string."""
    val = int(val)
    str = ''
    for (noun, div) in (('second', 60), ('minute', 60), ('hour', 24),
                        ('day', 365), ('year', 1000)):
        r = val % div
        val = val / div
        if r:
            str = '%d %s%s%s%s' % (r, noun, r > 1 and 's' or '',
                                   str and ', ' or '', str)
    return str

props = [('href', 'Feed URI'),
         ('link', 'Feed page URI'),
         ('interval', 'Poll interval', english_interval),
         ('lastpolled', 'Last successful poll time',
          lambda s: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s))),
         ('article_lifetime', 'Article lifetime', english_interval)]

def display_group(g):
    """Print the properties of the given group in a readable form."""
    config = g.config
    for prop in props:
        if prop[0] in config:
            func = lambda x: x
            if len(prop) == 3:
                func = prop[2]

            print prop[1] + ':', func(config[prop[0]])

for arg in sys.argv[1:]:
    display_group(group.Group(arg))
