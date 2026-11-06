import json
import shutil
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_pneo.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def find_native_file(marker_name, sp):
    # file-native variant of spaces.find_native: the citation IS the delivery
    # ZIP itself (origName = basename of the .zip entry), not a marker inside
    # a folder - return the file, not its parent
    roots = spaces.search_roots(sp)
    for label, root in roots:
        for hit in sorted(root.rglob(marker_name)):
            if hit.is_file():
                return hit
    raise FileNotFoundError(
        "%s not found; searched: %s"
        % (marker_name, ", ".join(str(r) for _, r in roots) or "no existing space")
    )


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    links = d["properties"]["links"]
    citation = json_template.lineage_citation(d)
    native = find_native_file(citation, SPACES)

    # The delivery ZIP is unpacked into measurements/ (spec section 3.3),
    # its layout kept, so the manifest's measurements hrefs resolve inside
    # the package.
    with zipfile.ZipFile(native) as src:
        members = [i for i in src.infolist() if not i.is_dir()]
    packed = {"measurements/%s" % i.filename for i in members}
    for link in links["measurements"]:
        href = link["href"].lstrip("/")
        if href not in packed:
            raise Exception("measurements href %s is not in the delivery %s" % (href, native.name))

    # The converter writes the overview PNG(s) next to the manifest in
    # OUTSPACE, named as the previews hrefs.
    browses = []
    for link in links["previews"]:
        href = link["href"].lstrip("/")
        browse = OUTSPACE / Path(href).name
        if not browse.is_file():
            raise Exception("no overview %s in OUTSPACE for %s" % (browse.name, product))
        browses.append((browse, href))

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, %d file(s), type %s, %d browse(s))" % (
        out.name, native.name, len(members), ptype, len(browses)))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf, \
            zipfile.ZipFile(native) as src:
        zf.write(mf, "%s.JSON" % product)
        for browse, href in browses:
            zf.write(browse, href)
        for info in members:
            # streamed: a Pleiades-NEO image can be several GB
            with src.open(info) as fin, zf.open("measurements/%s" % info.filename, "w",
                                                force_zip64=True) as fout:
                shutil.copyfileobj(fin, fout, 1024 * 1024)
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
