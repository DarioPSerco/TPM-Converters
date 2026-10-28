"""Packager for Beijing-1 / NigeriaSat-1 / UK-DMC-1 EOPF-EOS products.

One OUTSPACE manifest -> one PRODUCTS/<ID>.ZIP (all entries STORED), per
"EOPF-EOS Specialization for Beijing-1, Nigeriasat-1 and UK-DMC-1 products"
1.0, sections 2.1, 3 and 4:

    <ID>.ZIP
    |-- <ID>.JSON                     manifest, byte-identical to OUTSPACE
    |-- measurements/<native tree>    the unzipped delivery, as delivered
    `-- previews/overviews/<ID>.PNG   the quicklook JPEG, re-encoded as PNG

The native unit is the folder holding the entry <dataset>.dim, which the
manifest lineage cites: every file under it (.dim, .tif, _ql.jpg, _meta.sip,
.htm, .xsl) goes to measurements/ with its relative path kept. One delivery
= one product.
"""
import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_dmc.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]

# local copies on purpose: importing product_dmc would pull in eoSip_converter
# (and its xml_nodes PYTHONPATH requirement) into the packager
DIM_EXTENSION = ".dim"


def dim_quicklook(dim):
    """The quicklook JPEG named by the .dim DATASET_QL_PATH, next to it
    (spec section 4: the overview; same rule as product_dmc)."""
    node = ET.parse(dim).getroot().find("Dataset_Id/DATASET_QL_PATH")
    href = node.get("href") if node is not None else None
    if not href:
        raise Exception("no Dataset_Id/DATASET_QL_PATH in %s" % dim)
    path = dim.parent / href
    if not path.is_file():
        raise Exception("quicklook %s named by %s not found" % (href, dim.name))
    return path


def png_bytes(jpg):
    buf = io.BytesIO()
    with Image.open(jpg) as im:
        im.save(buf, format="PNG")
    return buf.getvalue()


def native_files(native):
    """Every file of the delivery, sorted by relative path.

    The whole unzipped folder is the native product (spec section 3:
    content preserved), the .htm / .xsl rendering included."""
    return sorted((p for p in native.rglob("*") if p.is_file()),
                  key=lambda p: p.relative_to(native).as_posix())


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    ptype = d["properties"]["productInformation"]["productType"]
    citation = json_template.lineage_citation(d)
    if not citation.lower().endswith(DIM_EXTENSION):
        raise Exception("lineage citation is not a DIMAP header (%s): %s" % (DIM_EXTENSION, citation))
    native = spaces.find_native(citation, SPACES)

    browse = dim_quicklook(native / citation)
    files = native_files(native)
    packed = {"measurements/%s" % p.relative_to(native).as_posix() for p in files}
    for link in d["properties"]["links"]["measurements"]:
        href = link["href"].lstrip("/")
        if href not in packed:
            raise Exception("measurements href %s is not in the delivery" % href)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, %d file(s), type %s, browse %s)" % (
        out.name, native.name, len(files), ptype, browse.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        # spec section 4: previews/overviews/<package name>.PNG
        zf.writestr("previews/overviews/%s.PNG" % product, png_bytes(browse))
        for p in files:
            zf.write(p, "measurements/%s" % p.relative_to(native).as_posix())
    print("   done  %.1f MB" % (out.stat().st_size / 1e6))
    return native


if __name__ == "__main__":
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    failed = 0
    for mf in sorted(OUTSPACE.glob("*.JSON")):
        try:
            native = package_one(mf)
            print("PKG-OK\t%s\t%s" % (mf.name, native))
        except Exception as e:
            failed += 1
            print("PKG-FAIL\t%s\t%s" % (mf.name, e))
    print("ALL DONE ->", PRODUCTS)
    sys.exit(1 if failed else 0)
