# File handling, name conversion, bounding box parsing, Image processing tools for anaya project
import csv
import glob
import logging
from logging.handlers import RotatingFileHandler
import os
from PIL import Image
import sys
import time

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
def get_bbox(bbox_str, log=None):
    bbox = []
    parts = bbox_str.split(',')
    if len(parts) != 4:
        logit(log, 'Failed to get 4 values for bbox from {}'.format(bbox_str))
    else:
        for i in range(len(parts)):
            pt = parts[i].strip()
            tmp = pt.rstrip(')').lstrip('(')
            try:
                val = float(tmp)
            except:
                logit(log, 'Failed to parse element {} from {} into float value'
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
def get_csv_dict_reader(datafile, delimiter, fieldnames=None, log=None):
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
    else:
        logit(log, 'Opened file {} for dict read'.format(datafile))
    return dreader, f

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
        img = Image.open(infname)
        wpercent = (width / float(img.size[0]))
        height = int((float(img.size[1]) * float(wpercent)))
        size = (width, height)
        img = img.resize(size, sample_method)
        img.save(outfname)
        logit(log, 'Rewrote image {} to {}'.format(infname, outfname))
