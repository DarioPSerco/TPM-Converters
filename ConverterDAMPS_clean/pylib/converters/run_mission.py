import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import json_template, spaces

ROOT = Path(__file__).resolve().parents[2]
CONVERTERS = ROOT / "pylib" / "converters"

# one row per mission: converter dir, cfg, ingester entry point, xml_nodes
# version the cfg's [eoSip] VERSION gate expects, packager (None = not
# written yet: convert-only, no move - never move before packaging)
MISSIONS = {
    "geoeye1": ("geoeye1_json", "ingest_geoeye1.cfg", "ingester_geoeye1.py", "v101", "package_geoeye_zips.py"),
    "worldview": ("worldview_json", "ingest_worldview.cfg", "ingester_worldview.py", "v101", "package_worldview_zips.py"),
    "quickbird": ("quickbird_json", "ingest_quickbird.cfg", "ingester_quickbird.py", "v101", "package_quickbird_zips.py"),
    "iceye": ("iceye_json", "ingest_iceye.cfg", "ingester_iceye.py", "v101", "package_iceye_zips.py"),
    "pleiades": ("pleiades_json", "ingest_pleiades.cfg", "ingester_pleiades.py", "v100", "package_pleiades_zips.py"),
    "pneo": ("pneo_json", "ingest_pneo.cfg", "ingester_pneo.py", "v100", "package_pneo_zips.py"),
}


def citation_of(manifest):
    d = json.loads(manifest.read_text(encoding="utf-8"))
    return json_template.lineage_citation(d)


def outspace_citations(sp):
    m = {}
    for mf in sorted(sp["OUTSPACE"].glob("*.JSON")):
        try:
            m[citation_of(mf)] = mf
        except Exception:
            pass
    return m


def unit_of(path, sp):
    """Movable native unit containing path, or None if path is not under a
    movable root (e.g. already in DONESPACE)."""
    for label, root in spaces.search_roots(sp):
        if label == "DONESPACE":
            continue
        try:
            return spaces.containing_unit(path, root)
        except ValueError:
            continue
    return None


def convert(mission_dir, cfg, ingester, ver, sp):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "pylib" / "xml_nodes" / ver), str(CONVERTERS)]
    )
    before = outspace_citations(sp)
    results = []  # (entry, unit, ok, detail)
    entries = spaces.find_entries(sp)
    if not entries:
        print("convert: no entry files found in %s or %s\\STAGE_*"
              % (sp["INBOX"], sp["TMPSPACE"]))
    for entry, root in entries:
        print("convert: %s" % entry)
        proc = subprocess.run(
            [sys.executable, str(mission_dir / ingester), "-c", str(mission_dir / cfg), "--single", str(entry)],
            cwd=str(ROOT), env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        ok = proc.returncode == 0
        detail = "rc=%s" % proc.returncode
        if not ok:
            tail = (proc.stdout or "").strip().splitlines()[-12:]
            print("  FAILED (rc=%s); converter output tail:" % proc.returncode)
            for line in tail:
                print("  | %s" % line)
        results.append((entry, spaces.containing_unit(entry, root), ok, detail))
    after = outspace_citations(sp)
    for i, (entry, unit, ok, detail) in enumerate(results):
        if ok and entry.name not in after:
            results[i] = (entry, unit, False, "rc=0 but no JSON with citation %s in OUTSPACE" % entry.name)
    new = [c for c in after if c not in before]
    print("convert: %d entries, %d ok, %d new JSON in OUTSPACE"
          % (len(results), sum(1 for r in results if r[2]), len(new)))
    return results


def package(mission_dir, packager, sp):
    results = []  # (manifest_name, native_path_or_None, ok, detail)
    proc = subprocess.run(
        [sys.executable, str(mission_dir / packager)],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    sys.stdout.write(proc.stdout)
    for line in proc.stdout.splitlines():
        if line.startswith("PKG-OK\t"):
            _, name, native = line.split("\t", 2)
            results.append((name, Path(native), True, ""))
        elif line.startswith("PKG-FAIL\t"):
            _, name, detail = line.split("\t", 2)
            results.append((name, None, False, detail))
    if proc.returncode != 0 and not results:
        print("package: packager died: rc=%s\n%s" % (proc.returncode, proc.stderr[-2000:]))
    return results


def move(conv_results, pkg_results, sp):
    verdicts = {}  # unit -> ok (all touches succeeded)

    def touch(unit, ok):
        if unit is None:
            return
        unit = unit.resolve()
        verdicts[unit] = verdicts.get(unit, True) and ok

    for entry, unit, ok, detail in conv_results:
        touch(unit, ok)
    for name, native, ok, detail in pkg_results:
        if native is not None:
            touch(unit_of(native, sp), ok)
        elif not ok:
            # native unresolved by the packager; best effort via the manifest
            mf = sp["OUTSPACE"] / name
            try:
                touch(unit_of(spaces.find_native(citation_of(mf), sp), sp), False)
            except Exception:
                print("move: cannot map failed %s to a native unit (nothing moved)" % name)

    moved = []
    for unit, ok in sorted(verdicts.items()):
        if not unit.exists():
            continue
        dest_root = sp["DONESPACE"] if ok else sp["FAILEDSPACE"]
        dest = spaces.move_unit(unit, dest_root)
        moved.append((unit, dest, ok))
        print("move: %s -> %s" % (unit, dest))
    if not moved:
        print("move: nothing to move")
    return moved


def move_standalone(sp):
    """--stage move without in-run results: archive every unit whose products
    are fully delivered (manifest in OUTSPACE + ZIP in PRODUCTS)."""
    conv, pkg = [], []
    for citation, mf in outspace_citations(sp).items():
        product = json.loads(mf.read_text(encoding="utf-8"))["id"]
        if (sp["PRODUCTS"] / ("%s.ZIP" % product)).exists():
            try:
                native = spaces.find_native(citation, sp)
            except FileNotFoundError:
                continue
            pkg.append((mf.name, native, True, ""))
    return move(conv, pkg, sp)


def main():
    parser = argparse.ArgumentParser(description="convert + package + archive one mission, one command")
    parser.add_argument("mission", choices=sorted(MISSIONS))
    parser.add_argument("--stage", choices=["all", "convert", "package", "move"], default="all")
    args = parser.parse_args()

    dirname, cfg, ingester, ver, packager = MISSIONS[args.mission]
    mission_dir = CONVERTERS / dirname
    sp = spaces.read_spaces(mission_dir / cfg)

    if args.stage == "convert":
        results = convert(mission_dir, cfg, ingester, ver, sp)
        sys.exit(0 if all(r[2] for r in results) else 1)
    if args.stage == "package":
        if packager is None:
            print("%s has no packager yet - nothing to do" % args.mission)
            sys.exit(0)
        results = package(mission_dir, packager, sp)
        sys.exit(0 if all(r[2] for r in results) else 1)
    if args.stage == "move":
        if packager is None:
            print("%s has no packager yet - refusing to archive unpackaged natives" % args.mission)
            sys.exit(1)
        move_standalone(sp)
        sys.exit(0)

    # all: convert -> package -> move, strictly in that order
    conv = convert(mission_dir, cfg, ingester, ver, sp)
    if packager is None:
        print("%s has no packager yet: converted only, natives left in place" % args.mission)
        sys.exit(0 if all(r[2] for r in conv) else 1)
    pkg = package(mission_dir, packager, sp)
    move(conv, pkg, sp)

    failures = [r for r in conv if not r[2]] + [r for r in pkg if not r[2]]
    print("\n== %s: %d converted, %d packaged, %d failure(s) ==" % (
        args.mission, sum(1 for r in conv if r[2]), sum(1 for r in pkg if r[2]), len(failures)))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
