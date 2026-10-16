import configparser
import re
import shutil
import zipfile
from pathlib import Path

# [Main] keys, same names/semantics as the base ingester (ingester.py:593-604).
SPACE_KEYS = ("INBOX", "TMPSPACE", "OUTSPACE", "DONESPACE", "FAILEDSPACE")


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
    containing the marker. Nesting below each root is arbitrary."""
    roots = search_roots(spaces)
    for label, root in roots:
        for hit in sorted(root.rglob(marker_name)):
            if hit.is_file():
                return hit.parent
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


def zip_is_native(spaces):
    """True when the mission ingests the .zip itself (PLEIADES, PNEO):
    its [Search] extension pattern already selects .zip files."""
    return bool(re.compile(spaces["EXTPATTERN"]).match(".zip"))


def _free_stage(tmpspace, stem):
    stage = tmpspace / ("STAGE_%s" % stem)
    n = 0
    while stage.exists():
        n += 1
        stage = tmpspace / ("STAGE_%s_%d" % (stem, n))
    return stage


def expand_zips(spaces):
    """Unpack every .zip sitting directly in INBOX into its own
    TMPSPACE/STAGE_<stem>/ so the folder-based converters see a normal
    native unit. The original archive is moved next to the unit in the
    STAGE folder; move_unit deletes it on success (DONESPACE gets only the
    unzipped native) and archives it with the unit in FAILEDSPACE.
    No-op for missions whose native format is the zip itself.
    Returns [(zip_path, unit_path)]; a corrupt zip is left in INBOX."""
    if zip_is_native(spaces) or not spaces["INBOX"].is_dir():
        return []
    expanded = []
    # top level only: a .zip inside an unpacked native is product content
    for zp in sorted(spaces["INBOX"].glob("*")):
        if not (zp.is_file() and zp.suffix.lower() == ".zip"):
            continue
        stage = _free_stage(spaces["TMPSPACE"], zp.stem)
        try:
            with zipfile.ZipFile(zp) as zf:
                names = [n for n in zf.namelist() if n.strip("/")]
                tops = {n.split("/", 1)[0] for n in names}
                # archive already wrapping one folder: that folder is the
                # unit; otherwise wrap the loose files in <stem>/
                wrapped = len(tops) == 1 and any("/" in n for n in names)
                dest = stage if wrapped else stage / zp.stem
                dest.mkdir(parents=True)
                zf.extractall(dest)  # extractall drops absolute / ".." parts
        except (zipfile.BadZipFile, OSError) as e:
            # never leave a half-extracted unit for the converter to pick up
            shutil.rmtree(stage, ignore_errors=True)
            print("unzip: %s FAILED (%s), left in INBOX" % (zp, e))
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
        if rest and all(p.is_file() and p.suffix.lower() == ".zip" for p in rest):
            for zp in rest:
                if not keep_zip:
                    zp.unlink()
                    continue
                zdest = dest_root / zp.name
                n = 0
                while zdest.exists():
                    n += 1
                    zdest = dest_root / ("%s_%d%s" % (zp.stem, n, zp.suffix))
                shutil.move(str(zp), str(zdest))
        if not any(parent.iterdir()):
            parent.rmdir()
    return dest
