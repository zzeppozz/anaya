import exifread
import os
from PIL import Image

from dammap.common.constants import (IMAGE_KEYS, IMG_META, SEPARATOR)
from dammap.common.util import ready_filename

# .............................................................................
class DamMeta(object):
    # ............................................................................
    # Constructor
    # .............................................................................
    def __init__(
            self, fullpath, basepath,
            thumbpath=None, arroyo_num=None, arroyo_name=None,
            dam_name=None, dam_date=None, picnum=None,
            img_date=None, longitude=None, latitude=None,
            x_dir=None, x_deg=None, x_min=None, x_sec=None,
            y_dir=None, y_deg=None, y_min=None, y_sec=None,
            in_bounds=None, no_geo=None, logger=None):
        """Create a dam object from an image file

        Args:
            fullpath(str): Full filename and path
            relative_fname (str): directory and filename relative to a common
                directory path
            thumbpath (str): directory and filename of a thumbnail image relative to a
                common directory path
            arroyo_num (int): number of the arroyo as determined by the directory name
            arroyo_name (str): name of the arroyo as determined by the directory name
            dam_name (str): name of the dam as determined by the file name
            dam_date (str): date of the dam as determined by the file name
            picnum (str): number of the image file as determined by the file name
            img_date (str): date of the image as determined by the image file metadata
            longitude (float): longitude in decimal degrees of the image as computed
                from the image file metadata
            latitude (float): latitude in decimal degrees of the image as computed
                from the image file metadata
            x_dir (str): W (west corresponds to a negative longitude) or E (east
                corresponds to a positive longitude) of the prime meridian, as read
                from the image metadata.
            in decimal degrees of the image as computed
                from the image file metadata
            x_deg (int): longitude degrees, as read from the image metadata.
            x_min (int): longitude minutes, as read from the image metadata.
            x_sec (float): longitude seconds, as read from the image metadata.
            y_dir (str): S (south corresponds to a negative latitude) or N (north
                corresponds to a positive latitude) of the equator, as read
                from the image metadata.
            y_deg (int): latitude degrees, as read from the image metadata.
            y_min (int): latitude minutes, as read from the image metadata.
            y_sec (float): latitude seconds, as read from the image metadata.
            in_bounds (int): 1 if within the extent of some externally provided bounding box
            logger (object): logger for recording messages to file or command line.
        """
        self.set_logger(logger)
        self.fullpath = fullpath
        self._relative_path_idx = len(basepath)
        if not basepath.endswith(os.sep):
            self._relative_path_idx += 1
        self.relfname = self.fullpath[self._relative_path_idx:]
        self.basename = os.path.basename(self.relfname)
        self.x_deg = x_deg
        self.x_min = x_min
        self.x_sec = x_sec
        self.x_dir = x_dir
        self.y_deg = y_deg
        self.y_min = y_min
        self.y_sec = y_sec
        self.y_dir = y_dir
        self.longitude = longitude
        self.latitude = latitude
        self.img_date = img_date
        self.thumbpath = thumbpath
        self.in_bounds = in_bounds
        self.arroyo_num = arroyo_num
        self.arroyo_name = arroyo_name
        self.dam_name = dam_name
        self.dam_date = dam_date
        self.picnum = picnum
        self.wkt = None
        self.guilty_party = "unknown"

        # If any arroyo, dam values are missing, read from fullpath
        if None in (arroyo_num, arroyo_name, dam_name, dam_date, picnum):
            (
                self.arroyo_num,
                self.arroyo_name,
                self.dam_name,
                self.dam_date,
                self.picnum) = self.parse_relative_fname()
        # If any geo values are missing, read from image file metadata
        if None in (
                x_deg, x_min, x_sec, x_dir, y_deg, y_min, y_sec, y_dir,
                longitude, latitude):
            (self.img_date, xydd, xdms, ydms, self.guilty_party
             ) = self.get_image_metadata()
            if None not in (xydd, xdms, ydms):
                (self.x_deg, self.x_min, self.x_sec, self.x_dir) = xdms
                (self.y_deg, self.y_min, self.y_sec, self.y_dir) = ydms
                self.longitude = xydd[0]
                self.latitude = xydd[1]
        self.set_wkt()

    # ...............................................
    def set_logger(self, logger):
        self._logger = logger

    # ...............................................
    def log(self, msg=""):
        if self._logger is not None:
            self._logger.info(msg)
        else:
            print(msg)

    # ...............................................
    def parse_relative_fname(self, relfname=None):
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
        if relfname is None:
            relfname = self.relfname
        arroyo_num = arroyo_name = dam_name = dam_date = picnum = None
        try:
            dirname, fname = relfname.split(os.sep)
        except ValueError:
            print(f"Relfname {relfname} does not parse into 2")
        else:
            try:
                arroyo_num, arroyo_name = dirname.split(SEPARATOR)
            except ValueError:
                print(f"Dirname {dirname} does not parse into 2")
            else:
                basename, ext = os.path.splitext(fname)
                try:
                    dam_name, fulldate, picnum = basename.split(SEPARATOR)
                except ValueError:
                    print(f"Basename {basename} does not parse into 3")
                else:
                    tmp = fulldate.split("-")

                    try:
                        dam_date = [int(d) for d in tmp]
                    except TypeError:
                        print(f"Date {fulldate} does not parse into 3")
                    else:
                        if len(dam_date) != 3:
                            print(f"Date {dam_date} does not parse into 3")

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
    def get_image_metadata(self, fullname=None):
        if fullname is None:
            fullname = self.fullpath
        tags = date_tuple = dd = xdms = ydms = None
        # Read image metadata
        self.log(f"Reading {fullname}")
        try:
            # Open file in binary mode
            f = open(fullname, "rb")
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self.log(f"   ** Unable to read image metadata, {e}")
        finally:
            try:
                f.close()
            except:
                pass
        # Parse image metadata
        guilty_party = "unknown"
        if tags:
            try:
                guilty_party = f"{tags['Image Make']}: {tags['Image Model']}"
            except:
                pass
            dd, xdms, ydms = self._get_dd(tags)
            date_tuple = self._get_date(tags)
            if None in (dd, xdms, ydms):
                self.log(
                    f"   ** Failed to return decimal degrees from {guilty_party}")
        else:
            self.log(f"   ** exifread found no tags")
        return date_tuple, dd, xdms, ydms, guilty_party

    # ...............................................
    def _get_date(self, tags):
        # Get date
        dtstr = self._get_val_from_alternative_keys(tags, IMG_META.DATE_KEY_OPTS)

        if dtstr is not None:
            try:
                return [int(x) for x in dtstr.split(":")]
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
            pass
        else:
            nsew = tags[dirKey].printable
            if nsew == negativeIndicator:
                isNegative = True
            # Convert to float
            degrees = float(degObj.real)
            minutes = float(minObj.real)
            seconds = float(secObj.real)
            # Convert to decimal degrees
            dd = (seconds/3600) + (minutes/60) + degrees
            if isNegative:
                dd = -1 * dd
        return dd, degrees, minutes, seconds, nsew

    # ...............................................
    def _get_dd(self, tags):
        dd = xdms = ydms = None
        # Are the GPS tags present?
        if IMG_META.X_KEY in tags.keys() and IMG_META.Y_KEY in tags.keys():
            xdd, xdeg, xmin, xsec, xdir = self._get_location_vals(
                tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY, "W")
            ydd, ydeg, ymin, ysec, ydir = self._get_location_vals(
                tags, IMG_META.Y_KEY, IMG_META.Y_DIR_KEY, "S")
            # Convert to desired format
            dd = (xdd, ydd)
            xdms = (xdeg, xmin, xsec, xdir)
            ydms = (ydeg, ymin, ysec, ydir)
        else:
            self.log(f"Missing {IMG_META.X_KEY} or {IMG_META.Y_KEY} in tags for camera {self.guilty_party}")

        return dd, xdms, ydms

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
    def set_wkt(self):
        if self.dd_ok:
            self.wkt = "Point ({:.7f}  {:.7f})".format(self.longitude, self.latitude)

    # ...............................................
    @property
    def record(self):
        return {
            IMAGE_KEYS.FILE_PATH: self.fullpath,
            IMAGE_KEYS.THUMB_PATH: self.thumbpath,
            IMAGE_KEYS.BASE_NAME: self.basename,
            IMAGE_KEYS.ARROYO_NAME: self.arroyo_name,
            IMAGE_KEYS.ARROYO_NUM: self.arroyo_num,
            IMAGE_KEYS.DAM_NAME: self.dam_name,
            IMAGE_KEYS.PIC_NUM: self.picnum,
            IMAGE_KEYS.DAM_DATE: self.dam_date,
            IMAGE_KEYS.IMG_DATE: self.img_date,
            IMAGE_KEYS.LON: self.longitude,
            IMAGE_KEYS.LAT: self.latitude,
            IMAGE_KEYS.WKT: self.wkt,
            IMAGE_KEYS.X_DIR: self.x_dir,
            IMAGE_KEYS.X_DEG: self.x_deg,
            IMAGE_KEYS.X_MIN: self.x_min,
            IMAGE_KEYS.X_SEC: self.x_sec,
            IMAGE_KEYS.Y_DIR: self.y_dir,
            IMAGE_KEYS.Y_DEG: self.y_deg,
            IMAGE_KEYS.Y_MIN: self.y_min,
            IMAGE_KEYS.Y_SEC: self.y_sec,
            IMAGE_KEYS.IN_BNDS: self.in_bounds,
            IMAGE_KEYS.NO_GEO: self.dd_ok
        }

    # ...............................................
    def resize(self, outfname, width, sample_method=Image.ANTIALIAS, overwrite=True, log=None):
        resized = False
        if ready_filename(outfname, overwrite=overwrite):
            try:
                img = Image.open(self.fullpath)
            except Exception as e:
                self.log(f" *** Unable to open file {self.fullpath}, {e}")
            else:
                (orig_w, _) = img.size
                if orig_w <= width:
                    self.log(f"Image {self.fullpath} width {orig_w} cannot be reduced, saving to {outfname}")
                    img.save(outfname)
                else:
                    wpercent = (width / float(img.size[0]))
                    height = int(float(img.size[1]) * float(wpercent))
                    size = (width, height)
                    img = img.resize(size, sample_method)
                    img.save(outfname)
                    self.log(f"Reduced image {self.fullpath}, width {orig_w} to {outfname}, width {width}")
                    resized = True
        return resized