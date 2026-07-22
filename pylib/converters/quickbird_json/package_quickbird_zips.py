import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_quickbird.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def browses(native):
    return sorted(p for p in native.rglob("*") if p.is_file() and p.name.upper().endswith("-BROWSE.JPG"))


def pick_canonical(bs):
    # two browses (MUL + PAN); MUL-preferred, cf. package_geoeye_zips.py.
    # Matches product_quickbird.makeBrowses (canonical = mulBrowsePath, the
    # browse under a *_MUL/ folder). Unconditional MUL-preference is faithful
    # for every QuickBird type; a pure-PAN product has no _MUL browse and falls
    # through to bs[0].
    if len(bs) == 1:
        return bs[0]
    for b in bs:
        if b.parent.name.upper().endswith("_MUL"):
            return b
    return bs[0]


def png_bytes(jpg):
    buf = io.BytesIO()
    Image.open(jpg).save(buf, format="PNG")
    return buf.getvalue()


def add_tree(zf, folder, arc_root):
    # Whole-tree walk (GeoEye-style). QuickBird's GIS_FILES/ lives INSIDE the
    # native folder, so this captures GIS_FILES/*_PIXEL_SHAPE.* automatically —
    # no WorldView addGisFiles special-casing needed.
    for p in folder.rglob("*"):
        if p.is_file():
            zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = pinfo["resourceLineage"]["processStep"]["source"]["citation"]
    native_id = citation.replace("_README.XML", "")
    native = spaces.find_native(citation, SPACES)
    bs = browses(native)
    canon = pick_canonical(bs)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, %d browse, canon %s [%s])" % (
        out.name, native_id, ptype, len(bs), canon.name, canon.parent.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        d["properties"]["links"]["preview"][0]["href"] = "preview/%s.PNG" % product
        zf.writestr("%s.JSON" % product, json.dumps(d, indent=2, ensure_ascii=False).encode("utf-8"))
        zf.writestr("preview/%s.PNG" % product, png_bytes(canon))
        add_tree(zf, native, native_id)
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
