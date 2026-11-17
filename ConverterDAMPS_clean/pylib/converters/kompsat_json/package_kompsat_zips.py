import json
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
# kompsat_files has no eoSip_converter import: the packager must not pull in
# eoSip_converter (and its xml_nodes PYTHONPATH requirement)
sys.path.insert(0, str(BASE.parent))
from common import json_template, spaces
import kompsat_files as F

SPACES = spaces.read_spaces(BASE.parent / "ingest_kompsat.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    ptype = d["properties"]["productInformation"]["productType"]
    citation = json_template.lineage_citation(d)
    if not citation.lower().endswith(F.METADATA_EXT):
        raise Exception("lineage citation is not a KOMPSAT AUX metadata file: %s" % citation)
    entry = spaces.find_native(citation, SPACES) / citation
    native = Path(F.product_root(entry))

    # Only the product's own files (the whole scene for a KOMPSAT-2 bundle):
    # a delivery folder may hold several products. Their layout below the
    # product root is kept, so the manifest's measurements href resolves.
    files = [Path(p) for p in F.product_files(entry, str(native))]
    href = d["properties"]["links"]["measurements"][0]["href"].lstrip("/")
    if not any("measurements/%s" % p.relative_to(native).as_posix() == href for p in files):
        raise Exception("measurements href %s is not among the product files" % href)

    browse = OUTSPACE / ("%s.PNG" % product)
    if not browse.is_file():
        raise Exception("no overview PNG in OUTSPACE for %s" % product)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, %d file(s), type %s, browse %s)" % (
        out.name, citation, len(files), ptype, browse.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.write(browse, "previews/overviews/%s.PNG" % product)
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
