#!/usr/bin/python
#
# Polls feeds.
#
# This is intended to be run frequently from a cron job (once every
# few minutes).  It obeys the poll interval set for each feed, so
# running it too frequently will not change how often we contact a
# feed server.
#
# When run with no arguments, polls all feeds that should be checked.
# Otherwise, polls the feeds specfiied by the group names given as
# arguments.

import sys, time, hashlib, os, socket, traceback, resource
import feedparser

import settings, lockfile, group

# use a socket timeout of 20 seconds
socket.setdefaulttimeout(20)

logger = settings.get_logger('pnntprss.update')

def restrict(d, keys):
    res = {}
    for k in keys:
        if k in d:
            res[k] = d[k]

    return res

state_keys = ['etag', 'modified']
feed_info_keys = 'title title_detail link links subtitle subtitle_detail rights rights_detail id author author_detail'.split(' ')
entry_struct_time_keys = [x+'_parsed' for x in 'published updated created expired'.split(' ')]

def stable_repr(val):
    t = type(val)
    if t == list:
        return '[' + ', '.join(map(stable_repr, val)) + ']'
    elif t == tuple:
        return '(' + ', '.join(map(stable_repr, val)) + ')'
    elif t == dict:
        return '{' + ', '.join(sorted([stable_repr(x) + ': ' + stable_repr(y)
                                       for (x,y) in val.iteritems()])) + '}'
    else:
        return repr(val)

def transform(v, f):
    v = f(v)
    if isinstance(v, dict):
        for k in v:
            v[k] = transform(v[k], f)
    elif isinstance(v, list):
        for i in range(0, len(v)):
            v[i] = transform(v[i], f)
    elif isinstance(v, tuple):
        return tuple(transform(x, f) for x in v)

    return v

def fix_unicode_keys(d):
    if isinstance(d, dict):
        for k in ('type', 'rel'):
            if k in d:
                v = d[k]
                if type(v) == unicode:
                    d[k] = v.encode('utf-8')

    return d

def cputime():
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return ru.ru_utime + ru.ru_stime

def update_if_ready(g):
    if not g.ready_to_check(time.time()):
        return

    if not g.lockfile.trylock():
        # we are already updating, expiring, or otherwise messing with
        # this group.  No problem, we'll try again next time round.
        return

    try:
        logger.debug("Checking " + g.name)

        # group info could have changed by the time we locked
        g.reload_config()

        startt = cputime()
        try:
            update_group_from_feed(g,
                            feedparser.parse(g.config['href'],
                                             agent=settings.user_agent,
                                             **restrict(g.config, state_keys)))
            for k in ("last_failed_poll", "failed_polls"):
                if k in g.config:
                    del g.config[k]
        except:
            g.config["last_failed_poll"] = time.time()
            g.config["failed_polls"] = g.config.get("failed_polls", 0) + 1
            g.save_config()
            raise

        dt = cputime() - startt
        if dt > 1:
            logger.info("Updating from %s took unusually long (%s CPU seconds)" % (g.name, dt))
    finally:
        g.lockfile.unlock()

def update_group_from_feed(g, feed):
    try:
        # for debugging
        g.save("feed", repr(feed))

        if feed.bozo:
            if feed.get('status'):
                # we have a feed, but it's bozotic
                logger.warning("%s: bozo: %s" % (g.name, feed.bozo_exception))
            else:
                # no feed, give up
                raise feed.bozo_exception
    
        now = time.time()
        config = g.config
        config["lastpolled"] = now

        state = restrict(feed, state_keys)

        config.update(state)
        config.update(restrict(feed['feed'], feed_info_keys))
        
        if feed.status == 301:
            # permanent redirect.  update config
            config['href'] = feed.href

        # coerce struct_time to a tuple
        feed_updated_parsed = tuple(feed.get('updated_parsed')
                                    or time.gmtime(now))

        if 'entries' in feed and len(feed['entries']):
            index = g.load_eval("index", {})
    
            # XXX might need to generate index if it didn't exist
            g.saferemove("index")

            # entries are in reverse chronological order.  But we want
            # chronological order, to match article numbers
            for entry in reversed(feed.entries):
                # convert entry to true dict
                entry = dict(entry.iteritems())

                # feedparser version 5.x produces unicode string for
                # some entry values that were previously byte strings.
                # Convert them back so that we generate consistent ids
                # below.
                entry = transform(entry, fix_unicode_keys)

                # coerce struct_time fields to tuples
                for k in entry_struct_time_keys:
                    if k in entry:
                        entry[k] = tuple(entry[k])
                
                # some RSS feeds have ids, but they are empty!
                id = entry.get('id')
                if not id:
                    id = ', '.join(sorted([repr(x) + ': ' + repr(y) for (x,y) in entry.iteritems()]))

                # Normalize the id
                id = hashlib.md5(id.encode('utf-8')).hexdigest()
                entry['message_id'] = id
                num = index.get(id)
                action = "New"

                if num is not None:
                    a = g.article(num)
                    if a is not None:
                        if a.same_entry(entry):
                            continue

                        action = "Updated"
                    else:
                        num = None

                if num is None:
                    num = index[id] = g.next_article_number()

                # some feeds lack a updated time on entries, but we need
                # it for the date header.  Add a feed_updated_parsed value here.
                entry['feed_updated_parsed'] = feed_updated_parsed

                logger.info("%s article %s@%s (%s)"
                            % (action, id, g.name, num))
                g.save_article(num, entry)

            # XXX need to catch exceptions so we always save next art number
            g.save("index", repr(index))
    finally:
        g.save_config()

def run_tasks(tasks, concurrency):
    pids = {}

    def reap_one():
        (pid, status) = os.waitpid(-1, 0)
        if pid in pids:
            task = pids.pop(pid)
            if os.WIFEXITED(status):
                res = os.WEXITSTATUS(status)
                if res != 0:
                    logger.info("exit status %s: %s" % (res, task))
            else:
                logger.info("exit with signal %s: %s" % (os.WTERMSIG(status),
                                                         task))

    for task in tasks:
        while len(pids) >= concurrency:
            reap_one()
        
        pid = os.spawnvp(os.P_NOWAIT, task[0], task)
        pids[pid] = task

    while pids:
        reap_one()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            try:
                update_if_ready(group.Group(arg))
            except:
                logger.warning("%s: %s" % (arg, traceback.format_exc()))
    else:
        lock = lockfile.LockFile(os.path.join(settings.groups_dir, "update.lock"))
        if lock.trylock():
            try:
                def touching(l, it):
                    for x in it:
                        yield x
                        if not l.touch():
                            return
            
                now = time.time()
                run_tasks(touching(lock,((sys.argv[0], g.name)
                                         for g in group.groups()
                                         if g.ready_to_check(now))),
                          settings.feed_poll_concurrency)
            finally:
                lock.unlock()
