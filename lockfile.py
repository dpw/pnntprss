import os, os.path, warnings

# we use tempnam safely.
warnings.filterwarnings('ignore', 'tempnam', RuntimeWarning, 'lockfile')

class LockFile:
    def __init__(self, path):
        self.locked = False
        self.path = path
        (self.dir, self.prefix) = os.path.split(path)
        if not os.path.isdir(self.dir):
            raise "invalid directory for lock file: %s" % path

        if self.prefix[0] != '.':
            self.prefix = '.' + self.prefix

    def trylock(self):
        if self.locked:
            raise "already holding lock"
        
        while True:
            tmpfile = os.tempnam(self.dir, self.prefix)
            if not os.path.exists(tmpfile):
                break

        try:
            f = file(tmpfile, "w")
            f.close()

            try:
                os.link(tmpfile, self.path)
            except:
                pass
            
            st = os.stat(tmpfile)
            self.locked = (st.st_nlink > 1)
        finally:
            try:
                os.unlink(tmpfile)
            except:
                pass
        
        return self.locked

    def unlock(self):
        if not self.locked:
            raise "not locked"

        self.locked = False
        os.unlink(self.path)
