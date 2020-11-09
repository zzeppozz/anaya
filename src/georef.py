#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python
# Script dependency locations
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
import time

from constants import (
    GEOM_WKT, LONG_FLD, LAT_FLD, IMG_META, DELIMITER, BASE_PATH, IN_DIR, 
    ANC_DIR, THUMB_DIR, OUT_DIR, OUT_NAME, SAT_FNAME, LOG_MAX, LOG_FORMAT,
    LOG_DATE_FORMAT, RESIZE_WIDTH, IMAGES_KEY, CSV_FIELDS, ENCODING)

# ...............................................
def standardize_name(fname, root=None):
    if root:
        _, arroyo = os.path.split(root)
        arroyo_num, arroyo_name = arroyo.split('.')

    basename, ext = os.path.splitext(fname)
    for i in range(len(basename)):
        try:
            int(basename[i])
            break
        except:
            pass
    name = basename[:i]
    rest = basename[i:]
    parts = rest.split('_')            
    try:
        date_str, num_str = parts
    except:
        print('** Bad filename {}'.format(fname))
        date_str = rest[:8]
        num_str  = rest[8:]
        newname = '{}{}_{}{}'.format(name, date_str, num_str, ext)
    else:
        newname = fname
        
    picnum = int(num_str)
    yr = int(date_str[:4])
    mo = int(date_str[4:6])
    dy = int(date_str[6:8])
    
    return newname, name, picnum, (yr, mo, dy), (arroyo_num, arroyo_name)

# .............................................................................
class PicMapper(object):
# .............................................................................
    """
    Class to write a shapefile from GBIF CSV output or BISON JSON output 
    export p3=/Library/Frameworks/Python.framework/Versions/3.7/bin/python3.7
    Yelp help: https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
    """
    FIELDS = [('arroyo', ogr.OFTString), 
              ('fullpath', ogr.OFTString), 
              ('relpath', ogr.OFTString), 
              ('basename', ogr.OFTString),
              ('img_date', ogr.OFTString),
              (GEOM_WKT, ogr.OFTString),
              (LONG_FLD, ogr.OFTReal), 
              (LAT_FLD, ogr.OFTReal), 
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
    def __init__(
            self, image_path, buffer_distance=.0002, bbox=(-180, -90, 180, 90), 
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
    def _get_date(self, tags):
        # Get date
        dtstr = tags[IMG_META.DATE_KEY].values
        try:
            return [int(x) for x in dtstr.split(':')]
        except:
            return None
    
    # ...............................................
    def _log(self, msg):
        if self._logger:
            self._logger.info(msg)
        else:
            print(msg)
            
    # ...............................................
    def _get_location_vals(self, tags, locKey, dirKey, negativeIndicator):
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
    def _get_dd(self, tags):
        xdd, xdeg, xmin, xsec, xdir = self._get_location_vals(
            tags, IMG_META.X_KEY, IMG_META.X_DIR_KEY, 'W')
        ydd, ydeg, ymin, ysec, ydir = self._get_location_vals(
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
        rel_satellite_fname = os.path.join(ANC_DIR, SAT_FNAME)
        f = open(fname, 'w')
        f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
        f.write('<Document id="root_doc">\n')
        f.write('<Folder><name>{}</name>\n'.format(foldername))
        f.write('   <GroundOverlay>\n')
        f.write('      <name>Satellite overlay on terrain</name>\n')
        f.write('      <description>Local imagery</description>\n')
        f.write('      <Icon><href>{}</href></Icon>\n'.format(rel_satellite_fname))
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
    def _create_layer(self, fields, shpFname):
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
    
    def _good_geo(self, damdata):
        good_geo = False
        # (minX, minY, maxX, maxY)
        xdd = float(damdata[LONG_FLD])
        ydd = float(damdata[LAT_FLD])
        if xdd < self.bbox[0]:
            self._log('X value {} < min {}'.format(xdd, self.bbox[0]))
        elif xdd > self.bbox[2]:
            self._log('X value {} > max {}'.format(xdd, self.bbox[2]))
        elif ydd < self.bbox[1]:
            self._log('Y value {} < min {}'.format(ydd, self.bbox[1]))
        elif ydd > self.bbox[3]:
            self._log('Y value {} > max {}'.format(ydd, self.bbox[3]))
        else:
            good_geo = True
        return good_geo
            
    # ...............................................
    def _create_feat_shp(self, lyr, fname, damdata, rel_idx):
        if damdata['in_bounds'] is False:
            pass
        else:
            [yr, mo, day] = damdata['img_date']
            pth, basefname = os.path.split(fname)
            relative_path = fname[rel_idx:]    
            _, lastArroyo = os.path.split(pth)
            wkt = damdata[GEOM_WKT]
            feat = ogr.Feature( lyr.GetLayerDefn() )
            try:
                feat.SetField('arroyo', lastArroyo)
                feat.SetField('fullpath', fname)
                feat.SetField('relpath', relative_path)
                feat.SetField('basename', basefname)
                feat.SetField('img_date', '{}-{}-{}'.format(yr, mo, day))
                feat.SetField('xdegrees', damdata['xdegrees'])
                feat.SetField('xminutes', damdata['xminutes'])
                feat.SetField('xseconds', damdata['xseconds'])
                feat.SetField('xdirection', damdata['xdirection'])
                feat.SetField('ydegrees', damdata['ydegrees'])
                feat.SetField('yminutes', damdata['yminutes'])
                feat.SetField('yseconds', damdata['yseconds'])
                feat.SetField('ydirection', damdata['ydirection'])
                feat.SetField(LONG_FLD, damdata[LONG_FLD])
                feat.SetField(LAT_FLD, damdata[LAT_FLD])
                feat.SetField(GEOM_WKT, wkt)
                geom = ogr.CreateGeometryFromWkt(wkt)
                feat.SetGeometryDirectly(geom)
            except Exception as e:
                self._log('Failed to fillOGRFeature, e = {}'.format(e))
            else:
                # Create new feature, setting FID, in this layer
                lyr.CreateFeature(feat)
                feat.Destroy()
            
    # ...............................................
    def _create_feat_kml(self, kmlf, fname, damdata):
        """
        <img style="max-width:500px;" 
         src="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
         SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
        """
        if damdata['in_bounds'] is False:
            pass
        else:
            [yr, mo, day] = damdata['img_date'] 
            xdd = damdata[LONG_FLD]
            ydd = damdata[LAT_FLD]
            pth, basefname = os.path.split(fname)
            basename, _ = os.path.splitext(basefname)
            _, lastArroyo = os.path.split(pth)
            dt = '{}-{}-{}'.format(yr, mo, day)
        
            kmlf.write('  <Placemark>\n')
            kmlf.write('    <name>{}</name>\n'.format(basefname))
            kmlf.write('    <description>{} in {} on {}</description>\n'
                       .format(basename, lastArroyo, dt))
            kmlf.write('    <img style="max-width:{}px;" src="file://{}"></img>\n'
                       .format(RESIZE_WIDTH, fname))
            kmlf.write('    <Point><coordinates>{},{}</coordinates></Point>\n'
                       .format(xdd, ydd))
            kmlf.write('  </Placemark>\n')
        
    # ...............................................
    def _add_coords(self, all_coords, currfname, damdata):
        currx = float(damdata[LONG_FLD])
        curry = float(damdata[LAT_FLD])
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
    def create_thumbnails(self, out_path, img_data, overwrite=True):
        thumb_path = os.path.join(out_path, THUMB_DIR)
        all_coords = {}
        for relfname, damdata in img_data.iteritems():
            fullfname = damdata['fullpath']
            # Reduce image
            thumbfname = os.path.join(thumb_path, relfname)
            reduce_image_size(
                fullfname, thumbfname, width=RESIZE_WIDTH, 
                sample_method=Image.ANTIALIAS, overwrite=overwrite)
            # Why?
            has_geo = damdata[GEOM_WKT].startswith('Point')
            if has_geo:
                all_coords = self._add_coords(all_coords, relfname, damdata)
        return all_coords
            
            
    # ...............................................
    def create_shapefile_kml(
            self, out_path, shpfname, kmlfname, img_data, 
            do_shape=True, do_kml=True):
        thumb_path = os.path.join(out_path, THUMB_DIR)
        rel_idx = len(thumb_path)
        if do_kml:
            kmlf = self._open_kml_file(kmlfname)
        if do_shape:
            dataset, lyr = self._create_layer(self.FIELDS, shpfname)

        for relfname, damdata in img_data.iteritems():
            has_geo = damdata[GEOM_WKT].startswith('Point')
            if has_geo:
                thumbfname = os.path.join(thumb_path, relfname)
                if do_kml:
                    self._create_feat_kml(kmlf, thumbfname, damdata)
                if do_shape:
                    self._create_feat_shp(lyr, thumbfname, damdata, rel_idx)
            
        if do_kml:
            self._close_kml_file(kmlf)
        if do_shape:
            dataset.Destroy()
            print('Closed/wrote dataset %s' % shpfname)
            success = True
            self._log('Success {} writing shapefile {}'.format(success, 
                                                               shpfname))
    
    
    # ...............................................
    def get_image_metadata(self, fullname):
        dd = xdms = ydms = yr = mo = day = None
        try:
            # Open image file for reading (binary mode)
            f = open(fullname, 'rb')
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self._log('{}: Unable to read image metadata, {}'.format(
                fullname, e))
        finally:
            f.close()
        try:
            dd, xdms, ydms = self._get_dd(tags)
        except Exception as e:
            self._log('{}: Unable to get x y, {}'.format(fullname, e))
        try:
            yr, mo, day = self._get_date(tags)
        except Exception as e:
            self._log('{}: Unable to get date, {}'.format(fullname, e))
        return [yr, mo, day], dd, xdms, ydms
    
    # ...............................................
    def eval_extent(self, dd):
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
        parts = relfname.split(os.sep)
        arroyo = parts[0]
        arroyo_num, arroyo_name = arroyo.split('.')
        basename, _ = os.path.splitext(parts[-1])
        
        if len(parts) != 2:
            self._log('Relative path parts {}'.format(parts))
          
        parts = basename.split('_')
        try:
            ntmp, ctmp = parts
        except:
            print('Bad filename {}'.format(relfname))
        else:
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
    def process_all_images(self, resize_width=RESIZE_WIDTH, resize_path=None):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        if resize_path.endswith('/'):
            resize_path = resize_path[:-1]
        image_data = {}
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    (_, name, picnum, (fyear, fmon, fday), 
                     (arroyo_num, arroyo_name)) = standardize_name(fname, root=root)
                        
                    if not image_data.has_key(arroyo_name):
                        image_data[arroyo_name] = {'num': arroyo_num}
                    else:
                        image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.get_image_metadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.eval_extent(dd)
                    if resize_path is not None:
                        # includes trailing /
                        rel_fname = orig_fname[len(self.image_path):]
                        resize_fname = resize_path + rel_fname
                        reduce_image_size(
                            orig_fname, resize_fname, width=RESIZE_WIDTH, 
                            sample_method=Image.ANTIALIAS)
                        image_data[arroyo_name][resize_fname] = (
                            [yr, mo, day], dd, xdms, ydms)
                    else:
                        image_data[arroyo_name][resize_fname] =  (
                            [yr, mo, day], dd, xdms, ydms)
                        
        return image_data    
    
    # ...............................................
    def _parse_datestring(self, dtstr):
        parts = dtstr.lstrip('([').rstrip('])').split(',')
        try:
            date_vals = [int(p.strip()) for p in parts]
        except:
            date_vals = None
        return date_vals
        
    # ...............................................
    def read_csv_metadata(self, csv_fname, delimiter=DELIMITER):
        all_data = {}
        arroyos = {}
        img_meta = {}
        img_out_of_range = {}
        img_count = 0
        img_count_geo = 0
        drdr, f = get_csv_dict_reader(csv_fname, delimiter)
        try:
            for rec in drdr:
                img_count += 1
                fullfname = rec['fullpath']
                relfname = fullfname[len(self.image_path)+1:]
                arroyo_name = rec['arroyo']
                rec['img_date'] = self._parse_datestring(rec['img_date'])
                rec['dam_date'] = self._parse_datestring(rec['dam_date'])
                
                # Count images with geo data
                if rec[GEOM_WKT].startswith('Point') and self._good_geo(rec):
                    rec['in_bounds'] = True
                    img_count_geo += 1
                else:
                    rec['in_bounds'] = False
                    img_out_of_range[relfname] = rec
                    
                # Save metadata for each image  
                img_meta[relfname] = rec
                # Summarize arroyos
                try:
                    arroyos[arroyo_name].append(relfname)
                except:
                    arroyos[arroyo_name] = [relfname]
        except Exception as e:
            self._log('Failed to read image metadata from {}, line {}, {}'.format(
                csv_fname, drdr.line_num, e))
        finally:
            f.close()
            
        all_data['arroyo_count'] = len(arroyos.keys())
        all_data['arroyos'] = arroyos
        all_data[IMAGES_KEY] = img_meta
        all_data['img_count'] = img_count
        all_data['img_count_geo'] = img_count_geo
        all_data['out_of_range'] = img_out_of_range

        return all_data
    
    # ...............................................
    def read_image_data(self):
        """Read metadata from all image files within the BASE_PATH """
        all_data = {'BASE_PATH': BASE_PATH,
                    'arroyos': None,
                    'img_count': None,
                    'img_count_geo': None,
                    'dam_count': None,
                    'dam_count_geo': None,
                    IMAGES_KEY: []}
        arroyos = {}
        img_meta = {}
        img_count = 0
        img_count_geo = 0
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'):
                    img_count += 1
                    fullfname = os.path.join(root, fname)
                    relfname = fullfname[len(self.image_path)+1:]
                    xdeg = xmin = xsec = xdir = ydeg = ymin = ysec = ydir = ''
                    lon = lat = wkt = ''
                    self._log('Reading {} ...'.format(fullfname))
    
                    _, dam_name, picnum, dam_date, (arroyo_num, arroyo_name) = \
                        standardize_name(fname, root=root)
                    img_date, xydd, xdms, ydms = self.get_image_metadata(fullfname)
                    
                    if xdms is not None:
                        (xdeg, xmin, xsec, xdir) = xdms
                    if ydms is not None:
                        (ydeg, ymin, ysec, ydir) = ydms
                    if xydd is None:
                        in_bounds = False
                        self._log('Failed to return decimal degrees for {}'.format(relfname))
                    else:
                        in_bounds = True
                        lon = xydd[0]
                        lat = xydd[1]
                        wkt = 'Point ({:.7f}  {:.7f})'.format(lon, lat)
                        img_count_geo += 1
                        self.eval_extent(xydd)
                                
                    img_meta[relfname] = {'arroyo': arroyo_name, 
                                          'arroyo_num': arroyo_num,
                                          'dam': dam_name,
                                          'dam_num': picnum,
                                          'dam_date': dam_date,
                                          'img_date': img_date,
                                          LONG_FLD: lon,
                                          LAT_FLD: lat,
                                          GEOM_WKT: wkt,
                                          'xdirection': xdir,
                                          'xdegrees': xdeg,
                                          'xminutes': xmin, 
                                          'xseconds': xsec,
                                          'ydirection': ydir,
                                          'ydegrees': ydeg,
                                          'yminutes': ymin,
                                          'yseconds': ysec,
                                          'fullpath': fullfname,
                                          'in_bounds': in_bounds}
                    try:
                        arroyos[arroyo_name].append(relfname)
                    except:
                        arroyos[arroyo_name] = [relfname]
#                     self._log('  Read {}'.format(fullfname))

        all_data['arroyo_count'] = len(arroyos.keys())
        all_data['arroyos'] = arroyos
        all_data[IMAGES_KEY] = img_meta
        all_data['img_count'] = img_count
        all_data['img_count_geo'] = img_count_geo
        return all_data
    
    # ...............................................
    def write_csv_data(self, out_csv_fname, img_data, delimiter=DELIMITER):
        with open(out_csv_fname, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=delimiter)
            csvwriter.writerow(CSV_FIELDS)
            for relfname, meta in img_data.iteritems():
                rec = []
                for fld in CSV_FIELDS:
                    try:
                        rec.append(meta[fld])
                    except:
                        rec.append('')
                csvwriter.writerow(rec)


    # ...............................................
    def resize_images(self, resize_path, image_data, resize_width=RESIZE_WIDTH):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        if resize_path.endswith('/'):
            resize_path = resize_path[:-1]

        for root, _, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    (_, name, picnum, [fname_yr, fname_mo, fname_day], 
                     (arroyo_num, arroyo_name)) = standardize_name(fname, root=root)
                    if not image_data.has_key(arroyo_name):
                        image_data[arroyo_name] = {'num': arroyo_num}
                    else:
                        image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.eval_extent(dd)
                    if resize_path is not None:
                        # includes trailing /
                        rel_fname = orig_fname[len(self.image_path):]
                        resize_fname = resize_path + rel_fname
                        reduce_image_size(
                            orig_fname, resize_fname, width=resize_width, 
                            sample_method=Image.ANTIALIAS)
                        image_data[arroyo_name][resize_fname] = (
                            [yr, mo, day], dd, xdms, ydms)
                    else:
                        image_data[arroyo_name][resize_fname] = (
                            [yr, mo, day], dd, xdms, ydms)
                        
        return image_data

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
    fileLogHandler = RotatingFileHandler(logfname, maxBytes=LOG_MAX, backupCount=2)
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
def get_csv_dict_reader(datafile, delimiter, fieldnames=None):
    try:
        f = open(datafile, 'r')
        if fieldnames is None:
            header = next(f)
            tmpflds = header.split(delimiter)
            fieldnames = [fld.strip() for fld in tmpflds]
        dreader = csv.DictReader(
                f, fieldnames=fieldnames, delimiter=delimiter)
            
    except Exception as e:
        raise Exception('Failed to read or open {}, ({})'
                        .format(datafile, str(e)))
    else:
        print('Opened file {} for dict read'.format(datafile))
    return dreader, f

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
def reduce_image_size(
        infname, outfname, width=RESIZE_WIDTH, sample_method=Image.ANTIALIAS,
        overwrite=True):
    if ready_filename(outfname, overwrite=overwrite):
        img = Image.open(infname)
        wpercent = (width / float(img.size[0]))
        height = int((float(img.size[1]) * float(wpercent)))
        size = (width, height)
        img = img.resize(size, sample_method)
        img.save(outfname)
        print('Rewrote image {} to {}'.format(infname, outfname))
        

# ...............................................
def _replace_chars(oldname):
    newname = oldname
    if newname.find(" "):
        newname = newname.replace(" ", "")
    if newname.find("'"):
        newname = newname.replace("'", "")
    if newname.find(")"):
        newname = newname.replace(")", ".")
    return newname

# ...............................................
def fix_dirnames(fullpath):
    for root, dirs, _ in os.walk(fullpath):
        for oldname in dirs:
            newname = _replace_chars(oldname)
            if newname != oldname:
                oldpath = os.path.join(root, oldname)
                newpath = os.path.join(root, newname)
                retval = os.rename(oldpath, newpath)
                print('Rename {} - {} to {}'.format(retval, oldpath, newpath))

# ...............................................
def fix_filenames(fullpath):
    total = renamed = 0
    for root, _, files in os.walk(fullpath):
        for old_fname in files:
            if old_fname.lower().endswith('jpg'):
                total += 1
                new_fname = _replace_chars(old_fname)
                (new_fname, name, picnum, yrmody) = standardize_name(new_fname)
                if new_fname != old_fname:
                    renamed += 1
                    old_fullname = os.path.join(root, old_fname)
                    new_fullname = os.path.join(root, new_fname)
                    _ = os.rename(old_fullname, new_fullname)
                    print('Rename {} to {}'.format(old_fname, new_fname))
    print('Renamed {} of {} files'.format(renamed, total))

# .............................................................................
# .............................................................................
# ...............................................
if __name__ == '__main__':    
#     maxY = 35.45045
#     minY = 35.43479
#     maxX = -106.05353
#     minX = -106.07259    
    maxY = 35.45
    minY = 35.428
    maxX = -106.04
    minX = -106.08
    
    dam_buffer = .00002
    
    log = get_logger(os.path.join(BASE_PATH, OUT_DIR))
    log = None
    image_path = os.path.join(BASE_PATH, IN_DIR)
    out_path = os.path.join(BASE_PATH, OUT_DIR)
    resize_path= os.path.join(out_path, THUMB_DIR)
    
    base_outfile = os.path.join(out_path, OUT_NAME)
    csv_fname = '{}.csv'.format(base_outfile)
    shp_fname = '{}.shp'.format(base_outfile)
    kml_fname = '{}.kml'.format(base_outfile)

    bbox = (minX, minY, maxX, maxY)
    
    pm = PicMapper(
        image_path, buffer_distance=dam_buffer, bbox=bbox, logger=log)
      
    # Read data
    if os.path.exists(csv_fname):
        all_data = pm.read_csv_metadata(csv_fname)
    else:
        all_data = pm.read_image_data()
        print('Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
        print('Computed: {}'.format(pm.extent))
        pm.write_csv_data(csv_fname, all_data[IMAGES_KEY])
  
    img_data = all_data[IMAGES_KEY]
    # Reduce image sizes
    t = time.localtime()
    stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
 
    # Write smaller images
    all_coords = pm.create_thumbnails(out_path, img_data, overwrite=False)
    # Write data
    pm.create_shapefile_kml(
        out_path, shp_fname, kml_fname, img_data, do_shape=True, do_kml=False)
      


'''

'''