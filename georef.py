#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python

# Script dependency locations
p2_gdal_loc = '/Library/Frameworks/GDAL.framework/Versions/2.1/Python/2.7/site-packages'
p2_pil_loc = '/Library/Python/2.7/site-packages/'

import sys
sys.path.insert(0, p2_gdal_loc)
sys.path.insert(0, p2_pil_loc)

import exifread
import os
from osgeo import ogr, osr
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import time

BASE_PATH='/Users/astewart/Home/Anaya'
IN_DIR = 'anaya_pics'
THUMB_DIR = 'anaya_thumbs'
OUT_DIR = 'AnayaGE'
OUTNAME = 'dam_anaya'
SAT_FNAME = 'satellite/op140814.tif'

# LOG_FORMAT = ' '.join(["%(asctime)s",
#                    "%(threadName)s.%(module)s.%(funcName)s",
#                    "line",
#                    "%(lineno)d",
#                    "%(levelname)-8s",
#                    "%(message)s"])
# 
# LOG_DATE_FORMAT = '%d %b %Y %H:%M'

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
    def __init__(self, image_path, buffer_distance=.002, 
                 bbox=(-180, -90, 180, 90), logger=None):
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
        f.write('      <Icon><href>{}</href></Icon>\n'.format(SAT_FNAME))
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
    def parse_relfname(self, relfname):
        datechars = []
        namechars = []
        icntchars = []
        oncount = False
        
        parts = relfname.split(os.path.pathsep)
        arroyo = parts[0]
        arroyo_num, arroyo_name = arroyo.split(')')
        basename, ext = os.path.splitext(parts[-1])
        
        if len(parts) == 2:
            self._log('Relative path contains 2')
        else:
            self._log('Relative path parts {}'.format(parts))
        
        for ch in basename:
            try:
                int(ch)
                if oncount:
                    datechars.append(ch)
                else:
                    icntchars.append(ch)
            except:
                if ch == '_':
                    oncount = True
                else:
                    namechars.append(ch)
                    
        name = namechars.join('')
        date = datechars.join('')
        picnum = int(icntchars.join(''))
        
        return arroyo_num, arroyo_name, name, date, picnum    
        
    # ...............................................
    def processAllImages(self, resize_width=500, resize_path=None):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        if resize_path.endswith('/'):
            resize_path = resize_path[:-1]
        image_data = {}
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    arroyo_num, arroyo_name, name, year, picnum = \
                        self.parse_filename(root, fname)
                        
                    if not image_data.has_key(arroyo_name):
                        image_data[arroyo_name] = {'num': arroyo_num}
                    else:
                        image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.evaluateExtent(dd)
                    if resize_path is not None:
                        # includes trailing /
                        rel_fname = orig_fname[len(self.image_path):]
                        resize_fname = resize_path + rel_fname
                        reduceImageSize(orig_fname, resize_fname, resize_width, Image.ANTIALIAS)
                        image_data[arroyo_name][resize_fname] =  ([yr, mo, day], dd, xdms, ydms)
                    else:
                        image_data[arroyo_name][resize_fname] =  ([yr, mo, day], dd, xdms, ydms)
                        
        return image_data    
    
    # ...............................................
    def gather_image_data(self):
        """
        {rel_fname: {}
        }
        """
        startidx = len(BASE_PATH)
        all_data = {'BASE_PATH': BASE_PATH,
                    'arroyos': None,
                    'dam_count': None,
                    'images': []}
        arroyos = {}
        img_meta = {}
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    fullfname = os.path.join(root, fname)
                    relfname = fullfname[len(BASE_PATH):]
                    
                    arroyo_num, arroyo_name, dam_name, dam_year, picnum = \
                        self.parse_relfname(relfname)
                        
                    try:
                        arroyos[arroyo_name].append(relfname)
                    except:
                        arroyos[arroyo_name] = [relfname]
                                                
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(fullfname)
                    img_meta[relfname] = {'arroyo': arroyo_name,
                                          'arroyo#': arroyo_num,
                                          'dam': dam_name,
                                          'dam_year': dam_year,
                                          'img_date': [yr, mo, day],
                                          'dec_deg': dd,
                                          'x_dms': xdms,
                                          'y_dms': ydms }
                    if dd is None:
                        self._log('Failed to return decimal degrees for {}'.format(relfname))
                    else:
                        self.evaluateExtent(dd)
                    all_data['images'].append(img_meta) 
        all_data['arroyo_count'] = len(arroyos.keys())
        return all_data    
    
    # ...............................................
    def resize_images(self, resize_path, image_data, resize_width=500):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        if resize_path.endswith('/'):
            resize_path = resize_path[:-1]

#         for arroyo in image_data.keys():
#             for 
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    arroyo_num, arroyo_name, name, year, picnum = self.parse_filename(root, fname)
                    if not image_data.has_key(arroyo_name):
                        image_data[arroyo_name] = {'num': arroyo_num}
                    else:
                        image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.evaluateExtent(dd)
                    if resize_path is not None:
                        # includes trailing /
                        rel_fname = orig_fname[len(self.image_path):]
                        resize_fname = resize_path + rel_fname
                        reduceImageSize(orig_fname, resize_fname, resize_width, Image.ANTIALIAS)
                        image_data[arroyo_name][resize_fname] =  ([yr, mo, day], dd, xdms, ydms)
                    else:
                        image_data[arroyo_name][resize_fname] =  ([yr, mo, day], dd, xdms, ydms)
                        
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
    maxsize = 52000000
    level = logging.DEBUG
    
    # get log filename
    scriptname, _ = os.path.splitext(os.path.basename(__file__))
    secs = time.time()
    timestamp = "{}".format(time.strftime("%Y%m%d-%H%M", time.localtime(secs)))
    logname = '{}.{}'.format(scriptname, timestamp)
    logfname = os.path.join(outpath, logname + '.log')
    
    # get logger
    log = logging.getLogger(logname)
    log.setLevel(level)
    
    # add file handler
    fileLogHandler = RotatingFileHandler(logfname, maxBytes=maxsize, backupCount=2)
    fileLogHandler.setLevel(level)
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
    maxY = 35.45045
    minY = 35.43479
    maxX = -106.05353
    minX = -106.07259
    
    dam_buffer = .0002
    resize_width = 500
    
#     log = getLogger(os.path.join(BASE_PATH, OUT_DIR))
    log = None
    image_path = os.path.join(BASE_PATH, IN_DIR)
    resize_path= os.path.join(BASE_PATH, THUMB_DIR)
    bbox = (minX, minY, maxX, maxY)

    sep = '_'
    
    pm = PicMapper(image_path, buffer_distance=dam_buffer, 
                   bbox=bbox, logger=log)
    image_data = pm.gather_image_data()
    

    shpfname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME + '.shp')
    kmlfname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME + '.kml')
    
    # Read data
    image_data = pm.gather_image_data()
    print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
    print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))

    # Reduce image sizes
    t = time.localtime()
    stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)

    
#     # Write data
#     pm.createShapefileAndKML(outdir, shpfname, kmlfname, imageData, start_idx)
     


'''
p2_gdal_loc = '/Library/Frameworks/GDAL.framework/Versions/2.1/Python/2.7/site-packages'
p2_pil_loc = '/Library/Python/2.7/site-packages/'

import sys
sys.path.insert(0, p2_gdal_loc)
sys.path.insert(0, p2_pil_loc)

import exifread
import os
from osgeo import ogr, osr
import logging
from PIL import Image
import time

from georef import PicMapper, getBbox, getLogger, readyFilename, reduceImageSize

IN_PATH = '/Users/astewart/Home/anaya_pics/'
THUMB_PATH = '/Users/astewart/Home/anaya_thumbs/'
OUT_PATH = '/Users/astewart/Home/AnayaGE'
OUTNAME = 'dam_anaya'
SAT_IMAGE_FNAME = '/Users/astewart/Home/AnayaGE/satellite/op140814.tif'
kml_flag = False
shp_flag = False
csv_flag = True

maxY = 35.45045
minY = 35.43479
maxX = -106.05353
minX = -106.07259

dam_buffer = .0002

image_path = IN_PATH
buffer_distance = dam_buffer
bbox = (minX, minY, maxX, maxY)

sep = '_'


pm = PicMapper(image_path, buffer_distance=buffer_distance, 
               bbox=(minX, minY, maxX, maxY), 
               do_kml=kml_flag, do_shape=shp_flag)


shpfname = os.path.join(OUTPATH, OUTNAME + '.shp')
kmlfname = os.path.join(OUTPATH, OUTNAME + '.kml')

# Read data
imageData = pm.processAllImages(resize_width=500, resize_path=THUMB_PATH)
print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
print('Computed: '.format(pm._minX, pm._minY, pm._maxX, pm._maxY))

# Reduce image sizes
t = time.localtime()
stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)

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