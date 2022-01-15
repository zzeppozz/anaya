# Reproject input shapefile dam_anaya.shp from EPSG:4326 to dam_anaya_102713.shp in EPSG:102713
# NAD 1983 StatePlane New Mexico Central FIPS 3002 Feet, aka ESRI:102713
ogr2ogr \
    -t_srs EPSG:102713   \
    -f `ESRI Shapefile`  \
    dam_anaya_102713.shp \
    dam_anaya.shp
