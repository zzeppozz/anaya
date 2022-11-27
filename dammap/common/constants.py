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
DUPES_FNAME = "duplicate_coords"
DUPES_SHPFNAME = "analyze/anaya_overlaps.shp"

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
    PIC_NUM = "pic_num"
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
    NO_GEO = "no_geo"

SHP_FIELDS = [
    (IMAGE_KEYS.FILE_PATH, ogr.OFTString),
    (IMAGE_KEYS.THUMB_PATH, ogr.OFTString),
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
#
# dam_buffer = .0002
# resize_width = 500


# .............................................................................
class IMG_META:
    X_KEY = "GPS GPSLongitude"
    X_DIR_KEY = "GPS GPSLongitudeRef"
    Y_KEY = "GPS GPSLatitude"
    Y_DIR_KEY = "GPS GPSLatitudeRef"
    DATE_KEY_OPTS = ["GPS GPSDate", "Image DateTime", "EXIF DateTimeOriginal"]

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

SOME_DUPES = [
    [
        "14_Liz/liz_2021-07-11_0671", "14_Liz/liz_2021-07-11_0681", "14_Liz/liz_2021-07-11_0691",
        "14_Liz/liz_2021-07-11_0701", "14_Liz/liz_2021-07-11_0721", "14_Liz/liz_2021-07-11_0731",
        "14_Liz/liz_2021-07-11_0741"
        "17_Josie/josie_2021-08-01.0011", "17_Josie/josie_2021-08-01.0021", "17_Josie/josie_2021-08-01.0031",
        "17_Josie/josie_2021-08-01.0041", "17_Josie/josie_2021-08-01.0051", "17_Josie/josie_2021-08-01.0061",
        "17_Josie/josie_2021-08-01.0071", "17_Josie/josie_2021-08-01.0081", "17_Josie/josie_2021-08-01.0091",
        "17_Josie/josie_2021-08-01.0101", "17_Josie/josie_2021-08-01.0111", "17_Josie/josie_2021-08-01.0121",
        "17_Josie/josie_2021-08-01.0131", "17_Josie/josie_2021-08-01.0141", "17_Josie/josie_2021-08-01.0151",
        "17_Josie/josie_2021-08-01.0161", "17_Josie/josie_2021-08-01.0171", "17_Josie/josie_2021-08-01.0181",
        "17_Josie/josie_2021-08-01.0191",
        "17_Josie/josie_2021-08-01.0201", "17_Josie/josie_2021-08-01.0211", "17_Josie/josie_2021-08-01.0231",
        "17_Josie/josie_2021-08-01.0251", "17_Josie/josie_2021-08-01.0261", "17_Josie/josie_2021-08-01.0281",
        "17_Josie/josie_2021-08-01.0291"
        "46_Sauna/sauna_2021-07-16.0011"
        "5_Cottonwood/cottonwood_2021-07-30_0041", "5_Cottonwood/cottonwood_2021-07-30_0051",
        "5_Cottonwood/cottonwood_2021-07-30_0061", "5_Cottonwood/cottonwood_2021-07-30_0071",
        "5_Cottonwood/cottonwood_2021-07-30_0081", "5_Cottonwood/cottonwood_2021-07-30_0091",
        "5_Cottonwood/cottonwood_2021-07-30_0101"
    ],
    [
        "16_Spillover/spillover_2014-11-22_024",
        "18_Gerroyo/gerroyo_2014-11-23_0011", "18_Gerroyo/gerroyo_2014-11-23_0021",
        "18_Gerroyo/gerroyo_2014-11-23_0031", "18_Gerroyo/gerroyo_2014-11-23_0071",
        "18_Gerroyo/gerroyo_2014-11-23_0111", "18_Gerroyo/gerroyo_2014-11-23_0141",
        "18_Gerroyo/gerroyo_2014-11-23_0151", "18_Gerroyo/gerroyo_2014-11-23_0161",
        "18_Gerroyo/gerroyo_2014-11-23_0171", "18_Gerroyo/gerroyo_2014-11-23_0181"
    ]

]

