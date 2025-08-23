"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime
import shutil

from dammap.common.constants import (
    MAC_PATH, IN_DIR, OUT_DIR, MAX_X, MAX_Y, MIN_X, MIN_Y)
from dammap.common.util import (get_logger, stamp)
from dammap.transform.dam_map import PicMapper

kml_flag = False
shp_flag = False
import os
from PIL import Image

from dammap.common.constants import (
    MAC_PATH, SURVEY_DIR, OUT_DIR)
from dammap.common.util import get_logger, rename_in_place, copy_fileandmeta_to_dir
from dammap.common.name import DamNameOp
from dammap.common.dammeta import DamMeta

# from dammap.common.constants import ALL_DATA_KEYS as ADK
# from dammap.common.constants import IMAGE_KEYS as IK

# DELETE_CHARS = ["\"", ",", """, " ", "(", ")", "_"]
image_extensions = (".jpg", ".tif", ".tiff")

# ...............................................
def do_recognize_image_file(fname):
    # Read only non-hidden image files
    if not fname.startswith("."):
        for ext in image_extensions:
            if fname.lower().endswith(ext):
                return True
    return False

# ...............................................
def standardize_camera_filenames(surveypath):
    logger.info("Start Standardizing Camera Filenames")
    for root, arroyos, _ in os.walk(surveypath):
        for arr in arroyos:
            pth = os.path.join(root, arr)
            files = os.listdir(pth)
            for fname in files:
                if do_recognize_image_file(fname):
                    fullfname = os.path.join(root, arr, fname)

                    # Get metadata from directory and filename
                    damrec = DamMeta(fullfname, surveypath, logger=logger)
                    if damrec.has_meta:
                        new_basefname = DamNameOp.create_filename(fullfname, damrec)
                        rename_in_place(fullfname, new_basefname)
                    else:
                        logger.info(f"Cannot read metadata from {fullfname}")

# ...............................................
def create_dam_subdir_structure(surveypath, newroot, do_group=False):
    """Create subdirectories for each dam within each arroyo directory.

    Args:
        surveypath: full path to directory containing arroyo directories containing
            images.
        outpath: full path for new directory containing arroyo directories containing
            dam subdirectories containing images.
        do_group: if true, group dams with identical GPS coordinates into the same dam
            subdirectory, if false, each image represents a unique dam.

    Postcondition:
        Creates and populates a new directory tree with another level of directories
        below arroyos, like:
            outpath
                arroyo_a
                    dam_1
                    dam_2
                    ...
                arroyo_b
                    dam_1
                    dam_2
                    ...
    """
    logger.info("Start Standardizing Camera Filenames")

    for root, arroyos, _ in os.walk(surveypath):
        for arr in arroyos:
            oldpath = os.path.join(root, arr)
            files = os.listdir(oldpath)
            for fname in files:
                # Start numbering dams, 1 per image
                if do_group is False:
                    damnum = 1
                    damdir = f"dam_{damnum}"
                    newpath = os.path.join(newroot, arr, damdir)
                if do_recognize_image_file(fname):
                    oldpath = os.path.join(root, arr)
                    copy_fileandmeta_to_dir(oldpath, newpath, fname)




# ...............................................
if __name__ == "__main__":
    n = datetime.datetime.now()
    datestr = f"{n.year}-{n.month}-{n.day}"
    name = f"organize_survey_{datestr}"
    is_dev = False
    bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

    surveypath = os.path.join(MAC_PATH, SURVEY_DIR)
    organized_path = os.path.join(MAC_PATH, "dam_2025")
    outpath = os.path.join(MAC_PATH, OUT_DIR)
    logger = get_logger(outpath, logname=name)

    # Rename image files to be standard
    # standardize_camera_filenames(surveypath)

    # Separate 2025_survey data into one image per dam
    create_dam_subdir_structure(surveypath, organized_path, do_group=False)



"""
n = datetime.datetime.now()
datestr = f"{n.year}-{n.month}-{n.day}"
name = f"organize_survey_{datestr}"
is_dev = False
bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

surveypath = os.path.join(MAC_PATH, SURVEY_DIR)
outpath = os.path.join(MAC_PATH, OUT_DIR)

for root, arroyos, files in os.walk(surveypath):
    for arr in arroyos:
        for fname in files:
            # Read only non-hidden jpg files
            if not fname.startswith(".") and fname.lower().endswith("tiff"):
                fullfname = os.path.join(root, fname)

                # Get metadata from directory and filename
                damrec = DamMeta(fullfname, surveypath, logger=logger)
                new_basefname = DamNameOp.create_filename(fullfname, damrec)
                rename_in_place(fullfname, new_basefname)

"""