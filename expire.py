#!/usr/bin/python

# Go through all the groups, expiring articles that have exceeded
# their lifetime.

import os, time

import settings, group

logger = settings.get_logger('pnntprss.expire')

def expire(g):
    """Expire articles in the given group."""
    
    if not g.lockfile.trylock():
        # we are already updating, expiring, or otherwise messing with
        # this group.  No problem, we'll try again next time round.
        return

    try:
        lifetime = g.config.get('article_lifetime', settings.article_lifetime)
        if lifetime:
            now = time.time()
            to_remove = set()
            
            for art in g.article_numbers():
                stat = os.stat(g.article_file(art))
                if now - stat.st_mtime > lifetime:
                    to_remove.add(art)

            if to_remove:
                logger.info("Expiring in " + g.name)
                index = g.load_eval("index", {})
                
                # XXX might need to generate index if it didn't exist
                g.saferemove("index")

                for (id, art) in index.items():
                    if art in to_remove:
                        logger.info("Expiring article %s@%s (%s)"
                                    % (id, g.name, art))
                        del index[id]
                
                # XXX need to catch exceptions so we always save next art number
                g.save("index", repr(index))
                
                for art in to_remove:
                    g.delete_article(art)
    finally:
        g.lockfile.unlock()


for g in group.groups():
    expire(g)
    
