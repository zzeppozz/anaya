from enum import Enum
import inspect

GEOM_WKT = "geomwkt"
LONG_FLD = "longitude"
LAT_FLD = "latitude"

# def get_image_keys(key_class):
#     keys = []
#     members = inspect.getmembers(key_class, lambda a: not (inspect.isroutine(a)))
#     for a in members:
#         if not a[0].startswith("__") and a[0].endswith('__'):
#             keys.append(a[1])
#     return keys

# Metadata for all dam data
class ALL_DATA_KEYS (Enum):
    BASE_PATH = "base_path"
    ARROYO_COUNT = "arroyo_count"
    ARROYO_META = "arroyo_meta"
    IMAGE_META = "img_meta"
    IMG_COUNT = "img_count"
    IMG_GEO_COUNT = "img_count_geo"
    OUT_OF_RANGE = "out_of_range"
    DAM_DATE = "dam_date"

# Metadata for image files
class IMAGE_KEYS(Enum):
    # Data from directory and filenames
    FILE_PATH = "fullpath"
    ARROYO_NAME = "arroyo"
    ARROYO_NUM = "arroyo_num"
    DAM_NAME = "dam"
    DAM_NUM = "dam_num"
    DAM_DATE = "dam_date"
    # Data from image files
    IMG_DATE = "img_date"
    LON = "longitude"
    LAT = "latitude"
    WKT = "geomwkt"
    X_DIR = "xdirection"
    X_DEG = "xdegrees"
    X_MIN = "xminutes"
    X_SEC = "xseconds"
    Y_DIR = "ydirection"
    Y_DEG = "ydegrees"
    Y_MIN = "yminutes"
    Y_SEC = "yseconds"
    IN_BNDS = "in_bounds"

CSV_FIELDS = [
    IMAGE_KEYS.FILE_PATH,
    IMAGE_KEYS.ARROYO_NAME,
    IMAGE_KEYS.ARROYO_NUM,
    IMAGE_KEYS.DAM_NAME,
    IMAGE_KEYS.DAM_NUM,
    IMAGE_KEYS.DAM_DATE,
    IMAGE_KEYS.IMG_DATE,
    IMAGE_KEYS.LON,
    IMAGE_KEYS.LAT,
    IMAGE_KEYS.WKT,
    IMAGE_KEYS.X_DIR,
    IMAGE_KEYS.X_DEG,
    IMAGE_KEYS.X_MIN,
    IMAGE_KEYS.X_SEC,
    IMAGE_KEYS.Y_DIR,
    IMAGE_KEYS.Y_DEG,
    IMAGE_KEYS.Y_MIN,
    IMAGE_KEYS.Y_SEC,
    IMAGE_KEYS.IN_BNDS
]

DELIMITER = "\t"
ENCODING = "utf-8"
SEPARATOR = "_"

# Sanity check
ARROYO_COUNT = 69
IMAGE_COUNT = 2886

# Path/filenames
IN_DIR = "dams"
ANC_DIR = "ancillary"
OUT_DIR ="outdam"
THUMB_DIR = "thumb"
THUMB_DIR_SMALL = "small_thumb"
SAT_FNAME = "op140814.tif"
RESIZE_WIDTH = 500
SAT_IMAGE_FNAME = "op140814.tif"

# maxY = 35.45045
# minY = 35.43479
# maxX = -106.05353
# minX = -106.07259
# 
# dam_buffer = .0002
# resize_width = 500


# .............................................................................
class IMG_META:
    X_KEY = "GPS GPSLongitude"
    X_DIR_KEY = "GPS GPSLongitudeRef"
    Y_KEY = "GPS GPSLatitude"
    Y_DIR_KEY = "GPS GPSLatitudeRef"
    DATE_KEY = "GPS GPSDate"
