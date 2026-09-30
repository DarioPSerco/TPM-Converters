import json
import sys
import tarfile
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve()
sys.path.insert(0, str(BASE.parents[1]))
from common import json_template, spaces

# local copy on purpose: importing the product module would pull in
# eoSip_converter (and its xml_nodes PYTHONPATH requirement) into the packager
TGZ_SUFFIXES = (".tgz", ".tar.gz")


def is_tgz(name):
    lowered = str(name).lower()
    return any(lowered.endswith(suffix) for suffix in TGZ_SUFFIXES)

SPACES = spaces.read_spaces(BASE.parent / "ingest_cosmoskymed.cfg")
OUTSPACE = SPACES["OUTSPACE"]
PRODUCTS = SPACES["PRODUCTS"]


def add_tgz_members(zf, archive, arc_root):
    """Write the members of a .tgz delivery straight into the ZIP, so
    measurements/ holds the native product UNCOMPRESSED, as the spec asks
    ("uncompressed when required"), with the supplier's own filenames."""
    n = 0
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf:
            if not member.isfile():
                continue
            name = member.name.replace("\\", "/").lstrip("./")
            with tf.extractfile(member) as src:
                info = zipfile.ZipInfo("%s/%s" % (arc_root, name))
                info.file_size = member.size
                with zf.open(info, "w") as dst:
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        dst.write(chunk)
            n += 1
    return n


def add_tree(zf, folder, arc_root):
    # Whole-tree walk: the native delivery folder holds the product file plus
    # the DFDN delivery note, the DFAS accompanying sheet and the checksum;
    # the spec keeps the native product package as delivered - except that a
    # .tgz delivery goes in uncompressed.
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        if is_tgz(p.name):
            n = add_tgz_members(zf, p, arc_root)
            print("   %s expanded: %d file(s)" % (p.name, n))
            continue
        zf.write(p, "%s/%s" % (arc_root, p.relative_to(folder).as_posix()))


def package_one(mf):
    d = json.loads(mf.read_text(encoding="utf-8"))
    product = d["id"]
    pinfo = d["properties"]["productInformation"]
    ptype = pinfo["productType"]
    citation = json_template.lineage_citation(d)
    native = spaces.find_native(citation, SPACES)
    native_id = native.name

    # COSMO-SkyMed ships its quicklook as an HDF5 dataset, so the converter
    # writes the overview PNG next to the manifest in OUTSPACE.
    browse = OUTSPACE / ("%s.PNG" % product)
    if not browse.is_file():
        raise Exception("no overview PNG in OUTSPACE for %s" % product)

    out = PRODUCTS / ("%s.ZIP" % product)
    print("=> %s  (native %s, type %s, browse %s)" % (
        out.name, native_id, ptype, browse.name))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
        zf.write(mf, "%s.JSON" % product)
        zf.write(browse, "preview/overviews/%s.PNG" % product)
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
