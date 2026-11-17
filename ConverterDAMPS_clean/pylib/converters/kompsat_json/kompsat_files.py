"""KOMPSAT native product layout: naming, AUX metadata, product files.

Pure helpers with no eoSip_converter import, shared by the product class and
the packager (the packager must not pull in eoSip_converter and its xml_nodes
PYTHONPATH requirement).

Native layout handled (the specialization does not describe it, see
test/fixtures/SYNTHETIC_FIXTURE_NOTE.md):

- every image comes with an ASCII metadata file <image stem>.txt holding
  ``AUX_<NAME> <value>`` lines (optionally grouped by ``BEGIN_<group>`` /
  ``END_<group>`` lines). That file is the conversion entry.
- KOMPSAT-2 (MSC) names:
  MSC_<yymmddhhmmss>_<orbit>_<path/row><MODE>[<P|N>]<nn>[<band>]_<1R|1G>
  with MODE PN / PP (panchromatic), MS (4-band multispectral image), M1..M4
  (one multispectral band per image) or BN / BP (browse). Real products carry
  an optional processing letter after M1..M4 and a band letter after <nn>
  (e.g. ...M1N06G_1R, ...M3P01N_1G). A bundle (L1_OPT_BDL / L1_GEO_BDL) is the PAN
  component and the MS component of the same scene: the entry is the PAN
  metadata; the MS component sits in the same folder or in a sibling folder.
- KOMPSAT-1 (EOC): one panchromatic image; the product files are the ones
  named after the metadata file stem.
"""
import os
import re

METADATA_EXT = ".txt"

# KOMPSAT-2 MSC file name; group 'scene' ignores the mode token
MSC_NAME_RE = re.compile(
    r"^(?P<prefix>MSC_(?P<time>\d{12})_(?P<orbit>\d+)_(?P<pathrow>\d+?))"
    r"(?P<mode>P[NP]|PS|MS|M[1-4]|B[NP])(?P<proc>[NP])?(?P<nn>\d{2})(?P<band>[A-Z])?"
    r"_(?P<level>1[RG])(?P<rest>[_.].*)?$",
    re.IGNORECASE)

PAN_MODES = ("PN", "PP")
MS_MODES = ("MS", "M1", "M2", "M3", "M4")

# metadata files that are not the product AUX metadata
NOT_AUX_RE = re.compile(r"(_rpc|_readme|_license)$", re.IGNORECASE)


def parse_aux(path):
    """AUX metadata file -> {KEY: value}. ``BEGIN_<g>`` / ``END_<g>`` lines
    group the keys: a grouped key is stored as '<g>.<KEY>' and, when not set
    already, as '<KEY>'. Blank lines, comments and value-less keys are
    skipped; surrounding quotes are removed."""
    values = {}
    group = None
    with open(path, "r", encoding="utf-8", errors="replace") as fd:
        for raw in fd:
            line = raw.strip()
            if not line or line.startswith(("#", ";", "//")):
                continue
            parts = re.split(r"\s*=\s*|\s+", line, maxsplit=1)
            key = parts[0].upper()
            value = parts[1].strip().strip('"').strip("'").strip() if len(parts) > 1 else ""
            if key.startswith("BEGIN_") and not value:
                group = key[len("BEGIN_"):]
                continue
            if key.startswith("END_") and not value:
                group = None
                continue
            if not value:
                continue
            if group:
                values.setdefault("%s.%s" % (group, key), value)
            values.setdefault(key, value)
    return values


def is_aux_metadata(path):
    """True for a .txt file holding AUX_ keys."""
    stem, ext = os.path.splitext(os.path.basename(str(path)))
    if ext.lower() != METADATA_EXT or NOT_AUX_RE.search(stem):
        return False
    try:
        return any(k.startswith("AUX_") or ".AUX_" in k for k in parse_aux(path))
    except OSError:
        return False


def msc_name(name):
    """Fields of a KOMPSAT-2 MSC file name, or None."""
    match = MSC_NAME_RE.match(os.path.basename(str(name)))
    if not match:
        return None
    fields = match.groupdict()
    fields["mode"] = fields["mode"].upper()
    fields["level"] = fields["level"].upper()
    return fields


def scene_key(name):
    """(prefix, level) shared by every component of a KOMPSAT-2 scene, or
    None for a name that is not an MSC name."""
    fields = msc_name(name)
    return (fields["prefix"].upper(), fields["level"]) if fields else None


def _walk(folder):
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        for name in sorted(files):
            yield os.path.join(root, name)


def scene_files(folder, key):
    """Files under folder belonging to the KOMPSAT-2 scene key, any mode."""
    return [p for p in _walk(folder) if scene_key(p) == key]


def stem_files(folder, stem):
    """Files under folder named after stem (stem followed by '_' or '.')."""
    return [p for p in _walk(folder)
            if os.path.basename(p).startswith(stem + "_")
            or os.path.basename(p).startswith(stem + ".")]


def has_ms_component(files):
    return any((msc_name(p) or {}).get("mode") in MS_MODES for p in files)


def product_root(entry):
    """Folder the product files are searched under: the folder of the entry
    metadata; for a KOMPSAT-2 bundle whose MS component sits in a sibling
    folder (<scene>/PAN/ + <scene>/MS/), the folder above."""
    folder = os.path.dirname(os.path.abspath(str(entry)))
    key = scene_key(entry)
    if key is None:
        return folder
    if has_ms_component(scene_files(folder, key)):
        return folder
    parent = os.path.dirname(folder)
    if parent != folder and has_ms_component(scene_files(parent, key)):
        return parent
    return folder


def product_files(entry, root=None):
    """Every file of the product the entry metadata belongs to, sorted by
    relative path: the whole scene (all components) for KOMPSAT-2, the files
    named after the metadata stem otherwise."""
    root = root or product_root(entry)
    key = scene_key(entry)
    if key is not None:
        found = scene_files(root, key)
    else:
        stem = os.path.splitext(os.path.basename(str(entry)))[0]
        found = stem_files(root, stem)
    return sorted(found, key=lambda p: os.path.relpath(p, root).replace(os.sep, "/"))
