GEOM_WKT = "geomwkt"
LONG_FLD = 'longitude'
LAT_FLD = 'latitude'

IMAGES_KEY = 'images'
CSV_FIELDS = (
    'arroyo', 'arroyo_num', 'dam', 'dam_num', 'dam_date', 'img_date', 
    LONG_FLD, LAT_FLD, GEOM_WKT, 'xdirection', 'xdegrees', 'xminutes', 'xseconds',
    'ydirection', 'ydegrees', 'yminutes', 'yseconds', 'fullpath')

DELIMITER = '\t'
ENCODING = 'utf-8'

BASE_PATH='/Users/astewart/Home/Anaya/anaya_map'
IN_DIR = 'dams'
ANC_DIR = 'ancillary'
OUT_DIR = 'output'
OUT_NAME = 'dam_anaya'
THUMB_DIR = 'thumb'
THUMB_DIR_SMALL = 'small_thumb'
SAT_FNAME = 'op140814.tif'
RESIZE_WIDTH = 500

LOG_FORMAT = ' '.join(["%(asctime)s",
                   "%(threadName)s.%(module)s.%(funcName)s",
                   "line",
                   "%(lineno)d",
                   "%(levelname)-8s",
                   "%(message)s"])
LOG_DATE_FORMAT = '%d %b %Y %H:%M'
LOG_MAX = 52000000

# {'arroyo': arroyo_name, 
#   'arroyo_num': arroyo_num,
#   'dam': dam_name,
#   'dam_num': picnum,
#   'dam_date': dam_date,
#   'img_date': img_date,
#   LONG_FLD: lon,
#   LAT_FLD: lat,
#   GEOM_WKT: wkt,
#   'xdirection': xdir,
#   'xdegrees': xdeg,
#   'xminutes': xmin, 
#   'xseconds': xsec,
#   'ydirection': ydir,
#   'ydegrees': ydeg,
#   'yminutes': ymin,
#   'yseconds': ysec,
#   'fullpath': fullfname}

# maxY = 35.45045
# minY = 35.43479
# maxX = -106.05353
# minX = -106.07259
# 
# dam_buffer = .0002
# resize_width = 500


# .............................................................................
class IMG_META:
    X_KEY = 'GPS GPSLongitude'
    X_DIR_KEY = 'GPS GPSLongitudeRef'
    Y_KEY = 'GPS GPSLatitude'
    Y_DIR_KEY = 'GPS GPSLatitudeRef'
    DATE_KEY = 'GPS GPSDate'
