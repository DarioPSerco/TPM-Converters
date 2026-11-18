"""This class represents an IRS-P5 (Cartosat-1) or IRS-P6 (ResourceSat-1
LISS-III) native product.

The entry file is the one the cfg [Search] patterns select, one per native
delivery; layouts, names and the metadata read: see cartosat_files.py and
test/fixtures/SYNTHETIC_FIXTURE_NOTE.md.

Product types ("EOPF-EOS Specialization for IRS-P5 (Cartosat-1) products"
1.0, Tables 1, 2; applied to IRS-P6 as well):

IR5 L3_ORT_PAN: Euro-Maps orthoimage(s), PAN, 2.5 m        entry <delivery>_oid.txt
IR5 L3_DSM____: Euro-Maps 3D DSM tile, STER, 2.5 m         entry em3d_..._dsm.tif
IR6 L3_ORT_PAN: IRS-P6 LISS-III orthoimage, PAN, 20 m      entry metadata.xml

Where each value comes from:
- IR5 ortho: every EM_Ortho_Image_<n>/*_metadata.xml gives one
  acquisitionParameters entry: times and orbit from DATASET_NAME (orbit
  checked against Orbit_no), sun angles from Sun_azimuth / Sun_elevation,
  orbit direction from the local solar time (no native value);
  processingDate from DATASET_PRODUCTION_DATE; footprint from the
  *_imagery.tif GeoTIFF corners (EPSG:3035) turned to lon/lat; overview
  from <delivery>_ql.tif.
- IR5 DSM: footprint, CRS and overview from the GeoTIFF layers. The tile
  carries no sensing time, orbit number or orbit direction (it merges
  several acquisitions): beginningDateTime =
  endingDateTime = processingDate = the em3d name date at 00:00:00 (a
  production date - the only date of the tile; Table 11 sets
  endingDateTime to beginningDateTime when not available), orbitDirection
  DESCENDING (Cartosat-1 acquires in daylight only, on the descending pass),
  orbitNumber (Table 12, mandatory) the cfg METADATA_ORBIT value, with a
  warning. All tiles of a delivery date share the package name
  times: the <bbvv> counter keeps them apart (name_registry).
- IR6 ortho: times and orbit from DATASET_NAME, processingDate from
  DATASET_PRODUCTION_DATE, CRS from PROJECTION (CS -> EPSG:3909); sun
  angles, orbit direction (satellite heading) and footprint (scene corners)
  from the <scene>_ssd.txt; overview from imagery.bil (NIR, red, green).
"""
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.product_directory import Product_Directory

from cartosat_json import cartosat_files as F

__version__ = '1.0.0'

# custom metadata keys (mission-local)
PLATFORM_SHORT_NAME = 'platform_short_name'
INSTRUMENT_SHORT_NAME = 'instrument_short_name'
PROCESSED_LEVEL_CODE = 'processed_level_code'
CREATION_TIME = 'creation_time'

# <MMM> -> (platformShortName (Table 8, extended to IRS-P6), <MMM>
# platform id); <MMM> = 'IR' + platform id
PLATFORMS = {"IR5": ("IRS-P5", "5"), "IR6": ("IRS-P6", "6")}

# instrumentShortName (Table 9) for every product type
INSTRUMENT = "PAN"

# layout -> (product type, operationalMode) (Tables 1, 2; IRS-P6
# orthoimages are L3_ORT_PAN / PAN)
PRODUCT_TYPES = {
    F.ORTHO_P5: ("L3_ORT_PAN", "PAN"),
    F.DSM_P5: ("L3_DSM____", "STER"),
    F.ORTHO_P6: ("L3_ORT_PAN", "PAN"),
}
PROCESSING_LEVEL = "3"      # Table 16
PROCESSED_LEVEL_CODE_L3 = "L3"  # Table 17

# resolution in metres per platform: Table 10 fixed value for IRS-P5, the
# LISS-III orthoimage pixel size for IRS-P6
RESOLUTIONS = {"IR5": 2.5, "IR6": 20.0}

# wavelengths in metres per platform, grouped by spectralRange: Table 14
# for IRS-P5, the four LISS-III bands for IRS-P6
WAVELENGTHS = {
    "IR5": [("VNIR", [(500e-9, 850e-9)])],
    "IR6": [("VIS", [(520e-9, 590e-9), (620e-9, 680e-9)]),
            ("NIR", [(770e-9, 860e-9)]),
            ("SWIR", [(1550e-9, 1700e-9)])],
}

# measurements link media type per layout (Table 19); the IRS-P6 link is
# its metadata.xml, the whole delivery being in measurements/
MEDIA_TYPES = {F.ORTHO_P5: "image/tiff", F.DSM_P5: "image/tiff", F.ORTHO_P6: "application/xml"}

# DSM orbit direction: Cartosat-1 acquires in daylight only, on the
# descending pass of its sun-synchronous orbit
DSM_ORBIT_DIRECTION = "DESCENDING"

# zero-based (red, green, blue) band indices of the IRS-P6 overview: the
# LISS-III bands are green, red, NIR, SWIR - false colour NIR / red / green
P6_OVERVIEW_BANDS = (2, 1, 0)

OVERVIEW_MAX_SIZE = 1000


# -- image helpers ----------------------------------------------------------

def _read_reduced(path, max_size=OVERVIEW_MAX_SIZE * 2):
    """GeoTIFF as (rows, cols, bands), decimated so its long side is at most
    about max_size (the overview needs no more), and its no-data value
    (GDAL_NODATA tag) or None."""
    import tifffile
    with tifffile.TiffFile(path) as tf:
        tag = tf.pages[0].tags.get("GDAL_NODATA")
        data = tf.asarray()
    nodata = float(str(tag.value).strip("\x00 ")) if tag is not None else None
    if data.ndim == 2:
        data = data[:, :, np.newaxis]
    elif data.ndim == 3 and data.shape[0] < data.shape[-1] and data.shape[0] <= 8:
        data = np.moveaxis(data, 0, -1)  # planar (bands, rows, cols)
    step = max(1, int(np.ceil(max(data.shape[:2]) / float(max_size))))
    return data[::step, ::step, :], nodata


def _read_bil_reduced(path, header, max_size=OVERVIEW_MAX_SIZE * 2):
    """8-bit BIL image as (rows, cols, bands), decimated like _read_reduced."""
    rows, cols = int(header["NROWS"]), int(header["NCOLS"])
    bands, bits = int(header["NBANDS"]), int(header.get("NBITS", 8))
    if bits != 8 or int(header.get("SKIPBYTES", 0)) != 0:
        raise Exception("unsupported BIL layout (NBITS %s, SKIPBYTES %s): %s"
                        % (bits, header.get("SKIPBYTES"), path))
    if os.path.getsize(path) != rows * cols * bands:
        raise Exception("BIL size %d does not match %dx%dx%d: %s"
                        % (os.path.getsize(path), rows, cols, bands, path))
    data = np.memmap(path, dtype=np.uint8, mode="r", shape=(rows, bands, cols))
    step = max(1, int(np.ceil(max(rows, cols) / float(max_size))))
    return np.moveaxis(np.array(data[::step, :, ::step]), 1, -1)


def _stretch(band, valid):
    values = band[valid]
    out = np.zeros(band.shape, dtype=np.uint8)
    if values.size == 0:
        return out
    low, high = np.percentile(values, (2.0, 98.0))
    if high <= low:
        high = low + 1.0
    return (np.clip((band - low) / (high - low), 0, 1) * 255).astype(np.uint8)


def wavelengths(mmm):
    """Spectral ranges of the platform: outer bounds per range, band means
    as discreteWavelengths."""
    return [{
        "spectralRange": spectral_range,
        "startWavelength": min(b[0] for b in bands),
        "endWavelength": max(b[1] for b in bands),
        "discreteWavelengths": [round((b[0] + b[1]) / 2, 12) for b in bands],
    } for spectral_range, bands in WAVELENGTHS[mmm]]


class Product_Cartosat(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        self.kind, self.EO_FOLDER = F.layout(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.files = F.product_files(self.path)
        self.mmm = "IR6" if self.kind == F.ORTHO_P6 else "IR5"
        # lineage source citation, which run_mission.py and the packager use
        # to find the delivery again: the entry file; every IRS-P6 delivery
        # has the same metadata.xml, so it is cited with its folder:
        # <delivery folder>/metadata.xml
        name = os.path.basename(self.path)
        self.nativeFileName = "%s/%s" % (self.productFolderName, name) if self.kind == F.ORTHO_P6 else name
        self.preview_path = None
        self.tmpSize = 0
        self.typecode = None
        if self.debug != 0:
            print(" init class Product_Cartosat (%s, %s)" % (name, self.kind))

    # -- product lifecycle ------------------------------------------------

    def afterProductDone(self):
        pass

    def getMetadataInfo(self):
        pass

    # JSON-only mode: the base ingester browse stage is disabled; the preview
    # PNG is written next to the manifest by writeQuicklook().
    def makeBrowses(self, processInfo):
        pass

    def extractToPath(self, folder=None, dont_extract=False):
        """No extraction to disk is needed. Sum the size of the delivery
        files, which is what lands in measurements/."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)
        self.EXTRACTED_PATH = folder
        self.contentList = list(self.files)
        self.tmpSize = sum(os.stat(f).st_size for f in self.files)
        print((" #### native delivery %s: %d file(s), %d bytes"
               % (self.productFolderName, len(self.files), self.tmpSize)))

    def _relative(self, path):
        return os.path.relpath(path, self.EO_FOLDER).replace(os.sep, "/")

    def measurement_href(self):
        """Path of the measurements link target inside measurements/ (the
        delivery is packaged with its layout kept): the first orthoimage,
        the DSM layer, or the IRS-P6 metadata.xml."""
        if self.kind == F.ORTHO_P5:
            return self._relative(F.ortho_images(self.EO_FOLDER)[0]["image"])
        return self._relative(self.path)

    def writeQuicklook(self, destPath):
        """Write the overview PNG at destPath, 2-98 percentile stretch,
        no-data pixels transparent: IR5 ortho from <delivery>_ql.tif (else
        the first orthoimage), grey; DSM from the dsm layer, grey; IR6 from
        imagery.bil, false colour NIR / red / green."""
        from PIL import Image

        if self.kind == F.ORTHO_P6:
            parts = F.p6_parts(self.EO_FOLDER)
            source = parts["image"]
            data = _read_bil_reduced(source, F.parse_bil_header(parts["header"]))
            planes = [data[:, :, i].astype("float64") for i in P6_OVERVIEW_BANDS]
            valid = np.any(data > 0, axis=-1)
        else:
            if self.kind == F.ORTHO_P5:
                source = F.ortho_quicklook(self.path) or F.ortho_images(self.EO_FOLDER)[0]["image"]
            else:
                source = self.path
            data, nodata = _read_reduced(source)
            grey = data[:, :, 0].astype("float64")
            valid = grey != (nodata if nodata is not None else 0)
            planes = [grey, grey, grey]
        rgb = np.dstack([_stretch(p, valid) for p in planes])
        alpha = np.where(valid, 255, 0).astype(np.uint8)
        image = Image.fromarray(np.dstack([rgb, alpha]))
        image.thumbnail((OVERVIEW_MAX_SIZE, OVERVIEW_MAX_SIZE), Image.Resampling.LANCZOS)
        image.save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### overview written: %s (from %s)" % (destPath, os.path.basename(source))))
        return destPath

    # -- metadata ---------------------------------------------------------

    def buildTypeCode(self, processInfo):
        self.typecode, mode = PRODUCT_TYPES[self.kind]
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, self.typecode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, PROCESSING_LEVEL)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, PROCESSED_LEVEL_CODE_L3)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        print(("TYPECODE SET TO: %s" % self.typecode))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")
        self.metadata = met

        # platform (Tables 1, 8, 9): <MMM> = IR + platform id
        platform, platform_id = PLATFORMS[self.mmm]
        met.setMetadataPair(PLATFORM_SHORT_NAME, platform)
        met.setMetadataPair(INSTRUMENT_SHORT_NAME, INSTRUMENT)
        met.setMetadataPair(metadata.METADATA_PLATFORM, platform)
        met.setMetadataPair(metadata.METADATA_PLATFORM_2DIGITS_ALIAS, "IR")
        met.setMetadataPair(metadata.METADATA_PLATFORM_ID, platform_id)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT, INSTRUMENT)
        self.buildTypeCode(processInfo)

        if self.kind == F.ORTHO_P5:
            components, processed, ring, epsg = self._ortho_p5()
        elif self.kind == F.DSM_P5:
            components, processed, ring, epsg = self._dsm_p5()
        else:
            components, processed, ring, epsg = self._ortho_p6()

        # sensing times (Table 11): the outer bounds of the components
        start = min(c["begin"] for c in components)
        stop = max(c["end"] for c in components)
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)
        met.setMetadataPair(metadata.METADATA_ORBIT, components[0]["orbitNumber"])
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, components[0]["orbitDirection"])

        # native processing date (Table 16), package creation date (Table 6): now
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, processed)
        now = datetime.now(timezone.utc)
        created = now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (now.microsecond // 1000)
        met.setMetadataPair(CREATION_TIME, created)
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, created)

        # the manifest reports the native product size; the base pipeline would
        # fill the eoSIP size here, so mark it as not set
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)
        met.addLocalAttribute("components", components)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, components[0]["resolution"])
        met.addLocalAttribute("referenceSystemIdentifier", F.crs_uri(epsg))
        met.addLocalAttribute("nativeDataFile", self.measurement_href())
        met.addLocalAttribute("measurementsMediaType", MEDIA_TYPES[self.kind])
        self._set_footprint(ring)

    def _component(self, begin, end, orbit, direction, angles):
        return {
            "mode": PRODUCT_TYPES[self.kind][1],
            "begin": begin,
            "end": end,
            "resolution": RESOLUTIONS[self.mmm],
            "orbitNumber": orbit,
            "orbitDirection": direction,
            "angles": angles,
            "wavelengths": wavelengths(self.mmm),
        }

    def _ortho_p5(self):
        """IR5 L3_ORT_PAN: one component per EM_Ortho_Image_<n>."""
        components, corners, epsg, processed = [], [], None, None
        for image in F.ortho_images(self.EO_FOLDER):
            meta = F.parse_em_xml(image["metadata"])
            where = os.path.basename(image["metadata"])
            if meta["mission"] != "IR05" or (meta["sensor"] or "").upper() != "PAN":
                raise Exception("not an IRS-P5 PAN orthoimage (DATASET_MISSION %s, DATASET_SENSOR %s): %s"
                                % (meta["mission"], meta["sensor"], where))
            name = F.dataset_name(meta["dataset_name"])
            if name["mission"] != "IR05":
                raise Exception("DATASET_NAME mission %s is not IR05: %s" % (name["mission"], where))
            begin, end = F.name_utc(name["start"]), F.name_utc(name["stop"])
            if end < begin:
                raise Exception("DATASET_NAME stop before start: %s" % where)
            orbit = name["orbit"]
            native_orbit = meta["acquisition"].get("Orbit_no")
            if isinstance(native_orbit, float) and int(native_orbit) != orbit:
                raise Exception("orbit of DATASET_NAME (%d) and Orbit_no (%d) differ: %s"
                                % (orbit, int(native_orbit), where))
            angles = {}
            for key, code in (("illuminationAzimuthAngle", "Sun_azimuth"),
                              ("illuminationElevationAngle", "Sun_elevation")):
                value = meta["acquisition"].get(code)
                if not isinstance(value, float):
                    # acquisitionAngles are mandatory for L3_ORT_PAN (Table 10)
                    raise Exception("no %s in %s (mandatory for L3_ORT_PAN)" % (code, where))
                angles[key] = value
            if processed is None:
                if not meta["production_date"]:
                    raise Exception("no DATASET_PRODUCTION_DATE in %s" % where)
                processed = F.date_utc(meta["production_date"])
            georef = F.geotiff_georef(image["image"])
            if epsg is not None and georef["epsg"] != epsg:
                raise Exception("orthoimages of %s in different CRS" % self.productFolderName)
            epsg = georef["epsg"]
            image_corners = F.raster_corners(georef)
            corners.extend(image_corners)
            # no native orbit direction: the local solar time at the image centre
            centre = F.lonlat_ring(image_corners, epsg)
            lon = sum(p[0] for p in centre) / len(centre)
            components.append(self._component(begin, end, orbit, F.daylight_direction(begin, lon), angles))
        # one image: its corners; several: the rectangle around all of them
        if len(components) > 1:
            xs, ys = [c[0] for c in corners], [c[1] for c in corners]
            corners = [(min(xs), max(ys)), (max(xs), max(ys)), (max(xs), min(ys)), (min(xs), min(ys))]
        return components, processed, F.lonlat_ring(corners, epsg), epsg

    def _dsm_p5(self):
        """IR5 L3_DSM____: one component from the tile layers; times from the
        em3d name date, orbit direction DESCENDING, orbit number from the cfg
        (see the module docstring)."""
        layers = F.dsm_layers(self.path)
        georef = F.geotiff_georef(layers["dsm"])
        ring = F.lonlat_ring(F.raster_corners(georef), georef["epsg"])
        day = F.date_utc(F.dsm_name(self.path)["date"])
        component = self._component(day, day, self._cfg_orbit(), DSM_ORBIT_DIRECTION, {})
        return [component], day, ring, georef["epsg"]

    def _cfg_orbit(self):
        """Orbit number for a product that carries none: the cfg
        [Mission-specific-values] METADATA_ORBIT."""
        number = self.metadata.getMetadataValue(metadata.METADATA_ORBIT)
        if not self.metadata.valueExists(number):
            raise Exception("no orbit number in the product, and none in the cfg")
        print(" WARNING: no orbit number in %s: cfg value used (%s)" % (os.path.basename(self.path), number))
        return int(number)

    def _ortho_p6(self):
        """IR6 orthoimage: metadata.xml plus the <scene>_ssd.txt."""
        parts = F.p6_parts(self.EO_FOLDER)
        meta = F.parse_em_xml(parts["metadata"])
        name = F.dataset_name(meta["dataset_name"])
        if name["mission"] != "IR06":
            raise Exception("DATASET_NAME mission %s is not IR06: %s" % (name["mission"], self.path))
        begin, end = F.name_utc(name["start"]), F.name_utc(name["stop"])
        if end < begin:
            raise Exception("DATASET_NAME stop before start: %s" % self.path)
        if not meta["production_date"]:
            raise Exception("no DATASET_PRODUCTION_DATE in %s" % self.path)
        ssd = F.parse_ssd(parts["ssd"])
        where = os.path.basename(parts["ssd"])
        if "orbit" in ssd and int(ssd["orbit"]) != name["orbit"]:
            raise Exception("orbit of DATASET_NAME (%d) and %s (%d) differ"
                            % (name["orbit"], where, int(ssd["orbit"])))
        angles = {}
        for key, field in (("illuminationAzimuthAngle", "sun_azimuth"),
                           ("illuminationElevationAngle", "sun_elevation")):
            if field not in ssd:
                raise Exception("no %s in %s (mandatory for L3_ORT_PAN)" % (field, where))
            angles[key] = ssd[field]
        component = self._component(begin, end, name["orbit"], F.heading_direction(ssd.get("heading")), angles)
        return [component], F.date_utc(meta["production_date"]), F.ssd_ring(ssd), F.p6_epsg(meta)

    def extractQuality(self, helper, met):
        pass

    def _set_footprint(self, ring):
        """Footprint ring closed and counter-clockwise as RFC 7946 wants."""
        ring = [list(p) for p in ring]
        ring.append(list(ring[0]))
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
        if area < 0:
            ring.reverse()
        self.metadata.addLocalAttribute("footprintRing", ring)
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT,
                                      " ".join("%s %s" % (p[1], p[0]) for p in ring))

        flat = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
        flon = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))
        if flat < 0:
            flat_token = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat_token = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon_token = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon_token = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat_token)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon_token)

    def toString(self):
        return "path:%s" % self.path

    def dump(self):
        print(self.toString())
