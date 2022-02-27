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
* DEM - 2800x2805, print at 150 dpi~= 18.6"
```commandline
astewart@badenov:/tank/anaya/ancillary$ gdalinfo dem140814.tif
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
Origin = (1693300.000000000000000,1619230.000000000000000)
Pixel Size = (2.000000000000000,-2.000000000000000)
Metadata:
  AREA_OR_POINT=Area
Image Structure Metadata:
  INTERLEAVE=BAND
Corner Coordinates:
Upper Left  ( 1693300.000, 1619230.000) (106d 4'20.76"W, 35d27' 1.09"N)
Lower Left  ( 1693300.000, 1613620.000) (106d 4'20.88"W, 35d26' 5.60"N)
Upper Right ( 1698900.000, 1619230.000) (106d 3'13.07"W, 35d27' 0.98"N)
Lower Right ( 1698900.000, 1613620.000) (106d 3'13.20"W, 35d26' 5.49"N)
Center      ( 1696100.000, 1616425.000) (106d 3'46.98"W, 35d26'33.29"N)
Band 1 Block=2800x128 Type=Float32, ColorInterp=Gray
  Description = Surface Model Raster Band
  Min=5837.841 Max=6139.475 
  Minimum=5837.841, Maximum=6139.475, Mean=5995.771, StdDev=66.157
  NoData Value=-32767
  Metadata:
    STATISTICS_MAXIMUM=6139.4750976562
    STATISTICS_MEAN=5995.7708782904
    STATISTICS_MINIMUM=5837.8413085938
    STATISTICS_STDDEV=66.156804511765

```

### Satellite data
* Input raster data from county, op140814.tif
* All additional files are duplicates, with TIFFTAG_DATETIME=2015:05:03 21:46:49
* 11201 pixels square - to print at 150 dpi --> 74" square
* 
```commandline
$ gdalinfo op140814.tif
Driver: GTiff/GeoTIFF
Files: op140814.tif
Size is 11201, 11221
Origin = (1693299.500000000000000,1619230.500000000000000)
Pixel Size = (0.500000000000000,-0.500000000000000)
Metadata:
  TIFFTAG_DATETIME=2015:05:03 21:46:49
  TIFFTAG_IMAGEDESCRIPTION=OrthoVista
  TIFFTAG_RESOLUTIONUNIT=2 (pixels/inch)
  TIFFTAG_SOFTWARE=Adobe Photoshop CS6 (Windows)
  TIFFTAG_XRESOLUTION=72
  TIFFTAG_YRESOLUTION=72
Image Structure Metadata:
  COMPRESSION=JPEG
  INTERLEAVE=PIXEL
Corner Coordinates:
Upper Left  ( 1693299.500, 1619230.500) 
Lower Left  ( 1693299.500, 1613620.000) 
Upper Right ( 1698900.000, 1619230.500) 
Lower Right ( 1698900.000, 1613620.000) 
Center      ( 1696099.750, 1616425.250) 
Band 1 Block=256x256 Type=Byte, ColorInterp=Red
  Overviews: 5601x5611, 2801x2806, 1401x1403, 701x702, 351x351, 176x176, 88x88, 44x44, 22x22, 11x11
Band 2 Block=256x256 Type=Byte, ColorInterp=Green
  Overviews: 5601x5611, 2801x2806, 1401x1403, 701x702, 351x351, 176x176, 88x88, 44x44, 22x22, 11x11
Band 3 Block=256x256 Type=Byte, ColorInterp=Blue
  Overviews: 5601x5611, 2801x2806, 1401x1403, 701x702, 351x351, 176x176, 88x88, 44x44, 22x22, 11x11
Band 4 Block=256x256 Type=Byte, ColorInterp=Undefined
  Overviews: 5601x5611, 2801x2806, 1401x1403, 701x702, 351x351, 176x176, 88x88, 44x44, 22x22, 11x11

```
###  Stream flowlines
* Input shapefile data, flowline_140814.shp
* ogrinfo
  * projection parameters match
  * datum mismatch
```commandline
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
```commandline
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
```commandline
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