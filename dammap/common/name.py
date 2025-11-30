# .............................................................................
from logging import INFO, WARN, ERROR
import os.path

from dammap.common.constants import IMAGE_EXTENSIONS, DATE_SEP, SEPARATOR
from dammap.common.dammeta import DamMeta

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
        if ext.lower() in IMAGE_EXTENSIONS:
            ext = ext.lower()
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
        return f"{name}_{date}_{num}"


    # .............................................................................
    @staticmethod
    def create_filename(base_filename, damrec):
        # remove path if exists
        base_filename = os.path.basename(base_filename)
        basename, ext = os.path.splitext(base_filename)
        if ext.lower() == ".jpg":
            ext = ".JPG"
        damname = damrec.arroyo_name.lower()
        yr, mo, dy = damrec.img_date
        # change into strings
        datestr = DATE_SEP.join([yr, f"{mo:02d}", f"{dy:02d}"])
        newbasename = SEPARATOR.join([damname, datestr, damrec.picnum])
        return f"{newbasename}{ext}"


    # ...............................................
    @staticmethod
    def check_filename(dataroot, full_fname, logger):
        do_rename = False
        fullpth, fname = os.path.split(full_fname)
        relpth = fullpth[len(dataroot)+1:]
        pthparts = relpth.split(os.sep)
        try:
            arr, dam = pthparts
        except ValueError:
            arr = pthparts[0]
        arr_name = arr.split(SEPARATOR)[1]
        basefname = os.path.splitext(fname)[0]
        fparts = basefname.split(SEPARATOR)
        try:
            dam_name, fulldate, picnum = fparts
        except ValueError:
            try:
                first, last = fparts
            except ValueError:
                logger.log(WARN, f"What's up with this fname {fname}")
            else:
                logger.log(WARN, f"Filename {basefname} does not start with {arr_name}")
                if first.lower() != "img":
                    logger.log(WARN, f"Filename {basefname} does not start with img")
                try:
                    int(last)
                    picnum = last
                    do_rename = True
                except ValueError:
                    logger.log(WARN, f"Filename {basefname} does not end with an int")
        if do_rename:
            tags, _ = DamMeta.get_image_metadata(full_fname, logger)
            if tags:
                (yr, mo, dy) = DamMeta.get_camera_date(tags, logger)
                datestr = DATE_SEP.join([yr, f"{mo:02d}", f"{dy:02d}"])
                newfname = SEPARATOR.join([arr_name.lower(), datestr, picnum])
                return os.path.join(fullpth, newfname)
        else:
            # Existing fname is correct
            return full_fname

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
        datestr = DATE_SEP.join([year, f"{int(mon):02d}", f"{int(day):02d}"])
        return SEPARATOR.join([name, datestr, num])

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

    # ...............................................
    @staticmethod
    def construct_relative_fname(arroyo_num, arroyo_name, dam_name, dam_date, picnum):
        """Parse a relative filename into metadata about this file.

        Args:
            arroyo_num (str): integer/number of the arroyo
            arroyo_name (str): name of the arroyo
            dam_name (str): name of the dam
            dam_date (list): list of digit-strings, (yyyy, mm, dd)
            picnum (int): integer/number of the photo

        Returns:
            relfname (str): relative filename containing parent directory and filename
        """
        year, mon, day = dam_date
        new_arroyo_dir = f"{arroyo_num}_{arroyo_name}"
        new_arroyo_fname = f"{dam_name}_{year}-{mon}-{day}_{picnum}"
        new_rel_filename = os.path.join(new_arroyo_dir, new_arroyo_fname)
        return new_rel_filename

    # ...............................................
    @staticmethod
    def construct_relative_path(dam_meta):
        """Parse a relative filename into metadata about this file.

        Args:
            dam_meta (DamMeta): object with metadata about an image

        Returns:
            relpath (str): relative path containing parent directory and subdirs
        """
        relative_path = f"{dam_meta.arroyo_num}_{dam_meta.arroyo_name}"
        if dam_meta.dam_calc is not None:
            relative_path = os.path.join(relative_path, dam_meta.dam_calc)
        return relative_path

    # # ...............................................
    # @staticmethod
    # def construct_fname(arroyo_dir, dam_name, dam_date, picnum):
    #     """Parse a relative filename into metadata about this file.
    #
    #     Args:
    #         arroyo_num (str): integer/number of the arroyo
    #         arroyo_name (str): name of the arroyo
    #         dam_name (str): name of the dam
    #         dam_date (list): list of digit-strings, (yyyy, mm, dd)
    #         picnum (int): integer/number of the photo
    #
    #     Returns:
    #         relfname (str): relative filename containing parent directory and filename
    #     """
    #     year, mon, day = dam_date
    #     new_arroyo_dir = f"{arroyo_num}_{arroyo_name}"
    #     new_arroyo_fname = f"{dam_name}_{year}-{mon}-{day}_{picnum}"
    #     new_rel_filename = os.path.join(new_arroyo_dir, new_arroyo_fname)
    #     return new_rel_filename
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

# # .............................................................................
# def move_arroyos(csvfilename, delimiter, field, dest_arroyo_dir, logger):
#     """Move images from one arroyo to another, renaming appropriately.
#
#     Args:
#         csvfilename (str): CSV file with misplaced-images.
#         delimiter (char): character delimiting fields in the CSV file.
#         field (str): Field in CSV containing the full path of misplaced images.
#         dest_arroyo_dir (str): Destination arroyo directory for the images.
#     """
#     new_arroyo_num, new_arroyo_name = dest_arroyo_dir.split("_")
#     new_dam_name = new_arroyo_name.lower()
#     inpath = os.path.join(BASE_PATH, IN_DIR)
#
#     reader, inf = get_csv_dict_reader(csvfilename, delimiter)
#     for row in reader:
#         misnamed_imagefile = row[field]
#         rel_fname = misnamed_imagefile[len(inpath)+1:]
#         arroyo_num, arroyo_name, dam_name, dam_date, picnum = \
#             DamNameOp.parse_relative_fname(rel_fname)
#         if arroyo_name != new_arroyo_name:
#             # Add 90000 to the picnum to ensure no conflicts with files in destination directory
#             new_picnum = str(int(picnum) + 90000)
#             new_rel_filename = DamNameOp.construct_relative_fname(
#                 new_arroyo_num, new_arroyo_name, new_dam_name, dam_date, new_picnum)
#             renamed_imagefile = os.path.join(inpath, f"{new_rel_filename}.JPG")
#             # os.rename(misnamed_imagefile, renamed_imagefile)
#             logger.info(f"Rename {misnamed_imagefile} --> {renamed_imagefile}")
