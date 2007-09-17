#!/usr/bin/python

import sys, os, re, codecs

import settings, group

logger = settings.get_logger('pnntprss.nntp')

# RFC977: commands with parameters must separate the parameters from
# each other and from the command by one or more space or tab
# characters.
separator_re = re.compile(r'\s+')

class NNTPServer:
    def __init__(self, input, output):
        self.finished = False
        self.current_group = None
        self.current_article_number = None
        
        # reopen input with universal line ending support
        self.input = os.fdopen(input.fileno(), "rU", 0)
        self.output = codecs.getwriter("utf-8")(output)

    def debug_in(self, l):
        logger.debug("< " + l)

    def debug_out(self, l):
        logger.debug("> " + l)

    def readlines(self):
        # avoid using file as iterator, since it implies buffering
        while True:
            l = self.input.readline()
            if not l:
                break
            
            # remove trailing newline
            if l[-1] == '\n':
                l = l[0:-1]

            logger.debug("< " + l)
            yield l

    def writeline(self, l):
        self.debug_out(l)
        self.output.write(l)
        self.output.write('\r\n')
        self.output.flush()

    def write(self, data):
        lines = data.split("\r\n")
        for l in lines[:-1]:
            self.debug_out(l)

        if lines[-1]:
            self.debug_out(lines[-1])
            
        self.output.write(data)
        self.output.flush()

    def process_commands(self):
        self.writeline('201 server ready - no posting allowed')
        
        for l in self.readlines():
            tokens = separator_re.split(l)
            if not tokens:
                self.writeline('501 command syntax error')
    
            m = getattr(self, 'do_' + tokens[0].upper(), None)
            if m:
                m(tokens[1:])
            else:
                self.writeline('500 command not recognized')

            if self.finished:
                break

    def do_MODE(self, params):
        if params and params[0].upper() == 'READER':
            self.writeline("201 Hello, you can't post")
        else:
            self.writeline('501 command syntax error')

    def do_QUIT(self, params):
        if params:
            self.writeline('501 command syntax error')
            return

        self.writeline('205 closing connection - goodbye!')
        self.finished = True

    def do_LIST(self, params):
        if params:
            self.writeline('501 command syntax error')
            return

        self.writeline('215 list of newsgroups follows')

        for g in group.groups():
            (lowest, highest, count) = g.article_range()
            self.writeline('%s %s %s n' % (g.name, highest, lowest))

        self.writeline('.')

    def do_GROUP(self, params):
        if len(params) != 1:
            self.writeline('501 command syntax error')
            return

        try:
            g = group.Group(params[0])
        except group.NoSuchGroupError:
            self.writeline('411 no such news group')
            return

        (lowest, highest, count) = g.article_range()
        self.writeline('211 %s %s %s %s group selected'
                       % (count, lowest, highest, g.name))

        if lowest <= highest:
            self.current_group = g
            self.current_article_number = lowest
        else:
            self.current_group = None
            self.current_article_number = None

    def do_XOVER(self, params):
        if len(params) > 1:
            self.writeline('501 command syntax error')
            return

        if self.current_group == None:
            self.writeline('412 no newsgroup has been selected')
            return

        # xXX prope range handling, including msgid and current
        # article forms
        range = params[0]
        dash = range.find('-')
        try:
            if dash < 0:
                range = [int(range)]
            elif dash == len(range)-1:
                range = group.Range(lo=int(range[0:dash]))
            else:
                range = group.Range(lo=int(range[0:dash]),
                                    hi=int(range[dash+1:]))
        except:
            self.writeline('501 command syntax error')
            return

        arts = self.current_group.articles(range)
        if not arts:
            self.writeline('420 no articles in range')
            return
            
        self.writeline('224 xover lines follow')

        # XXX encoding
        for art in arts:
            fields = [str(art.number()), art.subject(), art.author(),
                      art.date(), art.message_id(), '', '', '']
            self.writeline("\t".join([f.replace("\t", " ") for f in fields]))

        self.writeline('.')

    def retrieve_article(self, params):
        """Fetch an Article according to the parameters of
        ARTICLE, HEAD, BODY, and STAT."""
        if len(params) > 1:
            self.writeline('501 command syntax error')
            return None

        if self.current_group == None:
            self.writeline('412 no newsgroup has been selected')
            return None

        if len(params) == 1:
            self.current_article_number = int(params[0])
        elif self.current_article_number == None:
            self.writeline('420 no current article has been selected')
            return None

        art = self.current_group.article(self.current_article_number)
        if art == None:
            self.writeline('423 no such article number in this group')
            return None

        return art

    def do_ARTICLE(self, params):
        art = self.retrieve_article(params)
        if not art:
            return
        
        self.writeline('220 %s %s article retrieved - head and body follow'
                       % (art.number(), art.message_id()))
        msg = art.make_message()
        self.write(msg.header_bytes())
        self.writeline('')
        self.write(msg.dot_stuffed_body())

    def do_HEAD(self, params):
        art = self.retrieve_article(params)
        if not art:
            return
        
        self.writeline('221 %s %s article retrieved - head follows'
                       % (art.number(), art.message_id()))
        self.write(art.make_message().header_bytes())
        self.writeline('.')

    def do_BODY(self, params):
        art = self.retrieve_article(params)
        if not art:
            return
        
        self.writeline('222 %s %s article retrieved - body follows'
                       % (art.number(), art.message_id()))
        self.write(art.make_message().dot_stuffed_body())

    def do_STAT(self, params):
        art = self.retrieve_article(params)
        if not art:
            return
        
        self.writeline('223 %s %s article exists'
                       % (art.number(), art.message_id()))

