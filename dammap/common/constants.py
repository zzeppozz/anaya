from osgeo import ogr, osr

# Path/filenames
IN_DIR = "dams"
ANC_DIR = "ancillary"
OUT_DIR ="outdam"
THUMB_DIR = "thumb"
THUMB_DIR_SMALL = "small_thumb"
SAT_FNAME = "op140814.tif"
RESIZE_WIDTH = 500
SAT_IMAGE_FNAME = "op140814.tif"

# Sanity check
ARROYO_COUNT = 69
IMAGE_COUNT = 2886

DELIMITER = "\t"
ENCODING = "utf-8"
SEPARATOR = "_"

# Metadata for all dam data
class ALL_DATA_KEYS ():
    BASE_PATH = "base_path"
    ARROYO_COUNT = "arroyo_count"
    ARROYO_META = "arroyo_meta"
    IMAGE_META = "img_meta"
    IMAGE_OUT_OF_RANGE = "img_out_of_range_meta"
    IMG_COUNT = "img_count"
    IMG_GEO_COUNT = "img_count_geo"

# Metadata for image files
class IMAGE_KEYS():
    # Data from directory and filenames
    FILE_PATH = "fullpath"
    THUMB_PATH = "thumbpath"
    BASE_NAME = "basename"
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
    X_DIR = "x_dir"
    X_DEG = "x_deg"
    X_MIN = "x_min"
    X_SEC = "x_sec"
    Y_DIR = "y_dir"
    Y_DEG = "y_deg"
    Y_MIN = "y_min"
    Y_SEC = "y_sec"
    IN_BNDS = "in_bounds"

SHP_FIELDS = [
    # Only for shapefiles
    ('thumbpath', ogr.OFTString),
    ('thumbname', ogr.OFTString),
    # Saved in dictionary and CSV
    (IMAGE_KEYS.FILE_PATH, ogr.OFTString),
    (IMAGE_KEYS.ARROYO_NAME, ogr.OFTString),
    (IMAGE_KEYS.ARROYO_NUM, ogr.OFTInteger),
    (IMAGE_KEYS.DAM_NAME, ogr.OFTString),
    (IMAGE_KEYS.DAM_NUM, ogr.OFTString),
    (IMAGE_KEYS.DAM_DATE, ogr.OFTString),
    (IMAGE_KEYS.IMG_DATE, ogr.OFTString),
    (IMAGE_KEYS.LON, ogr.OFTReal),
    (IMAGE_KEYS.LAT, ogr.OFTReal),
    (IMAGE_KEYS.WKT, ogr.OFTString),
    (IMAGE_KEYS.X_DIR, ogr.OFTString),
    (IMAGE_KEYS.X_DEG, ogr.OFTReal),
    (IMAGE_KEYS.X_MIN, ogr.OFTReal),
    (IMAGE_KEYS.X_SEC, ogr.OFTReal),
    (IMAGE_KEYS.Y_DIR, ogr.OFTString),
    (IMAGE_KEYS.Y_DEG, ogr.OFTReal),
    (IMAGE_KEYS.Y_MIN, ogr.OFTReal),
    (IMAGE_KEYS.Y_SEC, ogr.OFTReal),
    (IMAGE_KEYS.IN_BNDS, ogr.OFTInteger)
    ]


CSV_FIELDS = [f[0] for f in SHP_FIELDS]

CSV_FIELDS_SMALL = [
    IMAGE_KEYS.FILE_PATH,
    IMAGE_KEYS.ARROYO_NAME,
    IMAGE_KEYS.ARROYO_NUM,
    IMAGE_KEYS.DAM_NAME,
    IMAGE_KEYS.DAM_NUM,
    IMAGE_KEYS.DAM_DATE
]


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
    DATE_KEY_OPTS = ["GPS GPSDate", "Image DateTime"]

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