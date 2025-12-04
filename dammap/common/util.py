# File handling, name conversion, bounding box parsing, Image processing common for anaya project
import csv
import glob
import logging
from logging.handlers import RotatingFileHandler
import os, shutil
import sys
import time

from dammap.common.constants import MAC_PATH, IMAGE_EXTENSIONS
from dammap.common.constants import DAM_PREFIX, SEPARATOR

LOG_FORMAT = ' '.join(["%(asctime)s",
                       "%(module)s.%(funcName)s",
                       "line",
                       "%(lineno)d",
                       "%(levelname)-8s",
                       "%(message)s"])
LOG_DATE_FORMAT = '%d %b %Y %H:%M'
LOG_MAX = 52000000


# .............................................................................
def get_logger(outpath, logname=None):
    if not os.path.exists(outpath):
        try:
            os.makedirs(outpath)
        except:
            raise

    level = logging.DEBUG
    secs = time.time()
    timestamp = "{}".format(time.strftime("%Y%m%d-%H%M", time.localtime(secs)))
    if logname is None:
        logname, _ = os.path.splitext(os.path.basename(__file__))
    logfname = os.path.join(outpath, logname + '.log')
    ready_filename(logfname, overwrite=True)
    # get logger
    log = logging.getLogger(logname)
    log.setLevel(level)
    # create file handler
    file_log_handler = RotatingFileHandler(logfname, maxBytes=LOG_MAX, backupCount=2)
    file_log_handler.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    file_log_handler.setFormatter(formatter)
    log.addHandler(file_log_handler)
    # add a console logger
    log.addHandler(logging.StreamHandler(stream=sys.stdout))
    return log, logfname

# .............................................................................
def logit(log, msg):
    if log:
        log.warn(msg)
    else:
        print(msg)

# ...............................................
def stamp(log, msg):
    t = time.localtime()
    log.info('## {} {}-{}-{} {}:{}:{}'.format(
        msg, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))


# ...............................................
def do_recognize_image_file(fname):
    # Read only non-hidden image files
    if not fname.startswith("."):
        for ext in IMAGE_EXTENSIONS:
            if fname.lower().endswith(ext):
                return True
    return False

# ...............................................
def identify_path_element(full_name):
    """Identify whether the path element is an image file, a dam name, or arroyo name.

    Args:
        full_name: full path to a filename or directory name

    Returns:
        One of "image", "dam", "arroyo", or None
    """
    head, tail = os.path.split(full_name)
    # Read only non-hidden files/dirs
    if not tail.startswith("."):
        if os.path.isfile(full_name):
            for ext in IMAGE_EXTENSIONS:
                if full_name.lower().endswith(ext):
                    return "image"
        else:
            parts = tail.split(SEPARATOR)
            try:
                int(parts[0])
                return "arroyo"
            except:
                if parts[0] == DAM_PREFIX:
                    return "dam"
    return None

# ...............................................
def merge_files_into_tree(frompath, topath):
    for root, dirlist, files in os.walk(frompath):
        # for dir in dirlist:
        for fname in files:
            if not fname.startswith("."):
                arroyo_dir = os.path.split(root)[1]
                from_filename = os.path.join(root, fname)
                dest_path = os.path.join(topath, arroyo_dir)
                to_filename = os.path.join(dest_path, fname)
                # Test before move
                if os.path.exists(to_filename):
                    print(f"Old file {to_filename} already exists")
                else:
                    if not os.path.exists(dest_path):
                        os.mkdir(dest_path)
                    os.rename(from_filename, to_filename)
                    print("Rename {} --> {}".format(from_filename, to_filename))

# ...............................................
def rename_in_place(from_fullfname, to_basefname):
    pth = os.path.split(from_fullfname)[0]
    to_fullfname = os.path.join(pth, to_basefname)
    # Test before move
    if os.path.exists(to_fullfname):
        print(f"File {to_fullfname} already exists")
    else:
        os.rename(from_fullfname, to_fullfname)
        print(f"Rename {from_fullfname} --> {to_basefname}")

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
    """Delete overwrite is true and file exists; makedirs if needed.

    Args:
        fullfilename: full path to filename to check for existence and directory.
        overwrite: flag indicating whether to overwrite existing file.

    Returns:
        True if the file does not exist.  False if the file exists and overwrite
        is False.

    Postcondition:
        If overwrite is True, and the file exists, the file will be deleted.
        If the file does not exist, and the directories do not exist, directories will
        be created.
    """
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
def copy_fileandmeta_to_dir(oldpath, newpath, fname, basepath=MAC_PATH):
    """Copy the file with permissions and metadata to a new directory.

    Args:
        oldpath: full path to the parent directory containing the file to copy
        newpath: full path to the new parent directory for the file
        fname: basename of the file to copy
        basepath: common directory for both old and new paths (to shorten log statement)
    """
    old_fullfname = os.path.join(oldpath, fname)
    new_fullfname = os.path.join(newpath, fname)
    idx = len(basepath) + 1
    if ready_filename(new_fullfname, overwrite=True):
        try:
            shutil.copy2(old_fullfname, newpath)
            # print(f"Copied {fname} from  {oldpath[idx:]}  to  {newpath[idx:]}")
        except Exception as e:
            raise Exception(f"Failed to copy {fname} from {oldpath} to {newpath}")


# .............................................................................
def delete_file(file_name, delete_dir=False):
    """Delete file if it exists, delete directory if it becomes empty

    Args:
        file_name: full path to file for deletion
        delete_dir: flag indicating whether to delete the parent directory if it
            is empty after file deletion

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
        f = open(datafile, "r", newline="")
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
        f = open(datafile, 'r', newline="")
        reader = csv.reader(f, delimiter=delimiter)
    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return reader, f


# .............................................................................
def get_csv_writer(datafile, delimiter, doAppend=True):
    csv.field_size_limit(sys.maxsize)
    if doAppend:
        mode = 'a'
    else:
        mode = 'w'

    try:
        f = open(datafile, mode, newline="")
        writer = csv.writer(f, delimiter=delimiter)
    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return writer, f
