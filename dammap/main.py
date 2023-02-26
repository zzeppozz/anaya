"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import argparse
import os
import time

from dammap.common.constants import (IN_DIR, OUT_DIR, THUMB_DIR)
from dammap.common.name import fix_names_in_tree
from dammap.common.util import (get_logger, stamp)
from transform.dam_map import PicMapper

kml_flag = False
shp_flag = False

# # ...............................................
# def stamp(msg):
#     t = time.localtime()
#     print("## {} {}-{}-{} {}:{}:{}".format(
#         msg, t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))
#

# ...............................................
if __name__ == "__main__":
    is_dev = False
    MAC_PATH = "/Users/aimeestewart/Library/Mobile Documents/com~apple~CloudDocs/Documents/Home/Anaya/anaya_map"
    BASE_PATH = "/tank/anaya/"
    maxY = 35.45045
    minY = 35.43479
    maxX = -106.05353
    minX = -106.07259
    dam_buffer = .0002
    bbox = (minX, minY, maxX, maxY)

    inpath = os.path.join(BASE_PATH, IN_DIR)
    outpath = os.path.join(BASE_PATH, OUT_DIR)
    resize_path = os.path.join(outpath, THUMB_DIR)

    # newpath = os.path.join(BASE_PATH, "newdams")
    # fix_names_in_tree(newpath, do_files=True)

    # Define output filenames
    base_fname = os.path.join(outpath, "anaya_dams")
    csv_fname = "{}.csv".format(base_fname)
    shp_fname = "{}.shp".format(base_fname)
    kml_fname = "{}.kml".format(base_fname)
    logger = get_logger(outpath, logname="dam_map")

    pm = PicMapper(inpath, buffer_distance=dam_buffer, bbox=bbox, logger=logger)

    stamp(logger, "Start")

    # Sets all_data dictionary on object
    read_count = pm.populate_images()
    stamp(logger, f"Read {read_count} filenames")

    # # Rewrite thumbnails of all images
    total = pm.resize_images(
        outpath, small_width=800, medium_width=1200, large_width=2000, overwrite=True)
    stamp(logger, f"Wrote {total} thumbnails")

    # Write data to CSV, Shapefile, KML
    pm.write_outputs(csvfname=csv_fname, shpfname=shp_fname)
    stamp(logger, "Wrote shapefile")

    # Write out replicated coordinates
    pm.print_duplicates()
    pm.print_summary()
