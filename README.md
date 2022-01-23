# anaya
Project to georeference Anaya Springs arroyos

## Dependencies:

* OSGEO GDAL and OGR: Raster and Vector Geospatial functions
  * Apt/RPM package must be installed on the base system, and python package must be 
    installed in the default system python, then the virtual environment must inherit  

* ExifRead: reads image metadata

* Pillow: Image processing, https://pillow.readthedocs.io/en/latest/handbook/index.html

## Run

dam_process.dam_map.PicMapper contains all the functions to read metadata, 
and read and rewrite image files. 

tools.util contains helper functions for image proce
go.py is a helper script to execute image file assessment and rewrite


## Coordinate System
 * Data is in ESPG:102713, aka ESRI:102713
   * NAD 1983 StatePlane New Mexico Central FIPS 3002 Feet
   * State Plane map at https://geodesy.noaa.gov/SPCS/images/spcs83_conus_final.png
   * Projection defined at https://epsg.io/102713

## Ancillary data

* Data provided by the county
* 140814 refers to a geospatial grid defined by state
* All data in EPSG:102713

### Satellite data
* Input raster data from county, op140814.tif
* All additional files are duplicates, with TIFFTAG_DATETIME=2015:05:03 21:46:49

###  Stream flowlines
* Input shapefile data, flowline_140814.shp
* ogrinfo
  * projection parameters match
  * datum mismatch
```
$ ogrinfo -al flowline_140814.shp | more
INFO: Open of `flowline_140814.shp'
      using driver `ESRI Shapefile' successful.

Layer name: flowline_140814
Metadata:
  DBF_DATE_LAST_UPDATE=2015-11-24
Geometry: Line String
Feature Count: 3858
Extent: (1693145.000052, 1613437.000092) - (1699098.999955, 1619302.999843)
Layer SRS WKT:
PROJCRS["NAD83(HARN) / New Mexico Central (ftUS)",
    BASEGEOGCRS["NAD83(HARN)",
        DATUM["NAD83 (High Accuracy Reference Network)",
            ELLIPSOID["GRS 1980",6378137,298.257222101,
                LENGTHUNIT["metre",1]],
            ID["EPSG",6152]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["Degree",0.0174532925199433]]],
    CONVERSION["unnamed",
        METHOD["Transverse Mercator",
            ID["EPSG",9807]],
        PARAMETER["Latitude of natural origin",31,
            ANGLEUNIT["Degree",0.0174532925199433],
            ID["EPSG",8801]],
        PARAMETER["Longitude of natural origin",-106.25,
            ANGLEUNIT["Degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["Scale factor at natural origin",0.9999,
            SCALEUNIT["unity",1],
            ID["EPSG",8805]],
        PARAMETER["False easting",1640416.66666667,
            LENGTHUNIT["US survey foot",0.304800609601219],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["US survey foot",0.304800609601219],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["(E)",east,
            ORDER[1],
            LENGTHUNIT["US survey foot",0.304800609601219,
                ID["EPSG",9003]]],
        AXIS["(N)",north,
            ORDER[2],
            LENGTHUNIT["US survey foot",0.304800609601219,
                ID["EPSG",9003]]]]

```

### Topography
* Input shapefile data, topo_140814.shp
* ogrinfo 
  * projection parameters match
  * datum mismatch
```
$ ogrinfo -al topo_140814.shp | more
INFO: Open of `topo_140814.shp'
      using driver `ESRI Shapefile' successful.

Layer name: topo_140814
Metadata:
  DBF_DATE_LAST_UPDATE=2015-11-24
Geometry: Line String
Feature Count: 8859
Extent: (1693301.000000, 1613621.000000) - (1698899.000000, 1619229.000000)
Layer SRS WKT:
PROJCRS["NAD83(HARN) / New Mexico Central (ftUS)",
    BASEGEOGCRS["NAD83(HARN)",
        DATUM["NAD83 (High Accuracy Reference Network)",
            ELLIPSOID["GRS 1980",6378137,298.257222101,
                LENGTHUNIT["metre",1]],
            ID["EPSG",6152]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["Degree",0.0174532925199433]]],
    CONVERSION["unnamed",
        METHOD["Transverse Mercator",
            ID["EPSG",9807]],
        PARAMETER["Latitude of natural origin",31,
            ANGLEUNIT["Degree",0.0174532925199433],
            ID["EPSG",8801]],
        PARAMETER["Longitude of natural origin",-106.25,
            ANGLEUNIT["Degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["Scale factor at natural origin",0.9999,
            SCALEUNIT["unity",1],
            ID["EPSG",8805]],
        PARAMETER["False easting",1640416.66666667,
            LENGTHUNIT["US survey foot",0.304800609601219],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["US survey foot",0.304800609601219],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["(E)",east,
            ORDER[1],
            LENGTHUNIT["US survey foot",0.304800609601219,
                ID["EPSG",9003]]],
        AXIS["(N)",north,
            ORDER[2],
            LENGTHUNIT["US survey foot",0.304800609601219,
                ID["EPSG",9003]]]]
Data axis to CRS axis mapping: 1,2
```
### Digital Elevation Model
* Input raster dem140814.tif
* gdalinfo 
  * indicates SRS EPSG:2903, https://epsg.io/2903
  * parameters do not match
  * layer overlays with others in QGIS
```
$ gdalinfo dem140814.tif
Driver: GTiff/GeoTIFF
Files: dem140814.tif
       dem140814.tif.aux.xml
Size is 2800, 2805
Coordinate System is:
PROJCRS["NAD83(HARN) / New Mexico Central (ftUS)",
    BASEGEOGCRS["NAD83(HARN)",
        DATUM["NAD83 (High Accuracy Reference Network)",
            ELLIPSOID["GRS 1980",6378137,298.257222100887,
                LENGTHUNIT["metre",1]]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["degree",0.0174532925199433]],
        ID["EPSG",4152]],
    CONVERSION["Transverse Mercator",
        METHOD["Transverse Mercator",
            ID["EPSG",9807]],
        PARAMETER["Latitude of natural origin",31,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8801]],
        PARAMETER["Longitude of natural origin",-106.25,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8802]],
        PARAMETER["Scale factor at natural origin",0.9999,
            SCALEUNIT["unity",1],
            ID["EPSG",8805]],
        PARAMETER["False easting",500000.000000001,
            LENGTHUNIT["metre",1],
            ID["EPSG",8806]],
        PARAMETER["False northing",0,
            LENGTHUNIT["metre",1],
            ID["EPSG",8807]]],
    CS[Cartesian,2],
        AXIS["easting",east,
            ORDER[1],
            LENGTHUNIT["US survey foot",0.304800609601219]],
        AXIS["northing",north,
            ORDER[2],
            LENGTHUNIT["US survey foot",0.304800609601219]],
    ID["EPSG",2903]]
Data axis to CRS axis mapping: 1,2
```