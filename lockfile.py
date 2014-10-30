# Unix lockfiles

import os, os.path, time, warnings, errno

import settings

logger = settings.get_logger('pnntprss.lockfile')

# we use tempnam safely.
warnings.filterwarnings('ignore', 'tempnam', RuntimeWarning, 'lockfile')

class LockFileStateError(Exception):
    """An Exception indicating that the lock was not in the appropriate state"""
    pass

class LockFile:
    """An object representing a Unix lockfile."""
    
    def __init__(self, path, expiry_time=30 * 60):
        self.locked = False
        self.path = path
        self.expiry_time = expiry_time
        (self.dir, self.prefix) = os.path.split(path)
        if self.prefix[0] != '.':
            self.prefix = '.' + self.prefix

    def trylock(self, directory_must_exist=False):
        """Try to acquire the lock."""
        
        if self.locked:
            raise LockFileStateError("already holding lock file: %s" % self.path)

        try:
            st = os.stat(self.path)
            if time.time() - st.st_mtime < self.expiry_time:
                # lock exists, and isn't stale, so we don't acquire it
                return False

            logger.info("removing stale lock file %s" % self.path)
            os.remove(self.path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        while True:
            tmpfile = os.tempnam(self.dir, self.prefix)
            if not os.path.exists(tmpfile):
                break

        try:
            f = file(tmpfile, "w")
            f.close()
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise

            if directory_must_exist:
                raise ValueError("missing directory for lock file: %s" % path)

            return False

        try:
            os.link(tmpfile, self.path)
            st = os.stat(tmpfile)
            if st.st_nlink > 1:
                self.locked = tmpfile
                return True
        except:
            pass

        # The directory containing the lock file might be deleted by
        # another process (which must hold the lock) while we are
        # attempting to lock.  In that case, we will fail to delete
        # our temp file, but that's ok.
        try:
            os.unlink(tmpfile)
        except:
            pass

        return False

    def lock(self):
        while not self.trylock(True):
            time.sleep(5)

    def touch(self):
        """Touch the lock file, to avoid it becoming stale during an
        extended operation."""
        if not self.locked:
            raise LockFileStateError("not holding lock file: %s" % self.path)

        st = os.stat(self.locked)
        if st.st_nlink == 1:
            # someone snatched our lock
            return False

        os.utime(self.locked, None)
        return True
    
    def unlock(self):
        """Release the lock."""
        if not self.locked:
            raise LockFileStateError("not holding lock file: %s" % self.path)

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
