"""Pytest bootstrap for iceye_json tests.

Puts the converters root and the ICEYE xml_nodes version (v101, per cfg
[eoSip] VERSION=101) on sys.path so the test runs standalone:
pytest pylib/converters/iceye_json/test
(eoSip_converter is expected to be importable / pip-installed editable.)
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
_converters = _here.parents[2]            # pylib/converters
_xml_nodes_v101 = _here.parents[3] / "xml_nodes" / "v101"

for _p in (_converters, _xml_nodes_v101):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
