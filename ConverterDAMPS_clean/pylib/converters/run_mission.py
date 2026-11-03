import argparse
import json
import os
import re
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
    "geosat": ("geosat_json", "ingest_geosat.cfg", "ingester_geosat.py", "v100", "package_geosat_zips.py"),
    "cosmoskymed": ("cosmoskymed_json", "ingest_cosmoskymed.cfg", "ingester_cosmoskymed.py", "v101", "package_cosmoskymed_zips.py"),
    "planetscope": ("planetscope_json", "ingest_planetscope.cfg", "ingester_planetscope.py", "v101", "package_planetscope_zips.py"),
    "radarsat1": ("radarsat1_json", "ingest_radarsat1.cfg", "ingester_radarsat1.py", "v101", "package_radarsat1_zips.py"),
    "terrasarx": ("terrasarx_json", "ingest_terrasarx.cfg", "ingester_terrasarx.py", "v101", "package_terrasarx_zips.py"),
    "skysat": ("skysat_json", "ingest_skysat.cfg", "ingester_skysat.py", "v101", "package_skysat_zips.py"),
    "dmc": ("dmc_json", "ingest_dmc.cfg", "ingester_dmc.py", "v101", "package_dmc_zips.py"),
    "radarsat2": ("radarsat2_json", "ingest_radarsat2.cfg", "ingester_radarsat2.py", "v101", "package_radarsat2_zips.py"),
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
            unit = spaces.containing_unit(path, root)
        except ValueError:
            continue
        # a native folder sitting directly in the root is itself the unit
        # (RADARSAT-1: INBOX/<scene>/<CEOS files>), and so is a native
        # archive the mission ingests as is (PLEIADES: INBOX/<delivery>.zip)
        if unit is None and (path.is_dir() or native_archive(path, sp)):
            return path
        return unit
    return None


def native_archive(path, sp):
    """True for an archive file that is itself the mission's entry (its
    extension matches the cfg [Search] pattern)."""
    return (path.is_file() and spaces.archive_suffix(path) is not None
            and re.match(sp["EXTPATTERN"], path.suffix) is not None)


class short_root:
    """Context manager giving the converter folder a short alias for the
    ingester runs. With [Paths] WINDOWS_EXTENDED_PATHS on Windows, a free drive
    letter is mapped onto ROOT (subst, no admin rights needed) and removed on
    exit: the ingesters and the base library build plain "a/b" paths from the
    cfg's relative spaces, which then stay far below the 260-character limit
    wherever the converter is installed. Elsewhere the alias is ROOT itself."""

    def __init__(self, sp):
        self.wanted = sp["EXTENDED_PATHS"]
        self.drive = None

    def __enter__(self):
        if not self.wanted:
            return ROOT
        used = set(os.listdrives()) if hasattr(os, "listdrives") else set()
        for letter in "ZYXWVUTSRQPONMLKJIHGFE":
            drive = "%s:" % letter
            if "%s\\" % drive in used or os.path.exists(drive + "\\"):
                continue
            if subprocess.run(["subst", drive, str(ROOT)], capture_output=True).returncode == 0:
                self.drive = drive
                return Path(drive + "\\")
        print("convert: no free drive letter for a short path, using %s" % ROOT)
        return ROOT

    def __exit__(self, *exc):
        if self.drive:
            subprocess.run(["subst", self.drive, "/D"], capture_output=True)
        return False


def short_entry(entry, alias):
    """entry (possibly a \\\\?\\ extended path under ROOT) seen through alias."""
    if alias == ROOT:
        return entry
    return alias / Path(entry).relative_to(spaces.extended_path(ROOT))


def convert(mission_dir, cfg, ingester, ver, sp):
    before = outspace_citations(sp)
    results = []  # (entry, unit, ok, detail)
    spaces.expand_zips(sp)  # INBOX/*.zip|.tar.gz|.tgz -> TMPSPACE/STAGE_<n>/
    # an archive still sitting in INBOX failed to unpack: count it, do not hide it
    for zp in spaces.inbox_archives(sp):
        results.append((zp, None, False, "unzip failed, left in INBOX"))
    entries = spaces.find_entries(sp)
    if not entries:
        print("convert: no entry files found in %s or %s\\STAGE_*"
              % (sp["INBOX"], sp["TMPSPACE"]))
    with short_root(sp) as alias:
        for entry, root in entries:
            print("convert: %s" % entry)
            proc = run_ingester(alias, mission_dir, cfg, ingester, ver, short_entry(entry, alias))
            ok = proc.returncode == 0
            detail = "rc=%s" % proc.returncode
            if not ok:
                tail = (proc.stdout or "").strip().splitlines()[-12:]
                print("  FAILED (rc=%s); converter output tail:" % proc.returncode)
                for line in tail:
                    print("  | %s" % line)
            unit = spaces.containing_unit(entry, root)
            if unit is None and native_archive(entry, sp):
                unit = entry  # the archive itself is the native unit
            results.append((entry, unit, ok, detail))
    after = outspace_citations(sp)
    for i, (entry, unit, ok, detail) in enumerate(results):
        # the citation is the entry file name, or its folder name when the
        # entry name is not unique (RADARSAT-2 product.xml)
        if ok and entry.name not in after and entry.parent.name not in after:
            results[i] = (entry, unit, False, "rc=0 but no JSON with citation %s in OUTSPACE" % entry.name)
    new = [c for c in after if c not in before]
    print("convert: %d entries, %d ok, %d new JSON in OUTSPACE"
          % (len(results), sum(1 for r in results if r[2]), len(new)))
    return results


def run_ingester(alias, mission_dir, cfg, ingester, ver, entry):
    # every path the ingester sees goes through alias (cwd included): its
    # relative spaces resolve under the short alias, not under ROOT
    mission = alias / mission_dir.relative_to(ROOT)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(alias / "pylib" / "xml_nodes" / ver), str(alias / "pylib" / "converters")]
    )
    return subprocess.run(
        [sys.executable, str(mission / ingester), "-c", str(mission / cfg), "--single", str(entry)],
        cwd=str(alias), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


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
        dest = spaces.move_unit(unit, dest_root, keep_zip=not ok)
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
