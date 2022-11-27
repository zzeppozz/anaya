import exifread
import os
from osgeo import ogr, osr
from PIL import Image

from dammap.common.constants import (
    DELIMITER, ANC_DIR, THUMB_DIR, OUT_DIR, SAT_FNAME, RESIZE_WIDTH, ARROYO_COUNT,
    IMAGE_COUNT, SHP_FIELDS)
from dammap.common.util import (
    get_csv_dict_reader, get_csv_dict_writer, get_logger, ready_filename)
from dammap.common.dammeta import DamMeta

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
            self, image_path, buffer_distance=.0002, bbox=(-180, -90, 180, 90), logger=None):
        """
        Args:
            image_path: Root path for image files to be processed
            buffer_distance: Buffer in which coordinates are considered to be the same location
            bbox: Bounds of the output data, in (min_x, min_y, max_x, max_y) format.  Outside these
                bounds, images will be discarded
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

    # ...............................................
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
    def _format_date(self, date_seq):
        yr = mo = day = '0'
        try:
            [yr, mo, day] = date_seq
        except:
            self._logger.warn(f"damdata does not have a valid date: {date_seq}")
        return '{}-{}-{}'.format(yr, mo, day)

    # ...............................................
    def _create_feat_shp(self, lyr, damrec):
        if damrec[IK.IN_BNDS] == 1:
            wkt = damrec[IK.WKT]
            feat = ogr.Feature( lyr.GetLayerDefn() )
            try:
                for fldname, _fldtype in SHP_FIELDS:
                    if fldname in (IK.IMG_DATE, IK.DAM_DATE):
                        datestr = self._format_date(damrec[fldname])
                        feat.SetField(fldname, datestr)
                    else:
                        feat.SetField(fldname, damrec[fldname])
                geom = ogr.CreateGeometryFromWkt(wkt)
                feat.SetGeometryDirectly(geom)
            except Exception as e:
                self._logger.warn('Failed to fillOGRFeature, e = {}'.format(e))
            else:
                # Create new feature, setting FID, in this layer
                lyr.CreateFeature(feat)
                feat.Destroy()

    # ...............................................
    def _create_feat_kml(self, kmlf, rel_thumbfname, damrec):
        """
        <img style="max-width:500px;"
         dammap="file:///Users/astewart/Home/2017AnayaPics/18-LL-Spring/SpringL1-20150125_0009.JPG">
         SpringL1-20150125_0009 in 18-LL-Spring on 2015-1-25
        """
        if damrec[IK.IN_BNDS] is False:
            pass
        else:
            [yr, mo, day] = damrec[IK.IMG_DATE]
            xdd = damrec[IK.LON]
            ydd = damrec[IK.LAT]
            arroyo = damrec[IK.ARROYO_NAME]
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
    def _create_lookat_kml(self, kmlf, rel_thumbfname, damrec):
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
        if damrec[IK.IN_BNDS] is False:
            pass
        else:
            try:
                [yr, mo, day] = damrec[IK.IMG_DATE]
                xdd = damrec[IK.LON]
                ydd = damrec[IK.LAT]
                arroyo = damrec[IK.ARROYO_NAME]
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
    def _add_coords(self, all_coords, currfname, damrec):
        currx = float(damrec[IK.LON])
        curry = float(damrec[IK.LAT])
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

    # # ...............................................
    # def create_thumbnails(self, out_path, img_data, overwrite=True):
    #     thumb_path = os.path.join(out_path, THUMB_DIR)
    #     all_coords = {}
    #     for relfname, damdata in img_data.items():
    #         fullfname = damdata[IK.FILE_PATH]
    #         # Reduce image
    #         thumbfname = os.path.join(thumb_path, relfname)
    #         reduce_image_size(
    #             fullfname, thumbfname, RESIZE_WIDTH, Image.ANTIALIAS,
    #             overwrite=overwrite, log=self._logger)
    #         # Why?
    #         has_geo = damdata[IK.WKT].startswith('Point')
    #         if has_geo:
    #             all_coords = self._add_coords(all_coords, relfname, damdata)
    #     return all_coords

    # ...............................................
    def _write_row(self, csvwriter, fields, data_dict):
        row = []
        for k in fields:
            if k in (IK.IMG_DATE, IK.DAM_DATE):
                datestr = self._format_date(data_dict[k])
                row.append(datestr)
            else:
                row.append(data_dict[k])
        try:
            csvwriter.writerow(row)
        except Exception as e:
            self._logger.error(f"Failed to write row {row}: {e}")

    # ...............................................
    def write_outputs(self, csvfname=None, shpfname=None, kmlfname=None, overwrite=True):
        csvwriter = csvf = dataset = lyr = None
        # Open one or more
        if csvfname is not None:
            csvfields = [fldname for fldname, tp in SHP_FIELDS]
            if ready_filename(csvfname, overwrite=overwrite):
                # csvwriter, csvf = get_csv_writer(csvfname, DELIMITER, doAppend=False)
                csvwriter, csvf = get_csv_dict_writer(csvfname, csvfields, DELIMITER)
        if shpfname is not None:
            if ready_filename(shpfname, overwrite=overwrite):
                dataset, lyr = self._create_layer(SHP_FIELDS, shpfname)

        # Iterate through features one time writing elements to each requested file
        for relfname, dimg in self.all_data[ADK.IMAGE_META].items():
            # CSV file
            if csvwriter:
                try:
                    csvwriter.writerow(dimg.record)
                    # self._write_row(csvwriter, csvfields, damrec)
                except Exception as e:
                    self._logger.error("Failed to write {}, {}".format(dimg.record, e))
            if dimg.in_bounds == 1:
                # Shapefile
                if dataset and lyr:
                    self._create_feat_shp(lyr, dimg.record)

        # Close open files
        if csvf:
            csvf.close()
        if dataset:
            dataset.Destroy()
            self._logger.info('Closed/wrote dataset {}'.format(shpfname))

    # ...............................................
    def eval_extent(self, x: float, y: float) -> int:
        """Return 1 if point is within bbox, 0 if outside.

        Args:
            x (float): Longitude value
            y (float): Latitude value

        Returns:
            in_bounds (int): flag indicating if the values are within the expected extent.
        """
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
        """Read a CSV file containing image metadata to populate all_data dictionary.

        Args:
            csv_fname (str): full filename of CSV file.
            delimiter (char): delimiter between fields in CSV file.
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
                    self.all_data[ADK.IMAGE_META][relfname] = rec
                    self.all_data[ADK.IMG_GEO_COUNT] += 1
                else:
                    self.all_data[ADK.IMAGE_OUT_OF_RANGE][relfname] = rec

                # Summarize arroyos
                try:
                    self.all_data[ADK.ARROYO_META][arroyo_name].append(relfname)
                except:
                    self.all_data[ADK.ARROYO_META][arroyo_name] = [relfname]
        except Exception as e:
            self._logger.error(
                'Failed to read image metadata from {}, line {}, {}'.format(
                    csv_fname, reader.line_num, e))
        finally:
            f.close()

        self.all_data[ADK.ARROYO_COUNT] = len(self.all_data[ADK.ARROYO_META])
        self.all_data[ADK.IMG_COUNT] = len(self.all_data[ADK.IMAGE_META])

    # ...............................................
    def test_extent(self, bbox):
        """Compare expected extent against bbox.

        Args:
            bbox (list): list of minX, minY, maxX, maxY
        """
        self._logger.info(
            'Given: {} {} {} {}'.format(
                self.bbox[0], self.bbox[1], self.bbox[2], self.bbox[3]))
        self._logger.info('Computed: {}'.format(self.extent))

    # ...............................................
    def populate_images(self):
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
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                # Read only non-hidden jpg files
                if not fname.startswith(".") and fname.lower().endswith("jpg"):
                    self.all_data[ADK.IMG_COUNT] += 1
                    fullfname = os.path.join(root, fname)

                    # Get metadata from directory and filename
                    relfname = fullfname[start_idx:]
                    dimg = DamMeta(fullfname, relfname)
                    if dimg.dd_ok:
                        self.all_data[ADK.IMG_GEO_COUNT] += 1
                        dimg.in_bounds = self.eval_extent(dimg.longitude, dimg.latitude)
                    else:
                        self._logger.warn(f"Failed to return decimal degrees for {relfname}")

                    # Add image metadata object to image_meta list
                    self.all_data[ADK.IMAGE_META][relfname] = dimg

                    # Add image filename to arroyo_meta dict
                    try:
                        self.all_data[ADK.ARROYO_META][dimg.arroyo_name].append(relfname)
                    except:
                        self.all_data[ADK.ARROYO_META][dimg.arroyo_name] = [relfname]

        self.all_data[ADK.ARROYO_COUNT] = len(self.all_data[ADK.ARROYO_META])

    # # ...............................................
    # def test_counts(self):
    #     # Read into metadata
    #     if not self.all_data:
    #         self.read_data_from_image_files()
    #     # Test the counts in the directories and files
    #     self._test_dir_counts()
    #     # Test the counts in the arroyos dictionary
    #     self._test_meta_counts()

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
    def resize_images(self, outpath, resize_width=RESIZE_WIDTH, overwrite=True):
        """Resize all original images in the image_path tree.

        Args:
            outpath (str): output path
            resize_width (int): width in pixels for resized images
            overwrite (bool): flag indicating whether to rewrite existing resized images.
        """
        if not self.all_data:
            self.read_data_from_image_files()
        for relfname, dimg in self.all_data[ADK.IMAGE_META].items():
            resize_fname = os.path.join(outpath, THUMB_DIR, dimg.relfname)

            # Rewrite the image
            dimg.resize(
                resize_fname, resize_width, sample_method=Image.ANTIALIAS,
                overwrite=overwrite)

            dimg.thumbpath = resize_fname

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
