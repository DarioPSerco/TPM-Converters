import configparser
import re
import shutil
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


def containing_unit(path, root):
    """Top-level folder under root that holds path: the movable native unit."""
    rel = path.resolve().relative_to(root.resolve())
    if len(rel.parts) < 2:
        return None  # entry sits directly in the root: nothing movable
    return root / rel.parts[0]


def move_unit(unit, dest_root):
    """Move a native unit into dest_root; never clobber an earlier archive -
    a re-run of the same product gets a _1, _2, ... suffix."""
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / unit.name
    n = 0
    while dest.exists():
        n += 1
        dest = dest_root / ("%s_%d" % (unit.name, n))
    shutil.move(str(unit), str(dest))
    parent = unit.parent
    if parent.name.startswith("STAGE_") and not any(parent.iterdir()):
        parent.rmdir()
    return dest
