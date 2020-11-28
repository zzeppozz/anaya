Developer Notes
===============


Dependencies
------------
* python2.7 
* osgeo GDAL and OGR
* PIL/Pillow

Directory pattern
-----------------
* Anaya/anaya_map

  * dam_anaya.* - output files
  * ancillary - dir of reference files
  
    * op140814.tif - satellite imagery
    * dem.*
    * flowline.*
    * topo.*
    * USGS - dir of drainage shapefiles
    
  * dams - input images
  * 
  
Projection
-----------

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
    
    
Input name patterns
-------------------

Renamed all dam directories and filenames:

* Removed spaces
* Removed apostrophes
* Replaced ')' with '.'


Renamed some directories, files:

* bend20131020_dams20131020new_0015 to bend20131020_0015
* alldone202005030011 to alldone20200503_0011
* alldone202005030021 to alldone20200503_0021
* 62.AllDone to 65.AllDone (there is a 62.Kuma)
* gerroyo20131024_dams20131024_0009 to gerroyo20131024_0009
* gerroyo20131024_dams20131024_0010 to gerroyo20131024_0010


