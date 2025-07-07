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
            thumb=None, arroyo_num=None, arroyo_name=None,
            dam_name=None, dam_date=None, picnum=None,
            img_date=None,
            verbatim_longitude=None, verbatim_latitude=None,
            verbatim_longitude_direction=None, verbatim_latitude_direction=None,
            longitude=None, latitude=None,
            x_dir=None, x_deg=None, x_min=None, x_sec=None,
            y_dir=None, y_deg=None, y_min=None, y_sec=None,
            in_bounds=None, no_geo=None, logger=None):
        """Create a dam object from an image file.

        Args:
            fullpath(str): Full filename and path
            relative_fname (str): directory and filename relative to a common
                directory path
            thumb (str): filename of a thumbnail image relative to a common directory path
            arroyo_num (int): number of the arroyo as determined by the directory name
            arroyo_name (str): name of the arroyo as determined by the directory name
            dam_name (str): name of the dam as determined by the file name
            dam_date (str): date of the dam as determined by the file name
            picnum (str): number of the image file as determined by the file name
            img_date (str): date of the image as determined by the image file metadata
            verbatim_longitude (str): longitude value of the image as reported by the
                image file metadata (d, m, s)
            verbatim_latitude (str): longitude value of the image as reported by the
                image file metadata (d, m, s)
            verbatim_longitude_direction (str): longitude direction (E, W) of the
                image as reported by the image file metadata
            verbatim_latitude_direction (str): latitude direction (N, S) of the
                image as reported by the image file metadata
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
        self.resolved_longitude = None
        self.resolved_latitude = None
        self.verbatim_longitude = verbatim_longitude
        self.verbatim_latitude = verbatim_latitude
        self.verbatim_longitude_direction = verbatim_longitude_direction
        self.verbatim_latitude_direction = verbatim_latitude_direction
        self.img_date = img_date
        self.thumb = thumb
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
            tags = self.get_image_metadata()
            if tags:
                self.img_date, self.guilty_party = self.get_camera_date(tags)
                xydd, xdms, ydms, verbatim_coordinates = self._get_coordinates(tags)
                if None not in (xydd, xdms, ydms, verbatim_coordinates):
                    (self.verbatim_longitude,
                     self.verbatim_longitude_direction,
                     self.verbatim_latitude,
                     self.verbatim_latitude_direction) = verbatim_coordinates
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
        # Get value, first matching alternative key takes precedence
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
        tags = None
        # Read image metadata
        try:
            # Open file in binary mode
            f = open(fullname, "rb")
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self.log(f"   ** Unable to read image {fullname} metadata, {e}")
        finally:
            try:
                f.close()
            except:
                pass
        if not tags:
            self.log(f"   ** exifread found no tags in {fullname}")
        return tags

    # ...............................................
    def get_camera_date(self, tags):
        # Get date
        date_tuple = [0, 0, 0]
        dtstr = self._get_val_from_alternative_keys(tags, IMG_META.DATE_KEY_OPTS)
        if dtstr is not None:
            try:
                date_tuple = [int(x) for x in dtstr.split(":")]
            except:
                self.log(f"datestr {dtstr} cannot be parsed into integers")
        # Get camera and model
        guilty_party = "unknown"
        try:
            guilty_party = f"{tags['Image Make']}: {tags['Image Model']}"
        except:
            pass
        return date_tuple, guilty_party

    # ...............................................
    def _get_location_vals(self, tags, locKey, dirKey):
        dd = degrees = minutes = seconds = nsew = None
        isNegative = False
        # Get longitude or latitude
        try:
            degObj, minObj, secObj = tags[locKey].values
        except KeyError:
            pass
        else:
            nsew = tags[dirKey].printable
            if nsew in IMG_META.NEGATIVE_INDICATORS:
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
    def _get_coordinates(self, tags):
        dd = xdms = ydms = verbatim_coordinates = None
        gpskeys = [k for k in tags.keys() if k.startswith("GPS")]
        # Are the GPS tags present?
        try:
            verbatim_longitude = f"{tags[IMG_META.X_KEY]}"
            verbatim_latitude = f"{tags[IMG_META.Y_KEY]}"
        except KeyError as e:
            self.log(
                f"Missing tag in {gpskeys} for {self.guilty_party}, {e}")
        else:
            try:
                verbatim_longitude_dir = f"{tags[IMG_META.X_DIR_KEY]}"
                verbatim_latitude_dir = f"{tags[IMG_META.Y_DIR_KEY]}"
            except KeyError as e:
                self.log(
                    f"Missing direction tag in {gpskeys} for {self.guilty_party}, {e}")
            else:
                verbatim_coordinates = (
                    verbatim_longitude, verbatim_longitude_dir,
                    verbatim_latitude, verbatim_latitude_dir)
                xdd, xdeg, xmin, xsec, xdir = self._get_location_vals(
                    tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY)
                ydd, ydeg, ymin, ysec, ydir = self._get_location_vals(
                    tags, IMG_META.Y_KEY, IMG_META.Y_DIR_KEY)
                # Convert to desired format
                dd = (xdd, ydd)
                xdms = (xdeg, xmin, xsec, xdir)
                ydms = (ydeg, ymin, ysec, ydir)

        return dd, xdms, ydms, verbatim_coordinates

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
            self. wkt = f"Point ({self.longitude:.7f}  {self.latitude:.7f})"

    # ...............................................
    @property
    def record(self):
        return {
            IMAGE_KEYS.FILE_PATH: self.fullpath,
            IMAGE_KEYS.THUMB: self.thumb,
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
            IMAGE_KEYS.VERB_LON: self.verbatim_longitude,
            IMAGE_KEYS.VERB_LAT: self.verbatim_latitude,
            IMAGE_KEYS.VERB_LON_DIR: self.verbatim_longitude_direction,
            IMAGE_KEYS.VERB_LAT_DIR: self.verbatim_latitude_direction,
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
    @property
    def record_for_csv(self):
        return {
            IMAGE_KEYS.FILE_PATH: self.fullpath,
            IMAGE_KEYS.THUMB: self.thumb,
            IMAGE_KEYS.BASE_NAME: self.basename,
            IMAGE_KEYS.ARROYO_NAME: self.arroyo_name,
            IMAGE_KEYS.ARROYO_NUM: self.arroyo_num,
            IMAGE_KEYS.DAM_NAME: str(self.dam_name),
            IMAGE_KEYS.PIC_NUM: self.picnum,
            IMAGE_KEYS.DAM_DATE: self.dam_date,
            IMAGE_KEYS.IMG_DATE: str(self.img_date),
            IMAGE_KEYS.LON: self.longitude,
            IMAGE_KEYS.LAT: self.latitude,
            IMAGE_KEYS.WKT: self.wkt,
            IMAGE_KEYS.VERB_LON: str(self.verbatim_longitude),
            IMAGE_KEYS.VERB_LAT: str(self.verbatim_latitude),
            IMAGE_KEYS.VERB_LON_DIR: self.verbatim_longitude_direction,
            IMAGE_KEYS.VERB_LAT_DIR: self.verbatim_latitude_direction,
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
