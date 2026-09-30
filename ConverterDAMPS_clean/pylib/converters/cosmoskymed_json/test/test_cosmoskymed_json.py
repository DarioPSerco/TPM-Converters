"""Structural proof: drive cosmoskymed_json extraction on SYNTHETIC native
COSMO-SkyMed products, emit the JSON manifest via the common template
generator, and assert the output matches TDS/template/CSK-template.json
key-path for key-path - SAR fields present, optical fields absent, no
placeholder left.

Fixtures are SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md). The HIMAGE
fixture's values are those of the real TDS product the converter was run on end
to end, so the asserted values are real-product values; the PINGPONG fixture is
invented and proves the dual-pol / Level 1A branches only.
"""
import json
import os
from pathlib import Path

import pytest

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from cosmoskymed_json import product_cosmoskymed, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_csk"
HIM_NAME = "CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301"
HIM_H5 = FIXTURE_DIR / HIM_NAME / "736299-502923" / ("%s.h5" % HIM_NAME)
SPP_NAME = "CSKS4_SCSU_PP_01_HH_RA_FF_20200704101010_20200704101020"
SPP_H5 = FIXTURE_DIR / SPP_NAME / "800001" / ("%s.h5" % SPP_NAME)
GEC_NAME = "CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732"
GEC_TGZ = FIXTURE_DIR / GEC_NAME / "1008699" / ("%s.tgz" % GEC_NAME)
CSK_TEMPLATE = Path(__file__).resolve().parents[4] / "TDS" / "template" / "CSK-template.json"

# EO product names as the naming convention builds them
# (<MMM>_<CCCC>_<TTTTTTTTTT>_<start>_<stop>_<vvvv>)
HIM_EO_NAME = "CS__OPER_L1BSM__DGM_20170515T172253_20170515T172301_0001"
SPP_EO_NAME = "CS__OPER_L1ASMU_SCS_20200704T101010_20200704T101020_0001"
GEC_EO_NAME = "CS__OPER_L1CSC__GEC_20171007T160717_20171007T160732_0001"

# the ten product types the specialization allows
ALLOWED_PRODUCT_TYPES = {
    "L1ASMU_SCS", "L1ASMB_SCS", "L1BSM__DGM", "L1CSM__GEC", "L1DSM__GTC",
    "L1ASCU_SCS", "L1ASCB_SCS", "L1BSC__DGM", "L1CSC__GEC", "L1DSC__GTC",
}


OPTICAL_KEYS = ["cloudCover", "illuminationAzimuthAngle", "illuminationElevationAngle",
                "snowCover", "sunAzimuthAngle"]
OPTICAL_TOKENS = ["GeoEye", "GE01", "WorldView", "QuickBird", "Pleiades", "ICEYE",
                  "OPTICAL", "VIS"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(h5_path, work_folder):
    prod = product_cosmoskymed.Product_CosmoSkymed(str(h5_path))
    prod.setDebug(0)
    pi = _ProcessInfoStub(str(work_folder))
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    prod.extractMetadata(met, pi)
    return prod, met


def _feature(h5_path, eo_name, work_folder, native_product_name=None):
    prod, met = _extract(h5_path, work_folder)
    # the ingester passes the entry file's basename, as here
    mission, dynamic = json_emitter.build_layers(
        met, prod, eo_name,
        native_product_name=native_product_name or os.path.basename(str(h5_path)))
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
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


def test_emitted_json_matches_csk_template_structure(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _, _, feature = _feature(HIM_H5, HIM_EO_NAME, work)
    json_template.validate(feature)

    with open(CSK_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)

    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_sar_values_present_and_no_placeholder(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _, _, feature = _feature(HIM_H5, HIM_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    par = acq["acquisitionParameters"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert len(feature["geometry"]["coordinates"][0]) == 5
    assert feature["geometry"]["coordinates"][0][0] == feature["geometry"]["coordinates"][0][-1]
    assert props["status"] == "ACQUIRED"
    assert props["date"] == "2017-05-15T17:22:53.648Z/2017-05-15T17:23:01.196Z"
    assert props["created"] == "2019-10-08T18:49:23.433Z"
    assert acq["platform"]["platformShortName"] == "COSMO-SkyMed-1"
    assert acq["platform"]["orbitType"] == "LEO"
    assert acq["instrument"]["instrumentShortName"] == "SAR-2000"
    assert acq["instrument"]["sensorType"] == "RADAR"
    assert par["acquisitionType"] == "NOMINAL"
    assert par["operationalMode"] == "HIM"
    assert par["rangeResolution"] == 5.0
    assert par["azimuthResolution"] == 5.0
    assert par["resolution"] == 5.0
    assert par["wavelengths"][0] == {"spectralRange": "X-Band",
                                     "discreteWavelength": 0.0312284,
                                     "startWavelength": 0.028,
                                     "stopWavelength": 0.052}
    assert par["polarisationMode"] == "S"
    assert par["polarisationChannel"] == "HH"
    assert par["orbitNumber"] == 53764
    assert par["orbitDirection"] == "DESCENDING"
    assert par["acquisitionAngles"]["incidenceAngle"] == pytest.approx(26.601576)

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1BSM__DGM"
    assert pinfo["productType"] in ALLOWED_PRODUCT_TYPES
    assert pinfo["processingLevel"] == "1B"
    assert pinfo["processingDate"] == "2019-10-08T18:49:23.433Z"
    assert isinstance(pinfo["size"], int) and pinfo["size"] > 0

    step = pinfo["resourceLineage"][0]["processStep"][0]
    assert step["source"][0]["sourceCitation"]["title"] == "%s.h5" % HIM_NAME
    assert step["source"][0]["processedLevel"]["code"] == "L1B"
    assert step["output"][0]["sourceCitation"]["title"] == "%s.ZIP" % HIM_EO_NAME

    links = props["links"]
    assert links["measurements"][0]["href"] == "/measurements/%s.h5" % HIM_NAME
    assert links["measurements"][0]["type"] == "application/vnd.hdfgroup.hdf5"
    assert links["measurements"][0]["title"] == "Native EO Product"
    assert links["measurements"][0]["category"] == "DATA"
    assert links["preview"][0]["href"] == "/preview/overviews/%s.PNG" % HIM_EO_NAME
    assert links["preview"][0]["type"] == "image/png"
    assert links["preview"][0]["title"] == "Preview Image"
    assert links["preview"][0]["category"] == "OVERVIEW"


def test_dual_polarisation_and_level_1a(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _, _, feature = _feature(SPP_H5, SPP_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "SPP"
    assert par["polarisationMode"] == "D"
    assert par["polarisationChannel"] == "HH,VV"
    assert par["rangeResolution"] == 20.0
    assert par["azimuthResolution"] == 15.0
    # single figure: worst of the two directions
    assert par["resolution"] == 20.0
    assert props["acquisitionInformation"][0]["platform"]["platformShortName"] == "COSMO-SkyMed-4"
    assert props["productInformation"]["productType"] == "L1ASMU_SCS"
    assert props["productInformation"]["productType"] in ALLOWED_PRODUCT_TYPES
    assert props["productInformation"]["processingLevel"] == "1A"
    step = props["productInformation"]["resourceLineage"][0]["processStep"][0]
    assert step["source"][0]["processedLevel"]["code"] == "L1A"


def test_geotiff_tgz_delivery_scansar_level_1c(tmp_path):
    """SCANSAR WIDEREGION GeoTIFF delivery: metadata from the attribute XML
    inside the .tgz, four subswaths but ONE polarisation channel."""
    work = tmp_path / "work"
    work.mkdir()
    prod, _, feature = _feature(GEC_TGZ, GEC_EO_NAME, work)
    assert json_template.find_placeholders(feature) == []
    assert prod.native_format == product_cosmoskymed.FORMAT_GEOTIFF
    assert prod.beam_names == ["S01", "S02", "S03", "S04"]

    props = feature["properties"]
    par = props["acquisitionInformation"][0]["acquisitionParameters"][0]
    assert par["operationalMode"] == "SCW"
    # four subswaths, all HH: one DISTINCT channel, so single polarisation
    assert par["polarisationMode"] == "S"
    assert par["polarisationChannel"] == "HH"
    assert par["rangeResolution"] == 30.0
    assert par["azimuthResolution"] == 30.0
    assert par["orbitNumber"] == 55911
    assert par["orbitDirection"] == "DESCENDING"
    assert par["acquisitionAngles"]["incidenceAngle"] == pytest.approx(30.409467)
    assert par["wavelengths"][0]["discreteWavelength"] == 0.031228

    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1CSC__GEC"
    assert pinfo["productType"] in ALLOWED_PRODUCT_TYPES
    assert pinfo["processingLevel"] == "1C"
    # size is the UNCOMPRESSED content, which is what lands in measurements/
    assert pinfo["size"] > GEC_TGZ.stat().st_size

    step = pinfo["resourceLineage"][0]["processStep"][0]
    # lineage cites the delivered file, the link points at the image file
    assert step["source"][0]["sourceCitation"]["title"] == "%s.tgz" % GEC_NAME
    assert step["source"][0]["processedLevel"]["code"] == "L1C"
    link = props["links"]["measurements"][0]
    assert link["href"] == "/measurements/%s.MBI.tif" % GEC_NAME
    assert link["type"] == "image/tiff"


def test_geotiff_tgz_structure_matches_template(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _, _, feature = _feature(GEC_TGZ, GEC_EO_NAME, work)
    with open(CSK_TEMPLATE, encoding="utf-8") as fd:
        reference = json.load(fd)
    got = _key_paths(feature)
    want = _key_paths(reference)
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_quicklook_from_tgz_geotiff(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, _ = _extract(GEC_TGZ, work)
    png = tmp_path / ("%s.PNG" % GEC_EO_NAME)
    prod.writeQuicklook(str(png))

    from PIL import Image
    with Image.open(png) as im:
        assert im.format == "PNG"
        assert im.size == (8, 6)


def test_unknown_native_format_is_rejected(tmp_path):
    bogus = tmp_path / "CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301.zip"
    bogus.write_bytes(b"not a native product")
    with pytest.raises(Exception, match="not a COSMO-SkyMed native product"):
        product_cosmoskymed.Product_CosmoSkymed(str(bogus))


def test_typecode_map_is_exactly_the_allowed_product_types():
    modes = set(product_cosmoskymed.MODE_MAP.values())
    families = set(product_cosmoskymed.MODE_FAMILY.values())
    natives = set(product_cosmoskymed.LEVEL_MAP)

    assert modes == {"HIM", "SPP", "SCW", "SCH"}
    assert families == {"SM", "SC"}
    # every mode/level combination maps, and only to an allowed type
    assert set(product_cosmoskymed.TYPECODE_MAP) == {
        (n, f) for n in natives for f in families}
    assert set(product_cosmoskymed.TYPECODE_MAP.values()) == ALLOWED_PRODUCT_TYPES
    # the package naming convention gives the type code exactly 10 characters
    for code in ALLOWED_PRODUCT_TYPES:
        assert len(code) == 10, code


def test_quicklook_written_as_png(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, _ = _extract(HIM_H5, work)
    png = tmp_path / ("%s.PNG" % HIM_EO_NAME)
    prod.writeQuicklook(str(png))
    assert png.is_file() and png.stat().st_size > 0

    from PIL import Image
    with Image.open(png) as im:
        assert im.format == "PNG"
        assert im.size == (8, 6)  # QLK raster is (6, 8)


def test_optical_fields_and_tokens_absent(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _, _, feature = _feature(HIM_H5, HIM_EO_NAME, work)
    paths = _key_paths(feature)
    for key in OPTICAL_KEYS:
        assert not any(key in p for p in paths), "optical field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OPTICAL_TOKENS:
        assert tok not in blob, "other-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()
    prod, met = _extract(HIM_H5, work)
    json_emitter.emit(met, prod, HIM_EO_NAME, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % HIM_EO_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
