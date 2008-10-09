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

import sys, time, md5, types, os, socket, traceback
import feedparser

import settings, lockfile, group

# use a socket timeout of 20 seconds
socket.setdefaulttimeout(20)

logger = settings.get_logger('pnntprss.update')

def md5hex(s):
    return md5.new(s).hexdigest()

def restrict(d, keys):
    res = {}
    for k in keys:
        if k in d:
            res[k] = d[k]

    return res

state_keys = [ 'etag', 'modified' ]
feed_info_keys = [ 'title', 'title_detail', 'link', 'links',
                   'subtitle', 'subtitle_detail', 'rights', 'rights_detail',
                   'id', 'author', 'author_detail' ]

def stable_repr(val):
    t = type(val)
    if t == types.ListType:
        return '[' + ', '.join(map(stable_repr, val)) + ']'
    elif t == types.TupleType:
        return '(' + ', '.join(map(stable_repr, val)) + ')'
    elif t == types.DictType:
        return '{' + ', '.join(sorted([repr(x) + ': ' + repr(y) for (x,y) in val.iteritems()])) + '}'
    else:
        return repr(val)

def update_if_ready(g):
    if not g.ready_to_check(time.time()):
        return

    if not g.lockfile.trylock():
        # we are already updating, expiring, or otherwise messing with
        # this group.  No problem, we'll try again next time round.
        return

    try:
        logger.info("Checking " + g.name)

        # group info could have changed by the time we locked
        g.reload_config()

        update_group_from_feed(g, feedparser.parse(g.config['href'],
                                              agent=settings.user_agent,
                                              **restrict(g.config, state_keys)))
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
        config.update(restrict(feed, state_keys))
        config.update(restrict(feed['feed'], feed_info_keys))

        if feed.status == 301:
            # permanent redirect.  update config
            config['href'] = feed.href

        if 'entries' in feed and len(feed['entries']):
            index = g.load_eval("index", {})
    
            # XXX might need to generate index if it didn't exist
            g.saferemove("index")

            # entries are in reverse chronological order.  But we want
            # chronological order, to match article numbers
            for entry in reversed(feed.entries):
                # convert entry to true dict
                entry = dict(entry.iteritems())
            
                # some RSS feeds have ids, but they are empty!
                id = entry.get('id')
                if id:
                    id = md5hex(id)
                else:
                    stable_repr = ', '.join(sorted([repr(x) + ': ' + repr(y) for (x,y) in entry.iteritems()]))
                    id = md5hex(stable_repr)

                entry['message_id'] = id
            
                num = index.get(id)
                action = "New"
                if num is None:
                    num = index[id] = g.next_article_number()
                else:
                    if g.article(num).same_entry(entry):
                        continue
                    else:
                        action = "Updated"

                # some feeds lack a updated time on entries, but we need
                # it for the date header.  Add a feed_updated_parsed value here.
                fup = feed.feed.get('updated_parsed')
                if not fup:
                    fup = feed.get('modified')
                    if not fup:
                        fup = time.gmtime(now)
                    
                entry['feed_updated_parsed'] = fup
    
                logger.info("%s article %s@%s (%s)"
                            % (action, id, g.name, num))
                g.save(str(num), repr(entry))

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
