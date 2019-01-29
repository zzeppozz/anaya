import exifread
import os
from osgeo import ogr, osr
from xml.etree import ElementTree

inpath = '/Users/astewart/Home/'
testpath = '/Users/astewart/Home/2017AnayaPics/1-RR-Billstoptobottom/'
outpath = '/Users/astewart/Google Drive/Shared/Anaya_Springs/process2019/'

rsdir = 'satellite'
ancdir = 'ancillary'
vdir = 'points'
picdir = 'AnayaSprings'
outdir = 'process2019'

dir2015 = '2015AnayaPics'
dir2016 = '2016AnayaPics'
dir2017 = '2017AnayaPics'


OUTNAME = 'anaya_springs2019'

X_KEY = 'GPS GPSLongitude'
X_DIR_KEY = 'GPS GPSLongitudeRef'
Y_KEY = 'GPS GPSLatitude'
Y_DIR_KEY = 'GPS GPSLatitudeRef'
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
def getDate(tags):
    # Get date
    dtstr = tags[DATE_KEY].values
    [yr, mo, day] = [int(x) for x in dtstr.split(':')]
    return  yr, mo, day
        
# ...............................................
def _getLocationDim(tags, locKey, dirKey, negativeIndicator):
    isNegative = False
    # Get longitude or latitude
    degObj, minObj, secObj = tags[locKey].values
    dir = tags[dirKey].printable
    if dir == negativeIndicator:
        isNegative = True
    # Convert to float
    degrees = degObj.num / float(degObj.den) 
    minutes = minObj.num / float(minObj.den)
    seconds = secObj.num / float(secObj.den)    
    # Convert to decimal degrees
    dd = (seconds/3600) + (minutes/60) + degrees
    if isNegative:
        dd = -1 * dd
    return dd, degrees, minutes, seconds, dir

# ...............................................
def getDD(tags):
    xdd, xdeg, xmin, xsec, xdir = _getLocationDim(tags, X_KEY, X_DIR_KEY, 'W')
    ydd, ydeg, ymin, ysec, ydir = _getLocationDim(tags, Y_KEY, Y_DIR_KEY, 'S')
    # Convert to desired format
    dd = (xdd, ydd)
    xdms = (xdeg, xmin, xsec, xdir)
    ydms = (ydeg, ymin, ysec, ydir)  
    
    return dd, xdms, ydms
    
# ...............................................
def _open_kml_file(fname):
    if os.path.exists(fname):
        os.remove(fname)
    foldername, _ = os.path.splitext(os.path.basename(fname))
    f = open(fname, 'w')
    f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    f.write('<Document id="root_doc">\n')
    f.write('<Folder><name>{}</name>\n'.format(foldername))
    return f

# ...............................................
def _close_kml_file(kmlf):
    kmlf.write('</Folder>\n')
    kmlf.write('</Document></kml>\n')
    kmlf.close()

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
def createFeatureInLayer(lyr, fname, pointdata, start_idx):
    ([yr, mo, day], (xdd, ydd), 
     (xdeg, xmin, xsec, xdir), (ydeg, ymin, ysec, ydir)) = pointdata
    pth, basefname = os.path.split(fname)
    relativePath = fname[start_idx:]
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
def createFeatureInKML(kmlf, fname, pointdata, start_idx):
    """
    <img style="max-width:500px;" 
     src="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
     SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
    """
    ([yr, mo, day], (xdd, ydd), xvals, yvals) = pointdata
    pth, basefname = os.path.split(fname)
    basename, _ = os.path.splitext(basefname)
    relativePath = fname[start_idx:]
    url = 'http://129.237.183.10/images/'
    tmp, lastArroyo = os.path.split(pth)
    dt = '{}-{}-{}'.format(yr, mo, day)

    kmlf.write('  <Placemark>\n')
    kmlf.write('    <name>{}</name>\n'.format(basefname))
    kmlf.write('    <description>{} in {} on {}</description>\n'.format(basename, lastArroyo, dt))
#     kmlf.write('    <img style="max-width:500px;" src="file://{}">\n'.format(fname))
    kmlf.write('    <img style="max-width:500px;" src="{}{}">\n'.format(url, relativePath)) 
        
    kmlf.write('    <Point>\n')
    kmlf.write('      <coordinates>{},{}</coordinates>\n'.format(xdd, ydd))
    kmlf.write('    </Point>\n')

    kmlf.write('  </Placemark>\n')
        
        
# ...............................................
def createShapefileAndKML(fields, shpfname, kmlfname, imageData, start_idx):
    kmlf = _open_kml_file(kmlfname)
    dataset, lyr = _createLayer(fields, shpfname)
    
    for fname, pointdata in imageData.iteritems():
        print('Writing feature {}'.format(fname))
        createFeatureInKML(kmlf, fname, pointdata)
        createFeatureInLayer(lyr, fname, pointdata, start_idx)
        
    _close_kml_file(kmlf)
    if dataset is not None:
        dataset.Destroy()
        print('Closed/wrote dataset %s' % shpfname)
        success = True
    
    return success


# ...............................................
def processImageFile(log, fullname):
    dd = xdms = ydms = yr = mo = day = None
    try:
        # Open image file for reading (binary mode)
        f = open(fullname, 'rb')
        # Get Exif tags
        tags = exifread.process_file(f)
    except Exception, e:
        print('{}: Unable to read image metadata'.format(fullname))
    finally:
        f.close()
    try:
        dd, xdms, ydms = getDD(tags)
    except Exception, e:
        print('{}: Unable to get x y'.format(fullname))
    try:
        yr, mo, day = getDate(tags)
    except Exception, e:
        print('{}: Unable to get date'.format(fullname))
    return [yr, mo, day], dd, xdms, ydms

# .............................................................................
# .............................................................................

sep = '_'
scriptname = os.path.splitext(os.path.basename(__file__))[0]
logfname = os.path.join(outpath, scriptname+'.log')
# log = open(logfname, 'w')
log = None
start_idx = len(inpath)

# for dir in (dir2015, dir2016, dir2017):
for dir in [dir2017]:
    this_year = dir[:4]
    this_fname = OUTNAME + sep + this_year 
    shpfname = os.path.join(outpath, this_fname + '.shp')
    kmlfname = os.path.join(outpath, this_fname + '.kml')
    
    # Read data
    imageData = {}
    thispath = os.path.join(inpath, dir)
    for root, dirs, files in os.walk(thispath):
        for fname in files:
            if fname.endswith('jpg') or fname.endswith('JPG'): 
                fullname = os.path.join(root, fname)
                print('Reading {}'.format(fullname))
                [yr, mo, day], dd, xdms, ydms = processImageFile(log, fullname)
                if dd is not None:
                    imageData[fullname] = ([yr, mo, day], dd, xdms, ydms)

    # Write data
    createShapefileAndKML(FIELDS, shpfname, kmlfname, imageData, start_idx)

# for root, dirs, files in os.walk(testpath):
#     relpath = fullname[start_idx:]
#     for fname in files:
#         fullname = os.path.join(root, fname)
#         if fname.endswith('.JPG'):
#             print fname
     


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