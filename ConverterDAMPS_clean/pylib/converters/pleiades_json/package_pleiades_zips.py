import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import spaces

SPACES = spaces.read_spaces(BASE.parent / "ingest_pleiades.cfg")
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


def browses(native_zip):
    # quicklook inside the Airbus DIMAP delivery (PREVIEW_*.JPG); PENDING
    # real-TDS validation - refine the selection rule when data arrives
    with zipfile.ZipFile(native_zip) as zf:
        return sorted(n for n in zf.namelist()
                      if Path(n).name.upper().endswith((".JPG", ".PNG"))
                      and ("PREVIEW" in Path(n).name.upper()
                           or "QUICKLOOK" in Path(n).name.upper()))


def png_bytes(native_zip, member):
    with zipfile.ZipFile(native_zip) as zf:
        data = zf.read(member)
    if member.upper().endswith(".PNG"):
        return data
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, format="PNG")
    return buf.getvalue()


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = pinfo["resourceLineage"]["processStep"]["source"]["citation"]
    native = find_native_file(citation, SPACES)
    bs = browses(native)
    if not bs:
        raise Exception("no PREVIEW/QUICKLOOK browse in %s" % native)
    canon = bs[0]

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, %d browse, canon %s)" % (
        out.name, native.name, ptype, len(bs), Path(canon).name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.writestr("preview/overviews/%s.PNG" % product, png_bytes(native, canon))
        zf.write(native, "measurements/%s" % native.name)
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
