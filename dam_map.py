import exifread
import os
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
    Yelp help: https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
    """    
    GEOMETRY_WKT = "geomwkt"
    LONGITUDE_FIELDNAME = 'longitude'
    LATITUDE_FIELDNAME = 'latitude'
    
    FIELDS = ['arroyo', 
              'fullpath', 
              'relpath', 
              'basename', 
              'imgdate', 
              GEOMETRY_WKT, 
              LONGITUDE_FIELDNAME,
              LATITUDE_FIELDNAME,
              'xdirection', 
              'xdegrees', 
              'xminutes', 
              'xseconds', 
              'ydirection', 
              'ydegrees', 
              'yminutes',
              'yseconds']

# ............................................................................
# Constructor
# .............................................................................
    def __init__(self, image_path, buffer_distance=.002, bbox=(-180, -90, 180, 90), 
                 logger=None):
        """
        @param image_path: Root path for image files to be processed
        @param image_buffer: Buffer in which images are considered to be the 
               same location
        @param bbox: Bounds of the output data, in (minX, minY, maxX, maxY) 
               format.  Outside these bounds, images will be discarded
        """
        self.image_path = image_path
        self.buffer_distance = buffer_distance
        self.bbox = bbox
        # Compute actual bounds of the data
        self._minX = bbox[0]
        self._minY = bbox[1]
        self._maxX = bbox[2]
        self._maxY = bbox[3]
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
    def _open_kml_file(self, fname, satellite_fname):
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
        if satellite_fname is not None:
            f.write('      <Icon><href>{}</href></Icon>\n'.format(satellite_fname))
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
    def _createFeatureInKML(self, kmlf, fname, rel_fname, pointdata):
        """
        <img style="max-width:500px;" 
         src="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
         SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
        """
        ([yr, mo, day], (xdd, ydd), xvals, yvals) = pointdata
        imgname, _ = os.path.splitext(os.path.basename(fname))
        parts = rel_fname.split('\\')
        lastArroyo = parts[0]
        dt = '{}-{}-{}'.format(yr, mo, day)
    
        kmlf.write('  <Placemark>\n')
        kmlf.write('    <name>{}</name>\n'.format(imgname))
        kmlf.write('    <description>{} in {} on {}</description>\n'.format(imgname, lastArroyo, dt))
        kmlf.write('    <img style="max-width:500px;" src="file://{}"></img>\n'.format(fname))
        kmlf.write('    <Point><coordinates>{},{}</coordinates></Point>\n'.format(xdd, ydd))
        kmlf.write('  </Placemark>\n')
        
    # ...............................................
    def _testBufferAddLocation(self, all_coords, currfname, currpointdata):
        (_, (currx, curry), _, _) = currpointdata
        for fname, (x,y) in all_coords.items():
            dx = abs(abs(x) - abs(currx))
            dy = abs(abs(y) - abs(curry))
            if dx < self.buffer_distance or dy < self.buffer_distance:
                self._log('Current file {} is within buffer of {} (dx = {}, dy = {})'
                          .format(currfname, fname, dx, dy))
                break
        all_coords[currfname] = (currx, curry)
        return all_coords
            
    # ...............................................
    def createKML(self, kmlfname, imageData, resize_width=500, resize_path=None, satellite_fname=None):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        kmlf = self._open_kml_file(kmlfname, satellite_fname)
            
        all_coords = {}
        for arroyo_name, arroyo_data in imageData.items():
            imageinfo = []
            for key, val in arroyo_data.items():
                if key == 'num':
                    arroyo_num = val
                else:
                    imageinfo.append((key, val))
            for fname, pointdata in imageinfo:
                # Resize image?
                if resize_path is not None:
                    if not resize_path.endswith('/'):
                        resize_path = resize_path + '/'
                    # includes trailing /
                    rel_fname = fname[len(self.image_path):]
                    newrel_fname = rel_fname.replace(')', '-')
                    resize_fname = resize_path + newrel_fname
                    reduceImageSize(fname, resize_fname, resize_width, Image.ANTIALIAS)
                    fname = resize_fname
                else:
                    rel_fname = fname[len(self.image_path):]
                self._createFeatureInKML(kmlf, fname, rel_fname, pointdata)
            
        self._close_kml_file(kmlf)
    
    
    # ...............................................
    def getImageMetadata(self, fullname):
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
    def evaluateExtent(self, dd):
        if self._minX is None:
            self._minX = dd[0]
            self._maxX = dd[0]
            self._minY = dd[1]
            self._maxY = dd[1]
        else:
            if dd[0] < self._minX:
                self._minX = dd[0]
            if dd[0] > self._maxX:
                self._maxX = dd[0]
                
            if dd[1] < self._minY:
                self._minY = dd[1]
            if dd[1] > self._maxY:
                self._maxY = dd[1]
    
    # ...............................................
    def parse_filename(self, root, fname):
        name = ''
        dt = ''
        count = ''
        oncount = False
        _, arroyo = os.path.split(root)
        arroyo_num, arroyo_name = arroyo.split(')')
        for ch in fname:
            try:
                int(ch)
                if oncount:
                    count += ch
                else:
                    dt += ch
            except:
                if ch == '_':
                    oncount = True
                else:
                    name += ch
        year = int(dt[:4])
        picnum = int(count)
        return arroyo_num, arroyo_name, name, year, picnum    
        
    # ...............................................
    def readAllImages(self):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        image_data = {}
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    arroyo_num, arroyo_name, name, year, picnum = self.parse_filename(root, fname)
                    try:
                        image_data[arroyo_name]['num'] = arroyo_num
                    except KeyError:
                        image_data[arroyo_name] = {'num': arroyo_num}
                        
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.evaluateExtent(dd)
                    image_data[arroyo_name][orig_fname] =  ([yr, mo, day], dd, xdms, ydms)
                        
        return image_data

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
        
# ...............................................
def readyFilename(fullfilename, overwrite=True):
    if os.path.exists(fullfilename):
        if overwrite:
            try:
                os.remove(fullfilename)
            except Exception as e:
                raise Exception('Unable to delete {} ({})'.format(fullfilename, e))
            else:
                return True
        else:
            return False
    else:
        pth, basename = os.path.split(fullfilename)
        try:
            os.makedirs(pth)
        except:
            pass
            
        if os.path.isdir(pth):
            return True
        else:
            raise Exception('Failed to create directories {}'.format(pth))

# ...............................................
def reduceImageSize(infname, outfname, width, sample_method):
    readyFilename(outfname, overwrite=True)
    img = Image.open(infname)
    wpercent = (width / float(img.size[0]))
    height = int((float(img.size[1]) * float(wpercent)))
    size = (width, height)
    img = img.resize(size, sample_method)
    img.save(outfname)
    print('Rewrote image {} to {}'.format(infname, outfname))


# .............................................................................
# .............................................................................
# ...............................................
if __name__ == '__main__':
    INPATH = '/Users/astewart/Home/anaya_pics/'
    SMALLPATH = '/Users/astewart/Home/anaya_pics_sm/'
    OUTPATH = '/Users/astewart/Home/AnayaGE'
    OUTNAME = 'dam_anaya'
    SAT_IMAGE_FNAME = '/Users/astewart/Home/AnayaGE/satellite/op140814.tif'
    
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
                     (minX, minY, maxX, maxY) format.  Outside these bounds, 
                     images will be discarded"""))
    args = parser.parse_args()
    
    image_path = args.image_path
    buffer_distance = args.buffer
    bbox_str = args.bbox
    kml_flag = args.do_kml

    sep = '_'
    bbox = getBbox(bbox_str)
    
    pm = PicMapper(image_path, buffer_distance=buffer_distance, 
                   bbox=(minX, minY, maxX, maxY))
    
    kmlfname = os.path.join(OUTPATH, OUTNAME + '.kml')
    
    # Read data
    imageData = pm.readAllImages()
    print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
    print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))

    # Write data
    pm.createKML(kmlfname, imageData, resize_width=500, resize_path=SMALLPATH, 
                 satellite_fname=SAT_IMAGE_FNAME)
     


'''
from dam_map import *

import exifread
import os
import logging
from PIL import Image
import time

INPATH = '/Users/astewart/Home/anaya_pics/'
SMALLPATH = '/Users/astewart/Home/anaya_pics_sm/'
OUTPATH = '/Users/astewart/Home/AnayaGE'
OUTNAME = 'dam_anaya'
SAT_IMAGE_FNAME = '/Users/astewart/Home/AnayaGE/satellite/op140814.tif'

maxY = 35.45045
minY = 35.43479
maxX = -106.05353
minX = -106.07259

image_path = INPATH

pm = PicMapper(image_path, 
               bbox=(minX, minY, maxX, maxY))

kmlfname = os.path.join(OUTPATH, OUTNAME + '.kml')

# Read data
imageData = pm.readAllImages()
print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))


# Write data
pm.createKML(kmlfname, imageData, resize_width=500, resize_path=SMALLPATH,
             satellite_fname=SAT_IMAGE_FNAME)

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