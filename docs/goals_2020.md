# Data
* SRS - EPSG:102713, match satellite image
* Layers:
  * Split dams into separate point layers (reproject)
  * Satellite raster
  * Flowline vector (reproject)

* Send Bill
  * ancillary/dam layers
  * KMZ file
  * CSV and Shapefiles

## Printed map
* Print: 40” square, 150-300 dpi

## Digital map
* Dam symbol arc, concave side facing downhill

## Other decisions

HUC data – not fine enough

Use flowline

### Orthophoto tfw file definition
https://en.wikipedia.org/wiki/World_file

```
Line 1: A: x-component of the pixel width (x-scale)
Line 2: D: y-component of the pixel width (y-skew)
Line 3: B: x-component of the pixel height (x-skew)
Line 4: E: y-component of the pixel height (y-scale), typically negative
Line 5: C: x-coordinate of the center of the original image's upper left pixel transformed to the map
Line 6: F: y-coordinate of the center of the original image's upper left pixel transformed to the map
```
