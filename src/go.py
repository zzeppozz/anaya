p2_gdal_loc = '/Library/Frameworks/GDAL.framework/Versions/2.1/Python/2.7/site-packages'
p2_pil_loc = '/Library/Python/2.7/site-packages/'

import sys
sys.path.insert(0, p2_gdal_loc)
sys.path.insert(0, p2_pil_loc)

import csv
import exifread
import os
from osgeo import ogr, osr
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import time

from constants import (
    GEOM_WKT, LONG_FLD, LAT_FLD, IMG_META, DELIMITER, BASE_PATH, IN_DIR, 
    ANC_DIR, THUMB_DIR, OUT_DIR, OUT_NAME, SAT_FNAME)

from georef import PicMapper, getBbox, getLogger, readyFilename, reduceImageSize

IN_PATH = '/Users/astewart/Home/anaya_pics/'
THUMB_PATH = '/Users/astewart/Home/anaya_thumbs/'
OUT_PATH = '/Users/astewart/Home/AnayaGE'
OUTNAME = 'dam_anaya'
SAT_IMAGE_FNAME = '/Users/astewart/Home/AnayaGE/satellite/op140814.tif'
kml_flag = False
shp_flag = False

maxY = 35.45045
minY = 35.43479
maxX = -106.05353
minX = -106.07259

dam_buffer = .0002

log = None
image_path = os.path.join(BASE_PATH, IN_DIR)
out_path = os.path.join(BASE_PATH, OUT_DIR)
resize_path= os.path.join(out_path, THUMB_DIR)

base_outfile = os.path.join(out_path, OUT_NAME)
csv_fname = '{}.csv'.format(base_outfile)
shp_fname = '{}.shp'.format(base_outfile)
kml_fname = '{}.kml'.format(base_outfile)

bbox = (minX, minY, maxX, maxY)

sep = '_'


pm = PicMapper(
    image_path, buffer_distance=dam_buffer, bbox=bbox, 
    do_kml=kml_flag, do_shape=shp_flag)



# Read data
imageData = pm.processAllImages(resize_width=500, resize_path=THUMB_PATH)
print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))

# Reduce image sizes
t = time.localtime()
stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)

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
    <img style="max-width:500px;" src="file:///Users/astewart/Home/2017AnayaPics/13-LL-GreyBottom/Grey-Bottom20151201_0002.JPG"></img>
</Placemark>
</kml>

"""
