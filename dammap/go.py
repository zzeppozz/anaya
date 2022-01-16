"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import argparse
import os

from common.constants import BADENOV_PATH, IN_DIR, OUT_DIR
from common.util import fix_names_in_tree
# from transform.dam_map import PicMapper

kml_flag = False
shp_flag = False

maxY = 35.45045
minY = 35.43479
maxX = -106.05353
minX = -106.07259

dam_buffer = .0002

# ...............................................
if __name__ == "__main__":
    default_inpath = os.path.join(BADENOV_PATH, IN_DIR)
    default_outpath = os.path.join(BADENOV_PATH, OUT_DIR)

    # parser = argparse.ArgumentParser(
    #     description='Process image data, to create geospatial outputs.')
    # parser.add_argument(
    #     'inpath', type=str, default=default_inpath,
    #     help='The base path for BISON input data and outputs.')
    # parser.add_argument('outpath', type=str, default=default_outpath,
    #     help='The full path to GBIF input species occurrence data.')
    # args = parser.parse_args()
    # inpath = args.inpath
    # outpath = args.outpath

    inpath = default_inpath
    outpath = default_outpath

    # fix_names_in_tree(inpath, do_files=False)
    fix_names_in_tree(inpath, do_files=True)

        # image_path = os.path.join(BASE_PATH, IN_DIR)
        # out_path = os.path.join(BASE_PATH, OUT_DIR)
        # resize_path= os.path.join(out_path, THUMB_DIR)

# base_outfile = os.path.join(out_path, OUT_NAME)
# csv_fname = '{}.csv'.format(base_outfile)
# shp_fname = '{}.shp'.format(base_outfile)
# kml_fname = '{}.kml'.format(base_outfile)
#
# bbox = (minX, minY, maxX, maxY)
#
# sep = '_'
#
#
# pm = PicMapper(
#     image_path, buffer_distance=dam_buffer, bbox=bbox,
#     shp_fname=shp_fname, kml_fname=None)
#
#
#
# # Read data
# imageData = pm.process_all_images(resize_width=500, resize_path=resize_path)
#
# print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
# print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))
#
# # Reduce image sizes
# t = time.localtime()
# stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)

"""

#SCHEMA#
<Schema name="anaya_springs" id="anaya_springs">
          <SimpleField name="arroyo" type="string"></SimpleField>
          <SimpleField name="fullpath" type="string"></SimpleField>
          <SimpleField name="relpath" type="string"></SimpleField>
          <SimpleField name="basename" type="string"></SimpleField>
          <SimpleField name="geomwkt" type="string"></SimpleField>
          <SimpleField name="longitude" type="float"></SimpleField>
          <SimpleField name="latitude" type="float"></SimpleField>
          <SimpleField name="xdirection" type="string"></SimpleField>
          <SimpleField name="xdegrees" type="float"></SimpleField>
          <SimpleField name="xminutes" type="float"></SimpleField>
          <SimpleField name="xseconds" type="float"></SimpleField>
          <SimpleField name="ydirection" type="string"></SimpleField>
          <SimpleField name="ydegrees" type="float"></SimpleField>
          <SimpleField name="yminutes" type="float"></SimpleField>
          <SimpleField name="yseconds" type="float"></SimpleField>
</Schema>

#FOLDERNAME#
<name>anaya_springs</name>

#PLACEMARKS#
  <Placemark>
    <ExtendedData><SchemaData schemaUrl="#anaya_springs">
        <SimpleData name="arroyo">1 RR-Bill's toptobottom</SimpleData>
        <SimpleData name="fullpath">/Users/astewart/Home/AnneBill/AnayaSprings/1 RR-Bill's toptobottom/201411_anaya20141103_0020.JPG</SimpleData>
        <SimpleData name="relpath">AnayaSprings/1 RR-Bill's toptobottom/201411_anaya20141103_0020.JPG</SimpleData>
        <SimpleData name="basename">201411_anaya20141103_0020.JPG</SimpleData>
        <SimpleData name="geomwkt">Point (-106.0620556  35.4359889)</SimpleData>
        <SimpleData name="longitude">-106.062055555555560</SimpleData>
        <SimpleData name="latitude">35.435988888888886</SimpleData>
        <SimpleData name="xdirection">W</SimpleData>
        <SimpleData name="xdegrees">106.000000000000000</SimpleData>
        <SimpleData name="xminutes">3.000000000000000</SimpleData>
        <SimpleData name="xseconds">43.399999999999999</SimpleData>
        <SimpleData name="ydirection">N</SimpleData>
        <SimpleData name="ydegrees">35.000000000000000</SimpleData>
        <SimpleData name="yminutes">26.000000000000000</SimpleData>
        <SimpleData name="yseconds">9.560000000000000</SimpleData>
    </SchemaData></ExtendedData>
        <Point><coordinates>-106.0620556,35.4359889</coordinates></Point>
  </Placemark>

<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
<Placemark>
    <name>Grey-Bottom20151201_0002.JPG</name>
    <description>Grey-Bottom20151201_0002 in 13-LL-GreyBottom on 2015-12-1</description>
    <gx:balloonVisibility>1</gx:balloonVisibility>
    <Point>
        <coordinates>-106.067033333,35.4413833333,0</coordinates>
    </Point>
    <img style="max-width:500px;" dammap="file:///Users/astewart/Home/2017AnayaPics/13-LL-GreyBottom/Grey-Bottom20151201_0002.JPG"></img>
</Placemark>
</kml>

"""
