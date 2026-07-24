import json
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_iceye.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def browses(native):
    # ICEYE ships a native PNG quicklook (mandatory, cf. product_iceye
    # extractToPath) - no JPG->PNG conversion needed, unlike the optical
    # packagers.
    return sorted(p for p in native.rglob("*.png") if p.is_file() and "QUICKLOOK" in p.name.upper())


def add_tree(zf, folder, arc_root):
    # Whole-tree walk (GeoEye-style): the SLH-like folders hold two products
    # (GRD + SLC); per approval, each ZIP carries the full native folder.
    for p in folder.rglob("*"):
        if p.is_file():
            zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = pinfo["resourceLineage"]["processStep"]["source"]["citation"]
    native = spaces.find_native(citation, SPACES)
    native_id = native.name
    bs = browses(native)
    if not bs:
        raise Exception("no QUICKLOOK png in %s" % native)
    canon = bs[0]

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, %d browse, canon %s)" % (
        out.name, native_id, ptype, len(bs), canon.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.write(canon, "preview/overviews/%s.PNG" % product)
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
