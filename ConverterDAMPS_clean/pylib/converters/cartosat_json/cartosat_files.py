"""IRS-P5 (Cartosat-1) and IRS-P6 native product layout: deliveries, names,
metadata, georeferencing.

Pure helpers with no eoSip_converter import, shared by the product class and
the packager (the packager must not pull in eoSip_converter and its xml_nodes
PYTHONPATH requirement).

Native layouts handled (the specialization does not describe them, see
test/fixtures/SYNTHETIC_FIXTURE_NOTE.md); the entry file is the one the cfg
[Search] patterns select, one per delivery:

- IRS-P5 ortho (L3_ORT_PAN), Euro-Maps delivery <delivery>/:
    <delivery>_oid.txt              order references - the entry
    <delivery>_ql.tif (+ .tfw)      16-bit quicklook GeoTIFF
    EM_Ortho_Image_<n>/<...>_imagery.tif + <...>_metadata.xml
  one or more images, all converted in the same package.
- IRS-P5 DSM (L3_DSM____), Euro-Maps 3D tile <tile>/:
    p5bproductformatter/em3d_<id>_<yyyymmdd>_<tile>_<layer>.tif
  layers dsm (the entry), acv, num, qc, src; no metadata file.
- IRS-P6 ortho, flat delivery (unpacked into <zip stem>/):
    metadata.xml (the entry), imagery.bil + .hdr + .blw, geolayer.bil,
    calib.dat, <scene>_ssd.txt (Euromap dump of the source scene).
"""
import math
import os
import re
import xml.etree.ElementTree as ET

ORTHO_P5 = "IR5_ORT"
DSM_P5 = "IR5_DSM"
ORTHO_P6 = "IR6_ORT"

# native mission token (DATASET_MISSION / DATASET_NAME prefix) -> <MMM>
MISSIONS = {"IR05": "IR5", "IR06": "IR6"}

OID_RE = re.compile(r"^(?P<delivery>.+)_oid\.txt$", re.IGNORECASE)
ORTHO_DIR_RE = re.compile(r"^EM_Ortho_Image_(?P<n>\d+)$", re.IGNORECASE)
DSM_FOLDER = "p5bproductformatter"
DSM_RE = re.compile(
    r"^em3d_(?P<id>\d+)_(?P<date>\d{8})_(?P<tile>[0-9A-Z]+)_(?P<layer>acv|dsm|num|qc|src)\.tif$",
    re.IGNORECASE)
DSM_LAYERS = ("dsm", "acv", "num", "qc", "src")
P6_ENTRY = "metadata.xml"
P6_IMAGE = "imagery.bil"
P6_HEADER = "imagery.hdr"
SSD_SUFFIX = "_ssd.txt"

# Euro-Maps DATASET_NAME, e.g.
# IR05_PAN_PF__3O_20140330T085820_20140330T085824_NSG_48181_C22F.TIF
# IR06_LI3_ORT_1O_20060320T094438_20060320T094500_DLR_12578_PRCS.BIL.ZIP
DATASET_NAME_RE = re.compile(
    r"^(?P<mission>IR\d\d)_(?P<sensor>[A-Z0-9]+)_.*?_(?P<start>\d{8}T\d{6})_(?P<stop>\d{8}T\d{6})"
    r"_(?P<centre>[A-Z0-9]+)_(?P<orbit>\d+)_", re.IGNORECASE)

# IRS-P6 orthoimage PROJECTION token -> EPSG code. "CS" carries no definition
# in the product; its coordinates are Gauss-Krueger Balkans zone 7 (false
# easting 7 500 000 m), taken as MGI 1901 / Balkans zone 7 (EPSG:3909)
P6_PROJECTIONS = {"CS": 3909}
P6_EASTING_RANGE = {3909: (7000000.0, 8000000.0)}

# ETRS89 / LAEA Europe (EPSG:3035): GRS 1980, centre 52N 10E, false easting
# / northing 4 321 000 / 3 210 000 m - the user-defined CRS of the ortho
# GeoTIFFs carries exactly these parameters
LAEA_3035 = {"a": 6378137.0, "invf": 298.257222101, "lat0": 52.0, "lon0": 10.0,
             "fe": 4321000.0, "fn": 3210000.0}
USER_DEFINED = 32767
CT_LAMBERT_AZIM_EQUAL_AREA = 10


# -- delivery layout --------------------------------------------------------

def layout(entry):
    """(kind, delivery root) of an entry file; raises for anything else."""
    entry = os.path.abspath(str(entry))
    folder = os.path.dirname(entry)
    name = os.path.basename(entry)
    if OID_RE.match(name):
        return ORTHO_P5, folder
    match = DSM_RE.match(name)
    if match and match.group("layer").lower() == "dsm" \
            and os.path.basename(folder).lower() == DSM_FOLDER:
        return DSM_P5, os.path.dirname(folder)
    if name.lower() == P6_ENTRY and _find(folder, P6_IMAGE) and ssd_file(folder):
        return ORTHO_P6, folder
    raise Exception("not an IRS-P5 ortho / DSM or IRS-P6 ortho delivery entry: %s" % entry)


def _find(folder, name):
    """Path of the file called name (any case) directly in folder, or None."""
    for item in sorted(os.listdir(folder)):
        if item.lower() == name.lower() and os.path.isfile(os.path.join(folder, item)):
            return os.path.join(folder, item)
    return None


def _walk(folder):
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for name in sorted(files):
            yield os.path.join(root, name)


def product_files(entry):
    """Every file of the delivery the entry belongs to, sorted by relative
    path: the whole delivery goes to measurements/ (spec section 3)."""
    root = layout(entry)[1]
    return sorted(_walk(root), key=lambda p: os.path.relpath(p, root).replace(os.sep, "/"))


def native_size(entry):
    """Size in bytes of the delivery (spec Table 15 size)."""
    return sum(os.path.getsize(p) for p in product_files(entry))


def ortho_images(root):
    """IRS-P5 ortho images as [{index, metadata, image}] by image number:
    every EM_Ortho_Image_<n>/ with exactly one *_metadata.xml and one
    *_imagery.tif. Raises when there is none or one is incomplete."""
    images = []
    for item in sorted(os.listdir(root)):
        match = ORTHO_DIR_RE.match(item)
        folder = os.path.join(root, item)
        if not match or not os.path.isdir(folder):
            continue
        files = sorted(os.listdir(folder))
        xmls = [f for f in files if f.lower().endswith("_metadata.xml")]
        tifs = [f for f in files if f.lower().endswith("_imagery.tif")]
        if len(xmls) != 1 or len(tifs) != 1:
            raise Exception("%s: expected one *_metadata.xml and one *_imagery.tif, found %s / %s"
                            % (folder, xmls or "none", tifs or "none"))
        images.append({"index": int(match.group("n")),
                       "metadata": os.path.join(folder, xmls[0]),
                       "image": os.path.join(folder, tifs[0])})
    if not images:
        raise Exception("no EM_Ortho_Image_<n>/ folder in %s" % root)
    return sorted(images, key=lambda i: i["index"])


def ortho_quicklook(entry):
    """<delivery>_ql.tif next to the <delivery>_oid.txt entry, or None."""
    entry = os.path.abspath(str(entry))
    delivery = OID_RE.match(os.path.basename(entry)).group("delivery")
    return _find(os.path.dirname(entry), delivery + "_ql.tif")


def dsm_name(name):
    """Fields of an em3d layer file name (id, date, tile, layer), or None."""
    match = DSM_RE.match(os.path.basename(str(name)))
    if not match:
        return None
    fields = match.groupdict()
    fields["layer"] = fields["layer"].lower()
    return fields


def dsm_layers(entry):
    """{layer: path} of the DSM tile of the em3d_..._dsm.tif entry; raises
    when one of the five layers is missing."""
    entry = os.path.abspath(str(entry))
    key = dsm_name(entry)
    folder = os.path.dirname(entry)
    layers = {}
    for item in sorted(os.listdir(folder)):
        fields = dsm_name(item)
        if fields and (fields["id"], fields["date"], fields["tile"].upper()) \
                == (key["id"], key["date"], key["tile"].upper()):
            layers[fields["layer"]] = os.path.join(folder, item)
    missing = [l for l in DSM_LAYERS if l not in layers]
    if missing:
        raise Exception("DSM tile %s: layer(s) %s missing" % (os.path.basename(entry), ", ".join(missing)))
    return layers


def ssd_file(folder):
    """The <scene>_ssd.txt of an IRS-P6 delivery, or None (several: error)."""
    found = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(SSD_SUFFIX)]
    if len(found) > 1:
        raise Exception("several *%s files in %s: %s" % (SSD_SUFFIX, folder, found))
    return os.path.join(folder, found[0]) if found else None


def p6_parts(root):
    """{metadata, image, header, ssd} of an IRS-P6 delivery; raises when one
    is missing."""
    parts = {"metadata": _find(root, P6_ENTRY), "image": _find(root, P6_IMAGE),
             "header": _find(root, P6_HEADER), "ssd": ssd_file(root)}
    missing = [k for k, v in parts.items() if v is None]
    if missing:
        raise Exception("IRS-P6 delivery %s: %s missing" % (root, ", ".join(missing)))
    return parts


# -- names and dates --------------------------------------------------------

def dataset_name(name):
    """Fields of a Euro-Maps DATASET_NAME: mission (IR05 / IR06), sensor,
    start / stop (yyyymmddThhmmss), centre, orbit (int). Raises when the
    name does not follow the pattern."""
    match = DATASET_NAME_RE.match(str(name).strip())
    if not match:
        raise Exception("unexpected DATASET_NAME '%s'" % name)
    fields = match.groupdict()
    fields["mission"] = fields["mission"].upper()
    fields["orbit"] = int(fields["orbit"])
    return fields


def name_utc(stamp):
    """yyyymmddThhmmss -> YYYY-MM-DDThh:mm:ss.000Z (spec Table 6)."""
    match = re.match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$", stamp or "")
    if not match:
        raise Exception("unexpected date-time '%s'" % stamp)
    return "%s-%s-%sT%s:%s:%s.000Z" % match.groups()


def date_utc(day):
    """YYYY-MM-DD or yyyymmdd (a date without time) -> YYYY-MM-DDT00:00:00.000Z."""
    match = re.match(r"^(\d{4})-?(\d{2})-?(\d{2})$", (day or "").strip())
    if not match:
        raise Exception("unexpected date '%s'" % day)
    return "%s-%s-%sT00:00:00.000Z" % match.groups()


# -- Euro-Maps metadata XML -------------------------------------------------

def _text(root, path):
    node = root.find(path)
    return node.text.strip() if node is not None and node.text and node.text.strip() else None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_em_xml(path):
    """Euro-Maps metadata XML (IRS-P5 *_metadata.xml, IRS-P6 metadata.xml;
    ISO-8859-1 declared) -> dict. 'acquisition' maps each
    Acquisition_Parameter code to its value (float when numeric)."""
    root = ET.parse(str(path)).getroot()
    acquisition = {}
    for param in root.iter("Acquisition_Parameter"):
        code = _text(param, "ACQUISITION_PARAMETER_CODE")
        value = _text(param, "ACQUISITION_PARAMETER_VALUE")
        if code:
            number = _float(value)
            acquisition[code] = number if number is not None else value
    return {
        "dataset_name": _text(root, "Production/DATASET_NAME"),
        "production_date": _text(root, "Production/DATASET_PRODUCTION_DATE"),
        "mission": _text(root, "Production/DATASET_MISSION"),
        "sensor": _text(root, "Production/DATASET_SENSOR"),
        "sensor_mode": _text(root, "Production/DATASET_SENSOR_MODE"),
        "projection": _text(root, "GeoInformation/PROJECTION"),
        "proj_definition": _text(root, "GeoInformation/PROJ_DEFINITION"),
        "xgeoref": _float(_text(root, "GeoInformation/XGEOREF")),
        "ygeoref": _float(_text(root, "GeoInformation/YGEOREF")),
        "xcellres": _float(_text(root, "GeoInformation/XCELLRES")),
        "ycellres": _float(_text(root, "GeoInformation/YCELLRES")),
        "columns": _float(_text(root, "Image/COLUMNS")),
        "rows": _float(_text(root, "Image/ROWS")),
        "channels": _float(_text(root, "Image/CHANNELS")),
        "acquisition": acquisition,
    }


# -- IRS-P6 Euromap ssd dump -------------------------------------------------

# Header Record field descriptions (as printed in the dump) -> key
SSD_FIELDS = {
    "Orbit number": "orbit",
    "Satellite heading angle": "heading",
    "Sun angle (Azimuth)": "sun_azimuth",
    "Sun angle (elevation)": "sun_elevation",
    "Left top corner geographic location of scene (lat)": "tl_lat",
    "Left top corner geographic location of scene (long)": "tl_lon",
    "Right top corner geographic location of scene (lat)": "tr_lat",
    "Right top corner geographic location of scene (long)": "tr_lon",
    "Right bottom corner geographic location of scene (lat)": "br_lat",
    "Right bottom corner geographic location of scene (long)": "br_lon",
    "Left bottom corner geographic location of scene (lat)": "bl_lat",
    "Left bottom corner geographic location of scene (long)": "bl_lon",
}
SSD_VALUE_RE = re.compile(r">(.*)<\s*$")


def parse_ssd(path):
    """Euromap <scene>_ssd.txt -> {key: float} for the SSD_FIELDS of its
    'Header Record' section (ASCII dump values between '>' and '<'); a
    field that is absent or empty is left out."""
    values = {}
    in_header = False
    with open(str(path), "r", encoding="latin-1") as fd:
        for line in fd:
            stripped = line.strip()
            if stripped.endswith("...."):
                if in_header:
                    break  # next record: the header record is complete
                in_header = stripped.startswith("Header Record")
                continue
            if not in_header:
                continue
            match = SSD_VALUE_RE.search(line)
            if not match:
                continue
            for description, key in SSD_FIELDS.items():
                if description in line and key not in values:
                    number = _float(match.group(1).strip())
                    if number is not None:
                        values[key] = number
    return values


def ssd_ring(ssd):
    """Scene corners of the ssd as a [lon, lat] ring TL, TR, BR, BL (not
    closed); raises when a corner is missing or out of range."""
    ring = []
    for corner in ("tl", "tr", "br", "bl"):
        lon, lat = ssd.get(corner + "_lon"), ssd.get(corner + "_lat")
        if lon is None or lat is None:
            raise Exception("ssd scene corner %s missing" % corner.upper())
        _check_lonlat(lon, lat)
        ring.append([lon, lat])
    return ring


# -- GeoTIFF georeferencing and CRS ------------------------------------------

def geotiff_georef(path):
    """Georeferencing of a GeoTIFF from its tags: {cols, rows, x0, y0 (outer
    corner of the top-left pixel), px, py (pixel size), epsg (int or None)}."""
    import tifffile
    with tifffile.TiffFile(str(path)) as tf:
        page = tf.pages[0]
        keys = tf.geotiff_metadata or {}
        rows, cols = page.shape[0], page.shape[1]
    scale = keys.get("ModelPixelScale")
    tie = keys.get("ModelTiepoint")
    if not scale or not tie or len(tie) < 6:
        raise Exception("no ModelPixelScale / ModelTiepoint in %s" % path)
    px, py = float(scale[0]), float(scale[1])
    i, j, x, y = float(tie[0]), float(tie[1]), float(tie[3]), float(tie[4])
    x0, y0 = x - i * px, y + j * py
    if int(keys.get("GTRasterTypeGeoKey", 1)) == 2:  # PixelIsPoint: tiepoint at the pixel centre
        x0, y0 = x0 - px / 2.0, y0 + py / 2.0
    return {"cols": cols, "rows": rows, "x0": x0, "y0": y0, "px": px, "py": py,
            "epsg": geokeys_epsg(keys)}


def geokeys_epsg(keys):
    """EPSG code of a projected GeoTIFF CRS: ProjectedCSTypeGeoKey, or 3035
    for a user-defined CRS whose parameters are those of ETRS89 / LAEA
    Europe; None otherwise."""
    code = keys.get("ProjectedCSTypeGeoKey")
    if code is not None and int(code) != USER_DEFINED:
        return int(code)
    try:
        if int(keys.get("ProjCoordTransGeoKey", 0)) != CT_LAMBERT_AZIM_EQUAL_AREA:
            return None
        params = (keys["GeogSemiMajorAxisGeoKey"], keys["GeogInvFlatteningGeoKey"],
                  keys["ProjCenterLatGeoKey"], keys["ProjCenterLongGeoKey"],
                  keys["ProjFalseEastingGeoKey"], keys["ProjFalseNorthingGeoKey"])
    except KeyError:
        return None
    expected = tuple(LAEA_3035[k] for k in ("a", "invf", "lat0", "lon0", "fe", "fn"))
    if all(abs(float(v) - e) <= 1e-6 * max(1.0, abs(e)) for v, e in zip(params, expected)):
        return 3035
    return None


def raster_corners(georef):
    """Projected outer corners TL, TR, BR, BL of a raster."""
    x0, y0 = georef["x0"], georef["y0"]
    x1 = x0 + georef["cols"] * georef["px"]
    y1 = y0 - georef["rows"] * georef["py"]
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def p6_epsg(meta):
    """EPSG code of an IRS-P6 orthoimage from its metadata PROJECTION token
    (P6_PROJECTIONS), checked against the easting range of that CRS."""
    code = P6_PROJECTIONS.get((meta.get("projection") or "").upper())
    if code is None:
        raise Exception("unsupported IRS-P6 PROJECTION '%s'" % meta.get("projection"))
    low, high = P6_EASTING_RANGE[code]
    if meta.get("xgeoref") is None or not low <= meta["xgeoref"] <= high:
        raise Exception("IRS-P6 XGEOREF %s outside EPSG:%d eastings" % (meta.get("xgeoref"), code))
    return code


def crs_uri(code):
    """EPSG code -> OGC CRS URI (spec Table 15 referenceSystemIdentifier)."""
    return "http://www.opengis.net/def/crs/EPSG/0/%d" % int(code)


def laea_inverse(x, y):
    """EPSG:3035 easting / northing (m) -> (lon, lat) in degrees, IOGP
    Guidance Note 7-2 Lambert Azimuthal Equal Area (ellipsoidal) inverse."""
    p = LAEA_3035
    a = p["a"]
    f = 1.0 / p["invf"]
    e2 = 2 * f - f * f
    e = math.sqrt(e2)
    lat0, lon0 = math.radians(p["lat0"]), math.radians(p["lon0"])

    def q(phi):
        s = math.sin(phi)
        return (1 - e2) * (s / (1 - e2 * s * s) - (1 / (2 * e)) * math.log((1 - e * s) / (1 + e * s)))

    qp, q0 = q(math.pi / 2), q(lat0)
    beta0 = math.asin(q0 / qp)
    rq = a * math.sqrt(qp / 2)
    d = a * (math.cos(lat0) / math.sqrt(1 - e2 * math.sin(lat0) ** 2)) / (rq * math.cos(beta0))
    dx, dy = x - p["fe"], y - p["fn"]
    rho = math.hypot(dx / d, d * dy)
    if rho == 0:
        return p["lon0"], p["lat0"]
    c = 2 * math.asin(rho / (2 * rq))
    beta = math.asin(math.cos(c) * math.sin(beta0) + (d * dy * math.sin(c) * math.cos(beta0)) / rho)
    lon = lon0 + math.atan2(dx * math.sin(c),
                            d * rho * math.cos(beta0) * math.cos(c) - d * d * dy * math.sin(beta0) * math.sin(c))
    lat = beta + (e2 / 3 + 31 * e2 ** 2 / 180 + 517 * e2 ** 3 / 5040) * math.sin(2 * beta) \
        + (23 * e2 ** 2 / 360 + 251 * e2 ** 3 / 3780) * math.sin(4 * beta) \
        + (761 * e2 ** 3 / 45360) * math.sin(6 * beta)
    return math.degrees(lon), math.degrees(lat)


def lonlat_ring(corners, epsg):
    """Projected corners -> [lon, lat] ring (not closed); EPSG:3035 only."""
    if epsg != 3035:
        raise Exception("unsupported CRS EPSG:%s (only EPSG:3035 is converted to lon/lat)" % epsg)
    ring = [list(laea_inverse(x, y)) for x, y in corners]
    for lon, lat in ring:
        _check_lonlat(lon, lat)
    return ring


def _check_lonlat(lon, lat):
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise Exception("footprint corner out of range: lon=%s lat=%s" % (lon, lat))


# -- orbit direction --------------------------------------------------------

def daylight_direction(start, lon):
    """Orbit direction from the local solar time of the pass, for products
    without a direction: IRS-P5 flies a sun-synchronous
    orbit with the descending node in the morning (about 10:30 local time),
    so a daylight pass (06:00-18:00 local) is DESCENDING, a night one
    ASCENDING. start: YYYY-MM-DDThh:mm:ss[...]."""
    match = re.match(r"^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", start or "")
    if not match or lon is None:
        raise Exception("no start time / longitude to derive the orbit direction")
    local_hours = (int(match.group(1)) + int(match.group(2)) / 60.0 + lon / 15.0) % 24.0
    return "DESCENDING" if 6.0 <= local_hours < 18.0 else "ASCENDING"


def heading_direction(heading):
    """Orbit direction from the satellite heading (degrees from north): a
    southbound heading (between 90 and 270) is DESCENDING, else ASCENDING."""
    if heading is None:
        raise Exception("no satellite heading to derive the orbit direction")
    return "DESCENDING" if 90.0 < float(heading) % 360.0 < 270.0 else "ASCENDING"


# -- IRS-P6 BIL header --------------------------------------------------------

def parse_bil_header(path):
    """imagery.hdr (KEY value lines) -> {KEY: value}, keys upper-case."""
    values = {}
    with open(str(path), "r", encoding="latin-1") as fd:
        for line in fd:
            parts = line.split(None, 1)
            if len(parts) == 2:
                values[parts[0].upper()] = parts[1].strip()
    return values
