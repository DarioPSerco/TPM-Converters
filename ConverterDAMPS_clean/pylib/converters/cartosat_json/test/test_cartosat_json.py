"""Tests for cartosat_json: the delivery layouts and parsers, the product
values of the three layouts, the package names, the overview, the packager
and the manifest.
Native products are the SYNTHETIC deliveries of fixtures/synthetic_ir5 (see
fixtures/SYNTHETIC_FIXTURE_NOTE.md): the file set, names and metadata
elements of the real IRS-P5 ortho / DSM and IRS-P6 deliveries, synthetic
values. Failing products are edited copies. Manifest tests against
TDS/template/IR5-template.json (the spec section 6.1 example) fill the
metadata by hand.
"""
import configparser
import importlib.util
import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from eoSip_converter.esaProducts import metadata as M
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

from common import json_template
from cartosat_json import cartosat_files as F
from cartosat_json import json_emitter as E
from cartosat_json import name_registry as NR
from cartosat_json import package_cartosat_zips as PKG
from cartosat_json import product_cartosat as P

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
SYNTHETIC = FIXTURES / "synthetic_ir5"
CFG = HERE.parent / "ingest_cartosat.cfg"
IR5_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "IR5-template.json"

ORT1 = SYNTHETIC / "ort1" / "delivery"
ORT2 = SYNTHETIC / "ort2" / "delivery"
DSM_A = SYNTHETIC / "dsm" / "tile_a"
DSM_B = SYNTHETIC / "dsm" / "tile_b"
IR6 = SYNTHETIC / "ir6" / "delivery"

ORT1_OID = ORT1 / "100527P500000000PF_00O4_oid.txt"
ORT2_OID = ORT2 / "100528P500000000PF_00O4_oid.txt"
DSM_A_TIF = DSM_A / "p5bproductformatter" / "em3d_100001_20200402_005E050NPA_dsm.tif"
DSM_B_TIF = DSM_B / "p5bproductformatter" / "em3d_100001_20200402_005E050NPB_dsm.tif"
IR6_XML = IR6 / "metadata.xml"
ENTRIES = [ORT1_OID, ORT2_OID, DSM_A_TIF, DSM_B_TIF, IR6_XML]

ORT1_EO_NAME = "IR5_OPER_L3_ORT_PAN_20100527T101520_20100527T101524_0001"
ORT2_EO_NAME = "IR5_OPER_L3_ORT_PAN_20100528T101520_20100528T101534_0001"
DSM_EO_NAME = "IR5_OPER_L3_DSM_____20200402T000000_20200402T000000_%04d"
IR6_EO_NAME = "IR6_OPER_L3_ORT_PAN_20060320T094438_20060320T094500_0001"
# spec section 2.2 example name: the length the ingester checks
REF_NAME = "IR5_OPER_L3_ORT_PAN_20100527T231608_20100527T231907_0001"

SAR_KEYS = ["polarisationMode", "polarisationChannel", "rangeResolution",
            "azimuthResolution", "antennaLookDirection", "platformSerialIdentifier"]
OTHER_MISSION_TOKENS = ["GeoEye", "WorldView", "QuickBird", "Pleiades", "ICEYE", "KOMPSAT",
                        "COSMO", "RADARSAT", "PlanetScope", "SkySat", "RapidEye", "GEOSAT",
                        "Beijing", "DMC"]


# -- helpers -------------------------------------------------------------------

def mission_values():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str
    cfg.read(CFG)
    return dict(cfg.items("Mission-specific-values")), cfg.get("Output", "OUTPUT_EO_PATTERN")


def copy_delivery(folder, dest):
    """Copy a synthetic delivery folder under dest; returns the copy."""
    shutil.copytree(folder, dest / folder.name)
    return dest / folder.name


def entry_in(copy, entry, delivery):
    return copy / entry.relative_to(delivery)


def edit(path, old, new, encoding="ISO-8859-1"):
    text = path.read_text(encoding=encoding)
    assert old in text, old
    path.write_text(text.replace(old, new), encoding=encoding)


def extract(entry, work, values=True):
    prod = P.Product_Cartosat(str(entry))
    prod.setDebug(0)
    prod.extractToPath(str(work))
    met = M.Metadata(mission_values()[0] if values else None)
    prod.extractMetadata(met, None)
    return prod, met


def eo_name(prod, met, registry):
    """Package name as the ingester builds it: counter from the registry,
    then the naming convention."""
    pattern = mission_values()[1]
    NR.assign_version(met, prod.nativeFileName, pattern, registry_path=str(registry))
    return NamingConvention_HightRes(pattern).buildProductName(met, None)


def feature_of(entry, work, registry=None):
    prod, met = extract(entry, work)
    name = eo_name(prod, met, registry or work / "cartosat_names.json")
    feature = json_template.build(
        *E.build_layers(met, prod, name, native_product_name=prod.nativeFileName),
        template_path=E.TEMPLATE_PATH)
    json_template.validate(feature)
    return prod, met, feature


def key_paths(node, prefix="$"):
    paths = set()
    if isinstance(node, dict):
        for k, v in node.items():
            paths |= key_paths(v, "%s.%s" % (prefix, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            paths |= key_paths(v, "%s[%d]" % (prefix, i))
    else:
        paths.add(prefix)
    return paths


def ring_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))


def generator():
    spec = importlib.util.spec_from_file_location("make_synthetic_ir5", FIXTURES / "make_synthetic_ir5.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def work(tmp_path):
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


# -- spec lookup tables -------------------------------------------------------------

def test_product_types_follow_tables_1_and_2():
    assert set(P.PRODUCT_TYPES.values()) == {("L3_ORT_PAN", "PAN"), ("L3_DSM____", "STER")}
    assert P.PRODUCT_TYPES[F.ORTHO_P6] == ("L3_ORT_PAN", "PAN")
    assert all(len(t) == 10 for t, _ in P.PRODUCT_TYPES.values())
    assert (P.PROCESSING_LEVEL, P.PROCESSED_LEVEL_CODE_L3) == ("3", "L3")


def test_platforms_and_instrument():
    assert P.PLATFORMS == {"IR5": ("IRS-P5", "5"), "IR6": ("IRS-P6", "6")}
    assert P.INSTRUMENT == "PAN"
    assert F.MISSIONS == {"IR05": "IR5", "IR06": "IR6"}


def test_resolutions_and_wavelengths():
    assert P.RESOLUTIONS == {"IR5": 2.5, "IR6": 20.0}
    assert P.wavelengths("IR5") == [{"spectralRange": "VNIR", "startWavelength": 500e-9,
                                     "endWavelength": 850e-9, "discreteWavelengths": [675e-9]}]
    assert P.wavelengths("IR6") == [
        {"spectralRange": "VIS", "startWavelength": 520e-9, "endWavelength": 680e-9,
         "discreteWavelengths": [555e-9, 650e-9]},
        {"spectralRange": "NIR", "startWavelength": 770e-9, "endWavelength": 860e-9,
         "discreteWavelengths": [815e-9]},
        {"spectralRange": "SWIR", "startWavelength": 1550e-9, "endWavelength": 1700e-9,
         "discreteWavelengths": [1625e-9]},
    ]


# -- cartosat_files: layouts, names, parsers -------------------------------------------

@pytest.mark.parametrize("entry,kind,root", [
    (ORT1_OID, F.ORTHO_P5, ORT1), (ORT2_OID, F.ORTHO_P5, ORT2),
    (DSM_A_TIF, F.DSM_P5, DSM_A), (IR6_XML, F.ORTHO_P6, IR6)])
def test_layout_of_each_entry(entry, kind, root):
    assert F.layout(entry) == (kind, str(root))


@pytest.mark.parametrize("path", [
    ORT1 / "100527P500000000PF_00O4_ql.tfw",
    ORT1 / "EM_Ortho_Image_1" / "100527P500000000PF_00O4_metadata.xml",
    DSM_A / "p5bproductformatter" / "em3d_100001_20200402_005E050NPA_acv.tif",
    IR6 / "imagery.hdr"])
def test_layout_rejects_files_that_are_not_entries(path):
    with pytest.raises(Exception, match="not an IRS-P5 ortho / DSM or IRS-P6 ortho delivery entry"):
        F.layout(path)


def test_irs_p6_entry_needs_its_image_and_ssd(tmp_path):
    copy = copy_delivery(IR6, tmp_path)
    (copy / "060320P6036037L0030S3_ssd.txt").unlink()
    with pytest.raises(Exception, match="delivery entry"):
        F.layout(copy / "metadata.xml")


def test_product_files_are_the_whole_delivery():
    files = F.product_files(ORT1_OID)
    assert [Path(f).relative_to(ORT1).as_posix() for f in files] == [
        "100527P500000000PF_00O4_oid.txt", "100527P500000000PF_00O4_ql.tfw",
        "100527P500000000PF_00O4_ql.tif", "EM_Ortho_Image_1/100527P500000000PF_00O4_imagery.tif",
        "EM_Ortho_Image_1/100527P500000000PF_00O4_metadata.xml"]
    assert F.native_size(ORT1_OID) == sum(Path(f).stat().st_size for f in files)
    assert len(F.product_files(IR6_XML)) == 7


def test_ortho_image_folder_must_be_complete(tmp_path):
    copy = copy_delivery(ORT1, tmp_path)
    (copy / "EM_Ortho_Image_1" / "100527P500000000PF_00O4_imagery.tif").unlink()
    with pytest.raises(Exception, match="expected one"):
        F.ortho_images(str(copy))


def test_dsm_tile_needs_all_five_layers(tmp_path):
    copy = copy_delivery(DSM_A, tmp_path)
    (copy / "p5bproductformatter" / "em3d_100001_20200402_005E050NPA_qc.tif").unlink()
    with pytest.raises(Exception, match="layer.*qc.*missing"):
        F.dsm_layers(entry_in(copy, DSM_A_TIF, DSM_A))


@pytest.mark.parametrize("name,expected", [
    ("IR05_PAN_PF__3O_20140330T085820_20140330T085824_NSG_48181_C22F.TIF",
     ("IR05", "PAN", "20140330T085820", "20140330T085824", 48181)),
    ("IR06_LI3_ORT_1O_20060320T094438_20060320T094500_DLR_12578_PRCS.BIL.ZIP",
     ("IR06", "LI3", "20060320T094438", "20060320T094500", 12578)),
])
def test_dataset_name(name, expected):
    fields = F.dataset_name(name)
    assert (fields["mission"], fields["sensor"], fields["start"], fields["stop"], fields["orbit"]) == expected


def test_dataset_name_must_follow_the_pattern():
    with pytest.raises(Exception, match="unexpected DATASET_NAME"):
        F.dataset_name("IR05_PAN_20140330_NSG.TIF")


def test_dates_are_rfc3339_with_milliseconds():
    assert F.name_utc("20140330T085820") == "2014-03-30T08:58:20.000Z"
    assert F.date_utc("2022-06-07") == F.date_utc("20220607") == "2022-06-07T00:00:00.000Z"
    with pytest.raises(Exception, match="unexpected date"):
        F.date_utc("07/06/2022")


def test_euro_maps_xml():
    meta = F.parse_em_xml(ORT1 / "EM_Ortho_Image_1" / "100527P500000000PF_00O4_metadata.xml")
    assert meta["mission"] == "IR05" and meta["sensor"] == "PAN" and meta["sensor_mode"] == "PF"
    assert meta["production_date"] == "2011-01-02"
    assert meta["acquisition"] == {"Orbit_no": 1234.0, "Sun_azimuth": 152.5,
                                   "Sun_elevation": 50.25, "Tilt_angle": 0.0}


def test_ssd_header_record_only():
    ssd = F.parse_ssd(IR6 / "060320P6036037L0030S3_ssd.txt")
    assert ssd["orbit"] == 12345  # not the 99999 of the later record
    assert (ssd["heading"], ssd["sun_azimuth"], ssd["sun_elevation"]) == (200.9, 157.2, 42.8)
    assert F.ssd_ring(ssd) == [[18.5, 45.5], [20.2, 45.2], [19.7, 44.0], [18.0, 44.3]]


def test_bil_header():
    assert F.parse_bil_header(IR6 / "imagery.hdr") == {
        "BYTEORDER": "M", "LAYOUT": "BIL", "NROWS": "12", "NCOLS": "16",
        "NBANDS": "4", "NBITS": "8", "SKIPBYTES": "0"}


def test_inverse_laea_at_the_iogp_example_point():
    lon, lat = F.laea_inverse(3962799.45, 2999718.85)
    assert abs(lon - 5.0) < 1e-7 and abs(lat - 50.0) < 1e-7
    assert F.laea_inverse(4321000.0, 3210000.0) == (10.0, 52.0)


def test_crs_of_the_geotiffs():
    assert F.geotiff_georef(DSM_A_TIF)["epsg"] == 3035
    ortho = F.geotiff_georef(ORT1 / "EM_Ortho_Image_1" / "100527P500000000PF_00O4_imagery.tif")
    assert ortho["epsg"] == 3035  # user-defined, with the ETRS89 / LAEA parameters
    assert (ortho["x0"], ortho["y0"], ortho["px"], ortho["cols"], ortho["rows"]) == \
        (3962799.45, 2999718.85, 2.5, 16, 12)
    named = {"ProjCoordTransGeoKey": 10, "ProjectedCSTypeGeoKey": 32767,
             "GeogSemiMajorAxisGeoKey": 6378137.0, "GeogInvFlatteningGeoKey": 298.257222101,
             "ProjCenterLatGeoKey": 52.0, "ProjCenterLongGeoKey": 10.0,
             "ProjFalseEastingGeoKey": 4321000.0, "ProjFalseNorthingGeoKey": 3210000.0}
    assert F.geokeys_epsg(named) == 3035
    assert F.geokeys_epsg(dict(named, ProjFalseEastingGeoKey=4320000.0)) is None
    assert F.geokeys_epsg(dict(named, ProjCoordTransGeoKey=1)) is None
    assert F.geokeys_epsg({"ProjectedCSTypeGeoKey": 32633}) == 32633


def test_irs_p6_projection():
    assert F.p6_epsg({"projection": "CS", "xgeoref": 7262270.0}) == 3909
    with pytest.raises(Exception, match="unsupported IRS-P6 PROJECTION"):
        F.p6_epsg({"projection": "UTM", "xgeoref": 7262270.0})
    with pytest.raises(Exception, match="outside EPSG:3909"):
        F.p6_epsg({"projection": "CS", "xgeoref": 500000.0})
    assert F.crs_uri(3909) == "http://www.opengis.net/def/crs/EPSG/0/3909"


def test_orbit_direction_rules():
    assert F.daylight_direction("2010-05-27T10:15:20.000Z", 5.0) == "DESCENDING"
    assert F.daylight_direction("2010-05-27T23:16:08.000Z", -66.4) == "ASCENDING"  # 18:50 local
    assert F.heading_direction(200.9) == "DESCENDING"
    assert F.heading_direction(20.0) == F.heading_direction(350.0) == "ASCENDING"
    with pytest.raises(Exception, match="no satellite heading"):
        F.heading_direction(None)


# -- name registry ----------------------------------------------------------------------

def test_registry_counts_first_come_first_served(tmp_path):
    path = tmp_path / "cartosat_names.json"
    base = lambda v: "BASE_" + v
    reg = NR.NameRegistry(str(path))
    assert reg.version_for("A", base) == "0001"
    assert reg.version_for("B", base) == "0002"
    # a native product converted again gets its own name back
    assert reg.version_for("A", base) == "0001"
    # another name starts again from 01
    assert reg.version_for("C", lambda v: "OTHER_" + v) == "0001"
    # the registry is kept on disk: a later run continues from it
    assert NR.NameRegistry(str(path)).version_for("D", base) == "0003"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "A": "BASE_0001", "B": "BASE_0002", "C": "OTHER_0001", "D": "BASE_0003"}


def test_registry_counter_limit(tmp_path):
    path = tmp_path / "cartosat_names.json"
    path.write_text(json.dumps({"N%d" % c: "BASE_00%02d" % c for c in range(1, 100)}),
                    encoding="utf-8")
    with pytest.raises(Exception, match="counter limit 99"):
        NR.NameRegistry(str(path)).version_for("NEW", lambda v: "BASE_" + v)


def test_registry_refuses_a_changed_name(tmp_path):
    path = tmp_path / "cartosat_names.json"
    path.write_text(json.dumps({"A": "BASE_0001"}), encoding="utf-8")
    with pytest.raises(Exception, match="metadata changed"):
        NR.NameRegistry(str(path)).version_for("A", lambda v: "NEW_" + v)


def test_registry_refuses_an_unreadable_file(tmp_path):
    path = tmp_path / "cartosat_names.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(Exception, match="not valid JSON"):
        NR.NameRegistry(str(path))


def test_registry_path_comes_from_the_cfg():
    assert mission_values()[0][NR.REGISTRY_KEY] == r"TDS\CARTOSAT\cartosat_names.json"
    with pytest.raises(Exception, match=NR.REGISTRY_KEY):
        NR.assign_version(M.Metadata(None), "A", mission_values()[1])


# -- product values from the synthetic deliveries -------------------------------------

def test_ortho_values(work):
    prod, _, feature = feature_of(ORT1_OID, work)
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    (par,) = acq["acquisitionParameters"]
    pinfo = props["productInformation"]

    assert feature["id"] == props["title"] == ORT1_EO_NAME
    assert props["status"] == "ACQUIRED"
    assert props["date"] == "2010-05-27T10:15:20.000Z/2010-05-27T10:15:24.000Z"
    assert props["created"].endswith("Z") and len(props["created"]) == 24
    assert acq["platform"] == {"platformShortName": "IRS-P5", "orbitType": "LEO"}
    assert acq["instrument"] == {"instrumentShortName": "PAN", "sensorType": "OPTICAL"}
    assert par == {
        "beginningDateTime": "2010-05-27T10:15:20.000Z", "endingDateTime": "2010-05-27T10:15:24.000Z",
        "operationalMode": "PAN", "resolution": 2.5, "acquisitionType": "NOMINAL",
        "orbitNumber": 1234, "orbitDirection": "DESCENDING", "wavelengths": P.wavelengths("IR5"),
        "acquisitionAngles": {"illuminationAzimuthAngle": 152.5, "illuminationElevationAngle": 50.25}}

    assert pinfo["size"] == F.native_size(ORT1_OID)
    assert pinfo["productType"] == "L3_ORT_PAN"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/3035"
    assert pinfo["processingLevel"] == "3"
    assert pinfo["processingDate"] == "2011-01-02T00:00:00.000Z"
    (step,) = pinfo["resourceLineage"][0]["processStep"]
    assert step["description"] == "EOPF-EOS Converter for IRS-P5"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["reference"] == [{"title": "EOPF-EOS Specialization for IRS-P5 (Cartosat-1) products",
                                  "edition": "1.0"}]
    assert step["source"] == [{"sourceCitation": {"title": ORT1_OID.name},
                               "processedLevel": {"code": "L3"}}]
    assert step["processingInformation"]["softwareReference"] == {
        "title": "EOPF-EOS Converter for IRS-P5 and IRS-P6", "edition": "1.0.0"}
    assert step["output"] == [{"sourceCitation": {"title": "%s.ZIP" % ORT1_EO_NAME}}]
    assert props["links"] == {
        "measurements": [{"href": "/measurements/EM_Ortho_Image_1/100527P500000000PF_00O4_imagery.tif",
                          "type": "image/tiff", "title": "Native EO Product", "category": "DATA"}],
        "previews": [{"href": "/previews/overviews/%s.PNG" % ORT1_EO_NAME,
                      "type": "image/png", "title": "Preview Image", "category": "OVERVIEW"}],
    }
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5
    assert abs(ring[0][0] - 5.0) < 1e-7 and abs(ring[0][1] - 50.0) < 1e-7
    assert ring_area(ring) > 0, "footprint must be counter-clockwise (RFC 7946)"


def test_two_orthoimages_in_one_package(work):
    _, _, feature = feature_of(ORT2_OID, work)
    first, second = feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"]
    assert (first["beginningDateTime"], second["beginningDateTime"]) == \
        ("2010-05-28T10:15:30.000Z", "2010-05-28T10:15:20.000Z")
    assert feature["properties"]["date"] == "2010-05-28T10:15:20.000Z/2010-05-28T10:15:34.000Z"
    assert first["acquisitionAngles"]["illuminationAzimuthAngle"] == 150.0
    assert second["acquisitionAngles"]["illuminationAzimuthAngle"] == 150.5
    assert feature["id"] == ORT2_EO_NAME
    # the footprint is the rectangle around both images: twice as wide as one
    ring = feature["geometry"]["coordinates"][0]
    one = F.lonlat_ring(F.raster_corners(F.geotiff_georef(
        ORT2 / "EM_Ortho_Image_1" / "100528P500000000PF_00O4_imagery.tif")), 3035)
    width = max(p[0] for p in ring) - min(p[0] for p in ring)
    width_one = max(p[0] for p in one) - min(p[0] for p in one)
    assert abs(width / width_one - 2.0) < 0.1


def test_dsm_values(work, capsys):
    prod, _, feature = feature_of(DSM_A_TIF, work)
    assert "WARNING: no orbit number in %s: cfg value used (0)" % DSM_A_TIF.name in capsys.readouterr().out
    props = feature["properties"]
    (par,) = props["acquisitionInformation"][0]["acquisitionParameters"]
    pinfo = props["productInformation"]
    assert feature["id"] == DSM_EO_NAME % 1
    assert par == {
        "beginningDateTime": "2020-04-02T00:00:00.000Z", "endingDateTime": "2020-04-02T00:00:00.000Z",
        "operationalMode": "STER", "resolution": 2.5, "acquisitionType": "NOMINAL",
        "orbitNumber": 0, "orbitDirection": "DESCENDING", "wavelengths": P.wavelengths("IR5")}
    assert pinfo["productType"] == "L3_DSM____"
    assert pinfo["processingDate"] == "2020-04-02T00:00:00.000Z"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/3035"
    assert pinfo["size"] == F.native_size(DSM_A_TIF)
    step = pinfo["resourceLineage"][0]["processStep"][0]
    assert step["source"][0]["sourceCitation"]["title"] == DSM_A_TIF.name
    assert props["links"]["measurements"][0] == {
        "href": "/measurements/p5bproductformatter/%s" % DSM_A_TIF.name,
        "type": "image/tiff", "title": "Native EO Product", "category": "DATA"}
    assert ring_area(feature["geometry"]["coordinates"][0]) > 0


def test_dsm_without_a_cfg_orbit_fails(work):
    with pytest.raises(Exception, match="no orbit number in the product, and none in the cfg"):
        extract(DSM_A_TIF, work, values=False)


def test_irs_p6_values(work):
    prod, _, feature = feature_of(IR6_XML, work)
    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    (par,) = acq["acquisitionParameters"]
    pinfo = props["productInformation"]
    assert feature["id"] == IR6_EO_NAME
    assert acq["platform"]["platformShortName"] == "IRS-P6"
    assert acq["instrument"]["instrumentShortName"] == "PAN"
    assert par == {
        "beginningDateTime": "2006-03-20T09:44:38.000Z", "endingDateTime": "2006-03-20T09:45:00.000Z",
        "operationalMode": "PAN", "resolution": 20.0, "acquisitionType": "NOMINAL",
        "orbitNumber": 12345, "orbitDirection": "DESCENDING", "wavelengths": P.wavelengths("IR6"),
        "acquisitionAngles": {"illuminationAzimuthAngle": 157.2, "illuminationElevationAngle": 42.8}}
    assert pinfo["productType"] == "L3_ORT_PAN"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/3909"
    assert pinfo["processingDate"] == "2007-10-28T00:00:00.000Z"
    step = pinfo["resourceLineage"][0]["processStep"][0]
    assert step["description"] == "EOPF-EOS Converter for IRS-P6"
    assert step["source"][0]["sourceCitation"]["title"] == "%s/metadata.xml" % IR6.name
    assert props["links"]["measurements"][0] == {
        "href": "/measurements/metadata.xml", "type": "application/xml",
        "title": "Native EO Product", "category": "DATA"}
    ring = feature["geometry"]["coordinates"][0]
    assert sorted(map(tuple, ring[:-1])) == sorted(map(tuple, F.ssd_ring(F.parse_ssd(
        IR6 / "060320P6036037L0030S3_ssd.txt"))))
    assert ring_area(ring) > 0


def test_package_names_and_counters(tmp_path, work):
    registry = tmp_path / "cartosat_names.json"
    names = {}
    for entry in ENTRIES + [DSM_A_TIF]:  # DSM_A again: its name comes back
        prod, met = extract(entry, work)
        names.setdefault(entry, []).append(eo_name(prod, met, registry))
    assert names[ORT1_OID] == [ORT1_EO_NAME]
    assert names[ORT2_OID] == [ORT2_EO_NAME]
    assert names[DSM_A_TIF] == [DSM_EO_NAME % 1, DSM_EO_NAME % 1]
    assert names[DSM_B_TIF] == [DSM_EO_NAME % 2]
    assert names[IR6_XML] == [IR6_EO_NAME]
    assert all(len(n) == len(REF_NAME) for v in names.values() for n in v)


# -- failing products ---------------------------------------------------------------------

ORT1_XML = Path("EM_Ortho_Image_1") / "100527P500000000PF_00O4_metadata.xml"


@pytest.mark.parametrize("old,new,message", [
    ("<ACQUISITION_PARAMETER_CODE>Sun_azimuth</ACQUISITION_PARAMETER_CODE>",
     "<ACQUISITION_PARAMETER_CODE>Sun_azimuth_x</ACQUISITION_PARAMETER_CODE>", "no Sun_azimuth"),
    ('<ACQUISITION_PARAMETER_VALUE unit="no unit">1234<', '<ACQUISITION_PARAMETER_VALUE unit="no unit">1235<',
     "differ"),
    ("<DATASET_MISSION>IR05</DATASET_MISSION>", "<DATASET_MISSION>IR06</DATASET_MISSION>",
     "not an IRS-P5 PAN orthoimage"),
    ("<DATASET_PRODUCTION_DATE>2011-01-02</DATASET_PRODUCTION_DATE>", "", "no DATASET_PRODUCTION_DATE"),
    ("IR05_PAN_PF__3O_20100527T101520_20100527T101524", "IR05_PAN_PF__3O_20100527T101520_20100527T101519",
     "stop before start"),
])
def test_invalid_ortho_metadata_fails(tmp_path, work, old, new, message):
    copy = copy_delivery(ORT1, tmp_path)
    edit(copy / ORT1_XML, old, new)
    with pytest.raises(Exception, match=message):
        extract(entry_in(copy, ORT1_OID, ORT1), work)


@pytest.mark.parametrize("old,new,message", [
    ("Sun angle (Azimuth) (deg)", "Sun angle (Azimut) (deg)", "no sun_azimuth"),
    (">   12345<", ">   12346<", "differ"),
    ("Satellite heading angle (deg)", "Satellite heading (deg)", "no satellite heading"),
    ("Left top corner geographic location of scene (lat) (deg)",
     "Left top corner location of scene (lat) (deg)", "corner TL missing"),
])
def test_invalid_ssd_fails(tmp_path, work, old, new, message):
    copy = copy_delivery(IR6, tmp_path)
    edit(copy / "060320P6036037L0030S3_ssd.txt", old, new, encoding="latin-1")
    with pytest.raises(Exception, match=message):
        extract(copy / "metadata.xml", work)


def test_irs_p6_projection_other_than_cs_fails(tmp_path, work):
    copy = copy_delivery(IR6, tmp_path)
    edit(copy / "metadata.xml", "<PROJECTION>CS</PROJECTION>", "<PROJECTION>UTM</PROJECTION>")
    with pytest.raises(Exception, match="unsupported IRS-P6 PROJECTION"):
        extract(copy / "metadata.xml", work)


def test_dsm_in_a_crs_other_than_3035_fails(tmp_path, work):
    copy = copy_delivery(DSM_A, tmp_path)
    g = generator()
    keys = dict(g.LAEA_3035)
    keys[g.PROJECTED_CS_TYPE] = 32633
    g.write_geotiff(entry_in(copy, DSM_A_TIF, DSM_A), g.ramp("int16", nodata=-32767), keys, 5.0,
                    nodata=-32767)
    with pytest.raises(Exception, match="unsupported CRS EPSG:32633"):
        extract(entry_in(copy, DSM_A_TIF, DSM_A), work)


# -- overview ----------------------------------------------------------------------------

@pytest.mark.parametrize("entry,source", [
    (ORT1_OID, "_ql.tif"), (DSM_A_TIF, "_dsm.tif"), (IR6_XML, "imagery.bil")])
def test_overview_png(tmp_path, entry, source, capsys):
    prod = P.Product_Cartosat(str(entry))
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    assert source in capsys.readouterr().out
    with Image.open(png) as im:
        assert im.format == "PNG" and im.mode == "RGBA" and im.size == (16, 12)
        assert im.getpixel((0, 5))[3] == 0      # the no-data first column is transparent
        assert im.getpixel((8, 5))[3] == 255


def test_ortho_overview_without_quicklook_uses_the_first_image(tmp_path, capsys):
    copy = copy_delivery(ORT1, tmp_path)
    (copy / "100527P500000000PF_00O4_ql.tif").unlink()
    prod = P.Product_Cartosat(str(entry_in(copy, ORT1_OID, ORT1)))
    prod.writeQuicklook(str(tmp_path / "overview.PNG"))
    assert "_imagery.tif" in capsys.readouterr().out


# -- manifest -----------------------------------------------------------------------------

def _reference():
    with open(IR5_TEMPLATE, encoding="utf-8") as fd:
        return json.load(fd)


def _filled_metadata(ref):
    """Metadata filled by hand with the reference template's values."""
    met = M.Metadata(None)
    prod = P.Product_Cartosat.__new__(P.Product_Cartosat)
    props = ref["properties"]
    pinfo = props["productInformation"]
    acq = props["acquisitionInformation"][0]
    step = pinfo["resourceLineage"][0]["processStep"][0]
    prod.tmpSize = pinfo["size"]
    prod.nativeFileName = step["source"][0]["sourceCitation"]["title"]
    met.setMetadataPair(P.PLATFORM_SHORT_NAME, acq["platform"]["platformShortName"])
    met.setMetadataPair(P.INSTRUMENT_SHORT_NAME, acq["instrument"]["instrumentShortName"])
    met.setMetadataPair(P.PROCESSED_LEVEL_CODE, step["source"][0]["processedLevel"]["code"])
    met.setMetadataPair(P.CREATION_TIME, props["created"])
    met.setMetadataPair(M.METADATA_TYPECODE, pinfo["productType"])
    met.setMetadataPair(M.METADATA_PROCESSING_LEVEL, pinfo["processingLevel"])
    met.setMetadataPair(M.METADATA_PROCESSING_TIME, pinfo["processingDate"])
    par = acq["acquisitionParameters"][0]
    met.setMetadataPair(M.METADATA_START_DATE_TIME, par["beginningDateTime"])
    met.setMetadataPair(M.METADATA_STOP_DATE_TIME, par["endingDateTime"])
    met.addLocalAttribute("components", [{
        "mode": p["operationalMode"], "begin": p["beginningDateTime"], "end": p["endingDateTime"],
        "resolution": p["resolution"], "orbitNumber": p["orbitNumber"],
        "orbitDirection": p["orbitDirection"], "angles": p.get("acquisitionAngles", {}),
        "wavelengths": p["wavelengths"]} for p in acq["acquisitionParameters"]])
    met.addLocalAttribute("referenceSystemIdentifier", pinfo["referenceSystemIdentifier"])
    measurement = props["links"]["measurements"][0]
    met.addLocalAttribute("nativeDataFile", measurement["href"][len("/measurements/"):])
    met.addLocalAttribute("measurementsMediaType", measurement["type"])
    met.addLocalAttribute("footprintRing", ref["geometry"]["coordinates"][0])
    return met, prod


def test_reference_template_fills_the_placeholder_template():
    ref = _reference()
    merged = json_template.build(ref, template_path=E.TEMPLATE_PATH)
    json_template.validate(merged)
    assert merged == ref


def test_emitted_manifest_equals_the_reference_template():
    ref = _reference()
    met, prod = _filled_metadata(ref)
    feature = json_template.build(*E.build_layers(met, prod, ref["id"]), template_path=E.TEMPLATE_PATH)
    json_template.validate(feature)
    assert feature == ref


def test_missing_mandatory_value_fails_with_its_path():
    met, prod = _filled_metadata(_reference())
    met.setMetadataPair(M.METADATA_PROCESSING_TIME, None)
    feature = json_template.build(*E.build_layers(met, prod, _reference()["id"]),
                                  template_path=E.TEMPLATE_PATH)
    with pytest.raises(ValueError, match=r"productInformation\.processingDate"):
        json_template.validate(feature)


@pytest.mark.parametrize("entry", ENTRIES)
def test_every_fixture_manifest_has_the_template_structure(work, entry):
    prod, _, feature = feature_of(entry, work)
    assert json_template.lineage_citation(feature) == prod.nativeFileName
    got = {re.sub(r"\[\d+\]", "[]", p) for p in key_paths(feature)}
    want = {re.sub(r"\[\d+\]", "[]", p) for p in key_paths(_reference())}
    if entry in (DSM_A_TIF, DSM_B_TIF):  # no acquisition angles for a DSM tile
        want = {p for p in want if "acquisitionAngles" not in p}
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_no_sar_fields_or_other_mission_names(work):
    for entry in (ORT1_OID, IR6_XML):
        _, _, feature = feature_of(entry, work)
        paths = key_paths(feature)
        for key in SAR_KEYS:
            assert not any(key in p for p in paths), "field leaked: %s" % key
        blob = json.dumps(feature)
        for token in OTHER_MISSION_TOKENS:
            assert token not in blob, "other-mission name leaked: %s" % token


def test_only_json_written_to_output_dir(tmp_path, work):
    out = tmp_path / "out"
    out.mkdir()
    prod, met = extract(ORT1_OID, work)
    name = eo_name(prod, met, work / "cartosat_names.json")
    E.emit(met, prod, name, str(out), native_product_name=prod.nativeFileName)
    assert [p.name for p in out.iterdir()] == ["%s.JSON" % name]


# -- cfg --------------------------------------------------------------------------------

def test_entry_patterns_select_one_entry_per_delivery():
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(CFG)
    name = re.compile(cfg.get("Search", "FILES_NAMEPATTERN"))
    ext = re.compile(cfg.get("Search", "FILES_EXTPATTERN"))
    selected = {p for p in SYNTHETIC.rglob("*") if p.is_file()
                and name.match(p.stem) and ext.match(p.suffix)}
    assert selected == set(ENTRIES)


def test_cfg_values():
    values = mission_values()[0]
    assert values["METADATA_ORBIT"] == "0"
    assert "METADATA_PRODUCT_VERSION" not in values
    assert values["METADATA_CODESPACE_REFERENCE_SYSTEM"] == "urn:esa:eop:crs"


# -- packager ---------------------------------------------------------------------------

@pytest.fixture
def spaces_in(tmp_path, monkeypatch):
    sp = {k: tmp_path / k for k in ("INBOX", "TMPSPACE", "OUTSPACE", "DONESPACE", "PRODUCTS")}
    for p in sp.values():
        p.mkdir()
    monkeypatch.setattr(PKG, "SPACES", dict(PKG.SPACES, **sp))
    monkeypatch.setattr(PKG, "OUTSPACE", sp["OUTSPACE"])
    monkeypatch.setattr(PKG, "PRODUCTS", sp["PRODUCTS"])
    return sp


def converted(delivery, entry, spaces_in, work):
    """Convert a delivery copied into INBOX: manifest and overview in OUTSPACE."""
    copy = copy_delivery(delivery, spaces_in["INBOX"])
    prod, _, feature = feature_of(entry_in(copy, entry, delivery), work)
    mf = spaces_in["OUTSPACE"] / ("%s.JSON" % feature["id"])
    mf.write_text(json.dumps(feature, indent=2), encoding="utf-8")
    prod.writeQuicklook(str(spaces_in["OUTSPACE"] / ("%s.PNG" % feature["id"])))
    return copy, feature, mf


@pytest.mark.parametrize("delivery,entry", [(ORT1, ORT1_OID), (DSM_A, DSM_A_TIF), (IR6, IR6_XML)])
def test_packager_builds_the_delivery_zip(spaces_in, work, delivery, entry):
    copy, feature, mf = converted(delivery, entry, spaces_in, work)
    assert PKG.package_one(mf) == copy
    name = feature["id"]
    with zipfile.ZipFile(spaces_in["PRODUCTS"] / ("%s.ZIP" % name)) as zf:
        assert {i.compress_type for i in zf.infolist()} == {zipfile.ZIP_STORED}
        assert zf.read("%s.JSON" % name) == mf.read_bytes()
        measurements = {"measurements/%s" % p.relative_to(copy).as_posix()
                        for p in copy.rglob("*") if p.is_file()}
        png = "previews/overviews/%s.PNG" % name
        assert set(zf.namelist()) == measurements | {"%s.JSON" % name, png}
        assert feature["properties"]["links"]["measurements"][0]["href"].lstrip("/") in measurements
        with Image.open(zf.open(png)) as im:
            assert im.format == "PNG"


def test_packager_rejects_a_measurements_href_outside_the_delivery(spaces_in, work):
    _, feature, mf = converted(ORT1, ORT1_OID, spaces_in, work)
    feature["properties"]["links"]["measurements"][0]["href"] = "/measurements/missing.tif"
    mf.write_text(json.dumps(feature), encoding="utf-8")
    with pytest.raises(Exception, match="not among the delivery files"):
        PKG.package_one(mf)


def test_packager_rejects_a_citation_that_is_not_an_entry(spaces_in, work):
    _, feature, mf = converted(ORT1, ORT1_OID, spaces_in, work)
    step = feature["properties"]["productInformation"]["resourceLineage"][0]["processStep"][0]
    step["source"][0]["sourceCitation"]["title"] = "100527P500000000PF_00O4_ql.tfw"
    mf.write_text(json.dumps(feature), encoding="utf-8")
    with pytest.raises(Exception, match="delivery entry"):
        PKG.package_one(mf)
