"""Pytest bootstrap for pleiades_json tests.

Puts the converters root and the Pleiades xml_nodes version (v100, per cfg
[eoSip] VERSION=100) on sys.path so the test runs standalone:
pytest pylib/converters/pleiades_json/test
(eoSip_converter is expected to be importable / pip-installed editable.)
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve()
_converters = _here.parents[2]            # pylib/converters
_xml_nodes_v100 = _here.parents[3] / "xml_nodes" / "v100"

for _p in (_converters, _xml_nodes_v100):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
