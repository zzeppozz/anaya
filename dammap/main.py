"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime
import os

from dammap.common.constants import (
    ALL_DATA_KEYS as ADK, AGG_DIR, MAC_PATH, EARLY_DATA_DIR, THUMB_DIR, THUMB_WIDTH, DAM_BUFFER,
    MAX_X, MAX_Y, MIN_X, MIN_Y, SURVEY_DIR, SURVEY_DAMSEP_DIR, OUT_DIR)
from dammap.common.organize import (
    create_dam_subdir_structure_for_unique_dams, match_dams_to_survey,
    standardize_camera_filenames)
from dammap.common.util import (get_logger, stamp)
from dammap.transform.dam_map import PicMapper

kml_flag = False
shp_flag = False

# ...............................................
if __name__ == "__main__":
    n = datetime.datetime.now()
    datestr = f"{n.year}-{n.month}-{n.day}"
    name = f"anaya_dams_{datestr}"
    # thumb_width = 2000
    is_dev = False
    # dam_buffer = .0002
    bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

    surveypath = os.path.join(MAC_PATH, SURVEY_DIR)
    survey_damsep_path = os.path.join(MAC_PATH, SURVEY_DAMSEP_DIR)
    earlypath = os.path.join(MAC_PATH, EARLY_DATA_DIR)
    aggregate_path = os.path.join(MAC_PATH, AGG_DIR)
    outpath = os.path.join(MAC_PATH, OUT_DIR)
    resize_path = os.path.join(outpath, THUMB_DIR)
    logger = get_logger(outpath, logname=name)

    # Define output filenames
    base_fname = os.path.join(outpath, name)
    csv_fname = "{}.csv".format(base_fname)
    shp_fname = "{}.shp".format(base_fname)
    kml_fname = "{}.kml".format(base_fname)
    logger = get_logger(outpath, logname=name)

    is_dev = False
    bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

    # # Rename image files to be standard
    # standardize_camera_filenames(surveypath)

    # Separate 2025_survey data into one image per dam
    # create_dam_subdir_structure_for_unique_dams(surveypath, organized_surveypath)

    # Read latest survey (ground truth) data, organized by arroyo and dam
    pm_survey = PicMapper(survey_damsep_path, buffer_distance=DAM_BUFFER, logger=logger)
    pm_survey.populate_images(is_dam_separated=True)
    logger.info(f"Read {pm_survey.all_data['img_count']} 2025 survey images")
    gt_arroyos = pm_survey.all_data[ADK.ARROYO_META]
    gt_images = pm_survey.all_data[ADK.IMAGE_META]

    # Read early data, organized only by arroyo
    pm_early = PicMapper(earlypath, buffer_distance=DAM_BUFFER, logger=logger)
    pm_early.populate_images(is_dam_separated=False)
    logger.info(f"Read {pm_early.all_data['img_count']} 2013-2024 images")
    old_arroyos = pm_early.all_data[ADK.ARROYO_META]
    old_images = pm_early.all_data[ADK.IMAGE_META]

    # for each survey/ground-truth arroyo
    for gt_arroyo in gt_arroyos:
        dam_coords = {}
        # make a dict of wkt:dam for arroyo
        for gt_img in gt_images:
            dam_coords[gt_img.wkt] = gt_img.dam_calc
        arroyo_coords = dam_coords.keys()
        # examine each old image and find closest ground-truth dam
        for relf_fname in old_arroyos[gt_arroyo]:
            # TODO: use ogr to find closest point
            pass

    # # Do not restrict to Bounding box
    # pm = PicMapper(earlypath, buffer_distance=DAM_BUFFER, logger=logger)
    # logger.info("Start")
    #
    # # Sets all_data dictionary on object
    # read_count = pm.populate_images()
    # logger.info(f"Read {read_count} filenames")

    # # # Rewrite thumbnails of all images
    # total = pm.reszie_images(outpath, THUMB_WIDTH, overwrite=False)
    # logger.info(f"Wrote {total} thumbnails")
    #
    # # Write data to CSV, Shapefile, KML
    # pm.write_outputs(csvfname=csv_fname, shpfname=shp_fname)
    # # pm.write_outputs(shpfname=shp_fname)
    # logger.info(f"Wrote CSV file {csv_fname}, shapefile {shp_fname}")
    #
    # # Write out replicated coordinates
    # pm.print_duplicates()
    # pm.print_summary()

"""
from dammap.main import *
from dammap.common.dammeta import *


n = datetime.datetime.now()
datestr = f"{n.year}-{n.month}-{n.day}"
name = f"anaya_dams_{datestr}"
# thumb_width = 2000
is_dev = False
# dam_buffer = .0002
bbox =( MIN_X, MIN_Y, MAX_X, MAX_Y)

surveypath = os.path.join(MAC_PATH, SURVEY_DIR)
survey_damsep_path = os.path.join(MAC_PATH, SURVEY_DAMSEP_DIR)
earlypath = os.path.join(MAC_PATH, EARLY_DATA_DIR)
aggregate_path = os.path.join(MAC_PATH, AGG_DIR)
outpath = os.path.join(MAC_PATH, OUT_DIR)
resize_path = os.path.join(outpath, THUMB_DIR)
logger = get_logger(outpath, logname=name)

# Read latest survey (ground truth) data, organized by arroyo and dam
pm_survey = PicMapper(survey_damsep_path, buffer_distance=DAM_BUFFER, logger=logger)
pm_survey.populate_images(is_dam_separated=True)
survey_ct = len(pm_survey.all_data['img_meta'].keys())
logger.info(f"Read {survey_ct} 2025 survey images")

# Read early data, organized only by arroyo
pm_early = PicMapper(earlypath, buffer_distance=DAM_BUFFER, logger=logger)
pm_early.populate_images(is_dam_separated=False)
early_ct = len(pm_survey.all_data['img_meta'].keys())
logger.info(f"Read {ct_early} 2013-2024 images")

"""