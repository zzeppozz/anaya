import hashlib
import os

DUP_DIRS = ['/Users/astewart/Pictures/Imported', 
                '/Users/astewart/Pictures/ImportedAlready']
GOOD_DIR = '/Users/astewart/Pictures/Lightroom'
DELETEME_FILENAME = '/Users/astewart/Pictures/deleteme.txt'

# ...............................................
def hashfile(fullfname, blocksize = 65536):
    f = open(fullfname, 'rb')
    hasher = hashlib.md5()
    buf = f.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = f.read(blocksize)
    f.close()
    return hasher.hexdigest()

# ...............................................
def findDups(parentFolders):
    dups = {}
    for pfolder in parentFolders:
        print('Scanning {} ...'.format(pfolder))
        for dirpath, dirnames, filenames in os.walk(pfolder):
            for fname in filenames:
                fullname = os.path.join(dirpath, fname)
                fhash = hashfile(fullname)
                # Add or append the file path
                if fhash in dups:
                    dups[fhash].append(fullname)
                else:
                    dups[fhash] = [fullname]
    return dups

# ...............................................
def writeDupsToDelete(finaldir, filenames, f):
    deleteme = []
    foundfinal = False
    for fullname in filenames:
        pth, fname = os.path.split(fullname)
        if pth != finaldir or foundfinal:
            deleteme.append(fullname)
        else:
            foundfinal = True
    if foundfinal:
        f.writelines(deleteme)
    
# ..............................................................................
# ..............................................................................
DUP_DIRS = ['/Users/astewart/Pictures/ImportedAlready']
DUP_DIRS.append(GOOD_DIR)
dupfnames = findDups(DUP_DIRS)
print('Writing duplicates ...')
try:
    f = open(DELETEME_FILENAME, 'w')
    for fhash, filenames in dupfnames.iteritems():
        obsfnames = writeDupsToDelete(GOOD_DIR, filenames, f)
finally:
    f.close()
    print('Completed list of duplicates: {}'.format(DELETEME_FILENAME))

    
