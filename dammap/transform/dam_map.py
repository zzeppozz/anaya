import csv
import exifread
import os
from osgeo import ogr, osr
from PIL import Image
import time

from dammap.common.util import (
    get_csv_dict_reader, get_logger, logit, ready_filename, reduce_image_size)
from dammap.common.constants import (
    GEOM_WKT, LONG_FLD, LAT_FLD, IMG_META, DELIMITER, SEPARATOR, IN_DIR, ANC_DIR,
    THUMB_DIR, OUT_DIR, SAT_FNAME, RESIZE_WIDTH, IMAGES_KEY, CSV_FIELDS)

# DELETE_CHARS = ['\'', ',', '"', ' ', '(', ')', '_']

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
            shp_fname=None, kml_fname=None, logger=None):
        """
        Args:
            image_path: Root path for image files to be processed
            buffer_distance: Buffer in which coordinates are considered to be the same location
            bbox: Bounds of the output data, in (min_x, min_y, max_x, max_y) format.  Outside these
                bounds, images will be discarded
        """
        self.base_path, _ = os.path.split(image_path)
        self.image_path = image_path
        self.buffer_distance = buffer_distance
        self.bbox = bbox
        # Compute actual bounds of the data
        self._min_x = bbox[0]
        self._min_y = bbox[1]
        self._max_x = bbox[2]
        self._max_y = bbox[3]
        if not logger:
            logger = get_logger(os.path.join(self.base_path, OUT_DIR))
        self._logger = logger

    # # ...............................................
    # def _clean_name(self, name):
    #     """Remove non-ascii and other special characters; replace first right paren with underscore"""
    #     tmpchars = []
    #     idx = name.index(RPAREN)
    #     tmp_name = name[0:idx] + '_' + name[idx+1:]
    #     for ch in tmp_name:
    #         if ch.isascii() and ch not in DELETE_CHARS:
    #             tmpchars.append(ch)
    #     new_name = ''.join(tmpchars)
    #     return new_name
    #
    # # ...............................................
    # def _standardize_name(self, filename, fullpath):
    #     date_str = num_str = '?'
    #     _, arroyo_dir = os.path.split(fullpath)
    #     new_arroyo_dir = self._clean_name(arroyo_dir)
    #     arroyo_num, arroyo_name = new_arroyo_dir.split('_')
    #
    #     # Fix missing extensions manually
    #     basename, ext = os.path.splitext(filename)
    #     if ext == '':
    #         logit(self._logger, 'Missing extension in {}, dir {}'.format(filename, fullpath))
    #         ext = '.JPG'
    #
    #     # Find first number in filename, indicating start of date/time string
    #     for i in range(len(basename)):
    #         try:
    #             int(basename[i])
    #             break
    #         except:
    #             pass
    #     name = basename[:i]
    #     rest = basename[i:]
    #     new_name = self._clean_name(name)
    #     # Date time parts split by underscore
    #     parts = rest.split('_')
    #     if len(parts) == 2:
    #         date_str, num_str = parts
    #     # or not
    #     elif len(parts) == 1:
    #         date_str = parts[0][:8]
    #         num_str = parts[0][8:]
    #     else:
    #         logit(self._logger, '** Bad filename {}'.format(filename))
    #
    #     try:
    #         new_filename = '{}_{}_{}{}'.format(new_name, date_str, num_str, ext)
    #     except:
    #         new_filename = filename
    #
    #     picnum = int(num_str)
    #     yr = int(date_str[:4])
    #     mo = int(date_str[4:6])
    #     dy = int(date_str[6:8])
    #
    #     return new_filename, name, picnum, (yr, mo, dy), (arroyo_num, arroyo_name)

    # ...............................................
    def _get_date(self, tags):
        # Get date
        dtstr = tags[IMG_META.DATE_KEY].values
        try:
            return [int(x) for x in dtstr.split(':')]
        except:
            return None
            
    # ...............................................
    def _get_location_vals(self, tags, locKey, dirKey, negativeIndicator):
        isNegative = False
        # Get longitude or latitude
        degObj, minObj, secObj = tags[locKey].values
        nsew = tags[dirKey].printable
        if nsew == negativeIndicator:
            isNegative = True
        # Convert to float
        degrees = degObj.num / float(degObj.den) 
        minutes = minObj.num / float(minObj.den)
        seconds = secObj.num / float(secObj.den)    
        # Convert to decimal degrees
        dd = (seconds/3600) + (minutes/60) + degrees
        if isNegative:
            dd = -1 * dd
        return dd, degrees, minutes, seconds, nsew
    
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
        (min_x, min_y, max_x, max_y) = self.bbox
        if os.path.exists(fname):
            os.remove(fname)
        foldername, _ = os.path.splitext(os.path.basename(fname))
        rel_satellite_fname = os.path.join('../..', ANC_DIR, SAT_FNAME)
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
        f.write('         <north>{}</north>\n'.format(max_y))
        f.write('         <south>{}</south>\n'.format(min_y))
        f.write('         <east>{}</east>\n'.format(max_x))
        f.write('         <west>{}</west>\n'.format(min_x))
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
        # (min_x, min_y, max_x, max_y)
        xdd = float(damdata[LONG_FLD])
        ydd = float(damdata[LAT_FLD])
        if xdd < self.bbox[0]:
            self._logger.warn('X value {} < min {}'.format(xdd, self.bbox[0]))
        elif xdd > self.bbox[2]:
            self._logger.warn('X value {} > max {}'.format(xdd, self.bbox[2]))
        elif ydd < self.bbox[1]:
            self._logger.warn('Y value {} < min {}'.format(ydd, self.bbox[1]))
        elif ydd > self.bbox[3]:
            self._logger.warn('Y value {} > max {}'.format(ydd, self.bbox[3]))
        else:
            good_geo = True
        return good_geo
            
    # ...............................................
    def _create_feat_shp(self, lyr, rel_thumbfname, damdata):
        if damdata['in_bounds'] is False:
            pass
        else:
            yr = mo = day = '0'
            try:
                [yr, mo, day] = damdata['img_date']
            except:
                self._logger.warn('damdata does not have a valid img_date')
            relpth, basefname = os.path.split(rel_thumbfname)  
            wkt = damdata[GEOM_WKT]
            feat = ogr.Feature( lyr.GetLayerDefn() )
            try:
                feat.SetField('arroyo', damdata['arroyo'])
                feat.SetField('relpath', rel_thumbfname)
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
                self._logger.warn('Failed to fillOGRFeature, e = {}'.format(e))
            else:
                # Create new feature, setting FID, in this layer
                lyr.CreateFeature(feat)
                feat.Destroy()
            
    # ...............................................
    def _create_feat_kml(self, kmlf, rel_thumbfname, damdata):
        """
        <img style="max-width:500px;" 
         dammap="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
         SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
        """
        if damdata['in_bounds'] is False:
            pass
        else:
            [yr, mo, day] = damdata['img_date'] 
            xdd = damdata[LONG_FLD]
            ydd = damdata[LAT_FLD]
            arroyo = damdata['arroyo']
            _, basefname = os.path.split(rel_thumbfname)
            basename, _ = os.path.splitext(basefname)
            dt = '{}-{}-{}'.format(yr, mo, day)
        
            kmlf.write('  <Placemark>\n')
            kmlf.write('    <name>{}</name>\n'.format(basefname))
            kmlf.write('    <description>{} in {} on {}</description>\n'
                       .format(basename, arroyo, dt))
            kmlf.write('    <img style="max-width:{}px;" dammap="{}" />\n'
                       .format(RESIZE_WIDTH, rel_thumbfname))
            kmlf.write('    <Point><coordinates>{},{}</coordinates></Point>\n'
                       .format(xdd, ydd))
            kmlf.write('  </Placemark>\n')
        
    # ...............................................
    def _create_lookat_kml(self, kmlf, rel_thumbfname, damdata):
        """
         <LookAt id="ID">
  <!-- inherited from AbstractView element -->
  <Placemark>
    <name>LookAt.kml</name>
    <LookAt>
      <gx:TimeStamp>
        <when>1994</when>
      </gx:TimeStamp>
      <longitude>-122.363</longitude>
      <latitude>37.81</latitude>
      <altitude>2000</altitude>
      <range>500</range>
      <tilt>45</tilt>
      <heading>0</heading>
      <altitudeMode>relativeToGround</altitudeMode>
    </LookAt>
    <Point>
      <coordinates>-122.363,37.82,0</coordinates>
    </Point>
  </Placemark>

  <!-- specific to LookAt -->
  <longitude>0</longitude>            <!-- kml:angle180 -->
  <latitude>0</latitude>              <!-- kml:angle90 -->
  <altitude>0</altitude>              <!-- double -->
  <heading>0</heading>                <!-- kml:angle360 -->
  <tilt>0</tilt>                      <!-- kml:anglepos90 -->
  <range></range>                     <!-- double -->
  <altitudeMode>clampToGround</altitudeMode>
          <!--kml:altitudeModeEnum:clampToGround, relativeToGround, absolute -->
          <!-- or, gx:altitudeMode can be substituted: clampToSeaFloor, relativeToSeaFloor -->

</LookAt>
        """
        if damdata['in_bounds'] is False:
            pass
        else:
            try:
                [yr, mo, day] = damdata['img_date'] 
                xdd = damdata[LONG_FLD]
                ydd = damdata[LAT_FLD]
                arroyo = damdata['arroyo']
            except Exception as e:
                self._logger.error('Failed reading data {}'.format(e))
            else:
                _, basefname = os.path.split(rel_thumbfname)
                basename, _ = os.path.splitext(basefname)
                dt = '{}-{}-{}'.format(yr, mo, day)     
                kmlf.write('  <Placemark>\n')
                kmlf.write('    <name>{}</name>\n'.format(basefname))
                kmlf.write('    <description>{} in {} on {}</description>\n'
                           .format(basename, arroyo, dt))
                kmlf.write('    <img style="max-width:{}px;" dammap="{}"/>\n'
                           .format(RESIZE_WIDTH, rel_thumbfname))
                kmlf.write('    <LookAt>')
                kmlf.write('       <longitude>{}</longitude>'.format(xdd))
                kmlf.write('       <latitude>{}</latitude>'.format(ydd))
                kmlf.write('       <altitude>2</altitude>')
                kmlf.write('       <range>4</range>')
                kmlf.write('       <tilt>45</tilt>')
                kmlf.write('       <heading>0</heading>')
                kmlf.write('       <altitudeMode>relativeToGround</altitudeMode>')
                kmlf.write('    </LookAt>')
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
                self._logger.info(
                    'Current file {} is within buffer of {} (dx = {}, dy = {})'.format(
                        currfname, fname, dx, dy))
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
                fullfname, thumbfname, RESIZE_WIDTH, Image.ANTIALIAS,
                overwrite=overwrite, log=self._logger)
            # Why?
            has_geo = damdata[GEOM_WKT].startswith('Point')
            if has_geo:
                all_coords = self._add_coords(all_coords, relfname, damdata)
        return all_coords
            
            
    # ...............................................
    def create_shapefile_kml(self, shpfname, kmlfname, img_data):
        kmlf = dataset = lyr = None
        # Open one or both
        if kmlfname is not None:
            ready_filename(kml_fname)
            kmlf = self._open_kml_file(kmlfname)
        if shpfname is not None:
            ready_filename(shpfname)
            dataset, lyr = self._create_layer(self.FIELDS, shpfname)

        # Iterate through features one time writing elements to each requested file
        for relfname, damdata in img_data.iteritems():
            if damdata['in_bounds'] is True:
                rel_thumbfname = os.path.join(THUMB_DIR, relfname)
                if kmlf:
                    self._create_lookat_kml(kmlf, rel_thumbfname, damdata)
                if dataset and lyr:
                    self._create_feat_shp(lyr, rel_thumbfname, damdata)

        # Close open files
        if kmlf:
            self._close_kml_file(kmlf)
        if dataset:
            dataset.Destroy()
            self._logger.info('Closed/wrote dataset {}'.format(shpfname))
    
    
    # ...............................................
    def get_image_metadata(self, fullname):
        tags = dd = xdms = ydms = yr = mo = day = None
        # Read image metadata
        try:
            # Open file in binary mode
            f = open(fullname, 'rb')
            # Get Exif tags
            tags = exifread.process_file(f)
        except Exception as e:
            self._logger.error('{}: Unable to read image metadata, {}'.format(
                fullname, e))
        finally:
            try:
                f.close()
            except:
                pass
        # Parse image metadata
        if tags:
            try:
                dd, xdms, ydms = self._get_dd(tags)
            except Exception as e:
                self._logger.error('{}: Unable to get x y, {}'.format(fullname, e))
            try:
                yr, mo, day = self._get_date(tags)
            except Exception as e:
                self._logger.error('{}: Unable to get date, {}'.format(fullname, e))
        return (yr, mo, day), dd, xdms, ydms
    
    # ...............................................
    def eval_extent(self, x: float, y: float) -> bool:
        in_bounds = True
        # in assigned bbox (min_x, min_y, max_x, max_y)?
        if (x < self.bbox[0] or 
            x > self.bbox[2] or 
            y < self.bbox[1] or 
            y > self.bbox[3]):
            in_bounds = False
            
        if x < self._min_x:
            self._min_x = x
        if x > self._max_x:
            self._max_x = x
            
        if y < self._min_y:
            self._min_y = y
        if y > self._max_y:
            self._max_y = y

        if self._min_x is None:
            self._min_x = x
            self._max_x = x
            self._min_y = y
            self._max_y = y
        else:
            if x < self._min_x:
                self._min_x = x
            if x > self._max_x:
                self._max_x = x
                
            if y < self._min_y:
                self._min_y = y
            if y > self._max_y:
                self._max_y = y
        return in_bounds
    
    # ...............................................
    @property
    def extent(self):
        return (self._min_x, self._min_y, self._max_x, self._max_y)

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
    def process_all_images(self, resize_width=RESIZE_WIDTH, resize_path=None):
        """
        {arroyo_name: {num: <arroyo_num>, fullname: ([yr, mo, day], dd, xdms, ydms),
                                          ...
                                          fullname: ([yr, mo, day], dd, xdms, ydms)}
        }
        """
        image_data = {}
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                if fname.endswith('jpg') or fname.endswith('JPG'): 
                    orig_fname = os.path.join(root, fname)
                    
                    (_, name, picnum, (fyear, fmon, fday), 
                     (arroyo_num, arroyo_name)) = self._standardize_name(fname, root)
                        
                    try:
                        image_data[arroyo_name]['num'] = arroyo_num
                    except:
                        image_data[arroyo_name] = {'num': arroyo_num}
                    # if not image_data.has_key(arroyo_name):
                    #     image_data[arroyo_name] = {'num': arroyo_num}
                    # else:
                    #     image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.get_image_metadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    in_bounds = self.eval_extent(dd[0], dd[1])
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
    def read_data_from_file(self, csv_fname, delimiter=DELIMITER):
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
                rec['in_bounds'] = bool(rec['in_bounds'])
                
                # Count images with good geo data
                if rec[GEOM_WKT].startswith('Point') and rec['in_bounds']:
                    img_count_geo += 1
                else:
                    img_out_of_range[relfname] = rec
                    
                # Save metadata for each image  
                img_meta[relfname] = rec
                # Summarize arroyos
                try:
                    arroyos[arroyo_name].append(relfname)
                except:
                    arroyos[arroyo_name] = [relfname]
        except Exception as e:
            self._logger.error(
                'Failed to read image metadata from {}, line {}, {}'.format(
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
    def _read_image_data(self, csv_fname):
        if os.path.exists(csv_fname):
            all_data = self.read_data_from_file(csv_fname)
        else:
            all_data = self.read_data_from_images(csv_fname)
            pm.write_csv_data(csv_fname, all_data[IMAGES_KEY])
        return all_data

    # ...............................................
    def test_extent(self, bbox):
        self._logger.info(
            'Given: {} {} {} {}'.format(
                self.bbox[0], self.bbox[1], self.bbox[2], self.bbox[3]))
        self._logger.info('Computed: {}'.format(pm.extent))

    # ...............................................
    def read_data_from_images(self, csv_fname):
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
                    self._logger.info('Reading {} ...'.format(fullfname))
    
                    _, dam_name, picnum, dam_date, (arroyo_num, arroyo_name) = \
                        self._standardize_name(fname, root)
                    img_date, xydd, xdms, ydms = self.get_image_metadata(fullfname)
                    
                    if xdms is not None:
                        (xdeg, xmin, xsec, xdir) = xdms
                    if ydms is not None:
                        (ydeg, ymin, ysec, ydir) = ydms
                    if xydd is None:
                        in_bounds = False
                        self._logger.warn('Failed to return decimal degrees for {}'.format(relfname))
                    else:
                        lon = xydd[0]
                        lat = xydd[1]
                        wkt = 'Point ({:.7f}  {:.7f})'.format(lon, lat)
                        img_count_geo += 1
                        in_bounds = self.eval_extent(lon, lat)
                                
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
#                     self._logger('  Read {}'.format(fullfname))

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
                     (arroyo_num, arroyo_name)) = self._standardize_name(fname, root)
                    if not image_data.has_key(arroyo_name):
                        image_data[arroyo_name] = {'num': arroyo_num}
                    else:
                        image_data[arroyo_name]['num'] = arroyo_num
                        
                    [yr, mo, day], dd, xdms, ydms = self.getImageMetadata(orig_fname)
                    if dd is None:
                        return {}
                    
                    self.eval_extent(dd[0], dd[1])
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
# .............................................................................
# ...............................................
if __name__ == '__main__':    
#     max_y = 35.45045
#     min_y = 35.43479
#     max_x = -106.05353
#     min_x = -106.07259    
    max_y = 35.45
    min_y = 35.42
    max_x = -106.04
    min_x = -106.08
    
    dam_buffer = .00002
    
    image_path = os.path.join(BASE_PATH, IN_DIR)
    out_path = os.path.join(BASE_PATH, OUT_DIR)
    resize_path= os.path.join(out_path, THUMB_DIR)
    
    base_outfile = os.path.join(out_path, OUT_NAME)
    csv_fname = '{}.csv'.format(base_outfile)
    shp_fname = '{}.shp'.format(base_outfile)
    kml_fname = None  #'{}.kml'.format(base_outfile)

    bbox = (min_x, min_y, max_x, max_y)
    
    pm = PicMapper(image_path, buffer_distance=dam_buffer, bbox=bbox)
      
    # Read data
    if os.path.exists(csv_fname):
        all_data = pm.read_csv_metadata(csv_fname)
    else:
        all_data = pm.read_image_data()
        logit(pm._logger, 'Given: {} {} {} {}'.format(pm.bbox[0], pm.bbox[1], pm.bbox[2], pm.bbox[3]))
        logit(pm._logger, 'Computed: {}'.format(pm.extent))
        pm.write_csv_data(csv_fname, all_data[IMAGES_KEY])
  
    img_data = all_data[IMAGES_KEY]
    # Reduce image sizes
    t = time.localtime()
    stamp = '{}_{}_{}-{}_{}'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
 
    # Write smaller images
    all_coords = pm.create_thumbnails(out_path, img_data, overwrite=False)
    # Write data
    pm.create_shapefile_kml(shp_fname, kml_fname, img_data)
      


'''

'''