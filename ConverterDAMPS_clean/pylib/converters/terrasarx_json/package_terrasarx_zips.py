import json
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_terrasarx.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def add_tree(zf, folder, arc_root):
    # Whole-tree walk: the product folder holds the main annotation and the
    # IMAGEDATA / ANNOTATION / AUXRASTER / PREVIEW / SUPPORT folders, kept as
    # delivered.
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = json_template.lineage_citation(d)
    # the citation is the main annotation <product name>.xml: its folder is
    # the native product, stored under its own name in measurements/
    native = spaces.find_native(citation, SPACES)
    native_id = native.name

    # the converter re-encodes the native browse TIFF as the overview PNG,
    # next to the manifest in OUTSPACE
    browse = OUTSPACE / ("%s.PNG" % product)
    if not browse.is_file():
        raise Exception("no overview PNG in OUTSPACE for %s" % product)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, browse %s)" % (
        out.name, native_id, ptype, browse.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        # spec "Previews component": previews/overviews/<package name>.PNG
        zf.write(browse, "previews/overviews/%s.PNG" % product)
        add_tree(zf, native, "measurements/%s" % native_id)
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
