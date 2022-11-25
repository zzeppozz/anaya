import exifread
import os
from osgeo import ogr, osr
from PIL import Image

from dammap.common.constants import (
    IMG_META, IN_DIR, DELIMITER, ANC_DIR, THUMB_DIR, OUT_DIR, SAT_FNAME, SEPARATOR,
    RESIZE_WIDTH, ARROYO_COUNT, IMAGE_COUNT, SHP_FIELDS, SOME_DUPES)


# .............................................................................
class DamMeta(object):
    # ............................................................................
    # Constructor
    # .............................................................................
    def __init(
            self, fullpath, relative_fname, thumbpath=None, basename=None,
            dam_num=None, img_date=None,
            longitude=None, latitude=None, geomwkt=None,
            x_dir=None, x_deg=None, x_min=None, x_sec=None,
            y_dir=None, y_deg=None, y_min=None, y_sec=None,
            in_bounds=None, logger=None):

        self.fullpath = fullpath
        self.relfname = relative_fname

        # Data from directory and filenames
        (
            self.arroyo_num,
            self.arroyo_name,
            self.dam_name,
            self.dam_date,
            self.picnum ) = self.parse_relative_fname()

        # Data from image files
        (self.img_date, xydd, xdms, ydms) = self.get_image_metadata()
        if None in (xydd, xdms, ydms):
            in_bounds = 0
            self.log('Failed to return decimal degrees for {}'.format(self.relfname))
        else:
            (self.x_deg, self.x_min, self.x_sec, self.x_dir) = xdms
            (self.y_deg, self.y_min, self.y_sec, self.y_dir) = ydms
            self.longitude = xydd[0]
            self.latitude = xydd[1]
            self.wkt = 'Point ({:.7f}  {:.7f})'.format(xydd[0], xydd[1])
        self.thumbpath = thumbpath
        self.basename = basename
        # Data from image files
        self.longitude = longitude
        self.latitude = latitude
        self.geomwkt = geomwkt

        self.in_bounds = in_bounds
        self.set_logger(logger)

    # ...............................................
    @property
    def dd_ok(self):
        if None in (
                self.x_deg, self.x_min, self.x_sec, self.x_dir,
                self.y_deg, self.y_min, self.y_sec, self.y_dir,
                self.longitude, self.latitude):
            return False
        return True

    # ...............................................
    def set_logger(self, logger):
        self._logger = logger
        
    # ...............................................
    @classmethod
    def log(self, msg):
        if self._logger is not None:
            self._logger.log(msg)
        else:
            print(msg)

    # ...............................................
    @classmethod
    def parse_relative_fname(self, relfname):
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
    def _get_val_from_alternative_keys(self, tags, alternative_keys):
        # Get value
        for key in alternative_keys:
            try:
                valstr = tags[key].values
            except KeyError:
                valstr = None
            else:
                # If date tag, possible space between date and time
                if key in IMG_META.DATE_KEY_OPTS:
                    try:
                        valstr.index(" ")
                    except ValueError:
                        pass
                    else:
                        valstr = valstr.split(" ")[0]
                break

        return valstr

    # ...............................................
    def get_image_metadata(self, fullname):
        tags = date_tuple = dd = xdms = ydms = None
        # Read image metadata
        try:
            # Open file in binary mode
            f = open(fullname, 'rb')
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self.log('{}: Unable to read image metadata, {}'.format(
                fullname, e))
        finally:
            try:
                f.close()
            except:
                pass
        # Parse image metadata
        if tags:
            dd, xdms, ydms = self._get_dd(tags)
            date_tuple = self._get_date(tags)
        else:
            self.log(f'{fullname}: exifread found no tags')
        return date_tuple, dd, xdms, ydms

    # ...............................................
    def _get_date(self, tags):
        # Get date
        dtstr = self._get_val_from_alternative_keys(tags, IMG_META.DATE_KEY_OPTS)

        if dtstr is not None:
            try:
                return [int(x) for x in dtstr.split(':')]
            except:
                self.log(f"datestr {dtstr} cannot be parsed into integers")
        return []

    # ...............................................
    def _get_location_vals(self, tags, locKey, dirKey, negativeIndicator):
        dd = degrees = minutes = seconds = nsew = None
        isNegative = False
        # Get longitude or latitude
        try:
            degObj, minObj, secObj = tags[locKey].values
        except KeyError:
            gpskeys = [k for k in tags.keys() if k.startswith("GPS")]
            self.log(f"Missing {locKey} in {gpskeys}")
            # raise
        else:
            nsew = tags[dirKey].printable
            if nsew == negativeIndicator:
                isNegative = True
            # Convert to float
            degrees = degObj.num
            minutes = minObj.num
            seconds = float(secObj.real)
            # Convert to decimal degrees
            dd = (seconds/3600) + (minutes/60) + degrees
            if isNegative:
                dd = -1 * dd
        return dd, degrees, minutes, seconds, nsew

    # ...............................................
    def _get_dd(self, tags):
        dd = xdms = ydms = None
        xdd, xdeg, xmin, xsec, xdir = self._get_location_vals(
            tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY, 'W')
        ydd, ydeg, ymin, ysec, ydir = self._get_location_vals(
            tags, IMG_META.Y_KEY, IMG_META.Y_DIR_KEY, 'S')

        if None in (xdd, xdeg, xmin, xsec, xdir, ydd, ydeg, ymin, ysec, ydir):
            self.log(f"Coordinates cannot be parsed")
        else:
            # Convert to desired format
            dd = (xdd, ydd)
            xdms = (xdeg, xmin, xsec, xdir)
            ydms = (ydeg, ymin, ysec, ydir)

        return dd, xdms, ydms
