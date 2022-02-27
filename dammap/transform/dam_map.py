import csv
import exifread
import os
from osgeo import ogr, osr
from PIL import Image
import time

from dammap.common.util import (
    get_csv_dict_reader, get_csv_dict_writer, parse_relative_fname,
    get_logger, logit, ready_filename, reduce_image_size)

from dammap.common.constants import (
    IMG_META, DELIMITER, SEPARATOR, IN_DIR, ANC_DIR, THUMB_DIR, OUT_DIR, SAT_FNAME,
    RESIZE_WIDTH, ARROYO_COUNT, IMAGE_COUNT, SHP_FIELDS, CSV_FIELDS)

from dammap.common.constants import ALL_DATA_KEYS as ADK
from dammap.common.constants import IMAGE_KEYS as IK

# DELETE_CHARS = ['\'', ',', '"', ' ', '(', ')', '_']

# .............................................................................
class PicMapper(object):
    """Read a directory of image files, and create geospatial files for mapping them.
    Yelp help: https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
    """
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
            shp_fname (str): optional name for output shapefile(s)
            kml_fname (str): optional name for output kml file
            logger (object): logger for error logging
        """
        self.base_path, _ = os.path.split(image_path)
        self.image_path = image_path
        self.buffer_distance = buffer_distance
        # Given bounds
        self.bbox = bbox
        # Compute actual bounds of the data
        self._min_x = bbox[0]
        self._min_y = bbox[1]
        self._max_x = bbox[2]
        self._max_y = bbox[3]
        if not logger:
            logger = get_logger(os.path.join(self.base_path, OUT_DIR))
        self._logger = logger

    # ...............................................
    @property
    def bounds(self):
        return (self._min_x, self._min_y, self._max_x, self._max_y)

    # ...............................................
    def _get_val_from_alternative_keys(self, tags, alternative_keys):
        # Get value
        for key in alternative_keys:
            try:
                valstr = tags[key].values
            except KeyError:
                valstr = None
            else:
                break
        return valstr

    # ...............................................
    def _get_date(self, tags):
        # Get date
        dtstr = self._get_val_from_alternative_keys(tags, IMG_META.DATE_KEY_OPTS)
        if dtstr is not None:
            try:
                return [int(x) for x in dtstr.split(':')]
            except:
                self._logger.error(f"datestr {dtstr} cannot be parsed into integers")
        return []
            
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
        if None in (xdd, xdeg, xmin, xsec, xdir, ydd, ydeg, ymin, ysec, ydir):
            self._logger.error(f"coordinates {xdd} {ydd} cannot be parsed")
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
        xdd = float(damdata[IK.LON])
        ydd = float(damdata[IK.LAT])
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
        if damdata[IK.IN_BNDS] is False:
            pass
        else:
            yr = mo = day = '0'
            try:
                [yr, mo, day] = damdata[IK.IMG_DATE]
            except:
                self._logger.warn('damdata does not have a valid img_date')
            relpth, basefname = os.path.split(rel_thumbfname)  
            wkt = damdata[IK.WKT]
            feat = ogr.Feature( lyr.GetLayerDefn() )
            try:
                feat.SetField(IK.ARROYO_NAME, damdata[IK.ARROYO_NAME])
                feat.SetField('thumbpath', rel_thumbfname)
                feat.SetField('thumbname', basefname)
                feat.SetField(IK.IMG_DATE, '{}-{}-{}'.format(yr, mo, day))
                feat.SetField(IK.X_DIR, damdata[IK.X_DEG])
                feat.SetField(IK.X_MIN, damdata[IK.X_MIN])
                feat.SetField(IK.X_SEC, damdata[IK.X_SEC])
                feat.SetField(IK.X_DIR, damdata[IK.X_DIR])
                feat.SetField(IK.Y_DEG, damdata[IK.Y_DEG])
                feat.SetField(IK.Y_MIN, damdata[IK.Y_MIN])
                feat.SetField(IK.Y_SEC, damdata[IK.Y_SEC])
                feat.SetField(IK.Y_DIR, damdata[IK.Y_DIR])
                feat.SetField(IK.LON, damdata[IK.LON])
                feat.SetField(IK.LAT, damdata[IK.LAT])
                feat.SetField(IK.WKT, wkt)
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
        if damdata[IK.IN_BNDS] is False:
            pass
        else:
            [yr, mo, day] = damdata[IK.IMG_DATE]
            xdd = damdata[IK.LON]
            ydd = damdata[IK.LAT]
            arroyo = damdata[IK.ARROYO_NAME]
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
        if damdata[IK.IN_BNDS] is False:
            pass
        else:
            try:
                [yr, mo, day] = damdata[IK.IMG_DATE]
                xdd = damdata[IK.LON]
                ydd = damdata[IK.LAT]
                arroyo = damdata[IK.ARROYO_NAME]
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
        currx = float(damdata[IK.LON])
        curry = float(damdata[IK.LAT])
        for fname, (x,y) in all_coords.items():
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
        for relfname, damdata in img_data.items():
            fullfname = damdata[IK.FILE_PATH]
            # Reduce image
            thumbfname = os.path.join(thumb_path, relfname)
            reduce_image_size(
                fullfname, thumbfname, RESIZE_WIDTH, Image.ANTIALIAS,
                overwrite=overwrite, log=self._logger)
            # Why?
            has_geo = damdata[IK.WKT].startswith('Point')
            if has_geo:
                all_coords = self._add_coords(all_coords, relfname, damdata)
        return all_coords

    # ...............................................
    def write_outputs(self, csvfname=None, shpfname=None, kmlfname=None, overwrite=True):
        csvwriter = csvf = kmlf = dataset = lyr = None
        # Open one or more
        if csvfname is not None:
            if ready_filename(csvfname, overwrite=overwrite):
                csvwriter, csvf = get_csv_dict_writer(csvfname, CSV_FIELDS, DELIMITER)
        if kmlfname is not None:
            if ready_filename(kmlfname, overwrite=overwrite):
                kmlf = self._open_kml_file(kmlfname)
        if shpfname is not None:
            if ready_filename(shpfname, overwrite=overwrite):
                dataset, lyr = self._create_layer(SHP_FIELDS, shpfname)

        # Iterate through features one time writing elements to each requested file
        for relfname, damdata in self.all_data[ADK.IMAGE_META].items():
            # CSV file
            if csvwriter:
                try:
                    csvwriter.writerow(damdata)
                except Exception as e:
                    self._logger.error("Failed to write {}, {}".format(damdata, e))
            if damdata[IK.IN_BNDS] == 1:
                # Thumbnail only relevant to geo-files
                rel_thumbfname = damdata[IK.THUMB_PATH]
                # rel_thumbfname = os.path.join(THUMB_DIR, relfname)
                # KML file
                if kmlf:
                    self._create_lookat_kml(kmlf, rel_thumbfname, damdata)
                # Shapefile
                if dataset and lyr:
                    self._create_feat_shp(lyr, rel_thumbfname, damdata)

        # Close open files
        if csvf:
            csvf.close()
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
            dd, xdms, ydms = self._get_dd(tags)
            date_tuple = self._get_date(tags)
        else:
            self._logger.error(f'{fullname}: Unable to get tags')
        return date_tuple, dd, xdms, ydms
    
    # ...............................................
    def eval_extent(self, x: float, y: float) -> int:
        """Return 1 if point is within bbox, 0 if outside."""
        in_bounds = 1
        # in assigned bbox (min_x, min_y, max_x, max_y)?
        if (x < self.bbox[0] or 
            x > self.bbox[2] or 
            y < self.bbox[1] or 
            y > self.bbox[3]):
            in_bounds = 0
            
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
    def _parse_datestring(self, dtstr):
        parts = dtstr.lstrip('([').rstrip('])').split(',')
        try:
            date_vals = [int(p.strip()) for p in parts]
        except:
            date_vals = None
        return date_vals
        
    # ...............................................
    def read_csv_data(self, csv_fname, delimiter=DELIMITER):
        start_idx = len(self.image_path) + 1
        self.all_data = {}
        arroyos = {}
        img_meta = {}
        img_out_of_range = {}
        img_count_total = 0
        img_count_geo = 0
        reader, f = get_csv_dict_reader(csv_fname, delimiter)
        try:
            for csvrec in reader:
                rec = {}
                img_count_total += 1
                # Copy all vals, parsing dates and bool
                for key, val in csvrec.items():
                    if key in (IK.IMG_DATE, IK.DAM_DATE):
                        rec[key] = self._parse_datestring(csvrec[key])
                    elif key == IK.IN_BNDS:
                        rec[IK.IN_BNDS] = int(csvrec[IK.IN_BNDS])
                    else:
                        rec[key] = csvrec[key]

                # Use relative filename and arroyo name as keys
                relfname = rec[IK.FILE_PATH][start_idx:]
                arroyo_name = rec[IK.ARROYO_NAME]

                # Count images with good geo data
                if rec[IK.WKT].startswith('Point') and rec[IK.IN_BNDS] == 1:
                    # Save metadata for each image
                    img_meta[relfname] = rec
                    img_count_geo += 1
                else:
                    img_out_of_range[relfname] = rec

                # Summarize arroyos
                try:
                    arroyos[arroyo_name].append(relfname)
                except:
                    arroyos[arroyo_name] = [relfname]
        except Exception as e:
            self._logger.error(
                'Failed to read image metadata from {}, line {}, {}'.format(
                    csv_fname, reader.line_num, e))
        finally:
            f.close()

        self.all_data[ADK.ARROYO_COUNT] = len(arroyos.keys())
        self.all_data[ADK.ARROYO_META] = arroyos
        self.all_data[ADK.IMAGE_META] = img_meta
        self.all_data[ADK.IMAGE_OUT_OF_RANGE] = img_out_of_range
        self.all_data[ADK.IMG_COUNT] = img_count_total
        self.all_data[ADK.IMG_GEO_COUNT] = img_count_geo

    # ...............................................
    def test_extent(self, bbox):
        self._logger.info(
            'Given: {} {} {} {}'.format(
                self.bbox[0], self.bbox[1], self.bbox[2], self.bbox[3]))
        self._logger.info('Computed: {}'.format(pm.extent))

    # ...............................................
    def read_metadata_from_directory(self):
        """Read metadata from the directory names and filenames within image_path.

        Results in:
            all_data dictionary with keys/values:
                'base_path': base path containing input and output directories
                'arroyo_meta': {arroyo_name: [rel_fname, ...], ...}
                'image_meta': {rel_fname: {image_metadata}, ...}
                'out_of_range': {rel_fname: {image_metadata}, ...}
                'img_count': total number of images
                'img_count_geo': number of georeferenced and in-bounds images
        """
        start_idx = len(self.image_path) + 1
        self.all_data = {
            ADK.BASE_PATH: self.base_path,
            ADK.ARROYO_META: {},
            ADK.ARROYO_COUNT: 0,
            ADK.IMAGE_META: {},
            ADK.IMAGE_OUT_OF_RANGE: {},
            ADK.IMG_COUNT: 0,
            ADK.IMG_GEO_COUNT: 0
        }
        arroyos = {}
        img_count_geo = 0
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                # Read only non-hidden jpg files
                if not fname.startswith(".") and fname.lower().endswith("jpg"):
                    self.all_data[ADK.IMG_COUNT] += 1
                    fullfname = os.path.join(root, fname)

                    # Get metadata from directory and filename
                    relfname = fullfname[start_idx:]
                    (arroyo_num, arroyo_name, dam_name, dam_date, picnum
                     ) = parse_relative_fname(relfname)

                    # Add image metadata to image_meta dict
                    self.all_data[ADK.IMAGE_META][relfname] = {
                        IK.FILE_PATH: fullfname,
                        IK.BASE_NAME: fname,
                        IK.ARROYO_NAME: arroyo_name,
                        IK.ARROYO_NUM: arroyo_num,
                        IK.DAM_NAME: dam_name,
                        IK.DAM_NUM: picnum,
                        IK.DAM_DATE: dam_date}

                    # Add image filename to arroyo_meta dict
                    try:
                        self.all_data[ADK.ARROYO_META][arroyo_name].append(relfname)
                    except:
                        self.all_data[ADK.ARROYO_META][arroyo_name] = [relfname]
        self.all_data[ADK.ARROYO_COUNT] = len(self.all_data[ADK.ARROYO_META])

    # # ...............................................
    # def compare_all_data(self, other_data):
    #     for akey, aval in self.all_data.items():
    #         if other_data[akey] ==

    # ...............................................
    def read_data_from_image_files(self):
        """Read metadata from all image files within the BASE_PATH """
        start_idx = len(self.image_path) + 1
        img_meta = {}
        img_count_geo = 0
        if not self.all_data:
            self.read_metadata_from_directory()

        for arroyo, rfn_lst in self.all_data[ADK.ARROYO_META].items():
            # Check each image in arroyo
            for relfname in rfn_lst:
                xdeg = xmin = xsec = xdir = ydeg = ymin = ysec = ydir = lon = lat = wkt = ''
                curr_image = self.all_data[ADK.IMAGE_META][relfname]

                # Read metadata from image file
                fullfname = os.path.join(self.image_path, relfname)
                img_date, xydd, xdms, ydms = self.get_image_metadata(fullfname)

                # Test geodata
                if xdms:
                    (xdeg, xmin, xsec, xdir) = xdms
                if ydms:
                    (ydeg, ymin, ysec, ydir) = ydms
                if xydd is None:
                    in_bounds = 0
                    self._logger.warn('Failed to return decimal degrees for {}'.format(relfname))
                else:
                    lon = xydd[0]
                    lat = xydd[1]
                    wkt = 'Point ({:.7f}  {:.7f})'.format(xydd[0], xydd[1])
                    img_count_geo += 1
                    in_bounds = self.eval_extent(lon, lat)

                curr_image[IK.IMG_DATE] = img_date
                curr_image[IK.LON] = lon
                curr_image[IK.LAT] = lat
                curr_image[IK.WKT] = wkt
                curr_image[IK.X_DIR] = xdir
                curr_image[IK.X_DEG] = xdeg
                curr_image[IK.X_MIN] = xmin
                curr_image[IK.X_SEC] = xsec
                curr_image[IK.Y_DIR] = ydir
                curr_image[IK.Y_DEG] = ydeg
                curr_image[IK.Y_SEC] = ysec
                curr_image[IK.Y_MIN] = ymin
                curr_image[IK.IN_BNDS] = in_bounds
        self.all_data[ADK.IMG_GEO_COUNT] = img_count_geo

    # ...............................................
    def test_counts(self):
        # Read into metadata
        if not self.all_data:
            self.read_data_from_image_files()
        # Test the counts in the directories and files
        self._test_dir_counts()
        # Test the counts in the arroyos dictionary
        self._test_meta_counts()

    # ...............................................
    def _test_dir_counts(self):
        # Count the image files in the directory
        fcount = dcount = 0
        for root, dirs, files in os.walk(self.image_path):
            for fname in files:
                if not fname.startswith(".") and fname.lower().endswith("jpg"):
                    fcount += 1
            for dirname in dirs:
                if not dirname.startswith("."):
                    dcount += 1
        if dcount != ARROYO_COUNT:
            print("Error: Found {} arroyo directories, expected {}".format(
                dcount, ARROYO_COUNT))
        if fcount != IMAGE_COUNT:
            print("Error: Found {} images files, expected {}".format(fcount, IMAGE_COUNT))

    # ...............................................
    def _test_meta_counts(self):
        # Count the image files in the arroyos dictionary
        ai_count = 0
        for ar, filelist in self.all_data[ADK.ARROYO_META].items():
            for f in filelist:
                ai_count += 1
        if not ai_count == IMAGE_COUNT:
            print("Error: Found {} images in arroyo_meta, expected {}".format(
                ai_count, IMAGE_COUNT))

        # Count the image files in the img_meta and out_of_range dictionaries
        key_count = (
                len(self.all_data[ADK.IMAGE_META])
                + len(self.all_data[ADK.IMAGE_OUT_OF_RANGE]))
        if not key_count == IMAGE_COUNT:
            print("Error: Found {} images in img_meta, expected {}".format(
                key_count, IMAGE_COUNT))

        # Count the image files in the images dictionary
        if not self.all_data[ADK.IMG_COUNT] == IMAGE_COUNT:
            print("Error: Found {} image count, expected {}".format(
                self.all_data[ADK.IMG_COUNT], IMAGE_COUNT))

    # ...............................................
    def resize_images(self, resize_path, resize_width=RESIZE_WIDTH, overwrite=True):
        """Resize all original images in the image_path tree.

        Args:
            resize_path (str): output path for resized images
            resize_width (int): width in pixels for resized images
        """
        start_idx = len(self.image_path) + 1
        if not self.all_data:
            self.read_data_from_image_files()
        for arroyo, rfn_lst in self.all_data[ADK.ARROYO_META].items():
            # Check each image in arroyo
            for relfname in rfn_lst:
                (arroyo_num, arroyo_name, dam_name, dam_date, picnum
                 ) = parse_relative_fname(relfname)

                # Get original file
                orig_fname = os.path.join(self.image_path, relfname)
                self._logger.info('Reading {} ...'.format(orig_fname))

                # Get new filename
                reldirs, fname = os.path.split(relfname)
                basename, ext = os.path.splitext(fname)
                # thumb_fname = '{}-{}'.format(basename, resize_width, ext)
                # resize_fname = os.path.join(resize_path, reldirs, thumb_fname)
                resize_fname = os.path.join(resize_path, relfname)

                # Rewrite the image
                reduce_image_size(
                    orig_fname, resize_fname, width=resize_width,
                    sample_method=Image.ANTIALIAS, overwrite=overwrite)
                # Add resized file to metadata for original image file
                rel_resize_fname = resize_fname[start_idx:]
                self.all_data[ADK.IMAGE_META][relfname][IK.THUMB_PATH] = rel_resize_fname


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
