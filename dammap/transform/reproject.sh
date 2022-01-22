# Reproject input shapefile from EPSG:4326 to EPSG:102713
# NAD 1983 StatePlane New Mexico Central FIPS 3002 Feet, aka ESRI:102713
# Defined at https://epsg.io/102713
ogr2ogr  -t_srs EPSG:102713  -f "ESRI Shapefile" anaya_dams_102713.shp   anaya_dams.shpogr2ogr -a_srs EPSG:4326  -t_srs EPSG:102713  -f `ESRI Shapefile` anaya_dams_102713.shp   anaya_dams.shp

ogr2ogr \
    -t_srs epsg_102713.prj \
    -f "ESRI Shapefile"  \
    anaya_dams_102713.shp \
    anaya_dams.shp





