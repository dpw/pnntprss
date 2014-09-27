#!/usr/bin/python
#
# Routines for generating and parsing english-language representations
# of various things.

import re

def describe_interval(val):
    """Convert an interval expressed as a number of seconds to a
    human-readable string.

    >>> describe_interval(0)
    '0 seconds'
    >>> describe_interval(1)
    '1 second'
    >>> describe_interval(60)
    '1 minute'
    >>> describe_interval(60 + 1)
    '1 minute, 1 second'
    >>> describe_interval(60 * 60)
    '1 hour'
    >>> describe_interval(60 * 60 + 1)
    '1 hour, 1 second'
    >>> describe_interval(24 * 60 * 60)
    '1 day'
    >>> describe_interval(365 * 24 * 60 * 60)
    '1 year'
    """

    if val == 0:
        return "0 seconds"

    str = ''
    for (unit, div) in (('second', 60), ('minute', 60), ('hour', 24),
                        ('day', 365), ('year', 1000)):
        r = val % div
        val = val / div
        if r:
            str = '%d %s%s%s%s' % (r, unit, r > 1 and 's' or '',
                                   str and ', ' or '', str)
    return str


unit_dict = {'second': 1,
             'minute' : 60,
             'hour' : 60 * 60,
             'day' : 24 * 60 * 60,
             'year' : 365 * 24 * 60 * 60}

singular = dict((n+'s', n) for n in ['second', 'minute', 'day', 'year'])

def parse_interval(s):
    """Convert an english string describing an interval into a number of
    seconds.
    
    >>> parse_interval('0 seconds')
    0
    >>> parse_interval('1 minute, 1 second')
    61
    """
    
    words = re.split('\W+', s)
    if not words or len(words) % 2 != 0:
        raise ValueError("number of words not even")
    
    def unit_multiplier(n):
        n = singular.get(n, n)
        # XXX check used
        return unit_dict.get(n)

    return sum((int(n) * unit_multiplier(unit)
                for n, unit in zip(words[0::2], words[1::2])))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
