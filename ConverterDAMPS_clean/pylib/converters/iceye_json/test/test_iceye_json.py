"""Structural proof: drive iceye_json extraction on a SYNTHETIC native ICEYE
product, emit the JSON manifest via the common template generator, and assert
the output carries every key path of the ICEYE spec template — SAR fields
present, optical fields absent, no placeholder left.

Fixture is SYNTHETIC (see fixtures/SYNTHETIC_FIXTURE_NOTE.md): this proves
pipeline + structure only, NOT value-correctness on real data (PENDING TDS).
"""
import json
from pathlib import Path

from eoSip_converter.esaProducts import metadata as M
from common import json_template
from iceye_json import product_iceye, json_emitter

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_ice"
NATIVE_DIR = FIXTURE_DIR / "SYNTH_ICEYE_X1_SLC_SM_20160501T144606"
METADATA_XML = NATIVE_DIR / "SYNTH_ICEYE_X1_SLC_SM_20160501T144606.xml"
EO_PRODUCT_NAME = "ICE_OPER_L1_SM__SLC_20160501T144606_20160501T144616_0001"

OPTICAL_KEYS = ["cloudCover", "illuminationAzimuthAngle", "illuminationElevationAngle",
                "startWavelength", "stopWavelength"]
OPTICAL_TOKENS = ["GeoEye", "GE01", "GIS", "WorldView", "QuickBird", "BGI", "OPTICAL", "VIS"]


class _ProcessInfoStub:
    def __init__(self, work_folder):
        self.workFolder = work_folder

    def addLog(self, *args, **kwargs):
        pass


def _extract(work_folder):
    prod = product_iceye.Product_Iceye(str(METADATA_XML))
    prod.setDebug(0)
    pi = _ProcessInfoStub(str(work_folder))
    prod.extractToPath(str(work_folder))
    met = M.Metadata(None)
    # simulate the base ingester's [Mission-specific-values] cfg injection
    # (polarisation is cfg-fixed for ICEYE, not read from the native metadata)
    met.setMetadataPair(M.METADATA_POLARISATION_MODE, "S")
    met.setMetadataPair(M.METADATA_POLARISATION_CHANNELS, "VV")
    prod.extractMetadata(met, pi)
    return prod, met


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


def test_emitted_json_matches_spec_template_structure(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()

    prod, met = _extract(work)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    json_template.validate(feature)

    with open(json_emitter.TEMPLATE_PATH, encoding="utf-8") as fd:
        reference = json.load(fd)

    # coordinates: a placeholder string in the template, an array in the output
    got = {k for k in _key_paths(feature) if not k.startswith("$.geometry.coordinates")}
    want = {k for k in _key_paths(reference) if not k.startswith("$.geometry.coordinates")}
    # SLC: referenceSystemIdentifier optional (Table 14), the fixture has none
    assert got == want, "missing: %s / extra: %s" % (sorted(want - got), sorted(got - want))


def test_sar_values_present_and_no_placeholder(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, met = _extract(work)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    assert json_template.find_placeholders(feature) == []

    props = feature["properties"]
    acq = props["acquisitionInformation"][0]
    par = acq["acquisitionParameters"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert props["status"] == "ACQUIRED"
    assert acq["platform"]["platformShortName"] == "ICEYE"
    assert acq["platform"]["orbitType"] == "LEO"
    assert acq["instrument"]["instrumentShortName"] == "SAR"
    assert acq["instrument"]["sensorType"] == "RADAR"
    assert acq["platform"]["platformSerialIdentifier"] == 1
    assert par["operationalMode"] == "SM"
    assert par["orbitNumber"] == 53
    assert par["orbitDirection"] == "ASCENDING"
    assert par["polarisationMode"] == "S"
    assert par["polarisationChannels"] == "VV"
    assert par["antennaLookDirection"] == "LEFT"
    assert par["resolution"] == 3.0  # Table 10, L1_SM__SLC
    assert isinstance(par["azimuthResolution"], float)
    assert isinstance(par["rangeResolution"], float)
    assert par["wavelengths"] == [{"spectralRange": "X", "discreteWavelength": 31.0666e-3}]
    assert isinstance(par["acquisitionAngles"]["incidenceAngle"], float)
    pinfo = props["productInformation"]
    assert pinfo["productType"] == "L1_SM__SLC"
    assert pinfo["processingLevel"] == "1A"
    assert "referenceSystemIdentifier" not in pinfo
    assert isinstance(props["productInformation"]["size"], int)
    assert props["productInformation"]["size"] > 0
    lineage = props["productInformation"]["resourceLineage"][0]["processStep"][0]
    assert lineage["source"][0]["sourceCitation"]["title"] == NATIVE_DIR.name
    assert lineage["source"][0]["processedLevel"]["code"] == "L1A"
    meas = props["links"]["measurements"][0]
    assert meas["href"] == "/measurements/SYNTH_ICEYE_X1_SLC_SM_20160501T144606.h5"
    assert meas["type"] == "application/x-hdf5"
    assert meas["title"] == "Native EO Product"
    assert props["links"]["preview"][0]["title"] == "Preview Image"


def test_optical_fields_and_tokens_absent(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    prod, met = _extract(work)
    mission, dynamic = json_emitter.build_layers(met, prod, EO_PRODUCT_NAME)
    feature = json_template.build(mission, dynamic,
                                  template_path=json_emitter.TEMPLATE_PATH)
    paths = _key_paths(feature)
    for key in OPTICAL_KEYS:
        assert not any(key in p for p in paths), "optical field leaked: %s" % key
    blob = json.dumps(feature)
    for tok in OPTICAL_TOKENS:
        assert tok not in blob, "optical-mission token leaked: %s" % tok


def test_only_json_written_to_output_dir(tmp_path):
    work = tmp_path / "work"
    out = tmp_path / "out"
    work.mkdir()
    out.mkdir()
    prod, met = _extract(work)
    json_emitter.emit(met, prod, EO_PRODUCT_NAME, str(out))
    written = [p.name for p in out.iterdir()]
    assert written == ["%s.JSON" % EO_PRODUCT_NAME], written
    assert not any(n.upper().endswith((".XML", ".ZIP")) for n in written), written
