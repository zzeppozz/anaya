"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import datetime
import os

from dammap.common.constants import (
    MAC_PATH, IN_DIR, OUT_DIR, THUMB_DIR, THUMB_WIDTH, DAM_BUFFER,
    MAX_X, MAX_Y, MIN_X, MIN_Y)
from dammap.common.util import (get_logger, stamp)
from transform.dam_map import PicMapper

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

    inpath = os.path.join(MAC_PATH, IN_DIR)
    outpath = os.path.join(MAC_PATH, OUT_DIR)
    resize_path = os.path.join(outpath, THUMB_DIR)

    # correction_csv = os.path.join(MAC_PATH, "corrections_2023_05/charlie_2023_05/points_to_update.csv")
    # newpath = os.path.join(BASE_PATH, "newdams")
    # fix_names_in_tree(newpath, do_files=True)

    # Define output filenames
    base_fname = os.path.join(outpath, name)
    csv_fname = "{}.csv".format(base_fname)
    shp_fname = "{}.shp".format(base_fname)
    kml_fname = "{}.kml".format(base_fname)
    logger = get_logger(outpath, logname=name)

    # logger = get_logger(outpath, logname="move_arroyos")
    # move_arroyos(correction_csv, ",", "fullpath", "55_Swell", logger)

    # pm = PicMapper(inpath, buffer_distance=dam_buffer, bbox=bbox, logger=logger)
    # Do not restrict to Bounding box
    pm = PicMapper(inpath, buffer_distance=DAM_BUFFER, logger=logger)
    logger.info("Start")

    # Sets all_data dictionary on object
    read_count = pm.populate_images()
    logger.info(f"Read {read_count} filenames")

    # # Rewrite thumbnails of all images
    total = pm.resize_images(outpath, THUMB_WIDTH, overwrite=False)
    logger.info(f"Wrote {total} thumbnails")

    # Write data to CSV, Shapefile, KML
    pm.write_outputs(csvfname=csv_fname, shpfname=shp_fname)
    # pm.write_outputs(shpfname=shp_fname)
    logger.info(f"Wrote CSV file {csv_fname}, shapefile {shp_fname}")

    # Write out replicated coordinates
    pm.print_duplicates()
    pm.print_summary()
