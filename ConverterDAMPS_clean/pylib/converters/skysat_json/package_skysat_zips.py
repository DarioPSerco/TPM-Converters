import json
import os
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

# local copy on purpose: importing the product module would pull in
# eoSip_converter (and its xml_nodes PYTHONPATH requirement) into the packager
METADATA_SUFFIX = "_metadata.json"


def item_files(folder, item_id):
    """Every file under folder belonging to the item: its name is the item id
    followed by '_' or '.' (same rule as product_skysat.item_files)."""
    found = []
    for root, dirs, files in os.walk(folder):
        for name in files:
            if name.startswith(item_id + "_") or name.startswith(item_id + "."):
                found.append(Path(root) / name)
    return sorted(found, key=lambda p: p.relative_to(folder).as_posix())


SPACES = spaces.read_spaces(BASE.parent / "ingest_skysat.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    links = d["properties"]["links"]
    citation = json_template.lineage_citation(d)
    if not citation.endswith(METADATA_SUFFIX):
        raise Exception("lineage citation is not an item metadata file: %s" % citation)
    item_id = citation[:-len(METADATA_SUFFIX)]
    native = spaces.find_native(citation, SPACES)

    # Only the item's own files: an Orders API delivery may hold several
    # items in one folder. Their layout below the entry folder is kept, so
    # the manifest's measurements hrefs resolve inside the ZIP.
    files = item_files(native, item_id)
    packed = {"measurements/%s" % p.relative_to(native).as_posix() for p in files}
    for link in links["measurements"]:
        href = link["href"].lstrip("/")
        if href not in packed:
            raise Exception("measurements href %s is not among the item files" % href)

    # SkySat delivers no browse image: the converter writes the overview
    # PNG(s) next to the manifest in OUTSPACE, named as the previews hrefs.
    browses = []
    for link in links["previews"]:
        href = link["href"].lstrip("/")
        browse = OUTSPACE / Path(href).name
        if not browse.is_file():
            raise Exception("no overview %s in OUTSPACE for %s" % (browse.name, product))
        browses.append((browse, href))

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (item %s, %d file(s), type %s, %d browse(s))" % (
        out.name, item_id, len(files), ptype, len(browses)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        for browse, href in browses:
            zf.write(browse, href)
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
