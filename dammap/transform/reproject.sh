# Reproject input shapefile from EPSG:4326 to EPSG:102713
# NAD 1983 StatePlane New Mexico Central FIPS 3002 Feet, aka ESRI:102713
# Map at https://geodesy.noaa.gov/SPCS/images/spcs83_conus_final.png
# Defined at https://epsg.io/102713
ogr2ogr \
    -t_srs epsg_102713.prj \
    -f "ESRI Shapefile"  \
    anaya_dams_102713.shp \
    anaya_dams.shp





