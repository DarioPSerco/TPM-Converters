"""Pytest bootstrap for quickbird_json tests.

Puts the converters root and the canonical xml_nodes version (v200) on sys.path
so the test runs standalone:  pytest pylib/converters/quickbird_json/test
(eoSip_converter is expected to be importable / pip-installed editable.)
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
_converters = _here.parents[2]            # pylib/converters
_xml_nodes_v200 = _here.parents[3] / "xml_nodes" / "v200"

for _p in (_converters, _xml_nodes_v200):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
