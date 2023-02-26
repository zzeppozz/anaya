# .............................................................................
import os.path

from dammap.common.constants import SEPARATOR


class DamNameOp():

    # .............................................................................
    @staticmethod
    def standarize_dir_name(olddir):
        newdir = ""
        return newdir


    # .............................................................................
    @staticmethod
    def standardize_filename(base_filename):
        # remove path if exists
        base_filename = os.path.basename(base_filename)
        basename, ext = os.path.splitext(base_filename)
        if ext.lower() == ".jpg":
            ext = ".JPG"
        for i in range(len(basename)):
            if basename[i].isdigit():
                idx = i
                break
        name = basename[0:idx]
        datenum = basename[idx:]
        parts = datenum.split("_")
        if len(parts) == 1:
            date = datenum[:8]
            num = datenum[8:]
        elif len(parts) == 2:
            date = parts[0]
            num = parts[1]
        else:
            raise Exception(f"Unexpected filename {base_filename}")


    # .............................................................................
    @staticmethod
    def format_filename(filename):
        name = ""
        year = ""
        mon = ""
        day = ""
        num = ""
        datecount = 0
        # remove path if exists
        base_filename = os.path.basename(filename)
        basename, ext = os.path.splitext(base_filename)
        if ext.lower() == ".jpg":
            ext = ".JPG"
        for ch in basename:
            if datecount < 8:
                if ch.isalpha():
                    name += ch
                elif ch.isdigit():
                    # fill year, month, date in that order
                    if len(year) < 4:
                        year += ch
                    elif len(mon) < 2:
                        mon += ch
                    elif len(day) < 2:
                        day += ch
                    datecount += 1
            elif ch.isdigit():
                num += ch
        return f"{name}_{year}-{mon}-{day}_{num}"

    # .............................................................................
    @staticmethod
    def fix_name(name, ext=None):
        """Modify name to consistent pattern.

         Exclude special characters, apostrophes, and parentheses and correct extensions

         Args:
            name (str): input directory or base filename for correction
            ext (str): optional extension, used only when fixing filenames

        Returns:
            string that is the modified name.  If filename, includes extension.
        """
        newchars = []
        # If this is a filename, and extension was not split out
        # remove extension chars from basename, and set extension correctly
        photo_ext = "jpg"
        if ext == "" and name.lower().endswith(photo_ext):
            name = name[:-3]
            ext = ".{}".format(photo_ext)
        found_paren = False
        for i in range(0, len(name)):
            ch = name[i]
            # Skip spaces, non-ascii, single quote characters
            if ch.isascii() and ch not in (" ", "'"):
                if ch.isalnum() or ch == "_":
                    newchars.append(ch)
                # Replace first ) with _, remove others
                elif ch == ")":
                    if not found_paren:
                        found_paren = True
                        newchars.append("_")
        newname = ''.join(newchars)
        # Parse date and number from filenames, then re-concatenate extension
        if ext is not None:
            newname = DamNameOp.format_filename(newname)
            newname += ext
        return newname

    # ...............................................
    @staticmethod
    def parse_relative_fname(relfname):
        """Parse a relative filename into metadata about this file.

        Args:
            relfname (str): relative filename containing parent directory and filename

        Returns:
            arroyo_num (str): integer/number of the arroyo
            arroyo_name (str): name of the arroyo
            dam_name (str): name of the dam
            dam_date (list): list of digit-strings, (yyyy, mm, dd)
            picnum (int): integer/number of the photo
        """
        arroyo_num = arroyo_name = dam_name = dam_date = picnum = None
        try:
            dirname, fname = relfname.split(os.sep)
        except ValueError:
            print('Relfname {} does not parse into 2'.format(relfname))
        else:
            try:
                arroyo_num, arroyo_name = dirname.split(SEPARATOR)
            except ValueError:
                print('Dirname {} does not parse into 2'.format(dirname))
            else:
                basename, ext = os.path.splitext(fname)
                try:
                    dam_name, fulldate, picnum = basename.split(SEPARATOR)
                except ValueError:
                    print('Basename {} does not parse into 3'.format(basename))
                else:
                    tmp = fulldate.split("-")

                    try:
                        dam_date = [int(d) for d in tmp]
                    except TypeError:
                        print('Date {} does not parse into 3'.format(fulldate))
                    else:
                        if len(dam_date) != 3:
                            print('Date {} does not parse into 3'.format(dam_date))

        return arroyo_num, arroyo_name, dam_name, dam_date, picnum

# .............................................................................
def fix_names_in_tree(inpath, do_files=False):
    """Fix names in a tree, either directories or files.

    Args:
        inpath (str): base directory
        do_files (bool): False if rename directories, True if rename files
    """
    start = len(inpath) + 1
    for root, dirlist, files in os.walk(inpath):
        # Fix directories
        if not do_files:
            for olddir in dirlist:
                # Fix filenames
                newdir = DamNameOp.fix_name(olddir)
                os.rename(os.path.join(root, olddir), os.path.join(root, newdir))
                print("{} --> {}".format(olddir, newdir))
        # Fix files
        else:
            for fname in files:
                basename, ext = os.path.splitext(fname)
                if not fname.startswith(".") and ext.lower() == ".jpg":
                    old_filename = os.path.join(root, fname)
                    newname = DamNameOp.fix_name(basename, ext=ext)
                    new_filename = os.path.join(root, newname)
                    # Test before rename
                    rel_fname = new_filename[start:]
                    arroyo_num, arroyo_name, name, date_lst, picnum = \
                        DamNameOp.parse_relative_fname(rel_fname)
                    if (None in (arroyo_num, arroyo_name, name, picnum)
                            or len(date_lst) < 2):
                        print("Stop me now! {}".format(rel_fname))
                    else:
                        os.rename(old_filename, new_filename)
                        print("Rename {} --> {}".format(fname, newname))


# ...............................................
def test_names_in_tree(inpath):
    """Tests filenames in a 2-level directory tree.

    Args:
        inpath (str): base directory
    """
    start = len(inpath) + 1
    for root, dirlist, files in os.walk(inpath):
        for fname in files:
            if not fname.startswith(".") and fname.lower().endswith("jpg"):
                full_fname = os.path.join(root, fname)
                rel_fname = full_fname[start:]
                arroyo_num, arroyo_name, name, date_lst, picnum = \
                    DamNameOp.parse_relative_fname(rel_fname)
                print("Relative filename {} parses to: ".format(rel_fname))
                print("   Arroyo: {} {}".format(arroyo_num, arroyo_name))
                print("   Dam:    {}, {}-{}-{}, {}".format(
                    name, date_lst[0], date_lst[1], date_lst[2], picnum))