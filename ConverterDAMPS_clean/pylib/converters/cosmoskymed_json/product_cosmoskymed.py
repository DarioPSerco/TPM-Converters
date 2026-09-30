"""This class represents a COSMO-SkyMed / COSMO-SkyMed Second Generation
native product.

Two delivery formats are handled, both driven by the same attribute names:

- **HDF5**: the entry file is the product `.h5`; metadata comes from its
  attribute tree (root + `S0n` beam group + image dataset) and the overview
  from the `S0n/QLK` dataset.
- **GeoTIFF in a `.tgz`**: the entry file is the delivery `.tgz`; it holds
  `<name>.MBI.tif` / `<name>.SBI.tif` (+ `.tfw`), `<name>.QLK.tif` and
  `<name>.attribs.xml`, the XML dump of the very same HDF5 attribute tree.
  Metadata comes from that XML and the overview from the QLK GeoTIFF.

In both cases the native product unit is the delivery folder holding the entry
file (entry + DFDN delivery note + DFAS accompanying sheet + checksum), which
is what the packager stores under measurements/ - uncompressed, as the
specialization requires.

Supported instrument modes (EOPF-EOS specialization for COSMO-SKYMED):
HIMAGE and PINGPONG (STRIPMAP), WIDEREGION and HUGEREGION (SCANSAR).

Supported processing levels / native product types:
SCS_U: Level 1A Single-look Complex Slant Unbalanced
SCS_B: Level 1A Single-look Complex Slant Balanced
DGM_B: Level 1B Detected Ground Multi-look
GEC_B: Level 1C Geocoded Ellipsoid Corrected
GTC_B: Level 1D Geocoded Terrain Corrected

The DFDN / DFAS XML sidecars carry no value the product attributes do not
already hold, so they are only carried over as delivered content.
"""
import os
import re
import tarfile
from typing import Optional

import numpy as np
from lxml import etree

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.esaProducts import formatUtils, metadata, product_EOSIP
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product_directory import Product_Directory

__version__ = '1.1.0'

H5_SUFFIX = ".h5"
TGZ_SUFFIXES = (".tgz", ".tar.gz")
QUICKLOOK_DATASET = "QLK"
IMAGE_DATASETS = ("MBI", "SBI")
BEAM_GROUP_RE = re.compile(r"^S\d{2}$")

FORMAT_HDF5 = "HDF5"
FORMAT_GEOTIFF = "GEOTIFF"

MEDIA_TYPES = {".h5": "application/vnd.hdfgroup.hdf5",
               ".tif": "image/tiff",
               ".tiff": "image/tiff"}

# custom metadata keys (mission-local, like ICEYE's 'level')
SATELLITE_ID = 'satellite_id'
MISSION_ID = 'mission_id'
ACQUISITION_MODE = 'acquisition_mode'
NATIVE_PRODUCT_TYPE = 'native_product_type'
NATIVE_FORMAT = 'native_format'
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


def as_floats(value):
    """Attribute value -> list of floats, from either backend (numpy array
    from HDF5, blank-separated text from the attribute XML dump)."""
    if isinstance(value, (list, tuple, np.ndarray)):
        return [float(v) for v in np.asarray(value).reshape(-1)]
    return [float(tok) for tok in str(value).split()]


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


def is_tgz(path):
    lowered = str(path).lower()
    return any(lowered.endswith(suffix) for suffix in TGZ_SUFFIXES)


def media_type_of(filename):
    ext = os.path.splitext(str(filename).lower())[1]
    if ext not in MEDIA_TYPES:
        raise Exception("no media type known for: %s" % filename)
    return MEDIA_TYPES[ext]


def tar_members(tgz_path):
    """[(archive member name, size)] of the regular files in the delivery."""
    with tarfile.open(tgz_path, "r:gz") as tf:
        return [(m.name, m.size) for m in tf.getmembers() if m.isfile()]


class Product_CosmoSkymed(Product_Directory):

    def __init__(self, path=None):
        super().__init__(path)
        lowered = str(self.path).lower()
        if lowered.endswith(H5_SUFFIX):
            self.native_format = FORMAT_HDF5
        elif is_tgz(lowered):
            self.native_format = FORMAT_GEOTIFF
        else:
            raise Exception("not a COSMO-SkyMed native product (.h5 / .tgz): %s" % path)

        self.EO_FOLDER = os.path.dirname(self.path)
        self.productFolderName = os.path.basename(self.EO_FOLDER)
        self.preview_path = None
        self.tmpSize = 0

        # attribute layers, read once, same names in both backends
        self.root_attrs = {}
        self.beam_attrs = {}
        self.image_attrs = {}
        self.beam_names = []
        self.polarisations = []
        self.image_dataset = None
        self.quicklook_dataset = None
        # GeoTIFF delivery only: member names inside the .tgz
        self.members = []
        self.image_file = None
        self.quicklook_file = None

        if self.native_format == FORMAT_HDF5:
            self._scan_hdf5()
        else:
            self._scan_tgz()

        if self.debug != 0:
            print(" init class Product_CosmoSkymed (%s)" % self.native_format)

    # -- HDF5 backend -----------------------------------------------------

    def _scan_hdf5(self):
        import h5py

        with h5py.File(self.path, 'r') as fd:
            self.root_attrs = {k: decode(v) for k, v in fd.attrs.items()}
            self.beam_names = sorted(k for k in fd.keys() if BEAM_GROUP_RE.match(k))
            if not self.beam_names:
                raise Exception("no S0n beam group in %s" % self.path)

            for name in self.beam_names:
                polarisation = decode(fd[name].attrs.get('Polarisation'))
                if polarisation is not None:
                    self._add_polarisation(str(polarisation))

            beam = fd[self.beam_names[0]]
            self.beam_attrs = {k: decode(v) for k, v in beam.attrs.items()}

            # the image and quicklook datasets sit under the beam group
            # (slant / ground range products) or at the root (geocoded ones)
            for holder in (beam, fd):
                for name, obj in holder.items():
                    if not isinstance(obj, h5py.Dataset):
                        continue
                    if name == QUICKLOOK_DATASET and self.quicklook_dataset is None:
                        self.quicklook_dataset = obj.name
                    elif CORNER_ATTRS[0] in obj.attrs and self.image_dataset is None:
                        self.image_dataset = obj.name
                        self.image_attrs = {k: decode(v) for k, v in obj.attrs.items()}

            if self.image_dataset is None:
                raise Exception("no image dataset with geodetic corners in %s" % self.path)

        self.image_file = self.origName

    # -- GeoTIFF (.tgz) backend -------------------------------------------

    def _scan_tgz(self):
        attribs_xml = None
        with tarfile.open(self.path, "r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                self.members.append((name, member.size))
                base = os.path.basename(name).lower()
                if base.endswith(".attribs.xml"):
                    attribs_xml = tf.extractfile(member).read()
                elif base.endswith(".qlk.tif") or base.endswith(".qlk.tiff"):
                    self.quicklook_file = name
                elif any(base.endswith("%s.tif" % d.lower()) or base.endswith("%s.tiff" % d.lower())
                         for d in IMAGE_DATASETS):
                    if self.image_file is None:
                        self.image_file = name

        if attribs_xml is None:
            raise Exception("no <name>.attribs.xml in %s" % self.path)
        if self.image_file is None:
            raise Exception("no MBI / SBI image file in %s" % self.path)

        self._read_attribs_xml(attribs_xml)
        self.image_file = os.path.basename(self.image_file)

    def _read_attribs_xml(self, data):
        """Parse <name>.attribs.xml: the HDF5 attribute tree as XML, with
        <_ROOT_>, the S0n beam groups and the image / quicklook datasets."""
        root = etree.fromstring(data)

        def attrs_of(node):
            return {a.get("Name"): (a.text or "").strip()
                    for a in node if a.tag == "Attribute"}

        root_node = root.find("_ROOT_")
        if root_node is None:
            raise Exception("no <_ROOT_> group in the attribute XML of %s" % self.path)
        self.root_attrs = attrs_of(root_node)

        beams = [node for node in root if BEAM_GROUP_RE.match(str(node.tag))]
        if not beams:
            raise Exception("no S0n beam group in the attribute XML of %s" % self.path)
        self.beam_names = [str(node.tag) for node in beams]
        for node in beams:
            polarisation = attrs_of(node).get('Polarisation')
            if polarisation:
                self._add_polarisation(polarisation)
        self.beam_attrs = attrs_of(beams[0])

        for node in root.iter():
            tag = str(node.tag)
            if tag == QUICKLOOK_DATASET and self.quicklook_dataset is None:
                self.quicklook_dataset = tag
            elif tag in IMAGE_DATASETS and self.image_dataset is None:
                candidate = attrs_of(node)
                if CORNER_ATTRS[0] in candidate:
                    self.image_dataset = tag
                    self.image_attrs = candidate

        if self.image_dataset is None:
            raise Exception("no image dataset with geodetic corners in the "
                            "attribute XML of %s" % self.path)

    # -- attribute access -------------------------------------------------

    def _add_polarisation(self, polarisation):
        """One channel per DISTINCT polarisation: a ScanSAR product has one
        S0n group per subswath, all with the same polarisation."""
        polarisation = str(polarisation).strip()
        if polarisation and polarisation not in self.polarisations:
            self.polarisations.append(polarisation)

    def attr(self, name, default=None):
        """Attribute lookup: image dataset first, then beam group, then root."""
        for layer in (self.image_attrs, self.beam_attrs, self.root_attrs):
            if name in layer:
                return layer[name]
        return default

    def need_attr(self, name):
        value = self.attr(name)
        if value is None:
            raise Exception("missing attribute: '%s' in %s" % (name, self.path))
        return value

    def first_attr(self, *names):
        for name in names:
            value = self.attr(name)
            if value is not None:
                return value
        raise Exception("missing attributes %s in %s" % (list(names), self.path))

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
        """No extraction to disk is needed: the manifest values are already
        read. Walk the delivery to get the size the manifest reports - for a
        .tgz delivery, the size its content takes once uncompressed, which is
        what lands in measurements/."""
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
                if is_tgz(name):
                    for member, size in (self.members or tar_members(eoFile)):
                        self.tmpSize += size
                else:
                    self.tmpSize += os.stat(eoFile).st_size
                if self.debug != 0:
                    print(" ## product content[%d]:'%s'" % (n, name))
        print((" #### native delivery: %d file(s), %d bytes uncompressed"
               % (n, self.tmpSize)))

    def writeQuicklook(self, destPath):
        """Write the native quicklook as a PNG at destPath: the `S0n/QLK`
        HDF5 dataset, or the `<name>.QLK.tif` member of the .tgz delivery.

        The quicklook keeps its native orientation (see the 'Quick Look
        Lines/Columns Order' attributes); it is written as-is, with no
        re-orientation."""
        from PIL import Image

        if self.native_format == FORMAT_HDF5:
            import h5py

            if self.quicklook_dataset is None:
                raise FileNotFoundError(
                    "corrupt COSMO-SkyMed native product (no %s quicklook dataset in %s)"
                    % (QUICKLOOK_DATASET, self.path))
            with h5py.File(self.path, 'r') as fd:
                data = fd[self.quicklook_dataset][:]
            image = Image.fromarray(self._to_uint8(data))
        else:
            if self.quicklook_file is None:
                raise FileNotFoundError(
                    "corrupt COSMO-SkyMed native product (no QLK GeoTIFF in %s)"
                    % self.path)
            with tarfile.open(self.path, "r:gz") as tf:
                with tf.extractfile(self.quicklook_file) as fd:
                    image = Image.open(fd)
                    image.load()
            if image.mode not in ("L", "RGB"):
                image = Image.fromarray(self._to_uint8(np.asarray(image)))

        image.save(destPath, "PNG")
        self.preview_path = destPath
        print((" #### quicklook written: %s" % destPath))
        return destPath

    @staticmethod
    def _to_uint8(data):
        data = np.asarray(data)
        if data.dtype == np.uint8:
            return data
        # scale to 8 bit; NaN/inf (float quicklooks) count as no signal
        data = np.nan_to_num(data.astype('float64'), nan=0.0, posinf=0.0, neginf=0.0)
        top = float(data.max())
        if top <= 0:
            return np.zeros(data.shape, dtype=np.uint8)
        return (np.clip(data / top, 0, 1) * 255).astype(np.uint8)

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
        met.setMetadataPair(NATIVE_FORMAT, self.native_format)

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
        met.setMetadataPair(metadata.METADATA_ORBIT, int(str(self.need_attr('Orbit Number')).strip()))
        orbit_direction = str(self.need_attr('Orbit Direction')).upper()
        if orbit_direction not in ('ASCENDING', 'DESCENDING'):
            raise Exception("invalid orbit direction: %s" % orbit_direction)
        met.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, orbit_direction)

        # polarisation: one channel per distinct S0n Polarisation
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
        range_resolution = as_floats(self.first_attr(
            'Ground Range Geometric Resolution',
            'Slant Range Geometric Resolution',
            'Ground Range Instrument Geometric Resolution'))[0]
        azimuth_resolution = as_floats(self.first_attr(
            'Azimuth Geometric Resolution',
            'Azimuth Instrument Geometric Resolution'))[0]
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
        near = as_floats(self.need_attr('Near Incidence Angle'))[0]
        far = as_floats(self.need_attr('Far Incidence Angle'))[0]
        incidence = round((near + far) / 2.0, 6)
        met.setMetadataPair(metadata.METADATA_INSTRUMENT_INCIDENCE_ANGLE, incidence)
        met.setMetadataPair(metadata.METADATA_MINIMUM_INCIDENCE_ANGLE, round(near, 6))
        met.setMetadataPair(metadata.METADATA_MAXIMUM_INCIDENCE_ANGLE, round(far, 6))

        # radar wavelength, rounded to the spec's discreteWavelength precision
        met.addLocalAttribute("radarWavelength",
                              round(as_floats(self.need_attr('Radar Wavelength'))[0], 7))

        # the measurements link points at the image file, as it lands in
        # measurements/ (the .h5 itself, or the GeoTIFF out of the .tgz)
        met.addLocalAttribute("nativeDataFile", self.image_file)
        met.addLocalAttribute("measurementsMediaType", media_type_of(self.image_file))

        print(("## resolution range=%s azimuth=%s; incidence=%s"
               % (range_resolution, azimuth_resolution, incidence)))

    def extractQuality(self, helper, met):
        pass

    def extractFootprint(self, processInfo):
        """Footprint posList (lat lon pairs, CCW) from the image dataset
        geodetic corners."""
        coords = []
        for name in CORNER_ATTRS:
            corner = as_floats(self.need_attr(name))
            coords.append(corner[0])  # latitude
            coords.append(corner[1])  # longitude
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
