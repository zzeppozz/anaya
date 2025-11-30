"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime

from osgeo import ogr
import os

from dammap.common.constants import (
    AGG_DIR, ALL_DATA_KEYS as ADK, BIG_DISTANCE, DAM_BUFFER, DAM_PREFIX, EARLY_DATA_DIR,
    MAC_PATH, MAX_X, MAX_Y, MIN_X, MIN_Y, OUT_DIR, SEPARATOR, SURVEY_DAMSEP_DIR, SURVEY_DIR)
from dammap.common.util import (
    get_logger, do_recognize_image_file, rename_in_place, copy_fileandmeta_to_dir)
from dammap.common.name import DamNameOp
from dammap.common.dammeta import DamMeta
from dammap.transform.dam_map import PicMapper

# DELETE_CHARS = ["\"", ",", """, " ", "(", ")", "_"]

# .............................................................................
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

# .............................................................................
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


# .............................................................................
def match_dams_to_survey(earlypath, gt_damsep_path, aggregate_path, logger):
    """Create subdirectories for multiple images per dam within each arroyo directory.

    Args:
        earlypath: full path to directory containing arroyo directories containing
            images not grouped by dam.
        gt_damsep_path: full path to directory containing ground-truth survey,
            containing arroyo directories with dam directories containing latest image.
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
    # Read latest survey (ground truth) data, organized by arroyo and dam
    gt_pm = PicMapper(gt_damsep_path, buffer_distance=DAM_BUFFER, logger=logger)
    gt_pm.populate_images(is_dam_separated=True)
    logger.info(f"Read {gt_pm.all_data['img_count']} 2025 survey images")
    gt_img_meta = gt_pm.all_data[ADK.IMAGE_META]

    # Read early data, organized only by arroyo
    pm_early = PicMapper(earlypath, buffer_distance=DAM_BUFFER, logger=logger)
    pm_early.populate_images(is_dam_separated=False)
    logger.info(f"Read {pm_early.all_data['img_count']} 2013-2024 images")
    old_arroyos = pm_early.all_data[ADK.ARROYO_FILES]
    old_img_meta = pm_early.all_data[ADK.IMAGE_META]

    for arr_name, arr_gt_files in gt_pm.all_data[ADK.ARROYO_FILES].items():
        # if arr_name in ["PricesTrail", "Tiny"]:
        print(f"-- Arroyo {arr_name}")
        try:
            arr_old_files = old_arroyos[arr_name]
        except:
            print(f"{arr_name} does not exist in old dataset")
        else:
            dam_calcs = match_old_coords_to_arroyo(
                arr_gt_files, arr_old_files, gt_img_meta, old_img_meta,
                aggregate_path)
            for damname, dimg_lst in dam_calcs.items():
                print(f"  -- Dam {damname}")
                for dimg in dimg_lst:
                    oldpath = os.path.split(dimg.fullpath)[0]
                    relpath = DamNameOp.construct_relative_path(dimg)
                    newpath = os.path.join(aggregate_path, relpath)
                    if dimg.dam_calc_dist > BIG_DISTANCE[0]:
                        print(
                            f"    -- BIG Distance {dimg.dam_calc_dist:.7f}; {dimg.basename}"
                            f"({BIG_DISTANCE[0]} dd ~= {BIG_DISTANCE[1]} meters)")
                    else:
                        print(
                            f"    -- Distance {dimg.dam_calc_dist:.7f}; {dimg.basename}")
                    # copy_fileandmeta_to_dir(
                    #     oldpath, newpath, dimg.basename, basepath=MAC_PATH)


# .............................................................................
def match_old_coords_to_arroyo(
        arr_gt_files, arr_old_files, gt_img_meta, old_img_meta,
        outpath):
    """Match coordinates of early survey images to closest dam in 2025 survey.

    Args:
        arr_gt_files: list of arroyo relative filenames in ground-truth arroyo dataset
        arr_old_files: list of arroyo relative filenames in old arroyo dataset
        gt_img_meta: dict of relative filename to DamMeta in ground-truth dataset
        old_img_meta: dict of relative filename to DamMeta in old dataset
        outpath: parent path for new, matched, combined dataset

    Returns:
        dict of dam_name: [DamMeta, ...] for all dams in arr_name

    """
    # make a dict of dam:ground-truth-coords for arroyo
    gtdam_coords = {}
    # make a dict of dam:[DamMeta, ...] for arroyo to return
    dam_calcs = {}
    for gt_rfname in arr_gt_files:
        gt_dimg = gt_img_meta[gt_rfname]
        if gt_dimg.dam_calc_dist != 0:
            print(f"Ground-truth {gt_dimg.dam_calc} distance {gt_dimg.dam_calc_dist}")
        gtdam_coords[gt_dimg.dam_calc] = [gt_dimg.longitude, gt_dimg.latitude]
        dam_calcs[gt_dimg.dam_calc] = [gt_dimg]

    # examine each old image and find closest ground-truth dam
    for rfname in arr_old_files:
        # copy_fileandmeta_to_dir(oldpath, newpath, fname)
        old_dimg = old_img_meta[rfname]
        old_coords = [old_dimg.longitude, old_dimg.latitude]
        closest_dist = 100
        closest_dam = None
        for dam, gt_coords in gtdam_coords.items():
            # Create a line and measure length
            ln = ogr.Geometry(ogr.wkbLineString)
            ln.AddPoint(*old_coords)
            ln.AddPoint(*gt_coords)
            dist = ln.Length()
            if closest_dam is None or dist < closest_dist:
                closest_dam = dam
                closest_dist = dist
        old_dimg.dam_calc = closest_dam
        old_dimg.dam_calc_dist = closest_dist
        dam_calcs[closest_dam].append(old_dimg)
    return dam_calcs

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

