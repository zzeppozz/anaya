import exifread
import os
from osgeo import ogr, osr

INPATH = '/Users/astewart/Home/AnneBill'
SHAPEFILENAME = 'anaya_springs.shp'
#inpath = inpath + '/58_RL-Gerview'

fnames = ['gerview20150407_0001.JPG', 'gerview20150407_0005.JPG', 
          'gerview20150407_0010.JPG', 'gerview20150407_0003.JPG', 
          'gerview20150407_0007.JPG']

X_KEY = 'GPS GPSLongitude'
X_DIRECTION_KEY = 'GPS GPSLongitudeRef'
Y_KEY = 'GPS GPSLatitude'
Y_DIRECTION_KEY = 'GPS GPSLatitudeRef'

GEOMETRY_WKT = "geomwkt"
LONGITUDE_FIELDNAME = 'longitude'
LATITUDE_FIELDNAME = 'latitude'

FIELDS = [('arroyo', ogr.OFTString), 
          ('fullpath', ogr.OFTString), 
          ('relpath', ogr.OFTString), 
          ('basename', ogr.OFTString),
          (GEOMETRY_WKT, ogr.OFTString),
          (LONGITUDE_FIELDNAME, ogr.OFTReal), 
          (LATITUDE_FIELDNAME, ogr.OFTReal), 
          ('xdirection', ogr.OFTString),
          ('xdegrees', ogr.OFTReal), 
          ('xminutes', ogr.OFTReal), 
          ('xseconds', ogr.OFTReal), 
          ('ydirection', ogr.OFTString),
          ('ydegrees', ogr.OFTReal), 
          ('yminutes', ogr.OFTReal), 
          ('yseconds', ogr.OFTReal)]

# ...............................................
def getDD(degObj, minObj, secObj, isNegative):
   degrees = degObj.num / float(degObj.den) 
   minutes = minObj.num / float(minObj.den)
   seconds = secObj.num / float(secObj.den)
   
   dd = (seconds/3600) + (minutes/60) + degrees
   if isNegative:
      dd = -1 * dd
   return dd, degrees, minutes, seconds
   
# ...............................................
def createLayer(fields, shpFname):
   ogr.RegisterAll()
   drv = ogr.GetDriverByName('ESRI Shapefile')
   tSRS = osr.SpatialReference()
   tSRS.ImportFromEPSG(4326)
   try:
      # Create the file object, a layer, and attributes
      ds = drv.CreateDataSource(shpFname)
      if ds is None:
         raise Exception('Dataset creation failed for %s' % shpFname)
      
      lyr = ds.CreateLayer('anayaSprings', geom_type=ogr.wkbPoint, srs=tSRS)
      if lyr is None:
         raise Exception('Layer creation failed for %s.' % shpFname)

   except Exception, e:
      raise Exception('Failed creating dataset or layer for %s (%s)' 
                       % (shpFname, str(e)))
      
   for (fldname, fldtype) in fields:
      fldDefn = ogr.FieldDefn(fldname, fldtype)
      if lyr.CreateField(fldDefn) != 0:
         raise Exception('CreateField failed for %s' % (fldname))
   return ds, lyr
      
# ...............................................
def createFeatureInLayer(lyr, fname, pointdata, relStart):
#   x = point[0]
#   y = point[1]
   ((xdd, ydd), (xdeg, xmin, xsec, xdir), (ydeg, ymin, ysec, ydir)) = pointdata
   pth, basefname = os.path.split(fname)
   relativePath = fname[relStart:]
   tmp, lastArroyo = os.path.split(pth)
   feat = ogr.Feature( lyr.GetLayerDefn() )
   try:
      feat.SetField('arroyo', lastArroyo)
      feat.SetField('fullpath', fname)
      feat.SetField('relpath', relativePath)
      feat.SetField('basename', basefname)
      feat.SetField('xdegrees', xdeg)
      feat.SetField('xminutes', xmin)
      feat.SetField('xseconds', xsec)
      feat.SetField('xdirection', xdir)
      feat.SetField('ydegrees', ydeg)
      feat.SetField('yminutes', ymin)
      feat.SetField('yseconds', ysec)
      feat.SetField('ydirection', ydir)
      feat.SetField(LONGITUDE_FIELDNAME, xdd)
      feat.SetField(LATITUDE_FIELDNAME, ydd)
      if xdd is not None and ydd is not None:
         wkt = 'Point (%.7f  %.7f)' % (xdd, ydd)
         feat.SetField(GEOMETRY_WKT, wkt)
         geom = ogr.CreateGeometryFromWkt(wkt)
         feat.SetGeometryDirectly(geom)
      else:
         print 'Failed to set geom with x = %s and y = %s' % (str(xdd), str(ydd))
   except Exception, e:
      print 'Failed to fillOGRFeature, e = %s' % str(e)
   else:
      # Create new feature, setting FID, in this layer
      lyr.CreateFeature(feat)
      feat.Destroy()
      
# ...............................................
def createLayerShapefile(fields, shpfname, imageData, relStart):
   dataset = None
   dataset, lyr = createLayer(fields, shpfname)
   for fname, pointdata in imageData.iteritems():
      feat = createFeatureInLayer(lyr, fname, pointdata, relStart)
   if dataset is not None:
      dataset.Destroy()
      print('Closed/wrote dataset %s' % shpfname)
      success = True
   return success

# ...............................................
def processImageFile(log, fullname):
   dd = xdms = ydms = None
   tmp, ext = os.path.splitext(fullname)
   if ext in ('.jpg', '.JPG'):
      try:
         # Open image file for reading (binary mode)
         f = open(fullname, 'rb')
         # Get Exif tags
         tags = exifread.process_file(f)
      except Exception, e:
         print('{}: Unable to read image metadata'.format(fullname))
      finally:
         f.close()
         
      xIsNeg = yIsNeg = False
      xDegrees, xMinutes, xSeconds = tags[X_KEY].values
      yDegrees, yMinutes, ySeconds = tags[Y_KEY].values
      xdir = tags[X_DIRECTION_KEY].printable
      ydir = tags[Y_DIRECTION_KEY].printable
      if xdir == 'W':
         xIsNeg = True
      if ydir == 'S':
         yIsNeg = True
      xdd, xdeg, xmin, xsec = getDD(xDegrees, xMinutes, xSeconds, xIsNeg)
      ydd, ydeg, ymin, ysec = getDD(yDegrees, yMinutes, ySeconds, yIsNeg)
      
      dd = (xdd, ydd)
      xdms = (xdeg, xmin, xsec, xdir)
      ydms = (ydeg, ymin, ysec, ydir)
      
   return dd, xdms, ydms

# .............................................................................
# .............................................................................

scriptname = os.path.splitext(os.path.basename(__file__))[0]
logfname = os.path.join(INPATH, scriptname+'.log')
log = open(logfname, 'w')
imageData = {}

for root, dirs, files in os.walk(INPATH):
   for fname in files:
      fullname = os.path.join(root, fname)
      dd, xdms, ydms = processImageFile(log, fullname)
      if dd is not None:
         imageData[fullname] = (dd, xdms, ydms)
      
relStart = len(INPATH) + 1
createLayerShapefile(FIELDS, os.path.join(INPATH, SHAPEFILENAME), 
                     imageData, relStart)

