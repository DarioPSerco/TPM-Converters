import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_worldview.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def browses(native):
    return sorted(p for p in native.rglob("*") if p.is_file() and p.name.upper().endswith("-BROWSE.JPG"))


def pick_canonical(bs, product_type):
    """Overview source: the MUL browse for an MS product type, the PAN one
    for a PAN product type (same rule as package_geoeye_zips.py)."""
    if len(bs) == 1:
        return bs[0]
    want_mul = not product_type.endswith("PAN")
    for b in bs:
        d = b.parent.name.upper()
        if want_mul and d.endswith("_MUL"):
            return b
        if (not want_mul) and (d.endswith("_PAN") or d.endswith("_PSH")):
            return b
    return bs[0]


def png_bytes(jpg):
    buf = io.BytesIO()
    Image.open(jpg).save(buf, format="PNG")
    return buf.getvalue()


def add_tree(zf, folder, arc_root):
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def package_one(mf):
    """One EOPF-EOS product per native order: the whole order folder (PAN and
    MUL components, order-level README/LAYOUT, GIS_FILES) goes under
    measurements/, as for GeoEye-1 and QuickBird."""
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = json_template.lineage_citation(d)
    native_id = citation.replace("_README.XML", "")
    native = spaces.find_native(citation, SPACES)
    bs = browses(native)
    canon = pick_canonical(bs, ptype)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, %d browse, canon %s)" % (out.name, native_id, ptype, len(bs), canon.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.writestr("preview/overviews/%s.PNG" % product, png_bytes(canon))
        add_tree(zf, native, "measurements")
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
