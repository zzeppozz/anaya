# Helper functions to clean up directory and filenames
import hashlib
import os

class DeDuper():
    def __init__(self, source_path, dest_path, *additional_paths):
        self.source_paths = [source_path, dest_path]
        self.dest_path = dest_path
        for pth in additional_paths:
            if os.path.exists(pth):
                self.source_paths.append(pth)

    # ...............................................
    def _examine_files(self):
        dups = {}
        for inpath in self.input_paths:
            for root, dirnames, filenames in os.walk(inpath):
                print('Scanning {} ...'.format(root))
                for fname in filenames:
                    fullname = os.path.join(root, fname)
                    fhash = hashfile(fullname)
                    # Add or append the file path
                    try:
                        dups[fhash].append(fullname)
                    except:
                        dups[fhash] = [fullname]
        return dups

    # ...............................................
    def _examine_filehash(filenames, f):
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

    # ...............................................
    def write_duplicates(self, out_fname):
        file_dict = self._examine_files()
        for hsh, matching_files in file_dict:
            if len(matching_files) == 1:
                pth, basefname = os.path.split(matching_files[0])
                if pth != self.dest_path:
                    print('# Copy {} from {} to destination dir'.format(basefname, pth, self.dest_path))
                    print('cp -p {} {}'.format(matching_files[0], self.dest_path))
                    print('# Delete {} from {}'.format(basefname, pth))
                    print('rm -f {}'.format(matching_files[0]))

# ...............................................
def hashfile(fullfname, blocksize=65536):
    f = open(fullfname, 'rb')
    hasher = hashlib.md5()
    buf = f.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = f.read(blocksize)
    f.close()
    return hasher.hexdigest()




# ..............................................................................
# ..............................................................................
DUP_DIRS = ['/Users/astewart/Pictures/Imported',
            '/Users/astewart/Pictures/ImportedAlready']
GOOD_DIR = '/Users/astewart/Pictures/Lightroom'
DELETEME_FILENAME = '/Users/astewart/Pictures/deleteme.txt'

DUP_DIRS = ['/Users/astewart/Pictures/ImportedAlready']
DUP_DIRS.append(GOOD_DIR)

DeDuper()
dupfnames = findDups(DUP_DIRS)
print('Writing duplicates ...')
try:
    f = open(DELETEME_FILENAME, 'w')
    for fhash, filenames in dupfnames.iteritems():
        obsfnames = writeDupsToDelete(GOOD_DIR, filenames, f)
finally:
    f.close()
    print('Completed list of duplicates: {}'.format(DELETEME_FILENAME))


