import exifread
import os
from osgeo import ogr, osr
import logging
from PIL import Image
import time

# .............................................................................
class IMG_META:
    X_KEY = 'GPS GPSLongitude'
    X_DIR_KEY = 'GPS GPSLongitudeRef'
    Y_KEY = 'GPS GPSLatitude'
    Y_DIR_KEY = 'GPS GPSLatitudeRef'
    DATE_KEY = 'GPS GPSDate'

# .............................................................................
class PicMapper(object):
# .............................................................................
    """
    Class to write a shapefile from GBIF CSV output or BISON JSON output 
    export p3=/Library/Frameworks/Python.framework/Versions/3.7/bin/python3.7
    """    
    GEOMETRY_WKT = "geomwkt"
    LONGITUDE_FIELDNAME = 'longitude'
    LATITUDE_FIELDNAME = 'latitude'
    
    FIELDS = [('arroyo', ogr.OFTString), 
              ('fullpath', ogr.OFTString), 
              ('relpath', ogr.OFTString), 
              ('basename', ogr.OFTString),
              ('imgdate', ogr.OFTString),
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

# ............................................................................
# Constructor
# .............................................................................
    def __init__(self, image_path, buffer_distance=.002, bbox=(-180, -90, 180, 90), 
                 do_kml=True, do_shape=False, logger=None):
        """
        @param image_path: Root path for image files to be processed
        @param image_buffer: Buffer in which images are considered to be the same location
        @param bbox: Tuple of the bounds of the output data, in 
                     (minx, miny, maxX, maxY) format.  Outside these bounds, 
                     images will be discarded
        @param do_kml: Do or not create a KML file for Google Earth
        @param do_shape: Do or not create a GIS shapefile
        """
        self.image_path = image_path
        self.buffer_distance = buffer_distance
        self.bbox = bbox
        self.do_kml = do_kml
        self.do_shape = do_shape
        self._logger = logger
    
    # ...............................................
    def _getDate(self, tags):
        # Get date
        dtstr = tags[IMG_META.DATE_KEY].values
        [yr, mo, day] = [int(x) for x in dtstr.split(':')]
        return  yr, mo, day
    
    # ...............................................
    def _log(self, msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)
            
    # ...............................................
    def _getLocationDim(self, tags, locKey, dirKey, negativeIndicator):
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
    def _getDD(self, tags):
        xdd, xdeg, xmin, xsec, xdir = self._getLocationDim(
            tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY, 'W')
        ydd, ydeg, ymin, ysec, ydir = self._getLocationDim(
            tags, IMG_META.Y_KEY, IMG_META.Y_DIR_KEY, 'S')
        # Convert to desired format
        dd = (xdd, ydd)
        xdms = (xdeg, xmin, xsec, xdir)
        ydms = (ydeg, ymin, ysec, ydir)  
        
        return dd, xdms, ydms
        
    # ...............................................
    def _open_kml_file(self, fname):
        """
        @todo: gather bounds from images
        """
        (minX, minY, maxX, maxY) = self.bbox
        if os.path.exists(fname):
            os.remove(fname)
        foldername, _ = os.path.splitext(os.path.basename(fname))
        f = open(fname, 'w')
        f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
        f.write('<Document id="root_doc">\n')
        f.write('<Folder><name>{}</name>\n'.format(foldername))
        f.write('   <GroundOverlay>\n')
        f.write('      <name>Satellite overlay on terrain</name>\n')
        f.write('      <description>Local imagery</description>\n')
        f.write('      <Icon><href>{}</href></Icon>\n'.format(SAT_IMAGE_FNAME))
        f.write('      <LatLonBox>\n')
        f.write('         <north>{}</north>\n'.format(maxY))
        f.write('         <south>{}</south>\n'.format(minY))
        f.write('         <east>{}</east>\n'.format(maxX))
        f.write('         <west>{}</west>\n'.format(minX))
        f.write('         <rotation>-0.1556640799496235</rotation>\n')
        f.write('      </LatLonBox>\n')
        f.write('   </GroundOverlay>\n')
        return f
    
    # ...............................................
    def _close_kml_file(self, kmlf):
        kmlf.write('</Folder>\n')
        kmlf.write('</Document></kml>\n')
        kmlf.close()
    
    # ...............................................
    def _createLayer(self, fields, shpFname):
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
        except Exception as e:
            raise Exception('Failed creating dataset or layer for %s (%s)' 
                                  % (shpFname, str(e)))
        # Create attributes
        for (fldname, fldtype) in fields:
            fldDefn = ogr.FieldDefn(fldname, fldtype)
            if lyr.CreateField(fldDefn) != 0:
                raise Exception('CreateField failed for %s' % (fldname))
        return ds, lyr
            
    # ...............................................
    def _createFeatureInLayer(self, lyr, fname, pointdata, start_idx):
        ([yr, mo, day], (xdd, ydd), 
         (xdeg, xmin, xsec, xdir), (ydeg, ymin, ysec, ydir)) = pointdata
        pth, basefname = os.path.split(fname)
        relative_path = fname[start_idx:]    
        tmp, lastArroyo = os.path.split(pth)
        feat = ogr.Feature( lyr.GetLayerDefn() )
        try:
            feat.SetField('arroyo', lastArroyo)
            feat.SetField('fullpath', fname)
            feat.SetField('relpath', relative_path)
            feat.SetField('basename', basefname)
            feat.SetField('imgdate', '{}-{}-{}'.format(yr, mo, day))
            feat.SetField('xdegrees', xdeg)
            feat.SetField('xminutes', xmin)
            feat.SetField('xseconds', xsec)
            feat.SetField('xdirection', xdir)
            feat.SetField('ydegrees', ydeg)
            feat.SetField('yminutes', ymin)
            feat.SetField('yseconds', ysec)
            feat.SetField('ydirection', ydir)
            feat.SetField(self.LONGITUDE_FIELDNAME, xdd)
            feat.SetField(self.LATITUDE_FIELDNAME, ydd)
            if xdd is not None and ydd is not None:
                wkt = 'Point (%.7f  %.7f)' % (xdd, ydd)
                feat.SetField(self.GEOMETRY_WKT, wkt)
                geom = ogr.CreateGeometryFromWkt(wkt)
                feat.SetGeometryDirectly(geom)
            else:
                self._log('Failed to set geom with x = {} and y = {}'
                          .format(xdd, ydd))
        except Exception as e:
            self._log('Failed to fillOGRFeature, e = {}'.format(e))
        else:
            # Create new feature, setting FID, in this layer
            lyr.CreateFeature(feat)
            feat.Destroy()
            
    # ...............................................
    def _createFeatureInKML(self, kmlf, fname, pointdata, start_idx):
        """
        <img style="max-width:500px;" 
         src="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
         SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
        """
        ([yr, mo, day], (xdd, ydd), xvals, yvals) = pointdata
        pth, basefname = os.path.split(fname)
        basename, _ = os.path.splitext(basefname)
        relativePath = fname[start_idx:]
    #     urlbase = 'http://129.237.183.10/images/'
    #     url = urlbase + relativePath
    #     url = 'http://badenov.nhm.ku.edu/images/Potsdamn20150522_0002.JPG'
        _, lastArroyo = os.path.split(pth)
        dt = '{}-{}-{}'.format(yr, mo, day)
    
        kmlf.write('  <Placemark>\n')
        kmlf.write('    <name>{}</name>\n'.format(basefname))
        kmlf.write('    <description>{} in {} on {}</description>\n'.format(basename, lastArroyo, dt))
        kmlf.write('    <img style="max-width:500px;" src="file://{}"></img>\n'.format(fname))
        kmlf.write('    <Point><coordinates>{},{}</coordinates></Point>\n'.format(xdd, ydd))
        kmlf.write('  </Placemark>\n')
            
    # ...............................................
    def _reduceImageSize(self, infname, outfname):
        basewidth = 500
        img = Image.open(infname)
        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)
        img.save(outfname)
        print('Rewrote image {} to {}'.format(infname, outfname))
        
    # ...............................................
    def _testBufferAddLocation(self, all_coords, currfname, currpointdata):
        (_, (currx, curry), _, _) = currpointdata
        for fname, (x,y) in all_coords.iteritems():
            dx = abs(abs(x) - abs(currx))
            dy = abs(abs(y) - abs(curry))
            if dx < self.buffer_distance or dy < self.buffer_distance:
                self._log('Current file {} is within buffer of {} (dx = {}, dy = {})'
                          .format(currfname, fname, dx, dy))
                break
        all_coords[currfname] = (currx, curry)
        return all_coords
            
    # ...............................................
    def createShapefileAndKML(self, out_image_path, shpfname, kmlfname, imageData, start_idx):
        if self.do_kml:
            kmlf = self._open_kml_file(kmlfname)
        if self.do_shape:
            dataset, lyr = self._createLayer(self.FIELDS, shpfname)
            
        all_coords = {}
        for infname, pointdata in imageData.iteritems():
            # Reduce image
            relativePath = infname[start_idx:]
            outfname = os.path.join(out_image_path, relativePath)
            outfname = out_image_path + relativePath
            self._reduceImageSize(infname, outfname)
            
            print('Writing feature {} to existing {} locations'.format(
                outfname, len(all_coords)))
            all_coords = self._testBufferAddLocation(all_coords, outfname, pointdata)
            if self.do_kml:
                self._createFeatureInKML(kmlf, outfname, pointdata, start_idx)
            if self.do_shape:
                self._createFeatureInLayer(lyr, outfname, pointdata, start_idx)
            
        if self.do_kml:
            self._close_kml_file(kmlf)
        if self.do_shape:
            dataset.Destroy()
            print('Closed/wrote dataset %s' % shpfname)
            success = True
            self._log('Success {} writing shapefile {}'.format(success, 
                                                               shpfname))
    
    
    # ...............................................
    def processImageFile(self, fullname):
        dd = xdms = ydms = yr = mo = day = None
        try:
            # Open image file for reading (binary mode)
            f = open(fullname, 'rb')
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self._log('{}: Unable to read image metadata'.format(fullname))
        finally:
            f.close()
        try:
            dd, xdms, ydms = self._getDD(tags)
        except Exception as e:
            self._log('{}: Unable to get x y'.format(fullname))
        try:
            yr, mo, day = self._getDate(tags)
        except Exception as e:
            self._log('{}: Unable to get date'.format(fullname))
        return [yr, mo, day], dd, xdms, ydms
    
    # ...............................................
    def evaluateExtent(self, dd, minX, minY, maxX, maxY):
        if dd[0] < minX:
            minX = dd[0]
        if dd[0] > maxX:
            maxX = dd[0]
            
        if dd[1] < minY:
            minY = dd[1]
        if dd[1] > maxY:
            maxY = dd[1]
        return minX, minY, maxX, maxY
    
#     # ...............................................
#     def reduceAllImages(self, imageData, outpath, start_idx):
#         for infname, pointdata in imageData.iteritems():
#             relativePath = infname[start_idx:]
#             outfname = os.path.join(outpath, relativePath)
#             print('Rewriting image {} to {}'.format(infname, outfname))
#             self._reduceImageSize(infname, outfname)
    
    # ...............................................
    def readAllImages(self, inpath):
        minX = minY = 9999
        maxX = maxY = -9999
        imageData = {}
        for root, dirs, files in os.walk(inpath):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    fullname = os.path.join(root, fname)
#                     self._log('Reading {}'.format(fullname))
                    [yr, mo, day], dd, xdms, ydms = pm.processImageFile(fullname)
                    if dd is not None:
                        minX, minY, maxX, maxY = pm.evaluateExtent(dd, minX, minY, maxX, maxY)
                        imageData[fullname] = ([yr, mo, day], dd, xdms, ydms)
        return imageData

# .............................................................................
def getLogger(outpath):
    LOG_FORMAT = ' '.join(["%(asctime)s",
                       "%(threadName)s.%(module)s.%(funcName)s",
                       "line",
                       "%(lineno)d",
                       "%(levelname)-8s",
                       "%(message)s"])
    LOG_DATE_FORMAT = '%d %b %Y %H:%M'
    # get name
    scriptname, _ = os.path.splitext(os.path.basename(__file__))
    secs = time.time()
    timestamp = "{}".format(time.strftime("%Y%m%d-%H%M", time.localtime(secs)))
    logname = '{}.{}'.format(scriptname, timestamp)
    logfname = os.path.join(outpath, logname + '.log')
    # get logger
    log = logging.getLogger(logname)
    log.setLevel(logging.DEBUG)
    fileLogHandler = logging.handlers.RotatingFileHandler(logfname, 
                                            maxBytes=52000000, backupCount=2)
    # add file handler
    fileLogHandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    fileLogHandler.setFormatter(formatter)
    log.addHandler(fileLogHandler)
    return log

# .............................................................................
def getBbox(bbox_str):
    bbox = []
    parts = bbox_str.split(',')
    if len(parts) != 4:
        print('Failed to get 4 values for bbox from {}'.format(bbox_str))
    else:
        for i in range(len(parts)):
            pt = parts[i].strip()
            tmp = pt.rstrip(')').lstrip('(')
            try:
                val = float(tmp)
            except: 
                print('Failed to parse element {} from {} into float value'
                      .format(i, bbox_str))
            else:
                bbox.append(val)
    return bbox
        


# .............................................................................
# .............................................................................
# ...............................................
if __name__ == '__main__':
    OUTPATH = '/Users/astewart/Google Drive/Shared/Anaya_Springs/process2019/'
    OUTNAME = 'dam_anaya'
    KML_PATH = '/Users/astewart/Home/AnayaGE'
    IMAGE_PATHS = [
    #     (2015, '/Users/astewart/Home/2015AnayaPics'),
    #     (2016, '/Users/astewart/Home/2016AnayaPics'),
        (2017, '/Users/astewart/Home/2017AnayaPics')]
    SAT_IMAGE_FNAME = '/Users/astewart/Google Drive/Shared/Anaya_Springs/satellite/op140814.tif'
    SAT_DIR = 'satellite'
    ANC_DIR = 'ancillary'
    
    maxY = 35.45045
    minY = 35.43479
    maxX = -106.05353
    minX = -106.07259
    
    dam_buffer = .0002

    import argparse
    parser = argparse.ArgumentParser(
             description=(""""Read a directory full of image files, then for 
             each image, gather metadata, optionally rewrite the image as a
             smaller file, and write as a feature in a KML file, Shapefiles, or 
             both."""))
    parser.add_argument('image_path', default=None,
             help=('Root path for image files to be processed.'))
    parser.add_argument('--buffer', type=float, default=dam_buffer,
             help=("""Buffer distance in decimal degrees, in which images can 
             be considered to be the same location"""))
    parser.add_argument('--bbox', type=str, 
                        default="({}, {}, {}, {})".format(minX, minY, maxX, maxY),
             help=("""Tuple of the bounds of the output data, in 
                     (minx, miny, maxX, maxY) format.  Outside these bounds, 
                     images will be discarded"""))
    parser.add_argument('--do_kml', type=bool, default=True,
             help=('Boolean flag to create a KML file for Google Earth'))
    parser.add_argument('--do_shape', type=bool, default=False,
             help=('Boolean flag to create shapefiles for GIS applications'))
    args = parser.parse_args()
    
    image_path = args.image_path
    buffer_distance = args.buffer
    bbox_str = args.bbox
    kml_flag = args.do_kml
    shp_flag = args.do_shape

    base_path = '/Users/astewart/Home/'
    sep = '_'
    bbox = getBbox(bbox_str)
    
    pm = PicMapper(base_path, buffer_distance=buffer_distance, 
                   bbox=(minX, minY, maxX, maxY), 
                   do_kml=kml_flag, do_shape=shp_flag)
    
    for yr, indir in IMAGE_PATHS:
        pm.image_path = indir
        
        this_fname = OUTNAME + sep + str(yr) 
        shpfname = os.path.join(OUTPATH, this_fname + '.shp')
        kmlfname = os.path.join(KML_PATH, this_fname + '.kml')
        start_idx = len(indir)
        
        # Read data
        imageData = pm.readAllImages(indir)
    
        # Reduce image sizes
        outdir = os.path.join(KML_PATH, str(yr))
        print indir, outdir
        
        # Write data
        pm.createShapefileAndKML(outdir, shpfname, kmlfname, imageData, start_idx)
     


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

<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
<Placemark>
    <name>Grey-Bottom20151201_0002.JPG</name>
    <description>Grey-Bottom20151201_0002 in 13-LL-GreyBottom on 2015-12-1</description>
    <gx:balloonVisibility>1</gx:balloonVisibility>
    <Point>
        <coordinates>-106.067033333,35.4413833333,0</coordinates>
    </Point>
    <img style="max-width:500px;" src="file:///Users/astewart/Home/2017AnayaPics/13-LL-GreyBottom/Grey-Bottom20151201_0002.JPG"></img>
</Placemark>
</kml>

'''