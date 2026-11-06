import configparser
import os
import re
import shutil
import tarfile
import zipfile
from pathlib import Path

# [Main] keys, same names/semantics as the base ingester (ingester.py:593-604).
SPACE_KEYS = ("INBOX", "TMPSPACE", "OUTSPACE", "DONESPACE", "FAILEDSPACE")

# delivery archives expand_zips unpacks when they sit directly in INBOX
ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tgz")


def extended_path(p):
    """Windows extended-length form (\\\\?\\C:\\...) of p: file APIs then accept
    paths over 260 characters without the LongPathsEnabled registry switch.
    Unchanged elsewhere."""
    if os.name != "nt":
        return Path(p)
    s = os.path.abspath(str(p))  # \\?\ turns normalisation off: do it first
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_spaces(cfg_path):
    cfg_path = Path(cfg_path).resolve()
    parser = configparser.RawConfigParser()
    parser.optionxform = str
    parser.read(cfg_path)
    # relative cfg paths are anchored at the repo root, like the CLI runs
    # (cwd = repo root); cfg sits at pylib/converters/<mission>/<cfg>
    root = cfg_path.parents[3]
    spaces = {}
    for key in SPACE_KEYS:
        raw = parser.get("Main", key)
        p = Path(raw)
        spaces[key] = p if p.is_absolute() else root / p
    try:
        raw = parser.get("Main", "PRODUCTS")
        p = Path(raw)
        spaces["PRODUCTS"] = p if p.is_absolute() else root / p
    except (configparser.NoOptionError, configparser.NoSectionError):
        spaces["PRODUCTS"] = spaces["OUTSPACE"].parent / "PRODUCTS"
    # opt-in per mission: natives whose own folder tree is already close to
    # 260 characters (TerraSAR-X DIMS deliveries) need the extended form
    spaces["EXTENDED_PATHS"] = os.name == "nt" and parser.getboolean(
        "Paths", "WINDOWS_EXTENDED_PATHS", fallback=False)
    if spaces["EXTENDED_PATHS"]:
        for key in SPACE_KEYS + ("PRODUCTS",):
            spaces[key] = extended_path(spaces[key])
    spaces["NAMEPATTERN"] = parser.get("Search", "FILES_NAMEPATTERN", fallback="^.*").strip()
    spaces["EXTPATTERN"] = parser.get("Search", "FILES_EXTPATTERN", fallback="^.*").strip()
    return spaces


def search_roots(spaces):
    # every place a native may legitimately sit: INBOX, staged trees in
    # TMPSPACE (STAGE_* only - batch_* workfolders are converter scratch),
    # and DONESPACE (already-processed, e.g. repackaging)
    roots = []
    if spaces["INBOX"].is_dir():
        roots.append(("INBOX", spaces["INBOX"]))
    if spaces["TMPSPACE"].is_dir():
        for stage in sorted(spaces["TMPSPACE"].glob("STAGE_*")):
            if stage.is_dir():
                roots.append(("TMPSPACE/%s" % stage.name, stage))
    if spaces["DONESPACE"].is_dir():
        roots.append(("DONESPACE", spaces["DONESPACE"]))
    return roots


def find_native(marker_name, spaces):
    """Locate the native holding the metadata file named marker_name
    (the manifest's source.citation), wherever it sits. Returns the folder
    containing the marker. Nesting below each root is arbitrary.
    A citation naming a folder (RADARSAT-2: every product has the same
    product.xml, so the citation is the product folder) returns that folder."""
    roots = search_roots(spaces)
    for label, root in roots:
        for hit in sorted(root.rglob(marker_name)):
            if hit.is_file():
                return hit.parent
        for hit in sorted(root.rglob(marker_name)):
            if hit.is_dir():
                return hit
    raise FileNotFoundError(
        "%s not found; searched: %s"
        % (marker_name, ", ".join(str(r) for _, r in roots) or "no existing space")
    )


def find_entries(spaces):
    """Entry metadata files to convert, in INBOX and TMPSPACE/STAGE_*,
    selected with the cfg's own [Search] patterns (fileHelper.select_files
    semantics: re.match on stem and on extension, dot included)."""
    name_re = re.compile(spaces["NAMEPATTERN"])
    ext_re = re.compile(spaces["EXTPATTERN"])
    entries = []
    for label, root in search_roots(spaces):
        if label == "DONESPACE":
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and name_re.match(p.stem) and ext_re.match(p.suffix):
                entries.append((p, root))
    return entries


def archive_suffix(path):
    """Archive suffix of path (.zip, .tar.gz, .tgz) or None."""
    lowered = path.name.lower()
    return next((s for s in ARCHIVE_SUFFIXES if lowered.endswith(s)), None)


def inbox_archives(spaces):
    """Delivery archives sitting directly in INBOX that expand_zips unpacks:
    every archive whose extension the mission does not ingest itself (.zip
    for PLEIADES/PNEO, .tgz for COSMO-SkyMed are native entries)."""
    if not spaces["INBOX"].is_dir():
        return []
    ext_re = re.compile(spaces["EXTPATTERN"])
    return [p for p in sorted(spaces["INBOX"].glob("*"))
            if p.is_file() and archive_suffix(p) and not ext_re.match(p.suffix)]


def _free_stage(tmpspace):
    # numbered, not named after the zip: native names are long enough that
    # STAGE_<stem>/<unit>/<file> breaks the 260-character Windows limit
    n = 1
    stage = tmpspace / ("STAGE_%d" % n)
    while stage.exists():
        n += 1
        stage = tmpspace / ("STAGE_%d" % n)
    return stage


def _archive_names(zp):
    if archive_suffix(zp) == ".zip":
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
    else:
        with tarfile.open(zp, "r:*") as tf:
            names = tf.getnames()
    names = [n.replace("\\", "/") for n in names]
    names = [n[2:] if n.startswith("./") else n for n in names]
    return [n for n in names if n.strip("/.")]


def _extract(zp, dest):
    if archive_suffix(zp) == ".zip":
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(dest)  # extractall drops absolute / ".." parts
    else:
        with tarfile.open(zp, "r:*") as tf:
            members = tf.getmembers()
            if os.name == "nt":
                # tarfile joins member names as stored ("a/b"): an extended
                # \\?\ destination needs native separators, nothing normalises them
                for m in members:
                    m.name = os.path.normpath(m.name)
                    if m.linkname:
                        m.linkname = os.path.normpath(m.linkname)
            tf.extractall(dest, members=members, filter="data")  # rejects absolute / ".." / links out


def expand_zips(spaces):
    """Unpack every delivery archive (.zip, .tar.gz, .tgz) sitting directly
    in INBOX into its own TMPSPACE/STAGE_<n>/ so the folder-based converters
    see a normal native unit. The original archive is moved next to the unit
    in the STAGE folder; move_unit deletes it on success (DONESPACE gets only
    the unpacked native) and archives it with the unit in FAILEDSPACE.
    Archives the mission ingests itself are left alone (inbox_archives).
    Returns [(archive_path, unit_path)]; a corrupt archive is left in INBOX."""
    expanded = []
    # top level only: an archive inside an unpacked native is product content
    for zp in inbox_archives(spaces):
        stem = zp.name[:-len(archive_suffix(zp))]
        stage = _free_stage(spaces["TMPSPACE"])
        try:
            names = _archive_names(zp)
            tops = {n.split("/", 1)[0] for n in names}
            # archive already wrapping one folder: that folder is the
            # unit; otherwise wrap the loose files in <stem>/
            wrapped = len(tops) == 1 and any("/" in n.rstrip("/") for n in names)
            dest = stage if wrapped else stage / stem
            dest.mkdir(parents=True)
            _extract(zp, dest)
        except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as e:
            # never leave a half-extracted unit for the converter to pick up
            shutil.rmtree(stage, ignore_errors=True)
            print("unzip: %s FAILED (%s), left in INBOX" % (zp, e))
            if isinstance(e, FileNotFoundError) and os.name == "nt":
                # extracting cannot miss a file: the path is over MAX_PATH
                print("unzip: path probably longer than 260 characters - install"
                      " the converter in a shorter folder or enable Windows long paths")
            continue
        unit = stage / tops.pop() if wrapped else dest
        shutil.move(str(zp), str(stage / zp.name))
        expanded.append((zp, unit))
        print("unzip: %s -> %s" % (zp, unit))
    return expanded


def containing_unit(path, root):
    """Top-level folder under root that holds path: the movable native unit."""
    rel = path.resolve().relative_to(root.resolve())
    if len(rel.parts) < 2:
        return None  # entry sits directly in the root: nothing movable
    return root / rel.parts[0]


def move_unit(unit, dest_root, keep_zip=True):
    """Move a native unit into dest_root; never clobber an earlier archive -
    a re-run of the same product gets a _1, _2, ... suffix. The original
    archive left by expand_zips goes along when keep_zip, else it is deleted:
    DONESPACE holds only the unzipped native."""
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / unit.name
    n = 0
    while dest.exists():
        n += 1
        dest = dest_root / ("%s_%d" % (unit.name, n))
    shutil.move(str(unit), str(dest))
    parent = unit.parent
    if parent.name.startswith("STAGE_"):
        # original archive left by expand_zips
        rest = list(parent.iterdir())
        if rest and all(p.is_file() and archive_suffix(p) for p in rest):
            for zp in rest:
                if not keep_zip:
                    zp.unlink()
                    continue
                zdest = dest_root / zp.name
                suffix = archive_suffix(zp)
                n = 0
                while zdest.exists():
                    n += 1
                    zdest = dest_root / ("%s_%d%s" % (zp.name[:-len(suffix)], n, suffix))
                shutil.move(str(zp), str(zdest))
        if not any(parent.iterdir()):
            parent.rmdir()
    return dest
