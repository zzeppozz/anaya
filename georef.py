import exifread
import os
from osgeo import ogr, osr
from xml.etree import ElementTree

INPATH = '/Users/astewart/Dropbox/Shared/Anaya Springs Pics for Aimee'
SHAPEFILENAME = 'anaya_springs.shp'
#inpath = inpath + '/58_RL-Gerview'

fnames = ['201411_anaya20141103_0017.JPG', '201411_anaya20141103_0021.JPG', 
          '201411_anaya20141103_0025.JPG', '201411_anaya20141103_0018.JPGx', 
          '201411_anaya20141103_0022.JPG', 'top-bot20141103_0100.JPG', 
          '201411_anaya20141103_0019.JPG', '201411_anaya20141103_0023.JPG', 
          'top-bot20141103_0101.JPG', '201411_anaya20141103_0020.JPG', 
          '201411_anaya20141103_0024.JPG', 'top-bot20141103_0102.JPG']

X_KEY = 'GPS GPSLongitude'
X_DIRECTION_KEY = 'GPS GPSLongitudeRef'
Y_KEY = 'GPS GPSLatitude'
Y_DIRECTION_KEY = 'GPS GPSLatitudeRef'
DATE_KEY = 'GPS GPSDate'

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
def getDate(basename):
   dt = tags['GPS GPSDate']

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
def _createLayer(fields, shpFname):
   ogr.RegisterAll()
   drv = ogr.GetDriverByName('ESRI Shapefile')
   tSRS = osr.SpatialReference()
   tSRS.ImportFromEPSG(4326)
   try:
      # Create the file object
      ds = drv.CreateDataSource(shpFname)
      if ds is None:
         raise Exception('Dataset creation failed for %s' % shpFname)
      # Create a layer
      lyr = ds.CreateLayer('anayaSprings', geom_type=ogr.wkbPoint, srs=tSRS)
      if lyr is None:
         raise Exception('Layer creation failed for %s.' % shpFname)
   except Exception, e:
      raise Exception('Failed creating dataset or layer for %s (%s)' 
                       % (shpFname, str(e)))
   # Create attributes
   for (fldname, fldtype) in fields:
      fldDefn = ogr.FieldDefn(fldname, fldtype)
      if lyr.CreateField(fldDefn) != 0:
         raise Exception('CreateField failed for %s' % (fldname))
   return ds, lyr
      
# ...............................................
def createFeatureInLayer(lyr, fname, pointdata, relStart):
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
def createShapefileAndKML(fields, shpfname, imageData, relStart):
   dataset = None
   dataset, lyr = _createLayer(fields, shpfname)
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
   # Read entire file
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
      # Get longitude, latitude
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
      # Convert to desired format
      dd = (xdd, ydd)
      xdms = (xdeg, xmin, xsec, xdir)
      ydms = (ydeg, ymin, ysec, ydir)  
      # Get date
      dtstr = tags[DATE_KEY].values
      [yr, mo, day] = [int(x) for x in dtstr.split(':')]
   return [yr, mo, day], dd, xdms, ydms

# .............................................................................
# .............................................................................

scriptname = os.path.splitext(os.path.basename(__file__))[0]
logfname = os.path.join(INPATH, scriptname+'.log')
log = open(logfname, 'w')
imageData = {}

for root, dirs, files in os.walk(INPATH):
   for fname in files:
      fullname = os.path.join(root, fname)
      [yr, mo, day], dd, xdms, ydms = processImageFile(log, fullname)
      if dd is not None:
         imageData[fullname] = ([yr, mo, day], dd, xdms, ydms)
      
relStart = len(INPATH) + 1
# createShapefileAndKML(FIELDS, os.path.join(INPATH, SHAPEFILENAME), 
#                      imageData, relStart)
for root, dirs, files in os.walk(INPATH):
   relpath = fullname[relStart:]
   print relpath
   for fname in files:
      fullname = os.path.join(root, fname)
      if fname.endswith('.JPG'):
         getDate(fname)
   


'''
#SCHEMA#
<Schema name="anaya_springs" id="anaya_springs">
        <SimpleField name="arroyo" type="string"></SimpleField>
        <SimpleField name="fullpath" type="string"></SimpleField>
        <SimpleField name="relpath" type="string"></SimpleField>
        <SimpleField name="basename" type="string"></SimpleField>
        <SimpleField name="geomwkt" type="string"></SimpleField>
        <SimpleField name="longitude" type="float"></SimpleField>
        <SimpleField name="latitude" type="float"></SimpleField>
        <SimpleField name="xdirection" type="string"></SimpleField>
        <SimpleField name="xdegrees" type="float"></SimpleField>
        <SimpleField name="xminutes" type="float"></SimpleField>
        <SimpleField name="xseconds" type="float"></SimpleField>
        <SimpleField name="ydirection" type="string"></SimpleField>
        <SimpleField name="ydegrees" type="float"></SimpleField>
        <SimpleField name="yminutes" type="float"></SimpleField>
        <SimpleField name="yseconds" type="float"></SimpleField>
</Schema>

#FOLDERNAME#
<name>anaya_springs</name>

#PLACEMARKS#
  <Placemark>
   <ExtendedData><SchemaData schemaUrl="#anaya_springs">
      <SimpleData name="arroyo">1 RR-Bill's toptobottom</SimpleData>
      <SimpleData name="fullpath">/Users/astewart/Home/AnneBill/AnayaSprings/1 RR-Bill's toptobottom/201411_anaya20141103_0020.JPG</SimpleData>
      <SimpleData name="relpath">AnayaSprings/1 RR-Bill's toptobottom/201411_anaya20141103_0020.JPG</SimpleData>
      <SimpleData name="basename">201411_anaya20141103_0020.JPG</SimpleData>
      <SimpleData name="geomwkt">Point (-106.0620556  35.4359889)</SimpleData>
      <SimpleData name="longitude">-106.062055555555560</SimpleData>
      <SimpleData name="latitude">35.435988888888886</SimpleData>
      <SimpleData name="xdirection">W</SimpleData>
      <SimpleData name="xdegrees">106.000000000000000</SimpleData>
      <SimpleData name="xminutes">3.000000000000000</SimpleData>
      <SimpleData name="xseconds">43.399999999999999</SimpleData>
      <SimpleData name="ydirection">N</SimpleData>
      <SimpleData name="ydegrees">35.000000000000000</SimpleData>
      <SimpleData name="yminutes">26.000000000000000</SimpleData>
      <SimpleData name="yseconds">9.560000000000000</SimpleData>
   </SchemaData></ExtendedData>
      <Point><coordinates>-106.0620556,35.4359889</coordinates></Point>
  </Placemark>

'''