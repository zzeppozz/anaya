#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python

# Script dependency location
p2_gdal_loc = '/Library/Frameworks/GDAL.framework/Versions/2.1/Python/2.7/site-packages'
import sys
sys.path.insert(0, p2_gdal_loc)

import csv
import exifread
import os
from osgeo import ogr, osr
import logging
from logging.handlers import RotatingFileHandler
# Using Pillow 6.1.0 installed with "pip2.7 install Pillow"
from PIL import Image
import simplekml as skml
import time

GEOM_WKT = "geomwkt"
LONG_FLD = 'longitude'
LAT_FLD = 'latitude'

DELIMITER = '\t'

# LOG_FORMAT = ' '.join(["%(asctime)s",
#                    "%(threadName)s.%(module)s.%(funcName)s",
#                    "line",
#                    "%(lineno)d",
#                    "%(levelname)-8s",
#                    "%(message)s"])
# 
# LOG_DATE_FORMAT = '%d %b %Y %H:%M'

# .............................................................................
class IMGMETA:
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
    IMAGES_KEY = 'images'
    CSV_FIELDS = ('arroyo', 'arroyo_num', 'dam', 'dam_num', 'dam_date', 
                  'img_date', LONG_FLD, LAT_FLD, GEOM_WKT, 
                  'xdirection', 'xdegrees', 'xminutes', 'xseconds',
                  'ydirection', 'ydegrees', 'yminutes', 'yseconds',
                  'fullpath')

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
        dtstr = tags[IMGMETA.DATE_KEY].values
        [yr, mo, day] = [int(x) for x in dtstr.split(':')]
        return  yr, mo, day
    
    # ...............................................
    def _log(self, msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)
            
    # ...............................................
    def _parse_coordinate(self, tags, locKey, dirKey, negativeIndicator):
        isNegative = False
        # Get longitude or latitude
        degObj, minObj, secObj = tags[locKey].values
        direction = tags[dirKey].printable
        if direction == negativeIndicator:
            isNegative = True
        # Convert to float
        degrees = degObj.num / float(degObj.den) 
        minutes = minObj.num / float(minObj.den)
        seconds = secObj.num / float(secObj.den)    
        # Convert to decimal degrees
        dd = (seconds/3600) + (minutes/60) + degrees
        if isNegative:
            dd = -1 * dd
        return dd, degrees, minutes, seconds, direction
    
    # ...............................................
    def _getDD(self, tags):
        xdd, xdeg, xmin, xsec, xdir = self._parse_coordinate(
            tags, IMGMETA.X_KEY, IMGMETA.X_DIR_KEY, 'W')
        ydd, ydeg, ymin, ysec, ydir = self._parse_coordinate(
            tags, IMGMETA.Y_KEY, IMGMETA.Y_DIR_KEY, 'S')
        
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
    def _create_shplayer(self, shp_fname):
        ogr.RegisterAll()
        drv = ogr.GetDriverByName('ESRI Shapefile')
        tSRS = osr.SpatialReference()
        tSRS.ImportFromEPSG(4326)
        try:
            # Create the file object
            ds = drv.CreateDataSource(shp_fname)
            if ds is None:
                raise Exception('Dataset creation failed for {}'.format(shp_fname))
            # Create a layer
            lyr = ds.CreateLayer('anayaSprings', geom_type=ogr.wkbPoint, srs=tSRS)
            if lyr is None:
                raise Exception('Layer creation failed for {}'.format(shp_fname))
        except Exception as e:
            raise Exception('Failed creating dataset or layer for {} ({})'
                            .format(shp_fname, str(e)))
        # Create attributes
        for fldname in self.CSV_FIELDS:
            fldtype = ogr.OFTString
            if (fldname in (LONG_FLD, LAT_FLD) or 
                fldname[1:] in ('degrees', 'minutes', 'seconds')):
                fldtype = ogr.OFTReal
                
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
            
        
#     # ...............................................
#     def _create_kml_point(self, kml, dam):
#         """
#         """
#         pnt = kml.newpoint(name=dam['dam'])
#         pnt.lookat = skml.LookAt(gxaltitudemode=skml.GxAltitudeMode.relativetoseafloor,
#                               latitude=dam[LAT_FLD], longitude=dam[LONG_FLD],
#                               range=3000, heading=56, tilt=78)
#         pnt.snippet.content = 'Arroyo {} - {}, {}'.format(dam['arroyo_num'], 
#                                     dam['arroyo'], dam['img_date'][0])
#         pnt.snippet.maxlines = 1
#         print kml.kml()
        
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
    def write_shapefile(self, out_image_path, shp_fname, all_data, start_idx):

        dataset, lyr = self._create_layer(self.CSV_FIELDS, shp_fname)
        all_coords = {}
        for infname, pointdata in all_data.iteritems():
            # Reduce image
            relativePath = infname[start_idx:]
            outfname = os.path.join(out_image_path, relativePath)
            outfname = out_image_path + relativePath
            self._reduceImageSize(infname, outfname)
            
            print('Writing feature {} to existing {} locations'.format(
                outfname, len(all_coords)))
            all_coords = self._testBufferAddLocation(all_coords, outfname, pointdata)
            self._createFeatureInLayer(lyr, outfname, pointdata, start_idx)
            
        dataset.Destroy()
        print('Closed/wrote dataset %s' % shp_fname)
        success = True
        self._log('Success {} writing shapefile {}'.format(success, 
                                                           shp_fname))
    
    
    # ...............................................
    def get_image_metadata(self, fullname):
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
    def evaluate_extent(self, dd):
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
    @property
    def extent(self):
        return (self._minX, self._minY, self._maxX, self._maxY)
        
    # ...............................................
    def parse_relfname(self, relfname):
        parts = relfname.split(os.sep)
        arroyo = parts[0]
        arroyo_num, arroyo_name = arroyo.split(')')
        basename, ext = os.path.splitext(parts[-1])
        
        if len(parts) != 2:
            self._log('Relative path parts {}'.format(parts))
            
        ntmp, ctmp = basename.split('_')
        picnum = int(ctmp)
        for i in range(len(ntmp)):
            try:
                int(ntmp[i])
                break
            except:
                pass
        name = ntmp[:i]
        dtmp = ntmp[i:]
        yr = dtmp[:4]
        mo = dtmp[4:6]
        dy = dtmp[6:]
        
        return arroyo_num, arroyo_name, name, [yr, mo, dy], picnum       
    
    # ...............................................
    def read_image_data(self):
        """
        """
        all_data = {'BASE_PATH': BASE_PATH,
                    'arroyos': None,
                    'img_count': None,
                    'img_count_geo': None,
                    'dam_count': None,
                    'dam_count_geo': None,
                    self.IMAGES_KEY: []}
        arroyos = {}
        IMGMETA = {}
        img_count = 0
        img_count_geo = 0
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    img_count += 1
                    fullfname = os.path.join(root, fname)
                    relfname = fullfname[len(self.image_path)+1:]
                    xdeg = xmin = xsec = xdir = ydeg = ymin = ysec = ydir = wkt = ''
    
                    arroyo_num, arroyo_name, dam_name, dam_date, picnum = \
                        self.parse_relfname(relfname)
                    [yr, mo, day], (xdd, ydd), xdms, ydms = self.get_image_metadata(fullfname)
                    
                    if xdms is not None:
                        (xdeg, xmin, xsec, xdir) = xdms
                    if ydms is not None:
                        (ydeg, ymin, ysec, ydir) = ydms
                    if xdd is not None and ydd is not None:
                        wkt = 'Point ({:.7f}  {:.7f})'.format(xdd, ydd)
                        img_count_geo += 1
                        self.evaluate_extent((xdd, ydd))
                    else:
                        self._log('Failed to return decimal degrees for {}'.format(relfname))
                    
                    IMGMETA[relfname] = {'arroyo': arroyo_name, 
                                          'arroyo_num': arroyo_num,
                                          'dam': dam_name,
                                          'dam_num': picnum,
                                          'dam_date': dam_date,
                                          'img_date': [yr, mo, day],
                                          LONG_FLD: xdd,
                                          LAT_FLD: ydd,
                                          GEOM_WKT: wkt,
                                          'xdirection': xdir,
                                          'xdegrees': xdeg,
                                          'xminutes': xmin, 
                                          'xseconds': xsec,
                                          'ydirection': ydir,
                                          'ydegrees': ydeg,
                                          'yminutes': ymin,
                                          'yseconds': ysec,
                                          'fullpath': fullfname}
                    try:
                        arroyos[arroyo_name].append(relfname)
                    except:
                        arroyos[arroyo_name] = [relfname]

        all_data['arroyo_count'] = len(arroyos.keys())
        all_data['arroyos'] = arroyos
        all_data['images'] = IMGMETA
        all_data['img_count'] = img_count
        all_data['img_count_geo'] = img_count_geo
        return all_data
    
    # ...............................................
    def write_csv_data(self, out_csv_fname, all_data, thumb_data, delimiter=DELIMITER):
        """        
        """
        with open(out_csv_fname, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=delimiter)
            header = [fld for fld in self.CSV_FIELDS]
            header.append('thumbnail')
            
            csvwriter.writerow(header)
            for relfname, imgdata in all_data[self.IMAGES_KEY].iteritems():
                try:
                    thumb_fname, width, height = thumb_data[relfname]
                except:
                    thumb_fname = 'x'
                rec = []
                for fld in self.CSV_FIELDS:
                    try:
                        rec.append(imgdata[fld])
                    except:
                        rec.append('')
                rec.append(thumb_fname)
                csvwriter.writerow(rec)


    # ...............................................
    def write_kml_data(self, out_kml_fname, all_data, thumb_data, filteryear):
        """
        """
        kml = skml.Kml(open=1)
#         fldr = kml.newfolder(name=filteryear)
        style = skml.Style()
        style.labelstyle.color = 'ffff00ff'
        style.iconstyle.scale = 1.0
#         style.balloonstyle.text = 'These are trees and this text is blue with a green background.'
#         style.balloonstyle.bgcolor = skml.Color.lightgreen
#         style.balloonstyle.textcolor = skml.Color.rgb(0, 0, 255)
        
        for relfname, dam in all_data[self.IMAGES_KEY].iteritems():
            if filteryear is None or dam['img_date'][0] == filteryear:
                try:
                    thumb_fname, width, height = thumb_data[relfname]
                except:
                    thumb_fname, width, height = ('x', 0, 0)
                
#                 info = """
#                         <![CDATA[
#                             <table width=100% cellpadding=0 cellspacing=0>
#                                 <tr>
#                                     <td><img width=100% src='{}' /></td>
#                                 </tr>
#                             </table>]]>
#                        """.format(thumb_fname)
                info = 'Arroyo {} - {}, {}'.format(dam['arroyo_num'], 
                                                   dam['arroyo'], 
                                                   dam['img_date'][0])
                info = ('<img src="{}" alt="picture" width="{}" height="{}" align="left" />'
                        .format(thumb_fname, width, height))
                pnt = kml.newpoint(name=dam['dam'], 
                                   coords=[(dam[LONG_FLD], dam[LAT_FLD])])
                pnt.style = style
                pnt.description = info
#                 pnt.style.balloonstyle.text = info
                pnt.lookat = skml.LookAt(
                    gxaltitudemode=skml.GxAltitudeMode.relativetoseafloor,
                    latitude=dam[LAT_FLD], longitude=dam[LONG_FLD],
                    range=3000, heading=56, tilt=78)
                pnt.snippet.content = 'Arroyo {} - {}, {}'.format(dam['arroyo_num'], 
                                            dam['arroyo'], dam['img_date'][0])
                pnt.snippet.maxlines = 1
        kml.save(out_kml_fname)


    # ...............................................
    def resize_images(self, resize_path, all_data, width=500, alg=Image.ANTIALIAS, quality=95):
        thumb_data = {}
        for relfname, dam in all_data[self.IMAGES_KEY].iteritems():
            origfname = dam['fullpath']
            sm_fname = os.path.join(resize_path, relfname)
            thumbname, w, h = resize_image(origfname, sm_fname, width, alg, quality=quality)
            thumb_data[relfname] = (thumbname, w, h) 
                        
        return thumb_data

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
        
# .............................................................................
def getCSVReader(datafile, delimiter):
    try:
        f = open(datafile, 'r') 
        reader = csv.reader(f, delimiter=delimiter)        
    except Exception, e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return reader, f

# .............................................................................
def getCSVWriter(datafile, delimiter, doAppend=True):
    csv.field_size_limit(sys.maxsize)
    if doAppend:
        mode = 'ab'
    else:
        mode = 'wb'
       
    try:
        f = open(datafile, mode) 
        writer = csv.writer(f, delimiter=delimiter)
    except Exception, e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return writer, f


# ...............................................
def resize_image(infname, outfname, width, sample_method, quality):
    readyFilename(outfname, overwrite=True)
    img = Image.open(infname)
    icc_profile = img.info.get("icc_profile")
    
    wpercent = (width / float(img.size[0]))
    height = int((float(img.size[1]) * float(wpercent)))
    size = (width, height)
    
    img = img.resize(size, sample_method)
    img.save(outfname, 'JPEG', quality=quality, icc_profile=icc_profile)
    
    print('Rewrote image {} to {}'.format(infname, outfname))
    return outfname, width, height


# .............................................................................
# .............................................................................
# ...............................................
if __name__ == '__main__':    
    BASE_PATH='/Users/astewart/Home/Anaya'
    THUMB_DIR = 'anaya_thumbs'
    OUT_DIR = 'AnayaGE'
    OUTNAME = 'dam_anaya'
    SAT_FNAME = 'satellite/op140814.tif'
    
    filteryear = None
    IN_DIR = 'anaya_pics'
    
    maxY = 35.45045
    minY = 35.43479
    maxX = -106.05353
    minX = -106.07259
    
    dam_buffer = .0002
    thumb_width = 500
    
#     log = getLogger(os.path.join(BASE_PATH, OUT_DIR))
    log = None
    image_path = os.path.join(BASE_PATH, IN_DIR)
    thumb_path= os.path.join(BASE_PATH, OUT_DIR, THUMB_DIR)
    out_csv_fname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME+'.csv')
    out_kml_fname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME+'.kml')
    bbox = (minX, minY, maxX, maxY)
    
    pm = PicMapper(image_path, buffer_distance=dam_buffer, 
                   bbox=bbox, logger=log)
    
    # Read data
    dam_data = pm.read_image_data()
    print('Given: {}'.format(pm.bbox))
    print('Computed: {}'.format(pm.extent))
    thumb_data = pm.resize_images(thumb_path, dam_data, width=thumb_width, alg=Image.ANTIALIAS, quality=95)
    pm.write_csv_data(out_csv_fname, dam_data, thumb_data)
    pm.write_kml_data(out_kml_fname, dam_data, thumb_data, filteryear)
    

    # Reduce image sizes
    t = time.localtime()
    stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)


'''
p2_gdal_loc = '/Library/Frameworks/GDAL.framework/Versions/2.1/Python/2.7/site-packages'
p2_pil_loc = '/Library/Python/2.7/site-packages/'

import sys
sys.path.insert(0, p2_gdal_loc)
sys.path.insert(0, p2_pil_loc)

import csv
import exifread
import os
from osgeo import ogr, osr
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import simplekml as skml
import time
from dam_map import *

GEOM_WKT = "geomwkt"
LONG_FLD = 'longitude'
LAT_FLD = 'latitude'

DELIMITER = '\t'
BASE_PATH='/Users/astewart/Home/Anaya'
IN_DIR = 'anaya_pics'
THUMB_DIR = 'anaya_thumbs'
OUT_DIR = 'AnayaGE'
OUTNAME = 'dam_anaya'
SAT_FNAME = 'satellite/op140814.tif'
SAT_IMAGE_FNAME = os.path.join(BASE_PATH, SAT_FNAME)

maxY = 35.45045
minY = 35.43479
maxX = -106.05353
minX = -106.07259

dam_buffer = .0002
resize_width = 500

log = None
image_path = os.path.join(BASE_PATH, IN_DIR)
resize_path= os.path.join(BASE_PATH, OUT_DIR, THUMB_DIR)
out_csv_fname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME+'.csv')
out_kml_fname = os.path.join(BASE_PATH, OUT_DIR, OUTNAME+'.kml')
bbox = (minX, minY, maxX, maxY)

################################################
infname = '/Users/astewart/Home/Anaya/anaya_pics/33)Conglomerate/conglomerate20151008_001.JPG'
outfname = '/Users/astewart/Home/Anaya/AnayaGE/anaya_thumbs/33)Conglomerate/conglomerate20151008_001.JPG'
width = 500
sample_method = Image.ANTIALIAS

# def resize_image(infname, outfname, width, sample_method):
img = Image.open(infname)
icc_profile = img.info.get("icc_profile")
img = img.resize(size, sample_method)
readyFilename(outfname, overwrite=True)
img.save(outfname, icc_profile=icc_profile, quality=95)

wpercent = (width / float(img.size[0]))
height = int((float(img.size[1]) * float(wpercent)))
size = (width, height)

# sample_method = Image.LANCZOS
# sample_method = Image.BILINEAR
# sample_method = Image.BICUBIC


img = img.resize(size, sample_method)
readyFilename(outfname, overwrite=True)
img.save(outfname, icc_profile=icc_profile, quality=95)

img2 = Image.open(outfname)
icc_profile2 = img.info.get("icc_profile")
if icc_profile == icc_profile2:
    print 'color profile is same'

print('Rewrote image {} to {}'.format(infname, outfname))
################################################

pm = PicMapper(image_path, buffer_distance=dam_buffer, 
               bbox=bbox, logger=log)

# Read data
dam_data = pm.read_image_data()
print('Given: {}'.format(pm.bbox))
print('Computed: {}'.format(pm.extent))
thumb_files = pm.resize_images(resize_path, dam_data, resize_width=500)
pm.write_csv_data(out_csv_fname, dam_data)
pm.write_kml_data(out_kml_fname, dam_data)

# Reduce image sizes
t = time.localtime()
stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)


'''