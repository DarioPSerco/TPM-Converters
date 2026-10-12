"""Structural proof: drive terrasarx_json extraction on TerraSAR-X /
TanDEM-X fixtures, emit the JSON manifest via the common template generator,
and assert the output matches feature_template_tsx.json key-path for
key-path, with the values of the real products.

Fixtures (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): the real main annotations
of five real products, cut down to the elements the converter reads, with a
shrunk real browse image and placeholder image data files.
"""
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from terrasarx_json import product_terrasarx, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_tsx"


def _annotation(label):
    return next((FIXTURE_DIR / label).glob("T[SD]X1_SAR__*.xml"))


SSC_SL = _annotation("SSC_SL")
SSC_HS = _annotation("SSC_HS")
MGD_SL = _annotation("MGD_SL")
GEC_SC = _annotation("GEC_SC")
EEC_SC = _annotation("EEC_SC")
ALL = [SSC_SL, SSC_HS, MGD_SL, GEC_SC, EEC_SC]

# the sixteen product types of the specialization, Tables 1 and 2
ALLOWED_PRODUCT_TYPES = {
    "L1BSL__SLC", "L1BSL__MGC", "L1BSL__GEC", "L1BSL__EEC",
    "L1BSM__GEC", "L1BSM__SLC", "L1BSM__MGD", "L1BSM__EEC",
    "L1BSC__SLC", "L1BSC__MGD", "L1BSC__GEC", "L1BSC__EEC",
    "L1BSCW_SLC", "L1BSCW_MGD", "L1BSCW_GEC", "L1BSCW_EEC",
}

OPTICAL_KEYS = ["cloudCover", "illuminationAzimuthAngle", "illuminationElevationAngle"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(xml_path, work_folder):
    prod = product_terrasarx.Product_TerraSARX(str(xml_path))
    prod.setDebug(0)
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, _ProcessInfoStub(str(work_folder)))
    return prod, met


def _feature(xml_path, work_folder, eo_name="TSX_OPER_TEST"):
    prod, met = _extract(xml_path, work_folder)
    # the ingester passes the entry file's basename, as here
    mission, dynamic = json_emitter.build_layers(
        met, prod, eo_name, native_product_name=os.path.basename(str(xml_path)))
    feature = json_template.build(mission, dynamic, template_path=json_emitter.TEMPLATE_PATH)
    return prod, met, feature


def _key_paths(node, prefix="$"):
    paths = set()
    if isinstance(node, dict):
        for k, v in node.items():
            paths |= _key_paths(v, "%s.%s" % (prefix, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            paths |= _key_paths(v, "%s[%d]" % (prefix, i))
    else:
        paths.add(prefix)
    return paths


def _acq(feature):
    return feature["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]


@pytest.mark.parametrize("xml_path", ALL, ids=lambda p: p.parent.name)
def test_emitted_json_matches_template_structure(xml_path, tmp_path):
    _, _, feature = _feature(xml_path, tmp_path)
    json_template.validate(feature)

    with open(json_emitter.TEMPLATE_PATH, encoding="utf-8") as fd:
        template = json.load(fd)
    template["geometry"]["coordinates"] = feature["geometry"]["coordinates"]
    template["properties"]["acquisitionInformation"][0]["acquisitionParameters"][0]["wavelengths"][0][
        "discreteWavelengths"] = [0.0]
    got, want = _key_paths(feature), _key_paths(template)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))

    text = json.dumps(feature)
    for key in OPTICAL_KEYS:
        assert key not in text
    assert feature["properties"]["productInformation"]["productType"] in ALLOWED_PRODUCT_TYPES

    ring = feature["geometry"]["coordinates"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert ring[0] == ring[-1] and len(ring) == 5


def test_spotlight_ssc_values(tmp_path):
    prod, met, feature = _feature(SSC_SL, tmp_path)
    props = feature["properties"]
    acq = _acq(feature)
    pinfo = props["productInformation"]
    step = pinfo["resourceLineage"][0]["processStep"][0]

    assert pinfo["productType"] == "L1BSL__SLC"
    assert acq["operationalMode"] == "SL"
    assert acq["beginningDateTime"] == "2008-03-11T14:18:59.153Z"
    assert acq["endingDateTime"] == "2008-03-11T14:19:00.653Z"
    assert props["date"] == "2008-03-11T14:18:59.153Z/2008-03-11T14:19:00.653Z"
    assert acq["polarisationMode"] == "S"
    assert acq["polarisationChannels"] == "HH"
    assert acq["antennaLookDirection"] == "RIGHT"
    assert acq["rangeResolution"] == 1.625
    assert acq["azimuthResolution"] == 1.6
    assert acq["resolution"] == 1.625
    assert acq["acquisitionAngles"]["incidenceAngle"] == 46.421
    assert acq["orbitNumber"] == 4107
    assert acq["orbitDirection"] == "ASCENDING"
    assert acq["acquisitionType"] == "NOMINAL"
    assert acq["wavelengths"] == [{"spectralRange": "X", "discreteWavelengths": [0.0310666]}]

    platform = props["acquisitionInformation"][0]["platform"]
    instrument = props["acquisitionInformation"][0]["instrument"]
    assert platform == {"platformShortName": "TerraSAR-X", "orbitType": "LEO"}
    assert instrument == {"instrumentShortName": "TSX-1", "sensorType": "RADAR"}

    assert props["status"] == "ACQUIRED"
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert pinfo["processingLevel"] == "1B"
    assert pinfo["processingDate"] == "2017-12-11T13:42:42.000Z"
    assert pinfo["size"] == prod.tmpSize
    assert step["source"][0]["sourceCitation"]["title"] == SSC_SL.name
    assert step["source"][0]["processedLevel"]["code"] == "L1B"
    assert step["description"] == "EOPF-EOS Converter for TerraSAR-X and TanDEM-X"
    assert step["stepDateTime"]["created"] == props["created"]
    assert step["output"][0]["sourceCitation"]["title"] == "TSX_OPER_TEST.ZIP"

    links = props["links"]
    assert links["measurements"][0] == {
        "href": "/measurements/%s/IMAGEDATA/IMAGE_HH_SRA_spot_070.cos" % SSC_SL.stem,
        "type": "application/octet-stream",
        "title": "Native EO Product", "category": "DATA"}
    assert links["previews"][0] == {"href": "/previews/overviews/TSX_OPER_TEST.PNG",
                                    "type": "image/png", "title": "Preview Image",
                                    "category": "OVERVIEW"}

    ring = feature["geometry"]["coordinates"][0]
    assert {(round(lon, 3), round(lat, 3)) for lon, lat in ring} == {
        (56.230, 27.152), (56.344, 27.169), (56.328, 27.264), (56.212, 27.247)}


def test_high_resolution_spotlight_is_sl(tmp_path):
    _, _, feature = _feature(SSC_HS, tmp_path)
    acq = _acq(feature)
    assert feature["properties"]["productInformation"]["productType"] == "L1BSL__SLC"
    assert acq["operationalMode"] == "SL"
    assert acq["beginningDateTime"] == "2007-11-29T17:07:32.109Z"
    assert acq["endingDateTime"] == "2007-11-29T17:07:32.841Z"


def test_tandemx_spotlight_mgd(tmp_path):
    _, _, feature = _feature(MGD_SL, tmp_path)
    props = feature["properties"]
    acq = _acq(feature)
    # the spec names the spotlight MGD product L1BSL__MGC
    assert props["productInformation"]["productType"] == "L1BSL__MGC"
    assert props["acquisitionInformation"][0]["platform"]["platformShortName"] == "TanDEM-X"
    assert props["acquisitionInformation"][0]["instrument"]["instrumentShortName"] == "TOR"
    assert acq["orbitNumber"] == 61648
    assert acq["resolution"] == 3.909
    assert props["links"]["measurements"][0]["type"] == "image/tiff; application=geotiff"


@pytest.mark.parametrize("xml_path, typecode, epsg, direction", [
    (GEC_SC, "L1BSC__GEC", 32611, "ASCENDING"),
    (EEC_SC, "L1BSC__EEC", 32616, "DESCENDING"),
], ids=["GEC_SC", "EEC_SC"])
def test_geocoded_scansar_utm(xml_path, typecode, epsg, direction, tmp_path):
    _, _, feature = _feature(xml_path, tmp_path)
    pinfo = feature["properties"]["productInformation"]
    assert pinfo["productType"] == typecode
    assert _acq(feature)["operationalMode"] == "SC"
    assert _acq(feature)["orbitDirection"] == direction
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/%d" % epsg


@pytest.mark.parametrize("xml_path", ALL, ids=lambda p: p.parent.name)
def test_quicklook_png(xml_path, tmp_path):
    prod, _ = _extract(xml_path, tmp_path)
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    with Image.open(png) as image, Image.open(prod.browse_file()) as browse:
        assert image.format == "PNG"
        assert image.size == browse.size
        assert image.getextrema() == browse.getextrema()


def test_type_code_table_matches_spec():
    assert set(product_terrasarx.TYPECODE_MAP.values()) == ALLOWED_PRODUCT_TYPES
    assert all(len(code) == 10 for code in ALLOWED_PRODUCT_TYPES)


def test_unsupported_imaging_mode_fails(tmp_path):
    prod = product_terrasarx.Product_TerraSARX(str(SSC_SL))
    prod.root.find("productInfo/acquisitionInfo/imagingMode").text = "XX"
    with pytest.raises(Exception, match="unsupported TerraSAR-X imaging mode"):
        prod.extractMetadata(M.Metadata(None), _ProcessInfoStub(str(tmp_path)))


def test_dual_polarisation(tmp_path):
    prod = product_terrasarx.Product_TerraSARX(str(SSC_SL))
    acquisition = prod.root.find("productInfo/acquisitionInfo")
    acquisition.find("polarisationMode").text = "DUAL"
    ET.SubElement(acquisition.find("polarisationList"), "polLayer").text = "VV"
    met = M.Metadata(None)
    prod.extractMetadata(met, _ProcessInfoStub(str(tmp_path)))
    assert met.getMetadataValue(M.METADATA_POLARISATION_MODE) == "D"
    assert met.getMetadataValue(M.METADATA_POLARISATION_CHANNELS) == "HH, VV"
