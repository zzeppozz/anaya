# Developer Notes



## Dependencies
* python3.6+
* osgeo GDAL and OGR
* PIL/Pillow

## Directory pattern
* anaya/data

  * dam_anaya.* - output files
  * ancillary - dir of reference files

    * satellite
      * op140814.tif - satellite imagery
    * dem.*
    * flowline.*
    * topo.*
    * USGS - dir of drainage shapefiles

* External directory for input images - anaya/dams

## Projection

* NAD 1983 StatePlane New Mexico Central FIPS 3002 Feet::

  * ESRI:102713 https://epsg.io/102713
  * Data source: proj.4
  * Info source: ESRI
  * Description: +proj=tmerc +lat_0=31 +lon_0=-106.25 +k=0.999900 +x_0=500000.0000000002 +y_0=0 +ellps=GRS80 +datum=NAD83 +to_meter=0.3048006096012192 no_defs
  * WKT:
    PROJCS["NAD_1983_StatePlane_New_Mexico_Central_FIPS_3002_Feet",
    GEOGCS["GCS_North_American_1983",
        DATUM["North_American_Datum_1983",
            SPHEROID["GRS_1980",6378137,298.257222101]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["False_Easting",1640416.666666667],
    PARAMETER["False_Northing",0],
    PARAMETER["Central_Meridian",-106.25],
    PARAMETER["Scale_Factor",0.9999],
    PARAMETER["Latitude_Of_Origin",31],
    UNIT["Foot_US",0.30480060960121924],
    AUTHORITY["EPSG","102713"]]


## Input name patterns

Renamed all dam directories:
* Removed spaces
* Removed non-alpha characters and non-digits
* Replaced first ')' with '_'

Renamed files:
* Make sure extension is separated from basename
* Separate basename into name_yyyy-mm-dd_num
