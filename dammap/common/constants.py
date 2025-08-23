from osgeo import ogr, osr

MAC_PATH = "/Users/astewart/Documents/anaya_latest"
BASE_PATH = "/tank/anaya/"

# Path/filenames
IN_DIR = "dams_2023"
SURVEY_DIR = "2025_survey"
ANC_DIR = "ancillary"
OUT_DIR ="outdam"
THUMB_DIR = "thumb"
THUMB_DIR_SMALL = "small_thumb"
SAT_FNAME = "op140814.tif"
RESIZE_WIDTH = 500
SAT_IMAGE_FNAME = "op140814.tif"
DUPES_FNAME = "duplicate_coords"
DUPES_SHPFNAME = "analyze/anaya_overlaps.shp"

DAM_BUFFER = .005
THUMB_WIDTH = 2000


MAX_Y = 35.45045
MIN_Y = 35.43479
MAX_X = -106.05353
MIN_X = -106.07259

# Sanity check
ARROYO_COUNT = 69
IMAGE_COUNT = 2886

DELIMITER = "\t"
ENCODING = "utf-8"
SEPARATOR = "_"

SPACE = " "
PARENS = ["(", ")"]
DELETES = ["'", ""]


# Metadata for all dam data
class ALL_DATA_KEYS ():
    BASE_PATH = "base_path"
    ARROYO_COUNT = "arroyo_count"
    ARROYO_META = "arroyo_meta"
    IMAGE_META = "img_meta"
    IMAGE_OUT_OF_RANGE = "img_out_of_range_meta"
    IMG_COUNT = "img_count"
    IMG_GEO_COUNT = "img_count_geo"
    UNIQUE_COORDS = "unique_coordinates"
    WITHIN_BUFFER = "coordinates_within_buffer"
    UNIQUE_CAMERAS = "cameras"

# Metadata for image files
class IMAGE_KEYS():
    # Data from directory and filenames
    FILE_PATH = "fullpath"
    THUMB = "thumb"
    BASE_NAME = "basename"
    ARROYO_NAME = "arroyo"
    ARROYO_NUM = "arroyo_num"
    DAM_NAME = "dam"
    PIC_NUM = "pic_num"
    DAM_DATE = "dam_date"
    # Data from image files
    IMG_DATE = "img_date"
    LON = "longitude"
    LAT = "latitude"
    WKT = "geomwkt"
    VERB_LON = "vlong"
    VERB_LAT = "vlat"
    VERB_LON_DIR = "vlong_dir"
    VERB_LAT_DIR = "vlat_dir"
    X_DIR = "x_dir"
    X_DEG = "x_deg"
    X_MIN = "x_min"
    X_SEC = "x_sec"
    Y_DIR = "y_dir"
    Y_DEG = "y_deg"
    Y_MIN = "y_min"
    Y_SEC = "y_sec"
    IN_BNDS = "in_bounds"
    NO_GEO = "no_geo"

SHP_FIELDS = [
    (IMAGE_KEYS.FILE_PATH, ogr.OFTString),
    (IMAGE_KEYS.THUMB, ogr.OFTString),
    (IMAGE_KEYS.BASE_NAME, ogr.OFTString),
    (IMAGE_KEYS.ARROYO_NAME, ogr.OFTString),
    (IMAGE_KEYS.ARROYO_NUM, ogr.OFTInteger),
    (IMAGE_KEYS.DAM_NAME, ogr.OFTString),
    (IMAGE_KEYS.PIC_NUM, ogr.OFTString),
    (IMAGE_KEYS.DAM_DATE, ogr.OFTString),
    (IMAGE_KEYS.IMG_DATE, ogr.OFTString),
    (IMAGE_KEYS.LON, ogr.OFTReal),
    (IMAGE_KEYS.LAT, ogr.OFTReal),
    (IMAGE_KEYS.WKT, ogr.OFTString),
    (IMAGE_KEYS.VERB_LON, ogr.OFTString),
    (IMAGE_KEYS.VERB_LAT, ogr.OFTString),
    (IMAGE_KEYS.VERB_LON_DIR, ogr.OFTString),
    (IMAGE_KEYS.VERB_LAT_DIR, ogr.OFTString),
    (IMAGE_KEYS.X_DIR, ogr.OFTString),
    (IMAGE_KEYS.X_DEG, ogr.OFTInteger),
    (IMAGE_KEYS.X_MIN, ogr.OFTInteger),
    (IMAGE_KEYS.X_SEC, ogr.OFTReal),
    (IMAGE_KEYS.Y_DIR, ogr.OFTString),
    (IMAGE_KEYS.Y_DEG, ogr.OFTInteger),
    (IMAGE_KEYS.Y_MIN, ogr.OFTInteger),
    (IMAGE_KEYS.Y_SEC, ogr.OFTReal),
    (IMAGE_KEYS.IN_BNDS, ogr.OFTInteger),
    (IMAGE_KEYS.NO_GEO, ogr.OFTInteger)
    ]


# maxY = 35.45045
# minY = 35.43479
# maxX = -106.05353
# minX = -106.07259

# .............................................................................
class IMG_META:
    """Class with metadata tags and value options in image files"""
    X_KEY = "GPS GPSLongitude"
    X_DIR_KEY = "GPS GPSLongitudeRef"
    Y_KEY = "GPS GPSLatitude"
    Y_DIR_KEY = "GPS GPSLatitudeRef"
    DATE_KEY_OPTS = ["GPS GPSDate", "Image DateTime", "EXIF DateTimeOriginal"]
    NEGATIVE_INDICATORS = ["W", "S"]

BAD_PATH = "/tank/anaya/dams/"
BAD_FILES = [
    "42_Bend/bend_2021-03-10_0131.JPG", #: Unable to get date, 'GPS GPSDate'
    "42_Bend/bend_2021-03-10_0041.JPG", #: Unable to get date, 'GPS GPSDate'
    "42_Bend/bend_2021-03-10_0151.JPG", #: Unable to get date, 'GPS GPSDate'
    "42_Bend/bend_2021-03-10_0011.JPG", #: Unable to get date, 'GPS GPSDate'
    "46_Sauna/sauna_2013-10-11_0161.JPG", #: Unable to get x y, 'GPS GPSLongitude'
    "46_Sauna/sauna_2013-10-11_0161.JPG", #: Unable to get date, 'GPS GPSDate'
    # Failed to return decimal degrees for
    "46_Sauna/sauna_2013-10-11_0161.JPG",
    "32_Fenceline/fenceline_2021-01-16_0041.JPG",
    "5_Cottonwood/cottonwood_2015-11-09_0008.JPG",
    "5_Cottonwood/cottonwood_2017-05-08_0021.JPG",
    "5_Cottonwood/cottonwood_2017-12-04_0025.JPG",
    "5_Cottonwood/cottonwood_2018-03-22_0003.JPG",
    "5_Cottonwood/cottonwood_2016-04-24_0010.JPG",
    "5_Cottonwood/cottonwood_2016-12-24_0016.JPG",
    "5_Cottonwood/cottonwood_2016-04-26_0014.JPG",
    "5_Cottonwood/cottonwood_2016-04-24_0011.JPG",
    "5_Cottonwood/cottonwood_2018-03-22_0028.JPG",
    "5_Cottonwood/cottonwood_2018-03-22_0005.JPG",
    "5_Cottonwood/cottonwood_2018-05-07_0002.JPG",
]

