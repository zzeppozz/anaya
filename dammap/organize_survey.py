"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime

kml_flag = False
shp_flag = False
import os

from dammap.common.constants import (
    DAM_BUFFER, EARLY_DATA_DIR, MAC_PATH, MAX_X, MAX_Y, MIN_X, MIN_Y, OUT_DIR,
    SURVEY_DIR)
from dammap.common.util import (
    get_logger, do_recognize_image_file, rename_in_place, copy_fileandmeta_to_dir)
from dammap.common.name import DamNameOp
from dammap.common.dammeta import DamMeta
from dammap.transform.dam_map import PicMapper

# DELETE_CHARS = ["\"", ",", """, " ", "(", ")", "_"]

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
def create_dam_subdir_structure_for_unique_dams(surveypath, newroot):
    """Create subdirectories for each dam within each arroyo directory.

    Args:
        surveypath: full path to directory containing arroyo directories containing
            images.
        newroot: full path for new directory containing arroyo directories containing
            dam subdirectories containing images.

    Note:
        This function assumes that each image represents a unique dam, none are grouped.

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
    logger.info("Start Restructuring Arroyos/Dams")
    for root, arroyos, _ in os.walk(surveypath):
        for arr in arroyos:
            # Start numbering dams in arroyo, 1 per image
            damnum = 0
            logger.info(f"Arroyo {arr}")
            oldpath = os.path.join(root, arr)
            files = os.listdir(oldpath)
            for fname in files:
                if do_recognize_image_file(fname):
                    damnum += 1
                    damdir = f"dam_{damnum}"
                    newpath = os.path.join(newroot, arr, damdir)
                    # logger.info(f"Dam {damdir}")
                    oldpath = os.path.join(root, arr)
                    copy_fileandmeta_to_dir(oldpath, newpath, fname)


# ...............................................
def group_dams_into_subdir_structure(surveypath, newroot):
    """Create subdirectories for multiple images per dam within each arroyo directory.

    Args:
        surveypath: full path to directory containing arroyo directories containing
            images.
        outpath: full path for new directory containing arroyo directories containing
            dam subdirectories containing images.

    Note:
        This function assumes that more than one image (one per year) may exist for a
        single dam.  All images for one dam will be grouped into the same dam_x
        subdirectory.

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
    logger.info("Start Restructuring and Grouping Dam Images into Arroyos/Dams")
    inpath = os.path.join(MAC_PATH, EARLY_DATA_DIR)
    pm = PicMapper(inpath, buffer_distance=DAM_BUFFER, logger=logger)
    logger.info("Start")

    # Sets all_data dictionary on object
    read_count = pm.populate_images()
    logger.info(f"Read {read_count} filenames")
                    if damrec.has_meta:
                        damnum += 1
                        damdir = f"dam_{damnum}"
                        newpath = os.path.join(newroot, arr, damdir)
                        # logger.info(f"Dam {damdir}")
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
    organized_surveypath = os.path.join(MAC_PATH, "dam_2025")
    earlypath = os.path.join(MAC_PATH, EARLY_DATA_DIR)
    outpath = os.path.join(MAC_PATH, OUT_DIR)
    logger = get_logger(outpath, logname=name)

    # Rename image files to be standard
    # standardize_camera_filenames(surveypath)

    # Separate 2025_survey data into one image per dam
    create_dam_subdir_structure_for_unique_dams(surveypath, )
    group_dams_into_subdir_structure(surveypath, organized_surveypath)



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