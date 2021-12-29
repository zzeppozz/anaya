# anaya
Project to georeference Anaya Springs arroyos

## Dependencies:

* OSGEO GDAL and OGR: Raster and Vector Geospatial functions
  * Apt/RPM package must be installed on the base system, and python package must be 
    installed in the default system python, then the virtual environment must inherit  

* ExifRead: reads image metadata

* Pillow: Image processing, https://pillow.readthedocs.io/en/latest/handbook/index.html

## Run

georef.PicMapper contains all the functions to read metadata, 
and read and rewrite image files. 

go.py is a helper script to execute image file assessment and rewrite