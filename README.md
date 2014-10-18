# pnntprss: A Python RSS/Atom -> NNTP gateway

pnntprss is a simple RSS/Atom feed reader.  It exposes feeds via NNTP,
so you can read them with the NNTP newsreader of your choice (I use
[Gnus](http://gnus.org/)).  Each RSS/Atom feed becomes an NNTP group.

pnntprss is written in Python (version 2.6 or 2.7, I haven't ported it
to 3.x yet).  It uses Mark Pilgrim's wonderful
[feedparser](http://code.google.com/p/feedparser/) which takes care of
much of the hard work.

pnntprss has a purposefully simple design.  It has no dependencies.
All feed data is stored in the filesystem, one directory per feed, one
file per feed item.  This works surprisingly well, even with hundreds
or thousands of items in a feed.  I have been running pnntprss
continuously for about many years; I have 60k feed items occupying 400MB
of disk space (I only expire high-volume feeds).

## Using pnntprss

1. Clone the pnntprss git repo somewhere.

2. Create a directory `~/.pnntprss/groups`.

3. Start the NNTP server in the background (assuming that you cloned
   the pnntprss repo into your `~/work` directory):

        python ~/work/pnntprss/nntpserver.py &

4. Add the following lines to your crontab (with `crontab -e`):

        0-59 * * * *    $HOME/pnntprss/update.py
        43 0,6,12,18 * * *      $/work/pnntprss/expire.py

   This will run `update.py` (which gets feeds) every minute and
   `expire.py` (which expires feed items) every 6 hours. (Note that
   `update.py` won't actually request every feed every minute if you do
   this; it will only request feeds that haven't been checked for a
   configurable interval, which defaults to 30 minutes.)

5. Use `admin.py` to add some feeds:

        `~/work/pnntprss/admin.py -a -u http://david.wragg.org/blog/ org.wragg.david

6. Point your NNTP client to `localhost:4321`
