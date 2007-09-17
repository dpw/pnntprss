import os, os.path, time

import settings, message, lockfile

class OpenRange:
    def __init__(self):
        pass

    def __contains__(self, num):
        return True

class Range:
    def __init__(self, lo=None, hi=None):
        self.lo = lo
        self.hi = hi

    def __contains__(self, num):
        return (self.lo is None or num >= self.lo) and (self.hi is None or num <= self.hi)

def isdigit(c):
    return c >= '0' and c <= '9'

# remove a file, which might not exist
def saferemove(path):
    try:
        os.remove(path)
    except:
        pass

def saferename(frm, to):
    # XXX on non-unix, should remove the file /to/ if present
    os.rename(frm, to)

class NoSuchGroupError(Exception):
    pass

def group_path(group_name):
    return "%s/%s" % (settings.groups_dir, group_name)

class Group:
    def __init__(self, name):
        self.name = name
        if not os.path.isdir(self.group_path()):
            raise NoSuchGroupError, name

        self.config = self.load_eval("config", {})
        self.lockfile = lockfile.LockFile(self.group_file("lock"))

    def group_path(self):
        return group_path(self.name)

    def group_file(self, fname):
        return "%s/%s/%s" % (settings.groups_dir, self.name, fname)

    def load_eval(self, fname, otherwise=None):
        path = self.group_file(fname)
        if not os.path.exists(path):
            return otherwise
        
        f = file(path)
        expr = f.read()
        f.close()
        return eval(expr)

    def reload_config(self):
        self.config = self.load_eval("config", {})

    def save_config(self):
        self.save("config", repr(self.config))

    def save(self, fname, val):
        path = self.group_file(fname)
        tmppath = path + ".new"
        f = file(tmppath, "w")
        f.write(val)
        f.close()
        saferename(tmppath, path)

    def saferemove(self, fname):
        saferemove(self.group_file(fname))

    def ready_to_check(self, t):
        return t - self.config.get("lastpolled", 0) >= self.config.get("interval", settings.feed_poll_interval)

    def article_range(self):
        lowest = self.config.get('next_article_number', 1)
        highest = lowest - 1
        count = 0

        for f in os.listdir(self.group_path()):
            if isdigit(f[0]):
                f = int(f)
                count += 1
                if f < lowest:
                    lowest = f
                if f > highest:
                    highest = f

        return (lowest, highest, count)

    def article(self, num):
        # XXX should return None if the article doesn't exist
        return Article(self, num, self.load_eval(num))

    def article_numbers(self, range=OpenRange()):
        for f in os.listdir(self.group_path()):
            if isdigit(f[0]):
                f = int(f)
                if f in range:
                    yield f

    def articles(self, range=OpenRange()):
        return [self.article(n) for n in sorted(self.article_numbers(range))]

    def next_article_number(self):
        num = self.config.get('next_article_number')
        if num is None:
            num = self.article_range()[1] + 1
        else:
            # just in case...
            while os.path.exists(self.group_file(str(num))):
                num += 1

        self.config['next_article_number'] = num + 1
        return num

def encode_email_header(name, email="unknown@unknown"):
    return '%s <%s>' % (message.encode_header_word(name),
                        message.encode_header_word(email))

def to_html(detail):
    type = detail['type']
    if type == 'text/plain':
        # XXX escape, wrap in <p>
        return detail['value']
    else:
        # maybe do something smarter for application/xhtml+xml?
        return detail['value']

class Article:
    def __init__(self, group, num, entry):
        self.group = group
        self.num = num
        self.entry = entry

    def same_entry(self, entry):
        def clean(e):
            if 'feed_updated_parsed' in e:
                e = dict(e)
                del e['feed_updated_parsed']
                
            return e

        return clean(self.entry) == clean(entry)

    def number(self):
        return self.num

    def message_id(self):
        return "<%s@%s>" % (self.entry['message_id'], self.group.name)

    def subject(self):
        if 'title_detail' in self.entry:
            # XXX need to strip HTML
            return self.entry['title_detail']['value']
        else:
            # XXX do something smarter here?
            return ""

    def content(self):
        if 'content' in self.entry:
            return self.entry['content'][0]
        elif 'summary_detail' in self.entry:
            return self.entry['summary_detail']
        else:
            return {'value':'', 'type':'text/plain'}

    def render_body(self):
        if 'link' not in self.entry:
            # without a link, plain text entries can be passed through
            c = self.content()
            if c['type'] == 'text/plain':
                return c

        # result is going to be HTML
        res = to_html(self.content())
        if 'link' in self.entry:
            link = self.entry['link']
            caption = self.entry.get('title_detail') or {'value':link,
                                                         'type':'text/plain'}
            res = "<h1><a href='%s'>%s</a></h1>\n%s" % (link, to_html(caption),
                                                        res)

        return {'value':res, 'type':'text/html'}

    def author(self):
        for d in [self.entry, self.group.config]:
            if 'author_detail' in d:
                ad = d['author_detail']
                if 'name' in ad and 'email' in ad:
                    return encode_email_header(ad['name'], ad['email'])
                elif 'name' in ad:
                    return encode_email_header(ad['name'])
                elif 'email' in ad:
                    return ad['email']
            elif 'author' in d:
                return encode_email_header(d['author'])

        if 'title' in self.group.config:
            return encode_email_header(self.group.config['title'])
                                
        return 'Unknown <unknown@unknown>'

    def date(self):
        t = self.entry.get('updated_parsed')
        if not t:
            t = self.entry.get('feed_updated_parsed')
            
        return time.strftime("%d %b %Y %H:%M:%S %z", t)

    def make_message(self):
        # we don't know lines and bytes, but NNTP clients seem to
        # tolerate those fields missing
        msg = message.Message()
        msg['From'] = self.author()
        msg['Newsgroups'] = self.group.name
        msg['Date'] = self.date()
        msg['Subject'] = self.subject()
        msg['Message-ID'] = self.message_id()
        msg['Path'] = 'pnntprss'

        body = self.render_body()
        msg.set_body(body['value'], body['type'])
        
        return msg

def groups():
    return [Group(d) for d in os.listdir(settings.groups_dir)
            if os.path.isdir(group_path(d))]
