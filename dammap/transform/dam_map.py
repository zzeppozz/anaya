import exifread
import os
from osgeo import ogr, osr
from PIL import Image

from dammap.common.constants import (
    BASE_PATH, DELIMITER, ANC_DIR, THUMB_DIR, OUT_DIR, SAT_FNAME, RESIZE_WIDTH, ARROYO_COUNT,
    IMAGE_COUNT, SHP_FIELDS)
from dammap.common.util import (
    get_csv_dict_reader, get_csv_dict_writer, get_logger, ready_filename)
from dammap.common.dammeta import DamMeta

from dammap.common.constants import ALL_DATA_KEYS as ADK
from dammap.common.constants import IMAGE_KEYS as IK

# DELETE_CHARS = ["\"", ",", """, " ", "(", ")", "_"]


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
    def _create_layer(self, fields, shpFname):
        ogr.RegisterAll()
        drv = ogr.GetDriverByName("ESRI Shapefile")
        tSRS = osr.SpatialReference()
        tSRS.ImportFromEPSG(4326)
        try:
            # Create the file object
            ds = drv.CreateDataSource(shpFname)
            if ds is None:
                raise Exception("Dataset creation failed for %s" % shpFname)
            # Create a layer
            lyr = ds.CreateLayer("anayaSprings", geom_type=ogr.wkbPoint, srs=tSRS)
            if lyr is None:
                raise Exception("Layer creation failed for %s." % shpFname)
        except Exception as e:
            raise Exception("Failed creating dataset or layer for %s (%s)"
                                  % (shpFname, str(e)))
        # Create attributes
        for (fldname, fldtype) in fields:
            fldDefn = ogr.FieldDefn(fldname, fldtype)
            if lyr.CreateField(fldDefn) != 0:
                raise Exception("CreateField failed for %s" % (fldname))
        return ds, lyr

    # # ...............................................
    # def _good_geo(self, damrec):
    #     good_geo = False
    #     # (min_x, min_y, max_x, max_y)
    #     xdd = float(damrec[IK.LON])
    #     ydd = float(damrec[IK.LAT])
    #     if xdd < self.bbox[0]:
    #         self._logger.warn("X value {} < min {}".format(xdd, self.bbox[0]))
    #     elif xdd > self.bbox[2]:
    #         self._logger.warn("X value {} > max {}".format(xdd, self.bbox[2]))
    #     elif ydd < self.bbox[1]:
    #         self._logger.warn("Y value {} < min {}".format(ydd, self.bbox[1]))
    #     elif ydd > self.bbox[3]:
    #         self._logger.warn("Y value {} > max {}".format(ydd, self.bbox[3]))
    #     else:
    #         good_geo = True
    #     return good_geo

    # ...............................................
    def _format_date(self, date_seq):
        yr = mo = day = "0"
        try:
            [yr, mo, day] = date_seq
        except:
            self._logger.warn(f"damrec does not have a valid date: {date_seq}")
        return "{}-{}-{}".format(yr, mo, day)

    # ...............................................
    def _create_feat_shp(self, lyr, damrec):
        if damrec[IK.IN_BNDS] == 1:
            wkt = damrec[IK.WKT]
            feat = ogr.Feature( lyr.GetLayerDefn() )
            for fldname, _fldtype in SHP_FIELDS:
                val = damrec[fldname]
                if fldname in (IK.IMG_DATE, IK.DAM_DATE):
                    val = self._format_date(damrec[fldname])
                # elif fldname in (IK.VERB_LON, IK.VERB_LON_DIR, IK.VERB_LAT, IK.VERB_LAT_DIR):
                #     val = f"{damrec[fldname]}"
                try:
                    feat.SetField(fldname, val)
                except Exception as e:
                    self._logger.warn(f"Failed to SetField for field {fldname}, value {val}, err = {e}")
            geom = ogr.CreateGeometryFromWkt(wkt)
            feat.SetGeometryDirectly(geom)
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
            dt = f"{yr}-{mo}-{day}"

            kmlf.write("  <Placemark>\n")
            kmlf.write(f"    <name>{basefname}</name>\n")
            kmlf.write(f"    <description>{basename} in {arroyo} on {dt}</description>\n")
            kmlf.write(f"    <img style='max-width:{RESIZE_WIDTH}px;' dammap='{rel_thumbfname}' />\n")
            kmlf.write(f"    <Point><coordinates>{xdd},{ydd}</coordinates></Point>\n")
            kmlf.write("  </Placemark>\n")

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
                self._logger.error(f"Failed reading data {e}")
            else:
                _, basefname = os.path.split(rel_thumbfname)
                basename, _ = os.path.splitext(basefname)
                dt = f"{yr}-{mo}-{day}"
                kmlf.write("  <Placemark>\n")
                kmlf.write(f"    <name>{basefname}</name>\n")
                kmlf.write(f"    <description>{basename} in {arroyo} on {dt}</description>\n")
                kmlf.write(f"    <img style='max-width:{RESIZE_WIDTH}px;' dammap='{rel_thumbfname}'/>\n")
                kmlf.write("    <LookAt>")
                kmlf.write(f"       <longitude>{xdd}</longitude>")
                kmlf.write(f"       <latitude>{ydd}</latitude>")
                kmlf.write("       <altitude>2</altitude>")
                kmlf.write("       <range>4</range>")
                kmlf.write("       <tilt>45</tilt>")
                kmlf.write("       <heading>0</heading>")
                kmlf.write("       <altitudeMode>relativeToGround</altitudeMode>")
                kmlf.write("    </LookAt>")
                kmlf.write(f"    <Point><coordinates>{xdd},{ydd}</coordinates></Point>\n")
                kmlf.write("  </Placemark>\n")

    # ...............................................
    def _add_coords(self, all_coords, currfname, damrec):
        currx = float(damrec[IK.LON])
        curry = float(damrec[IK.LAT])
        for fname, (x,y) in all_coords.items():
            dx = abs(abs(x) - abs(currx))
            dy = abs(abs(y) - abs(curry))
            if dx < self.buffer_distance or dy < self.buffer_distance:
                self._logger.info(
                    "Current file {} is within buffer of {} (dx = {}, dy = {})".format(
                        currfname, fname, dx, dy))
                break
        all_coords[currfname] = (currx, curry)
        return all_coords

    # # ...............................................
    # def create_thumbnails(self, out_path, img_data, overwrite=True):
    #     thumb_path = os.path.join(out_path, THUMB_DIR)
    #     all_coords = {}
    #     for relfname, damrec in img_data.items():
    #         fullfname = damrec[IK.FILE_PATH]
    #         # Reduce image
    #         thumbfname = os.path.join(thumb_path, relfname)
    #         reduce_image_size(
    #             fullfname, thumbfname, RESIZE_WIDTH, Image.ANTIALIAS,
    #             overwrite=overwrite, log=self._logger)
    #         # Why?
    #         has_geo = damrec[IK.WKT].startswith("Point")
    #         if has_geo:
    #             all_coords = self._add_coords(all_coords, relfname, damrec)
    #     return all_coords
    # 
    # # ...............................................
    # def _write_row(self, csvwriter, fields, data_dict):
    #     row = []
    #     for k in fields:
    #         if k in (IK.IMG_DATE, IK.DAM_DATE):
    #             datestr = self._format_date(data_dict[k])
    #             row.append(datestr)
    #         else:
    #             row.append(data_dict[k])
    #     try:
    #         csvwriter.writerow(row)
    #     except Exception as e:
    #         self._logger.error(f"Failed to write row {row}: {e}")

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
                    csvwriter.writerow(dimg.record_for_csv)
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
            self._logger.info("Closed/wrote dataset {}".format(shpfname))

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
        parts = dtstr.lstrip("([").rstrip("])").split(",")
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
                if rec[IK.WKT].startswith("Point") and rec[IK.IN_BNDS] == 1:
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
                "Failed to read image metadata from {}, line {}, {}".format(
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
            "Given: {} {} {} {}".format(
                self.bbox[0], self.bbox[1], self.bbox[2], self.bbox[3]))
        self._logger.info(f"Computed: {self.extent}")

    # ...............................................
    def _add_to_unique_coords(self, dimg):
        if dimg.dd_ok:
            if dimg.wkt in self.all_data[ADK.UNIQUE_COORDS].keys():
                if dimg.arroyo_name in self.all_data[ADK.UNIQUE_COORDS][dimg.wkt].keys():
                    self.all_data[ADK.UNIQUE_COORDS][dimg.wkt][dimg.arroyo_name].append(dimg.relfname)
                else:
                    self.all_data[ADK.UNIQUE_COORDS][dimg.wkt][dimg.arroyo_name] = [dimg.relfname]
            else:
                self.all_data[ADK.UNIQUE_COORDS][dimg.wkt] = {dimg.arroyo_name:  [dimg.relfname]}
        else:
            if dimg.arroyo_name in self.all_data[ADK.UNIQUE_COORDS]["no_geo"].keys():
                self.all_data[ADK.UNIQUE_COORDS]["no_geo"][dimg.arroyo_name].append(dimg.relfname)
            else:
                self.all_data[ADK.UNIQUE_COORDS]["no_geo"][dimg.arroyo_name] = [dimg.relfname]

    # ...............................................
    def _add_to_unique_cameras(self, dimg):
        if dimg.guilty_party in self.all_data[ADK.UNIQUE_CAMERAS].keys():
            self.all_data[ADK.UNIQUE_CAMERAS][dimg.guilty_party] += 1
        else:
            self.all_data[ADK.UNIQUE_CAMERAS][dimg.guilty_party] = 1

    # ...............................................
    def populate_images(self):
        """Read metadata from the directory names and filenames within image_path.

        Results in:
            all_data dictionary with keys/values:
                `base_path`: base path containing input and output directories
                `arroyo_meta`: {arroyo_name: [rel_fname, ...], ...}
                `image_meta`: {rel_fname: {image_metadata}, ...}
                `out_of_range`: {rel_fname: {image_metadata}, ...}
                `img_count`: total number of images
                `img_count_geo`: number of georeferenced and in-bounds images
                `unique_coordinates`: {wkt: {arroyo: [relfname, ...]},
                                             arroyo2: [],
                                             ...},
                                       wkt2: {...},
                                       ...}
        """
        self.all_data = {
            ADK.BASE_PATH: self.base_path,
            ADK.ARROYO_META: {},
            ADK.ARROYO_COUNT: 0,
            ADK.IMAGE_META: {},
            ADK.IMAGE_OUT_OF_RANGE: {},
            ADK.IMG_COUNT: 0,
            ADK.IMG_GEO_COUNT: 0,
            ADK.UNIQUE_COORDS: {"no_geo": {}},
            ADK.UNIQUE_CAMERAS: {}
        }
        for root, _, files in os.walk(self.image_path):
            for fname in files:
                # Read only non-hidden jpg files
                if not fname.startswith(".") and fname.lower().endswith("jpg"):
                    self.all_data[ADK.IMG_COUNT] += 1
                    fullfname = os.path.join(root, fname)

                    # Get metadata from directory and filename
                    dimg = DamMeta(fullfname, self.image_path, logger=self._logger)
                    # Add image metadata object to image_meta list
                    self.all_data[ADK.IMAGE_META][dimg.relfname] = dimg
                    # Add relfname to unique_coordinate  by arroyo
                    self._add_to_unique_coords(dimg)
                    # Increment count for each camera in dictionary
                    self._add_to_unique_cameras(dimg)
                    # Evaluate point within expected boundary
                    if dimg.dd_ok:
                        self.all_data[ADK.IMG_GEO_COUNT] += 1
                        dimg.in_bounds = self.eval_extent(dimg.longitude, dimg.latitude)

                    # Add image filename to arroyo_meta dict
                    try:
                        self.all_data[ADK.ARROYO_META][dimg.arroyo_name].append(dimg.relfname)
                    except:
                        self.all_data[ADK.ARROYO_META][dimg.arroyo_name] = [dimg.relfname]

        self.all_data[ADK.ARROYO_COUNT] = len(self.all_data[ADK.ARROYO_META])


    # ...............................................
    def _summarize_duplicates(self):
        """
        unique_coord_counts = {wkt:
                                    arroyo_count: arroyo_count,
                                    image_count: image_count
                                    arroyo1_name: x,
                                    arroyo2_name: y},
                               wkt2: ...}
        wkt_by_count = { 45: [wkt]
                        11: [wkt, wkt, ...]
                        4:  [...]
                        ...}
        """
        if not self.all_data:
            self.populate_images()
        # Counts
        unique_coord_counts = {}
        for wkt, arroyo_dict in self.all_data[ADK.UNIQUE_COORDS].items():
            unique_coord_counts[wkt] = {"arroyo_count": len(arroyo_dict)}
            image_count = 0
            for arroyo, relfnames in arroyo_dict.items():
                unique_coord_counts[wkt][arroyo] = len(relfnames)
                image_count += len(relfnames)
            unique_coord_counts[wkt]["image_count"] = image_count

        wkt_by_count = {}
        for wkt, summary in unique_coord_counts.items():
            try:
                wkt_by_count[summary["image_count"]].append(wkt)
            except KeyError:
                wkt_by_count[summary["image_count"]] = [wkt]

        return unique_coord_counts, wkt_by_count

    # ...............................................
    def _get_location_camera_info(self, relfname):
        dimg = self.all_data[ADK.IMAGE_META][relfname]
        if dimg:
            lon = f"{dimg.verbatim_longitude} {dimg.verbatim_longitude_direction}"
            lat = f"{dimg.verbatim_latitude} {dimg.verbatim_latitude_direction}"
            camera = f"{dimg.guilty_party}"
            return f"{lon},  {lat},  {camera}"
        else:
            return f"Cannot find image object for {relfname}"

    # ...............................................
    def print_duplicates(self):
        if not self.all_data:
            self.populate_images()
        # Counts
        unique_coord_counts, wkt_by_count = self._summarize_duplicates()

        # Print bad coordinate info
        bad_coord_dict = self.all_data[ADK.UNIQUE_COORDS]["no_geo"]
        self._logger.info(f"Missing or bad coordinates:  {len(bad_coord_dict)} arroyos")
        for arr, relfnames in bad_coord_dict.items():
            self._logger.info(f"   Arroyo {arr}:")
            for fn in relfnames:
                self._logger.info(f"      {fn}")

        # Print duplicates, starting with highest number of images per wkt
        ordered_counts = list(wkt_by_count.keys())
        ordered_counts.sort(reverse=True)
        for image_count in ordered_counts:
            if image_count > 1:
                wkts = wkt_by_count[image_count]
                for wkt in wkts:
                    if wkt != "no_geo":
                        self._logger.info("")
                        self._logger.info(f"** {image_count} images with the same coordinates {wkt}")
                        for key, val in unique_coord_counts[wkt].items():
                            # key is arroyo_name
                            if not key.endswith("_count"):
                                self._logger.info(f"   arroyo: {key} has {val} images for wkt")
                                for relfname in self.all_data[ADK.UNIQUE_COORDS][wkt][key]:
                                    coords_camera = self._get_location_camera_info(relfname)
                                    self._logger.info(f"      image: {relfname}, ({coords_camera})")


    # ...............................................
    def print_summary(self):
        self._logger.info("")
        self._logger.info("Summary:")
        self._logger.info(f"   Basepath: {self.all_data[ADK.BASE_PATH]})")
        self._logger.info(f"   Arroyos: {self.all_data[ADK.ARROYO_COUNT]})")
        self._logger.info(f"   Out of range: {len(self.all_data[ADK.IMAGE_OUT_OF_RANGE])}")
        self._logger.info(f"   Images: {self.all_data[ADK.IMG_COUNT]})")
        self._logger.info(f"   In bounds: {self.all_data[ADK.IMG_GEO_COUNT]})")
        self._logger.info("Cameras:")
        for camera, count in self.all_data[ADK.UNIQUE_CAMERAS].items():
            self._logger.info(f" {camera}: {count}")


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
    def _resize_image(
            self, image, thumb_width, thumb_fname, overwrite=True):
        success = True
        thumb_base = os.path.basename(thumb_fname)
        # If no width provided, copy that as thumbnail
        if thumb_width is None:
            if ready_filename(thumb_fname, overwrite=overwrite):
                try:
                    image.save(thumb_fname)
                except Exception as e:
                    success = False
                    self._logger.info(
                        f"Failed to copy image {thumb_base} as thumbnail ({e})")
                else:
                    self._logger.info(
                        f"Copied image {thumb_base} original width {image.size[0]} as thumbnail")
        else:
            if ready_filename(thumb_fname, overwrite=overwrite):
                wpercent = (thumb_width / float(image.size[0]))
                thumb_height = int(float(image.size[1]) * float(wpercent))
                size = (thumb_width, thumb_height)
                try:
                    img = image.resize(size, Image.ANTIALIAS)
                    img.save(thumb_fname)
                except Exception as e:
                    success = False
                    self._logger.info(
                        f"Failed to copy image {thumb_base} as thumbnail ({e})")
                else:
                    self._logger.info(
                        f"Reduced image {thumb_base} width {image.size[0]} to {thumb_width}")
        return success

    # ...............................................
    def resize_images(
            self, outpath, small_width=0, medium_width=0, large_width=0, overwrite=True):
        """Resize all original images in the image_path tree.

        Args:
            outpath (str): output path
            resize_width (int): width in pixels for resized images
            overwrite (bool): flag indicating whether to rewrite existing resized images.
        """
        count = 0
        if not self.all_data:
            self.populate_images()
        for relfname, dimg in self.all_data[ADK.IMAGE_META].items():
            if dimg.dd_ok:
                # Get the width, regardless of whether writing
                try:
                    img = Image.open(dimg.fullpath)
                except Exception as e:
                    self._logger.error(f" *** Unable to open file {dimg.fullpath}, {e}")
                else:
                    (orig_w, _) = img.size

                # Rewrite the image for one size in largest width smaller than original
                thumb_fname = os.path.join(
                    outpath, f"{THUMB_DIR}", dimg.relfname)
                thumb_width = None
                for w in (large_width, medium_width, small_width):
                    if thumb_width is None and orig_w > w:
                        thumb_width = w
                # thumb_width may be None

                exists = self._resize_image(
                    img, thumb_width, thumb_fname, overwrite=overwrite)

                if exists:
                    dimg.thumb = thumb_fname[len(BASE_PATH):]
                    count += 1
        return count

# .............................................................................
# .............................................................................
# ...............................................
if __name__ == "__main__":
#     max_y = 35.45045
#     min_y = 35.43479
#     max_x = -106.05353
#     min_x = -106.07259
    max_y = 35.45
    min_y = 35.42
    max_x = -106.04
    min_x = -106.08
    dam_buffer = .00002
