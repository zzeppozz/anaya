GEOM_WKT = "geomwkt"
LONG_FLD = 'longitude'
LAT_FLD = 'latitude'

DELIMITER = '\t'

BASE_PATH='/Users/astewart/Home/Anaya/anaya_map'
IN_DIR = 'dams'
ANC_DIR = 'ancillary'
OUT_DIR = 'out'
OUT_NAME = 'dam_anaya'
THUMB_DIR = 'thumb'
THUMB_DIR_SMALL = 'small_thumb'
SAT_FNAME = 'op140814.tif'

LOG_FORMAT = ' '.join(["%(asctime)s",
                   "%(threadName)s.%(module)s.%(funcName)s",
                   "line",
                   "%(lineno)d",
                   "%(levelname)-8s",
                   "%(message)s"])
LOG_DATE_FORMAT = '%d %b %Y %H:%M'
LOG_MAX = 52000000

# .............................................................................
class IMG_META:
    X_KEY = 'GPS GPSLongitude'
    X_DIR_KEY = 'GPS GPSLongitudeRef'
    Y_KEY = 'GPS GPSLatitude'
    Y_DIR_KEY = 'GPS GPSLatitudeRef'
    DATE_KEY = 'GPS GPSDate'
