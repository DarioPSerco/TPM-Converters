import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_worldview.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def browses(scene):
    return sorted(p for p in scene.rglob("*") if p.is_file() and p.name.upper().endswith("-BROWSE.JPG"))


def pick_canonical(bs):
    # one browse per product in all observed real data; if a multi-browse WV
    # product ever appears, add a selection rule here (e.g. MUL-preference,
    # cf. package_geoeye_zips.py pick_canonical)
    return bs[0]


def png_bytes(jpg):
    buf = io.BytesIO()
    Image.open(jpg).save(buf, format="PNG")
    return buf.getvalue()


def add_tree(zf, folder, arc_root):
    for p in folder.rglob("*"):
        if p.is_file():
            zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def pixel_shapes(scene, scene_xml):
    # per-scene PIXEL_SHAPE only, mirroring worldview/product_worldview.py addGisFiles
    # (NOT the order-level ORDER/PRODUCT/STRIP/TILE shapes). GIS_FILES sits at the
    # order-item root, one level above the scene folder.
    gis = scene.parent / "GIS_FILES"
    stem = scene_xml.replace(".XML", "_PIXEL_SHAPE")
    return [gis / ("%s.%s" % (stem, ext)) for ext in ("shp", "prj", "dbf", "shx")]


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    scene_xml = pinfo["resourceLineage"]["processStep"]["source"]["citation"]
    scene = spaces.find_native(scene_xml, SPACES)
    bs = browses(scene)
    canon = pick_canonical(bs)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (scene %s, type %s, %d browse, canon %s)" % (out.name, scene.name, ptype, len(bs), canon.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.writestr("preview/overviews/%s.PNG" % product, png_bytes(canon))
        add_tree(zf, scene, "measurements")
        shapes = [s for s in pixel_shapes(scene, scene_xml) if s.exists()]
        for s in shapes:
            zf.write(s, "measurements/GIS_FILES/%s" % s.name)
    print("   done  %.1f MB (%d pixel-shape files)" % (out.stat().st_size / 1e6, len(shapes)))
    return scene


if __name__ == "__main__":
    PRODUCTS.mkdir(parents=True, exist_ok=True)
    failed = 0
    for mf in sorted(OUTSPACE.glob("*.JSON")):
        try:
            scene = package_one(mf)
            print("PKG-OK\t%s\t%s" % (mf.name, scene))
        except Exception as e:
            failed += 1
            print("PKG-FAIL\t%s\t%s" % (mf.name, e))
    print("ALL DONE ->", PRODUCTS)
    sys.exit(1 if failed else 0)
