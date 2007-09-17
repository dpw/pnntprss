import lockfile

l1 = lockfile.LockFile('/tmp/xxx')
l2 = lockfile.LockFile('/tmp/xxx')
print l1.trylock()
print l2.trylock()
l1.unlock()
print l2.trylock()
l2.unlock()

