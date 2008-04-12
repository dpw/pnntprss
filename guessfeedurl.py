# Feed URL autodetection

import urllib2, urlparse
from HTMLParser import HTMLParser

import feedparser

import settings

# prefer atom links
type_goodness = {'application/rss+xml':1, 'application/atom+xml':2}

class LinkParser(HTMLParser):
    def reset(self):
        HTMLParser.reset(self)
        self.href = None
        self.goodness = 0
        self.inbody = False

    def handle_starttag(self, tag, attrs):
        if not self.inbody and tag == 'link':
            a = dict(attrs)
            if a.get('rel') == 'alternate' and 'href' in a:
                goodness = type_goodness.get(a.get('type'), 0)
                if goodness > self.goodness:
                    self.goodness = goodness
                    self.href = a['href']
        else:
            if tag == 'body':
                self.inbody = True
        
        HTMLParser.handle_starttag(self, tag, attrs)


def guess_feed_url(url):
    """Given a URL, find the corresponding feed URL.

    The URL specified may itself be a feed URL, or the URL of an HTML
    page which indicates its corresponding feed URL."""
    
    req = urllib2.Request(url)
    req.add_header('User-Agent', settings.user_agent)
    usock = urllib2.urlopen(req)
    content = usock.read()
    usock.close()

    try:
        feed = feedparser.parse(content)
        if feed.version:
            # looks like a real feed
            return url
    except:
        pass

    # assume HTML, and do feed autodection
    try:
        parser = LinkParser()
        parser.feed(content)
        if parser.href:
            return urlparse.urljoin(url, parser.href)
    except:
        pass

    return None

if __name__ == '__main__':
    import sys
    print guess_feed_url(sys.argv[1])
