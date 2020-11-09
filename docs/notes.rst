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


