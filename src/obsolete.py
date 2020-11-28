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

from constants import (
    GEOM_WKT, LONG_FLD, LAT_FLD, DELIMITER, LOG_FORMAT, LOG_DATE_FORMAT, 
    LOG_MAX, BASE_PATH, IN_DIR, THUMB_DIR, THUMB_DIR_SMALL, OUT_DIR, OUT_NAME, 
    SAT_FNAME, IMG_META)


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
                 bbox=None, logger=None):
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
        self._minX = None
        self._minY = None
        self._maxX = None
        self._maxY = None
        self._logger = logger
    
    # ...............................................
    def _get_date(self, tags):
        # Returns [yr, mo, day] or None
        gps_date = (None, None, None)
        # Get date
        try:
            dtstr = tags[IMG_META.DATE_KEY].values
        except Exception:
            self._log('Failed to get {}'.format(IMG_META.DATE_KEY))
        else:
            try:
                gps_date = [int(x) for x in dtstr.split(':')]
            except Exception:
                self._log('Invalid date {}'.format(dtstr))

        return gps_date
    
    # ...............................................
    def _log(self, msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)
            
    # ...............................................
    def _parse_coordinate(self, tags, locKey, dirKey, negativeIndicator):
        dd = degrees = minutes = seconds = direction = None
        isNegative = False
        # Get longitude or latitude
        try:
            degObj, minObj, secObj = tags[locKey].values
        except:
            pass
        else:
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
            tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY, 'W')
        ydd, ydeg, ymin, ysec, ydir = self._parse_coordinate(
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
        # TODO: use computed extent or provided bbox for KMZ file?
        if self.bbox is not None:
            (minX, minY, maxX, maxY) = self.bbox
        else:
            (minX, minY, maxX, maxY) = self.extent
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
        _, lastArroyo = os.path.split(pth)
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
            
            self._log('Writing feature {} to existing {} locations'.format(
                outfname, len(all_coords)))
            all_coords = self._testBufferAddLocation(all_coords, outfname, pointdata)
            self._createFeatureInLayer(lyr, outfname, pointdata, start_idx)
            
        dataset.Destroy()
        self._log('Closed/wrote dataset %s' % shp_fname)
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
            self._log('{}: Unable to get x y, ({})'.format(fullname, e))
            
        try:
            (yr, mo, day) = self._get_date(tags)
        except Exception as e:
            self._log('{}: Unable to get date, ({})'.format(fullname, e))
        return (yr, mo, day), dd, xdms, ydms
    
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
        basename, _ = os.path.splitext(parts[-1])
        
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
        yr = int(dtmp[:4])
        mo = int(dtmp[4:6])
        dy = int(dtmp[6:])
        
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
        IMG_META = {}
        img_count = 0
        img_count_geo = 0
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    img_count += 1
                    self._log('Read {} image {}'.format(img_count, fname))

                    fullfname = os.path.join(root, fname)
                    relfname = fullfname[len(self.image_path)+1:]
                    xdeg = xmin = xsec = xdir = ydeg = ymin = ysec = ydir = wkt = ''
    
                    arroyo_num, arroyo_name, dam_name, dam_date, picnum = \
                        self.parse_relfname(relfname)
                    gpsdate, (xdd, ydd), xdms, ydms = self.get_image_metadata(fullfname)
                                        
                    if xdd is None or ydd is None:
                        self._log('Failed to return decimal degrees for {}'.format(relfname))
                    else:
                        wkt = 'Point ({:.7f}  {:.7f})'.format(xdd, ydd)
                        img_count_geo += 1
                        self.evaluate_extent((xdd, ydd))
                        
                        [yr, mo, day] = gpsdate
                        (xdeg, xmin, xsec, xdir) = xdms
                        (ydeg, ymin, ysec, ydir) = ydms
                    
                        IMG_META[relfname] = {'arroyo': arroyo_name, 
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
        all_data['images'] = IMG_META
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
                    thumb_fname, _, _ = thumb_data[relfname]
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
    def _get_pt_info(self, dam, imgpth, width, height):
#         info = """
#                 <![CDATA[
#                     <table width=100% cellpadding=0 cellspacing=0>
#                         <tr>
#                             <td><img width=100% src='{}' /></td>
#                         </tr>
#                     </table>]]>
#                """.format(tfname)
#         info = ('<img src="{}" alt="picture" width="{}" height="{}" align="left" />'
#                 .format(imgpth, twidth, theight))
        dam_info = 'Arroyo {} - {}, {}'.format(dam['arroyo_num'], 
                                           dam['arroyo'], 
                                           dam['img_date'][0])
        
        if height is None:
            dims = 'width="100%"'
        else:
            dims = 'width="{}" height="{}"'.format(width, height)
        
        img_info = ('<img src="{}" alt="picture" {} align="left" />'
                    .format(imgpth, dims))
        
        lookat = skml.LookAt(gxaltitudemode=skml.GxAltitudeMode.relativetoseafloor,
                    latitude=dam[LAT_FLD], longitude=dam[LONG_FLD],
                    range=3000, heading=56, tilt=78)
        
        return dam_info, img_info, lookat

    # ...............................................
    def _get_dam_style(self, img_info):
        """
        """
        style = skml.Style()
        style.labelstyle.color = skml.Color.sienna
        style.iconstyle.scale = 0.5
        style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
        style.iconstyle.color = skml.Color.sienna
        style.balloonstyle.bgcolor = skml.Color.bisque
        style.balloonstyle.textcolor = skml.Color.rgb(0,0,0)
        style.balloonstyle.text = img_info
        return style

    # ...............................................
    def write_ge_data(self, out_fname_woext, all_data, photo_data, filteryear,
                      ftype='kmz'):
        """
        @param ftype: 'kmz' will use thumbnails and include in file.
                      'kml' will use full images and point to local file.
        """
        if ftype not in ('kml', 'kmz'):
            raise Exception('Invalid Google Earth filetype {}'.format(ftype))
        out_fname = out_fname_woext + '.' + ftype
        kml = skml.Kml(name='Anaya Dams', open=1)
        icon_fname = os.path.join(self.image_path, 'rockpile.png')
        folders = {}
        
        for relfname, dam in all_data[self.IMAGES_KEY].iteritems():
            if filteryear is None or dam['img_date'][0] == filteryear:
                img_fname, width, height = photo_data[relfname]
                
                # Include thumbnails in KMZ
                if ftype == 'kmz':
                    imgpth = kml.addfile(img_fname)
                # Reference larger local files in KML
                else:
                    imgpth = img_fname
                    
                dam_info, img_info, lookat = self._get_pt_info(dam, 
                                            imgpth, width, height)
                
                try:
                    fldr = folders[dam['arroyo']]
                except:
                    fldr = kml.newfolder(name=dam['arroyo'])
                    folders[dam['arroyo']] = fldr

                pnt = fldr.newpoint(name=dam['dam'], 
                                    coords=[(dam[LONG_FLD], dam[LAT_FLD])])
                pnt.description = dam_info
                pnt.style = self._get_dam_style(img_info)
#                 pnt.lookat = lookat
#                 pnt.snippet.content = dam_info
#                 pnt.snippet.maxlines = 1
        self._log('Saving GE file {}'.format(out_fname))
        kml.savekmz(out_fname)
    # ...............................................
    def resize_images(self, resize_path, all_data, width=500, 
                      alg=Image.ANTIALIAS, quality=95, overwrite=False):
        thumb_data = {}
        pic_data = {}
        self._log('Resize {} images'.format(len(all_data[self.IMAGES_KEY])))
        for relfname, dam in all_data[self.IMAGES_KEY].iteritems():
            origfname = dam['fullpath']
            sm_fname = os.path.join(resize_path, relfname)
            
            origsize, smsize = resize_image(origfname, sm_fname, width, alg, 
                                            quality=quality, 
                                            overwrite=overwrite)
            
            thumb_data[relfname] = (sm_fname, smsize[0], smsize[1]) 
            pic_data[relfname] = (origfname, origsize[0], origsize[1]) 
                        
        return thumb_data, pic_data

# .............................................................................
def get_logger(outpath):
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
    fileLogHandler = RotatingFileHandler(
        logfname, maxBytes=LOG_MAX, backupCount=2)
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
def ready_filename(fullfilename, overwrite=True):
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
        pth, _ = os.path.split(fullfilename)
        try:
            os.makedirs(pth)
        except:
            pass
            
        if os.path.isdir(pth):
            return True
        else:
            raise Exception('Failed to create directories {}'.format(pth))
        
# .............................................................................
def get_csv_reader(datafile, delimiter):
    try:
        f = open(datafile, 'r') 
        reader = csv.reader(f, delimiter=delimiter)        
    except Exception, e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    return reader, f

# .............................................................................
def get_csv_writer(datafile, delimiter, doAppend=True):
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
def resize_image(infname, outfname, width, sample_method, quality, overwrite=False):
    img = Image.open(infname)
    icc_profile = img.info.get("icc_profile")
    
    wpercent = (width / float(img.size[0]))
    height = int((float(img.size[1]) * float(wpercent)))
    newsize = (width, height)
    
    ready = ready_filename(outfname, overwrite=overwrite)
    if ready is True:
        img = img.resize(newsize, sample_method)
        img.save(outfname, 'JPEG', quality=quality, icc_profile=icc_profile)
        print('Rewrote image {} to {}'.format(infname, outfname))
        
    return img.size, newsize


# .............................................................................
# .............................................................................
# ...............................................
if __name__ == '__main__':    

    curr_path = BASE_PATH
    filteryear = None
    dam_buffer = .0002
    thumb_width = 500
    thumb_width_sm = 200
    do_write = False
    
#     log = get_logger(os.path.join(BASE_PATH, OUT_DIR))
    log = None
    image_path = os.path.join(curr_path, IN_DIR)
    thumb_path = os.path.join(curr_path, OUT_DIR, THUMB_DIR)
    thumb_path_sm = os.path.join(curr_path, OUT_DIR, THUMB_DIR_SMALL)
    out_fname_woext = os.path.join(curr_path, OUT_DIR, OUT_NAME)
    out_kml_fname = out_fname_woext + '.kml'
    out_csv_fname = out_fname_woext + '.csv'
    out_kmz_fname = out_fname_woext + '.kmz'
    
    t = time.localtime()
    tstamp = '{}-{}-{}T{}:{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
    print('# Start {}'.format(tstamp))
    print('Create KMZ {} for images in {}'.format(out_kmz_fname, image_path))
    
    pm = PicMapper(image_path, buffer_distance=dam_buffer, logger=log)
    
    # Read data
    dam_data = pm.read_image_data()
    print('Given: {}'.format(pm.bbox))
    print('Computed: {}'.format(pm.extent))
    
    width = thumb_width
    outpath = thumb_path

    # Write thumbnail images
    thumb_data, pic_data = pm.resize_images(outpath, dam_data, 
                                            width=width, 
                                            alg=Image.ANTIALIAS, 
                                            quality=95, 
                                            overwrite=False)
    
    # Write geo files
    pm.write_csv_data(out_csv_fname, dam_data, thumb_data)
    pm.write_ge_data(out_fname_woext, dam_data, thumb_data, filteryear,ftype='kmz')
    
    t = time.localtime()
    tstamp = '{}-{}-{}T{}:{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
    print('# End {}'.format(tstamp))
'''
'''