"""This class represents a COSMO-SkyMed / COSMO-SkyMed Second Generation
native HDF5 product.

The entry file handed to the converter is the product .h5 file; the native
product unit is the delivery folder holding it (.h5 + DFDN delivery note +
DFAS accompanying sheet + checksum), which is what the packager stores under
measurements/.

Supported instrument modes (EOPF-EOS specialization for COSMO-SKYMED):
HIMAGE and PINGPONG (STRIPMAP), WIDEREGION and HUGEREGION (SCANSAR).

Supported processing levels / native product types:
SCS_U: Level 1A Single-look Complex Slant Unbalanced
SCS_B: Level 1A Single-look Complex Slant Balanced
DGM_B: Level 1B Detected Ground Multi-look
GEC_B: Level 1C Geocoded Ellipsoid Corrected
GTC_B: Level 1D Geocoded Terrain Corrected

All metadata comes from the HDF5 attribute tree (root attributes, the S0n beam
group and its image dataset). The DFDN / DFAS XML sidecars carry no value the
HDF5 attributes do not already hold, so they are only carried over as delivered
content. TIFF / GEOTIFF-only deliveries are NOT handled: see the known limits
in README.md.
"""
import os
import re
from typing import Optional

import h5py
import numpy as np

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.0.0'

H5_SUFFIX = ".h5"
QUICKLOOK_DATASET = "QLK"
BEAM_GROUP_RE = re.compile(r"^S\d{2}$")

# custom metadata keys (mission-local, like ICEYE's 'level')
SATELLITE_ID = 'satellite_id'
MISSION_ID = 'mission_id'
ACQUISITION_MODE = 'acquisition_mode'
NATIVE_PRODUCT_TYPE = 'native_product_type'
PROCESSED_LEVEL_CODE = 'processed_level_code'

# instrument mode: native Acquisition Mode -> operationalMode (spec Table 10)
MODE_MAP = {
    'HIMAGE': 'HIM',
    'PINGPONG': 'SPP',
    'WIDEREGION': 'SCW',
    'HUGEREGION': 'SCH',
}

# instrument mode -> product type family used by the spec type codes
# (the STRIPMAP modes share SM, the SCANSAR modes share SC)
MODE_FAMILY = {'HIM': 'SM', 'SPP': 'SM', 'SCW': 'SC', 'SCH': 'SC'}

# native product type -> EOPF-EOS processing level / processedLevel code
LEVEL_MAP = {
    'SCS_U': ('1A', 'L1A'),
    'SCS_B': ('1A', 'L1A'),
    'DGM_B': ('1B', 'L1B'),
    'GEC_B': ('1C', 'L1C'),
    'GTC_B': ('1D', 'L1D'),
}

# The ten product types the specialization allows, keyed by
# (native product type, mode family) -> typecode, 10 chars:
# L1ASMU_SCS, L1ASMB_SCS, L1BSM__DGM, L1CSM__GEC, L1DSM__GTC,
# L1ASCU_SCS, L1ASCB_SCS, L1BSC__DGM, L1CSC__GEC, L1DSC__GTC
TYPECODE_MAP = {
    ('SCS_U', 'SM'): 'L1ASMU_SCS',
    ('SCS_B', 'SM'): 'L1ASMB_SCS',
    ('DGM_B', 'SM'): 'L1BSM__DGM',
    ('GEC_B', 'SM'): 'L1CSM__GEC',
    ('GTC_B', 'SM'): 'L1DSM__GTC',
    ('SCS_U', 'SC'): 'L1ASCU_SCS',
    ('SCS_B', 'SC'): 'L1ASCB_SCS',
    ('DGM_B', 'SC'): 'L1BSC__DGM',
    ('GEC_B', 'SC'): 'L1CSC__GEC',
    ('GTC_B', 'SC'): 'L1DSC__GTC',
}

# Satellite ID -> platformShortName (spec Table 8)
SATELLITE_MAP = {
    'CSKS1': 'COSMO-SkyMed-1',
    'CSKS2': 'COSMO-SkyMed-2',
    'CSKS3': 'COSMO-SkyMed-3',
    'CSKS4': 'COSMO-SkyMed-4',
    'CSG1': 'COSMO-SkyMed Second Generation-1',
    'CSG2': 'COSMO-SkyMed Second Generation-2',
}

# Mission ID -> instrumentShortName (spec Table 9)
INSTRUMENT_MAP = {'CSK': 'SAR-2000', 'CSG': 'CSG-SAR'}

# image dataset attribute names holding the footprint corners, in ring order
CORNER_ATTRS = (
    'Top Left Geodetic Coordinates',
    'Top Right Geodetic Coordinates',
    'Bottom Right Geodetic Coordinates',
    'Bottom Left Geodetic Coordinates',
)


def decode(value):
    """HDF5 attribute value -> python str / scalar."""
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace').strip()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray) and value.size == 1:
        return decode(value.reshape(-1)[0])
    return value


def normalise_utc(value):
    """COSMO-SkyMed UTC (YYYY-MM-DD hh:mm:ss with up to nanoseconds) -> RFC
    3339 with milliseconds (YYYY-MM-DDThh:mm:ss.sssZ)."""
    if value is None:
        return None
    text = str(value).strip().replace(' ', 'T').rstrip('Z')
    match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?$", text)
    if not match:
        raise Exception("unexpected COSMO-SkyMed UTC format: '%s'" % value)
    base, frac = match.group(1), match.group(2)
    millis = (frac + "000")[:3] if frac else "000"
    return "%s.%sZ" % (base, millis)


class Product_CosmoSkymed(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        if not str(path).lower().endswith(H5_SUFFIX):
            raise Exception("not a COSMO-SkyMed HDF5 product: %s" % path)

        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.preview_path = None
        self.tmpSize = 0

        # HDF5 attribute layers, read once (the .h5 stays closed afterwards)
        self.h5_attrs = {}
        self.beam_attrs = {}
        self.image_attrs = {}
        self.beam_names = []
        self.polarisations = []
        self.image_dataset = None
        self.quicklook_dataset = None
        self._scan_h5()

        if self.debug != 0:
            print(" init class Product_CosmoSkymed")

    # -- HDF5 access ------------------------------------------------------

    def _scan_h5(self):
        with h5py.File(self.path, 'r') as fd:
            self.h5_attrs = {k: decode(v) for k, v in fd.attrs.items()}
            self.beam_names = sorted(k for k in fd.keys() if BEAM_GROUP_RE.match(k))
            if not self.beam_names:
                raise Exception("no S0n beam group in %s" % self.path)

            for name in self.beam_names:
                polarisation = decode(fd[name].attrs.get('Polarisation'))
                if polarisation is not None:
                    self.polarisations.append(str(polarisation))

            beam = fd[self.beam_names[0]]
            self.beam_attrs = {k: decode(v) for k, v in beam.attrs.items()}

            for name, obj in beam.items():
                if not isinstance(obj, h5py.Dataset):
                    continue
                if name == QUICKLOOK_DATASET:
                    self.quicklook_dataset = "%s/%s" % (self.beam_names[0], name)
                elif CORNER_ATTRS[0] in obj.attrs and self.image_dataset is None:
                    self.image_dataset = "%s/%s" % (self.beam_names[0], name)
                    self.image_attrs = {k: decode(v) for k, v in obj.attrs.items()}

            if self.image_dataset is None:
                raise Exception("no image dataset with geodetic corners in %s" % self.path)

    def attr(self, name, default=None):
        """Attribute lookup: image dataset first, then beam group, then root."""
        for layer in (self.image_attrs, self.beam_attrs, self.h5_attrs):
            if name in layer:
                return layer[name]
        return default

    def need_attr(self, name):
        value = self.attr(name)
        if value is None:
            raise Exception("missing HDF5 attribute: '%s' in %s" % (name, self.path))
        return value

    def first_attr(self, *names):
        for name in names:
            value = self.attr(name)
            if value is not None:
                return value
        raise Exception("missing HDF5 attributes %s in %s" % (list(names), self.path))

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
        """No extraction needed: the native delivery folder is already
        uncompressed. Walk it to get the delivered size the manifest reports."""
        if not os.path.exists(folder):
            raise Exception("destination folder does not exist: %s" % folder)

        self.EXTRACTED_PATH = folder
        self.contentList = []
        self.tmpSize = 0
        n = 0
        for root, dirs, files in os.walk(self.EO_FOLDER):
            for name in files:
                n += 1
                eoFile = os.path.join(root, name)
                self.contentList.append(eoFile)
                self.tmpSize += os.stat(eoFile).st_size
                if self.debug != 0:
                    print(" ## product content[%d]:'%s'" % (n, name))
        print((" #### native delivery: %d file(s), %d bytes" % (n, self.tmpSize)))

    def writeQuicklook(self, destPath):
        """Write the HDF5 quicklook (S0n/QLK) as a PNG at destPath.

        The QLK raster is stored in native acquisition orientation (see the
        Quick Look Lines/Columns Order attributes); it is written as-is, with
        no re-orientation."""
        from PIL import Image

        if self.quicklook_dataset is None:
            raise FileNotFoundError(
                "corrupt COSMO-SkyMed native product (no %s quicklook dataset in %s)"
                % (QUICKLOOK_DATASET, self.path))

        with h5py.File(self.path, 'r') as fd:
            data = fd[self.quicklook_dataset][:]

        if data.dtype != np.uint8:
            # scale to 8 bit; NaN/inf (float quicklooks) count as no signal
            data = np.nan_to_num(data.astype('float64'), nan=0.0, posinf=0.0, neginf=0.0)
            top = float(data.max())
            data = (np.zeros(data.shape, dtype=np.uint8) if top <= 0
                    else (np.clip(data / top, 0, 1) * 255).astype(np.uint8))

        Image.fromarray(data).save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### quicklook written: %s" % destPath))
        return destPath

    # -- metadata ---------------------------------------------------------

    def buildTypeCode(self, processInfo):
        native_type = str(self.need_attr('Product Type')).upper()
        native_mode = str(self.need_attr('Acquisition Mode')).upper()

        if native_mode not in MODE_MAP:
            raise Exception("unsupported COSMO-SkyMed acquisition mode: '%s'" % native_mode)
        if native_type not in LEVEL_MAP:
            raise Exception("unsupported COSMO-SkyMed product type: '%s'" % native_type)

        mode = MODE_MAP[native_mode]
        family = MODE_FAMILY[mode]
        level, level_code = LEVEL_MAP[native_type]
        typecode = TYPECODE_MAP[(native_type, family)]

        self.metadata.setMetadataPair(NATIVE_PRODUCT_TYPE, native_type)
        self.metadata.setMetadataPair(ACQUISITION_MODE, native_mode)
        self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, mode)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_LEVEL, level)
        self.metadata.setMetadataPair(PROCESSED_LEVEL_CODE, level_code)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)
        print(("TYPECODE SET TO: %s (mode %s, level %s)" % (typecode, mode, level)))

    def extractMetadata(self, met: Optional[metadata.Metadata] = None,
                        processInfo: Optional[pinfo.processInfo] = None):
        if met is None:
            raise Exception("metadata is None")

        self.metadata = met

        # sensing times
        start = normalise_utc(self.need_attr('Scene Sensing Start UTC'))
        stop = normalise_utc(self.need_attr('Scene Sensing Stop UTC'))
        met.setMetadataPair(metadata.METADATA_START_DATE_TIME, start)
        met.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, stop)
        met.setMetadataPair(metadata.METADATA_START_DATE, start.split('T')[0])
        met.setMetadataPair(metadata.METADATA_START_TIME, start.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_STOP_DATE, stop.split('T')[0])
        met.setMetadataPair(metadata.METADATA_STOP_TIME, stop.split('T')[1].rstrip('Z'))
        met.setMetadataPair(metadata.METADATA_TIME_POSITION, stop)

        # production / processing time (the native product generation)
        generation = normalise_utc(self.need_attr('Product Generation UTC'))
        met.setMetadataPair(metadata.METADATA_DATASET_PRODUCTION_DATE, generation)
        met.setMetadataPair(metadata.METADATA_PROCESSING_TIME, generation)

        # platform / instrument
        satellite = str(self.need_attr('Satellite ID')).upper()
        mission = str(self.need_attr('Mission ID')).upper()
        if satellite not in SATELLITE_MAP:
            raise Exception("unknown COSMO-SkyMed satellite id: '%s'" % satellite)
        if mission not in INSTRUMENT_MAP:
            raise Exception("unknown COSMO-SkyMed mission id: '%s'" % mission)
        met.setMetadataPair(SATELLITE_ID, satellite)
        met.setMetadataPair(MISSION_ID, mission)
        met.setMetadataPair(metadata.METADATA_SATELLITE, satellite)

        # orbit
        met.setMetadataPair(metadata.METADATA_ORBIT, int(self.need_attr('Orbit Number')))
        orbit_direction = str(self.need_attr('Orbit Direction')).upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid orbit direction: %s" % orbit_direction)
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        # polarisation: one S0n beam group per channel
        if not self.polarisations:
            raise Exception("no Polarisation attribute in %s" % self.path)
        met.setMetadataPair(metadata.METADATA_POLARISATION_MODE,
                            'S' if len(self.polarisations) == 1 else 'D')
        met.setMetadataPair(metadata.METADATA_POLARISATION_CHANNELS,
                            ",".join(self.polarisations))

        # look direction (not in the manifest; kept for the conversion log)
        met.setMetadataPair(metadata.METADATA_ANTENNA_LOOK_DIRECTION,
                            str(self.need_attr('Look Side')).upper())

        self.buildTypeCode(processInfo)

        self.refineMetadata(processInfo)
        self.extractFootprint(processInfo)

    def refineMetadata(self, processInfo):
        met = self.metadata

        # the manifest reports the delivered package size; the base pipeline
        # would fill the eoSIP size here, so mark it as ICEYE does
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

        # resolutions: ground/slant range and azimuth geometric resolution
        range_resolution = float(self.first_attr(
            'Ground Range Geometric Resolution',
            'Slant Range Geometric Resolution',
            'Ground Range Instrument Geometric Resolution'))
        azimuth_resolution = float(self.first_attr(
            'Azimuth Geometric Resolution',
            'Azimuth Instrument Geometric Resolution'))
        if range_resolution <= 0 or azimuth_resolution <= 0:
            raise Exception("invalid resolution: range=%s azimuth=%s"
                            % (range_resolution, azimuth_resolution))
        resolution = round(max(range_resolution, azimuth_resolution), 3)
        met.addLocalAttribute("rangeResolution", round(range_resolution, 3))
        met.addLocalAttribute("azimuthResolution", round(azimuth_resolution, 3))
        # single figure the spec also asks for: worst of the two directions
        met.addLocalAttribute("resolution", resolution)
        met.setMetadataPair(metadata.METADATA_RESOLUTION, resolution)

        # scene incidence angle: mean of the near/far image incidence angles
        near = float(self.need_attr('Near Incidence Angle'))
        far = float(self.need_attr('Far Incidence Angle'))
        incidence = round((near + far) / 2.0, 6)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, incidence)
        met.setMetadataPair(metadata.METADATA_MINIMUM_INCIDENCE_ANGLE, round(near, 6))
        met.setMetadataPair(metadata.METADATA_MAXIMUM_INCIDENCE_ANGLE, round(far, 6))

        # radar wavelength, rounded to the spec's discreteWavelength precision
        met.addLocalAttribute("radarWavelength",
                              round(float(self.need_attr('Radar Wavelength')), 7))

        # native data file and its media type, for the measurements link
        met.addLocalAttribute("nativeDataFile", self.origName)
        met.addLocalAttribute("measurementsMediaType", "application/vnd.hdfgroup.hdf5")

        print(("## resolution range=%s azimuth=%s; incidence=%s"
               % (range_resolution, azimuth_resolution, incidence)))

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint posList (lat lon pairs, CCW) from the image dataset
        geodetic corners."""
        coords = []
        for name in CORNER_ATTRS:
            corner = self.need_attr(name)
            coords.append(float(corner[0]))  # latitude
            coords.append(float(corner[1]))  # longitude
        # close the ring
        coords.extend(coords[0:2])

        footprint = " ".join("%s" % c for c in coords)
        print(("footprint: %s" % footprint))
        self.metadata.setMetadataPair("first-footprint", footprint)

        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        if not browseIm.getIsCCW():
            browseIm.reverseFootprint()
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())

        flat, flon = browseIm.calculateCenter()
        flat = float(flat)
        flon = float(flon)
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))

        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
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
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat_token)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon_token)

    def toString(self):
        return "path:%s" % self.path

    def dump(self):
        print(self.toString())
