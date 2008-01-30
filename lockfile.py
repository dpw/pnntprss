# Unix lockfiles

import os, os.path, time, warnings

import settings

logger = settings.get_logger('pnntprss.lockfile')

# we use tempnam safely.
warnings.filterwarnings('ignore', 'tempnam', RuntimeWarning, 'lockfile')

class LockFile:
    """An object representing a Unix lockfile."""
    
    def __init__(self, path, expiry_time=30 * 60):
        self.locked = False
        self.path = path
        self.expiry_time = expiry_time
        (self.dir, self.prefix) = os.path.split(path)
        if not os.path.isdir(self.dir):
            raise "invalid directory for lock file: %s" % path

        if self.prefix[0] != '.':
            self.prefix = '.' + self.prefix

    def trylock(self):
        """Try to acquire the lock."""
        
        if self.locked:
            raise "already holding lock"

        if os.path.exists(self.path):
            try:
                st = os.stat(self.path)
                if time.time() - st.st_mtime < self.expiry_time:
                    # lock exists, and isn't stale, so we don't acquire it
                    return False

                logger.info("removing stale lock file %s" % self.path)
                os.remove(self.path)
            except:
                pass
        
        while True:
            tmpfile = os.tempnam(self.dir, self.prefix)
            if not os.path.exists(tmpfile):
                break

        f = file(tmpfile, "w")
        f.close()

        try:
            os.link(tmpfile, self.path)
        except:
            pass
            
        st = os.stat(tmpfile)
        if st.st_nlink > 1:
            self.locked = tmpfile
        
        return self.locked is not False

    def touch(self):
        """Touch the lock file, to avoid it becoming stale during an
        extended operation."""
        if not self.locked:
            raise "not locked"

        st = os.stat(self.locked)
        if st.st_nlink == 1:
            # someone snatched our lock
            return False

        os.utime(self.locked, None)
        return True
    
    def unlock(self):
        """Release the lock."""
        if not self.locked:
            raise "not locked"

        try:
            st = os.stat(self.locked)
            os.unlink(self.locked)
            if st.st_nlink == 1:
                logger.info("lock file %s was snatched" % self.path)
            else:
                os.unlink(self.path)
        finally:
            self.locked = False

if __name__ == '__main__':
    l1 = LockFile('/tmp/xxx')
    l2 = LockFile('/tmp/xxx')
    print l1.trylock()
    print l2.trylock()
    l1.unlock()
    print l2.trylock()
    l2.unlock()
