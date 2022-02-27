# File handling, name conversion, bounding box parsing, Image processing common for anaya project
import csv
import glob
import logging
from logging.handlers import RotatingFileHandler
import os
from PIL import Image
import sys
import time

from dammap.common.constants import SEPARATOR

LOG_FORMAT = ' '.join(["%(asctime)s",
                       "%(threadName)s.%(module)s.%(funcName)s",
                       "line",
                       "%(lineno)d",
                       "%(levelname)-8s",
                       "%(message)s"])
LOG_DATE_FORMAT = '%d %b %Y %H:%M'
LOG_MAX = 52000000


# .............................................................................
def get_logger(outpath):
    if not os.path.exists(outpath):
        try:
            os.makedirs(outpath)
        except:
            raise

    level = logging.DEBUG
    # get log filename
    scriptname, _ = os.path.splitext(os.path.basename(__file__))
    secs = time.time()
    timestamp = "{}".format(time.strftime("%Y%m%d-%H%M", time.localtime(secs)))
    logname = '{}.{}'.format(scriptname, timestamp)
    logfname = os.path.join(outpath, logname + '.log')
    # create file handler
    file_log_handler = RotatingFileHandler(logfname, maxBytes=LOG_MAX, backupCount=2)
    file_log_handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_log_handler.setFormatter(formatter)
    # get logger
    log = logging.getLogger(logname)
    log.setLevel(level)
    log.addHandler(file_log_handler)
    return log

# .............................................................................
def logit(log, msg):
    if log:
        log.warn(msg)
    else:
        print(msg)

# .............................................................................
def _format_filename(basename):
    name = ""
    year = ""
    mon = ""
    day = ""
    num = ""
    datecount = 0
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
    return "{}_{}-{}-{}_{}".format(name, year, mon, day, num)

# .............................................................................
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
        newname = _format_filename(newname)
        newname += ext
    return newname

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
                newdir = fix_name(olddir)
                os.rename(os.path.join(root, olddir), os.path.join(root, newdir))
                print("{} --> {}".format(olddir, newdir))
        # Fix files
        else:
            for fname in files:
                if not fname.startswith("."):
                    basename, ext = os.path.splitext(fname)
                    newname = fix_name(basename, ext=ext)
                    if not ext:
                        print(" *** Badname {} --> {}".format(fname, newname))
                    old_filename = os.path.join(root, fname)
                    new_filename = os.path.join(root, newname)
                    # Test before rename
                    rel_fname = new_filename[start:]
                    arroyo_num, arroyo_name, name, date_lst, picnum = parse_relative_fname(rel_fname)
                    if (None in (arroyo_num, arroyo_name, name, picnum)
                            or len(date_lst) < 2):
                        print("Stop me now! {}".format(rel_fname))
                    else:
                        os.rename(old_filename, new_filename)
                        print("Rename {} --> {}".format(fname, newname))

# ...............................................
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
                    dam_date = tuple([int(d) for d in tmp])
                except TypeError:
                    print('Date {} does not parse into 3'.format(fulldate))
                else:
                    if len(dam_date) != 3:
                        print('Date {} does not parse into 3'.format(dam_date))

    return arroyo_num, arroyo_name, dam_name, dam_date, picnum

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
                arroyo_num, arroyo_name, name, date_lst, picnum = parse_relative_fname(rel_fname)
                print("Relative filename {} parses to: ".format(rel_fname))
                print("   Arroyo: {} {}".format(arroyo_num, arroyo_name))
                print("   Dam:    {}, {}-{}-{}, {}".format(
                    name, date_lst[0], date_lst[1], date_lst[2], picnum))


# .............................................................................
def get_bbox(bbox_str):
    bbox = []
    parts = bbox_str.split(',')
    if len(parts) != 4:
        print('Failed to get 4 values for bbox from {}'.format(bbox_str))
    else:
        for i in range(len(parts)):
            pt = parts[i].strip()
            tmp = pt.rstrip(')').lstrip('(')
            try:
                val = float(tmp)
            except:
                print('Failed to parse element {} from {} into float value'
                      .format(i, bbox_str))
            else:
                bbox.append(val)
    return bbox


# ...............................................
def ready_filename(fullfilename, overwrite=True):
    if os.path.exists(fullfilename):
        if overwrite:
            try:
                delete_file(fullfilename)
            except Exception as e:
                raise Exception('Unable to delete {} ({})'.format(fullfilename, e))
            else:
                return True
        else:
            return False
    else:
        pth, _ = os.path.split(fullfilename)
        try:
            os.makedirs(pth)
        except:
            pass

        if os.path.isdir(pth):
            return True
        else:
            raise Exception('Failed to create directories {}'.format(pth))


# ...............................................
def delete_file(file_name, delete_dir=False):
    """Delete file if it exists, delete directory if it becomes empty

    Note:
        If file is shapefile, delete all related files
    """
    shp_extensions = [
        '.shp', '.shx', '.dbf', '.prj', '.sbn', '.sbx', '.fbn', '.fbx', '.ain',
        '.aih', '.ixs', '.mxs', '.atx', '.shp.xml', '.cpg', '.qix']
    success = True
    msg = ''
    if file_name is None:
        msg = 'Cannot delete file \'None\''
    else:
        pth, _ = os.path.split(file_name)
        if file_name is not None and os.path.exists(file_name):
            base, ext = os.path.splitext(file_name)
            if ext == '.shp':
                similar_file_names = glob.glob(base + '.*')
                for sim_file_name in similar_file_names:
                    _, sim_ext = os.path.splitext(sim_file_name)
                    if sim_ext in shp_extensions:
                        try:
                            os.remove(sim_file_name)
                        except Exception as e:
                            success = False
                            msg = 'Failed to remove {}, {}'.format(sim_file_name, str(e))
            else:
                try:
                    os.remove(file_name)
                except Exception as e:
                    success = False
                    msg = 'Failed to remove {}, {}'.format(file_name, str(e))
            if delete_dir and len(os.listdir(pth)) == 0:
                try:
                    os.removedirs(pth)
                except Exception as e:
                    success = False
                    msg = 'Failed to remove {}, {}'.format(pth, str(e))
    return success, msg


# .............................................................................
def get_csv_dict_reader(datafile, delimiter, fieldnames=None):
    try:
        f = open(datafile, 'r')
        if fieldnames is None:
            header = next(f)
            tmpflds = header.split(delimiter)
            fieldnames = [fld.strip() for fld in tmpflds]
        dreader = csv.DictReader(
            f, fieldnames=fieldnames, delimiter=delimiter)

    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return dreader, f


# .............................................................................
def get_csv_dict_writer(csvfile, header, delimiter, fmode="w"):
    """Create a CSV dictionary writer and write the header.

    Args:
        csvfile: output CSV file for writing
        header: header for output file
        delimiter: field separator
        fmode: Write ('w') or append ('a')

    Returns:
        writer (csv.DictWriter) ready to write
        f (file handle)

    Raises:
        Exception: on invalid file mode
        Exception: on failure to create a DictWriter
    """
    if fmode not in ("w", "a"):
        raise Exception("File mode must be 'w' (write) or 'a' (append)")

    csv.field_size_limit(sys.maxsize)
    try:
        f = open(csvfile, fmode, newline="", encoding='utf-8')
        writer = csv.DictWriter(f, fieldnames=header, delimiter=delimiter)
    except Exception as e:
        raise e
    else:
        writer.writeheader()
    return writer, f


# .............................................................................
def get_csv_reader(datafile, delimiter):
    try:
        f = open(datafile, 'r')
        reader = csv.reader(f, delimiter=delimiter)
    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return reader, f


# .............................................................................
def get_csv_writer(datafile, delimiter, doAppend=True):
    csv.field_size_limit(sys.maxsize)
    if doAppend:
        mode = 'ab'
    else:
        mode = 'wb'

    try:
        f = open(datafile, mode)
        writer = csv.writer(f, delimiter=delimiter)
    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return writer, f


# ...............................................
def reduce_image_size(
        infname, outfname, width, sample_method=Image.ANTIALIAS, overwrite=True, log=None):
    if ready_filename(outfname, overwrite=overwrite):
        try:
            img = Image.open(infname)
        except Exception as e:
            logit(log, " *** Unable to open file {}, {}".format(infname, e))
        else:
            wpercent = (width / float(img.size[0]))
            height = int((float(img.size[1]) * float(wpercent)))
            size = (width, height)
            img = img.resize(size, sample_method)
            img.save(outfname)
            logit(log, 'Rewrote image {} to {}'.format(infname, outfname))

