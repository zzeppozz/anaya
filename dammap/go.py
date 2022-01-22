"""Process Anaya dam photographs and create CSV, shapefile, and KML file for display."""
import argparse
import os
import time

from dammap.common.constants import (
    IN_DIR, OUT_DIR, THUMB_DIR, CSV_FIELDS, CSV_FIELDS_SMALL)
from dammap.common.util import (fix_names_in_tree, get_logger, test_names_in_tree)
from transform.dam_map import PicMapper

kml_flag = False
shp_flag = False

# ...............................................
if __name__ == "__main__":
    is_dev = False
    MAC_PATH = '/Users/aimeestewart/Library/Mobile Documents/com~apple~CloudDocs/Documents/Home/Anaya/anaya_map'
    BASE_PATH = '/tank/anaya/'
    maxY = 35.45045
    minY = 35.43479
    maxX = -106.05353
    minX = -106.07259
    dam_buffer = .0002
    bbox = (minX, minY, maxX, maxY)

    # parser = argparse.ArgumentParser(
    #     description='Process image data, to create geospatial outputs.')
    # parser.add_argument(
    #     'basepath', type=str, default=BASE_PATH,
    #     help='The base path for Dam Anaya input data and outputs.')
    # args = parser.parse_args()
    # inpath = args.inpath

    inpath = os.path.join(BASE_PATH, IN_DIR)
    outpath = os.path.join(BASE_PATH, OUT_DIR)
    resize_path = os.path.join(outpath, THUMB_DIR)

    # # Fix directories first
    # fix_names_in_tree(inpath, do_files=False)
    # # Fix filenames and test parsing before write
    # fix_names_in_tree(inpath, do_files=True)
    # # Test file and directories before further action
    # test_names_in_tree(inpath)

    # Define output filenames
    base_fname = os.path.join(outpath, 'anaya_dams')
    csv_fname = '{}.csv'.format(base_fname)
    shp_fname = '{}.shp'.format(base_fname)
    kml_fname = '{}.kml'.format(base_fname)
    logger = get_logger(outpath)

    pm = PicMapper(
        inpath, buffer_distance=dam_buffer, bbox=bbox, shp_fname=shp_fname,
        kml_fname=None, logger=logger)

    t = time.localtime()
    print('Start {}_{}_{} {}:{}:{}'.format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))

    # Sets all_data dictionary on object
    pm.read_metadata_from_directory()
    t = time.localtime()
    print('Read filenames {}_{}_{} {}:{}:{}'.format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))

    # Updates all images in the dictionary from the referenced files
    pm.read_data_from_image_files()
    pm.write_csv_data(csv_fname, header=CSV_FIELDS)
    pm.write_shapefile_kml(shpfname=shp_fname)
    t = time.localtime()
    print('Read image files {}_{}_{} {}:{}:{}'.format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))
    # Test that we have the expected number of records
    print('Testing results after reading image metadata')
    pm.test_counts()

    orig_all_data = pm.all_data
    pm.read_csv_data(csv_fname)
    # pm.compare_all_data(orig_all_data)

    # Test that we have the expected number of records
    print('Testing results after reading CSV metadata')
    pm.test_counts()
    t = time.localtime()
    print('End {}_{}_{} {}:{}:{}'.format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))

    # # Write smaller images and save to all_data dictionary
    # pm.resize_images(resize_width=500, resize_path=resize_path)

    print('Given: {}'.format(pm.bbox))
    print('Computed: {}'.format(pm.bounds))

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
