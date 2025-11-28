"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime

kml_flag = False
shp_flag = False
import os

from dammap.common.constants import (
    AGG_DIR, DAM_BUFFER, DAM_PREFIX, EARLY_DATA_DIR, MAC_PATH, MAX_X, MAX_Y, MIN_X, MIN_Y,
    OUT_DIR, SEPARATOR, SURVEY_DAMSEP_DIR, SURVEY_DIR)
from dammap.common.util import (
    get_logger, do_recognize_image_file, rename_in_place, copy_fileandmeta_to_dir)
from dammap.common.name import DamNameOp
from dammap.common.dammeta import DamMeta
from dammap.transform.dam_map import PicMapper

# DELETE_CHARS = ["\"", ",", """, " ", "(", ")", "_"]

# ...............................................
def standardize_camera_filenames(surveypath):
    logger.info(f"Start Standardizing Camera Filenames in {surveypath}")
    for root, arroyos, _ in os.walk(surveypath):
        for arr in arroyos:
            logger.info(f"Reading arroyo {arr}")
            pth = os.path.join(root, arr)
            files = os.listdir(pth)
            for fname in files:
                if do_recognize_image_file(fname):
                    logger.info(f"Found file {fname}")
                    fullfname = os.path.join(root, arr, fname)

                    # Get metadata from directory and filename
                    damrec = DamMeta(fullfname, surveypath, logger=logger)
                    if damrec.has_meta:
                        new_basefname = DamNameOp.create_filename(fullfname, damrec)
                        rename_in_place(fullfname, new_basefname)
                    else:
                        logger.info(f"Cannot read metadata from {fullfname}")

# ...............................................
def create_dam_subdir_structure_for_unique_dams(surveypath, survey_damsep_path):
    """Create subdirectories for each dam within each arroyo directory.

    Args:
        surveypath: full path to directory containing arroyo directories containing
            images.
        survey_damsep_path: full path for new directory containing arroyo directories containing
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
                    damdir = f"{DAM_PREFIX}{SEPARATOR}{damnum}"
                    newpath = os.path.join(survey_damsep_path, arr, damdir)
                    # logger.info(f"Dam {damdir}")
                    oldpath = os.path.join(root, arr)
                    copy_fileandmeta_to_dir(oldpath, newpath, fname)


# ...............................................
def match_dams_to_survey(earlypath, survey_damsep_path, aggregate_path):
    """Create subdirectories for multiple images per dam within each arroyo directory.

    Args:
        earlypath: full path to directory containing arroyo directories containing
            images not grouped by dam.
        survey_damsep_path: full path to directory containing latest survey, containing
            arroyo directories with dam directories containing latest image.
        aggregate_path: full path for new directory containing arroyo directories
            containing dam subdirectories containing multiple images, one per year.

    Note:
        This function assumes that more than one image (one per year) may exist for a
        single dam.  Each early image will be examined and compared to the survey data
        for the same arroyo, the closest dam will be identified, and the early image
        will be written to the appropriate directory in the aggregate path.  If the
        survey image has not yet been written to the aggregate path, it will also be
        copied.

    Postcondition:
        Creates and populates a new directory tree with multiple images under each
        dam in an arroyo, like:
            outpath
                arroyo_a
                    dam_1: 2013_pic, 2014_pic, 2018_pic, ...
                    ...
                arroyo_b
                    dam_1
                    ...
    """
    # Sets all_data dictionary on object
    pm_truth = PicMapper(survey_damsep_path, buffer_distance=DAM_BUFFER, logger=logger)
    ct_truth = pm_truth.populate_images(is_dam_separated=True)
    logger.info(f"Read {ct_truth} 2025 survey images")

    pm_early = PicMapper(earlypath, buffer_distance=DAM_BUFFER, logger=logger)
    ct_early = pm_early.populate_images(is_dam_separated=False)
    logger.info(f"Read {ct_early} 2013-2024 images")

# ...............................................
def match_dams_to_survey(truth_pm, early_pm, outpath):
    """Create subdirectories for multiple images per dam within each arroyo directory.

    Args:
        truth_pm: PicMapper object containing "ground truth" dams for every arroyo, one
            image per dam.
        early_pm: PicMapper object containing early dams for every arroyo, multiple
            images per dam.
        outpath: root directory for output of images organized by arroyos/dams/images

    Note:
        Each early image will be examined and compared to the survey data
        for the same arroyo, the closest dam will be identified, and the early image
        will be written to the appropriate directory in the aggregate path.  If the
        survey image has not yet been written to the aggregate path, it will also be
        copied.

    Postcondition:
        Creates and populates a new directory tree with multiple images under each
        dam in an arroyo, like:
            outpath
                arroyo_a
                    dam_1: 2013_pic, 2014_pic, 2018_pic, ...
                    ...
                arroyo_b
                    dam_1
                    ...
    """



# ...............................................
if __name__ == "__main__":
    n = datetime.datetime.now()
    datestr = f"{n.year}-{n.month}-{n.day}"
    name = f"organize_survey_{datestr}"
    is_dev = False
    bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

    surveypath = os.path.join(MAC_PATH, SURVEY_DIR)
    survey_damsep_path = os.path.join(MAC_PATH, SURVEY_DAMSEP_DIR)
    earlypath = os.path.join(MAC_PATH, EARLY_DATA_DIR)
    aggregate_path = os.path.join(MAC_PATH, AGG_DIR)
    outpath = os.path.join(MAC_PATH, OUT_DIR)
    logger = get_logger(outpath, logname=name)

    # # Rename image files to be standard
    # standardize_camera_filenames(surveypath)

    # Separate 2025_survey data into one image per dam
    # create_dam_subdir_structure_for_unique_dams(surveypath, survey_damsep_path)

    # Read early pics, match to closest pic in survey
    match_dams_to_survey(earlypath, survey_damsep_path, aggregate_path)

