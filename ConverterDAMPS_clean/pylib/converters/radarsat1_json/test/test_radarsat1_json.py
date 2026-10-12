"""Structural proof: drive radarsat1_json extraction on RADARSAT-1 CEOS
fixtures, emit the JSON manifest via the common template generator, and
assert the output matches feature_template_rs1.json key-path for key-path,
with the values of the real products.

Fixtures (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): real metadata files
(.vol, .nvol, .sarl, .sart, .txt) of four real deliveries, with a synthetic
30 x 40 image data file (.sard) in place of the real one.
"""
import json
import os
from pathlib import Path

import pytest
from PIL import Image

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from radarsat1_json import product_radarsat1, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_rs1"
SGF_VOL = FIXTURE_DIR / "01Jul98_13866_01" / "01Jul98_13866_01.vol"
SLC_VOL = FIXTURE_DIR / "01Jul98_13866_02" / "01Jul98_13866_02.vol"
SSG_VOL = FIXTURE_DIR / "08Dec99_21364_01" / "08Dec99_21364_01.vol"
SCN_VOL = FIXTURE_DIR / "10Jul98_13990" / "M8067100_10Jul98_13990_SCN.vol"

# the ten product types of the specialization, Table 2
ALLOWED_PRODUCT_TYPES = {
    "L1_BM__SLC", "L1_BM__SGF", "L2_BM__SSG", "L1_BSW_SLC", "L1_BSW_SGF",
    "L1_BMF_SLC", "L1_BMF_SGF", "L1_BS__SGF", "L1_SCW____", "L1_SCN____",
}

OPTICAL_KEYS = ["cloudCover", "illuminationAzimuthAngle", "illuminationElevationAngle"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(vol_path, work_folder):
    prod = product_radarsat1.Product_Radarsat1(str(vol_path))
    prod.setDebug(0)
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, _ProcessInfoStub(str(work_folder)))
    return prod, met


def _feature(vol_path, work_folder, eo_name="RS1_OPER_TEST"):
    prod, met = _extract(vol_path, work_folder)
    # the ingester passes the entry file's basename, as here
    mission, dynamic = json_emitter.build_layers(
        met, prod, eo_name, native_product_name=os.path.basename(str(vol_path)))
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


@pytest.mark.parametrize("vol", [SGF_VOL, SLC_VOL, SSG_VOL, SCN_VOL], ids=lambda p: p.stem)
def test_emitted_json_matches_template_structure(vol, tmp_path):
    _, _, feature = _feature(vol, tmp_path)
    json_template.validate(feature)

    with open(json_emitter.TEMPLATE_PATH, encoding="utf-8") as fd:
        template = json.load(fd)
    template["geometry"]["coordinates"] = feature["geometry"]["coordinates"]
    got, want = _key_paths(feature), _key_paths(template)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))

    text = json.dumps(feature)
    for key in OPTICAL_KEYS:
        assert key not in text
    assert feature["properties"]["productInformation"]["productType"] in ALLOWED_PRODUCT_TYPES


def test_wide_sgf_values(tmp_path):
    prod, met, feature = _feature(SGF_VOL, tmp_path)
    props = feature["properties"]
    acq = _acq(feature)
    pinfo = props["productInformation"]
    step = pinfo["resourceLineage"][0]["processStep"][0]

    assert pinfo["productType"] == "L1_BSW_SGF"
    assert acq["operationalMode"] == "BSW"
    assert acq["beginningDateTime"] == "1998-07-01T18:17:05.402Z"
    assert acq["endingDateTime"] == "1998-07-01T18:17:27.289Z"
    assert props["date"] == "1998-07-01T18:17:05.402Z/1998-07-01T18:17:27.289Z"
    assert acq["polarisationMode"] == "S"
    assert acq["polarisationChannels"] == "HH"
    assert acq["antennaLookDirection"] == "RIGHT"
    assert acq["rangeResolution"] == 26.584
    assert acq["azimuthResolution"] == 27.358
    assert acq["resolution"] == 27.358
    assert acq["acquisitionAngles"]["incidenceAngle"] == 35.199
    assert acq["orbitNumber"] == 13866
    assert acq["orbitDirection"] == "ASCENDING"
    assert acq["acquisitionType"] == "NOMINAL"
    assert acq["wavelengths"] == [{"spectralRange": "C", "discreteWavelength": 0.0565646}]

    platform = props["acquisitionInformation"][0]["platform"]
    instrument = props["acquisitionInformation"][0]["instrument"]
    assert platform == {"platformShortName": "RADARSAT-1", "orbitType": "LEO"}
    assert instrument == {"instrumentShortName": "SAR", "sensorType": "RADAR"}

    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert pinfo["processingLevel"] == "1"
    assert pinfo["processingDate"] == "2016-01-15T19:56:03.000Z"
    assert pinfo["size"] == prod.tmpSize
    assert step["source"][0]["sourceCitation"]["title"] == "01Jul98_13866_01.vol"
    assert step["source"][0]["processedLevel"]["code"] == "L1"
    assert step["description"] == "EOPF-EOS Converter for RADARSAT-1"
    assert step["stepDateTime"]["created"] == props["created"]

    links = props["links"]
    assert links["measurements"][0] == {"href": "/measurements/01Jul98_13866_01.sard",
                                        "type": "application/octet-stream",
                                        "title": "Native EO Product", "category": "DATA"}
    assert links["previews"][0] == {"href": "/previews/overviews/RS1_OPER_TEST.PNG",
                                    "type": "image/png", "title": "Preview Image",
                                    "category": "OVERVIEW"}

    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5
    assert {(round(lon, 3), round(lat, 3)) for lon, lat in ring} == {
        (-2.394, 14.038), (-1.145, 14.288), (-2.118, 12.743), (-0.877, 12.995)}


def test_wide_slc_values(tmp_path):
    _, _, feature = _feature(SLC_VOL, tmp_path)
    acq = _acq(feature)
    assert feature["properties"]["productInformation"]["productType"] == "L1_BSW_SLC"
    assert acq["rangeResolution"] == 13.134
    assert acq["resolution"] == 13.134


def test_ssg_is_level_2_utm(tmp_path):
    _, _, feature = _feature(SSG_VOL, tmp_path)
    pinfo = feature["properties"]["productInformation"]
    step = pinfo["resourceLineage"][0]["processStep"][0]
    assert pinfo["productType"] == "L2_BM__SSG"
    assert _acq(feature)["operationalMode"] == "BM"
    assert pinfo["processingLevel"] == "2"
    assert step["source"][0]["processedLevel"]["code"] == "L2"
    # Peru, southern hemisphere, UTM zone 18
    assert pinfo["referenceSystemIdentifier"] == "http://www.opengis.net/def/crs/EPSG/0/32718"
    # no Processing Parameters record: times from the scene description
    assert _acq(feature)["beginningDateTime"] == "1999-12-08T10:30:08.070Z"
    assert _acq(feature)["endingDateTime"] == "1999-12-08T10:30:08.070Z"


def test_scansar_narrow_times_in_order(tmp_path):
    # the scene description lists stop (10:35:10) before start (10:35:58);
    # the Processing Parameters record (trailer) gives them in order
    _, _, feature = _feature(SCN_VOL, tmp_path)
    acq = _acq(feature)
    assert feature["properties"]["productInformation"]["productType"] == "L1_SCN____"
    assert acq["operationalMode"] == "SCN"
    assert acq["beginningDateTime"] == "1998-07-10T10:35:10.522Z"
    assert acq["endingDateTime"] == "1998-07-10T10:35:58.657Z"
    assert acq["rangeResolution"] == 70.0
    assert acq["azimuthResolution"] == 50.0


@pytest.mark.parametrize("vol", [SGF_VOL, SLC_VOL, SCN_VOL], ids=lambda p: p.stem)
def test_quicklook_png(vol, tmp_path):
    prod, _ = _extract(vol, tmp_path)
    png = tmp_path / "overview.PNG"
    prod.writeQuicklook(str(png))
    with Image.open(png) as image:
        assert image.format == "PNG"
        assert image.mode == "L"
        assert max(image.size) <= product_radarsat1.PREVIEW_MAX_SIZE
        assert image.getextrema()[1] > 0


def test_type_code_table_matches_spec():
    assert set(product_radarsat1.TYPECODE_MAP.values()) == ALLOWED_PRODUCT_TYPES
    assert all(len(code) == 10 for code in ALLOWED_PRODUCT_TYPES)


def test_unsupported_beam_mode_fails(tmp_path):
    prod = product_radarsat1.Product_Radarsat1(str(SGF_VOL))
    prod.scene["BEAM MODE"] = "SAR EXTENDED HIGH 3"
    with pytest.raises(Exception, match="unsupported RADARSAT-1 beam mode"):
        prod.extractMetadata(M.Metadata(None), _ProcessInfoStub(str(tmp_path)))
