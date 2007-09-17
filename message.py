from email.Header import Header
from email.Charset import Charset
from StringIO import StringIO
import email.Charset
import base64
import quopri
import re

charset = Charset('utf-8')
charset.header_encoding = email.Charset.SHORTEST
charset.body_encoding = email.Charset.SHORTEST

line_end_re = re.compile(r'\r\n|\n\r|\n(?!\r)|\r(?!\n)')

def encode_header_word(word):
    if type(word) is unicode:
        # see if it is plain ascii first
        try:
            return word.encode('us-ascii')
        except:
            # try to encode non-ascii headers using email.Header.  The
            # 1000000 value is a maximum line length, meaning never
            # fold header lines.  This is important for the XOVER
            # response.
            return str(Header(word, charset, 1000000))
    else:
        return word

# base64 encode a string, splitting lines in the output
def base64encode(s):
    buf=StringIO()
    base64.encode(StringIO(s), buf)
    return buf.getvalue()
    
class Message:
    def __init__(self):
        self.headers = {}
        self.body = ''
        self.headers['MIME-Version'] = '1.0'

    def __len__(self):
        return len(self.headers)
        
    def __contains__(self, name):
        return name in self.headers

    def __getitem__(self, name):
        return self.headers[name]

    def __setitem__(self, name, value):
        if type(value) is unicode:
            value = encode_header_word(value)
        else:
            value = str(value)

        self.headers[name] = value

    def __delitem__(self, name):
        del self.headers[name]

    def set_body(self, value, content_type):
        encode = True
        if type(value) is unicode:
            # see if it is plain ascii first
            try:
                value = value.encode('us-ascii')
                encode = False
            except:
                value = value.encode('utf-8')
                content_type += "; charset='utf-8'"
        else:
            value = str(value)

        self['Content-Type'] = content_type

        if encode:
            # use the shortest of quoted-printable and base64 encodings
            qp = quopri.encodestring(value)
            b64 = base64.b64encode(value)
            if len(qp) <= len(b64):
                self.body = qp
                self['Content-Transfer-Encoding'] = 'quoted-printable'
            else:
                self.body = b64
                self['Content-Transfer-Encoding'] = 'base64'
        else:
            self.body = value

    def header_bytes(self):
        res = ''
        for (h, v) in self.headers.items():
            res += h + ': ' + v + '\r\n'

        return res

    def dot_stuffed_body(self):
        # take the body, normalize line endings, and dot-stuff
        body = line_end_re.sub('\r\n', self.body)
        if not body.endswith('\r\n'):
            body += '\r\n'

        if body.startswith('.'):
            body = '.' + body
        
        body = body.replace('\r\n.', '\r\n..')
        body += '.\r\n'
        return body
