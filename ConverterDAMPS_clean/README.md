# ConverterDAMPS_clean — minimal runtime tree for the seven `_json` converters

Extracted from `ConverterDAMPS` per `CLEAN_PACKAGE_ANALYSIS.md` (12 audit-hook
traces, 3 real conversions). Contains ONLY what these converters need.

## Provenance

Regenerated 2026-07-24 from ORIGINAL at commit
`1b67ec6b698e36c3a89320798b34017c61441c85` + uncommitted working tree
(pylib sources are not git-tracked; rollback reference:
`ConverterDAMPS/_snapshots/pre_measurements_layout_2026-07-24.zip`).
Includes the logging standardization (per-run `log/<MISSION_ID>/<YYYY-MM-DD>/`
tree, `MISSION_ID` cfg key, shared `makeConversionReport`, SUCCESS/FAILED run
markers) and the 2026-07-24 EO-SIP ZIP layout standardization (manifest
verbatim in the ZIP, native under `measurements/`, browse at
`preview/overviews/`). Logs land under `log/<mission>/<date>/` — nothing
writes to a flat `log/` or the repo root.

## Contents

| dir | role |
|---|---|
| `pylib/converters/{geoeye1,worldview,quickbird,iceye,pleiades,pneo,cosmoskymed}_json/` | the seven converters (code + `ingest_*.cfg` + packager + tests) |
| `pylib/converters/common/` | mission-agnostic JSON template engine + `feature_template.json` + `spaces.py` |
| `pylib/converters/run_mission.py` | one-command runner: convert + package + archive per mission |
| `pylib/eoSip_converter/` | base ingester package — **pruned**: `data/shapefile/` (186 MB) and `proj/` (5 MB) removed, never touched in any trace |
| `pylib/xml_nodes/{v100,v101,v200}/` | versioned XML builders; selected by path, see below |
| `TDS/template/*.json` | reference templates read by the test suites |
| `TDS/<MISSION>/{INBOX,OUTSPACE,TMPSPACE,DONESPACE,FAILEDSPACE}/` | empty workspace skeleton; cfgs point here with RELATIVE paths |
| `_validation/` | regeneration evidence (manifests, ZIP listings, reports, SUCCESS markers) |

## Install

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/pip install -e pylib/eoSip_converter
```

`eoSip_converter` must be installed FROM THIS TREE (editable). The pip metadata
in any other environment may still point at the old repo. Verify:
`.venv/Scripts/python -c "import eoSip_converter; print(eoSip_converter.__file__)"`
must print a path under THIS tree.

## Running a mission

Run from THIS directory (cfg `[Main]` paths are relative to CWD). Extract
native products into `TDS/<MISSION>/INBOX/` first (a raw `.zip` in INBOX is
silently skipped), then:

```bash
.venv/Scripts/python pylib/converters/run_mission.py <geoeye|worldview|quickbird|iceye|pleiades|pneo|cosmoskymed>
```

The runner converts every INBOX product, packages the delivery ZIPs into
`TDS/<M>/PRODUCTS/`, and archives the native to DONESPACE (FAILEDSPACE on
error). Logs + report + SUCCESS/FAILED marker land in `log/<mission>/<date>/`.

Manual single-product conversion still works:

```bash
PYTHONPATH="pylib/xml_nodes/v101;pylib/converters" \
  python pylib/converters/geoeye1_json/ingester_geoeye1.py \
  -c pylib/converters/geoeye1_json/ingest_geoeye1.cfg \
  --single <path to *_README.XML / scene XML>
```

### PYTHONPATH rules (cfg `VERSION` gate, `ingester.py` `checkTypologyOk`)

| converter                                                | xml_nodes version on PYTHONPATH |
|----------------------------------------------------------|---------------------------------|
| geoeye1_json, worldview_json, quickbird_json, iceye_json, cosmoskymed_json | `pylib/xml_nodes/v101`          |
| pleiades_json, pneo_json                                 | `pylib/xml_nodes/v100`          |

`v200` is used only by the geoeye1/worldview/quickbird test conftests.
`run_mission.py` sets the right PYTHONPATH itself.

### TRAP — never put `pylib/` itself on sys.path

The outer `pylib/eoSip_converter/` folder would shadow the installed
`eoSip_converter` package as an empty namespace package and every
`eoSip_converter.*` import breaks. PYTHONPATH gets `pylib/xml_nodes/<vN>` and
`pylib/converters` — never `pylib`.

## Tests

```bash
.venv/Scripts/python -m pytest pylib/converters -q
```

27 tests (GE1 3, WV 2, QB2 3, ICEYE 4, PL1 4, PNEO 4, CSK 7). The
iceye/pleiades/pneo/cosmoskymed suites read `TDS/template/*.json` via a relative
`parents[4]` hop — keep the tree depth as-is.

## Delivery-ZIP layout (all packagers)

```
<PRODUCT_ID>.ZIP            (all entries STORED)
├── <PRODUCT_ID>.JSON       manifest, byte-identical to the OUTSPACE JSON
├── measurements/           full native product tree
└── preview/overviews/<PRODUCT_ID>.PNG
```

The manifest `links` hrefs (`measurements/...`, `preview/overviews/...`)
resolve inside the ZIP — packagers copy the manifest verbatim, no rewrite.

## Known limits

- ICEYE validated on real TDS (SM/SC/SLH); pleiades/pneo converters+packagers
  validated on synthetic fixtures only — field values pending real TDS
  (PNEO sun angles inferred; PL1 "HiRI" suspected template bug).
- COSMO-SkyMed validated end to end on one real TDS product (CSK HIMAGE
  DGM_B, Level 1B, single pol). Open points: no SCANSAR (WIDEREGION /
  HUGEREGION) and no Second Generation (CSG) product seen yet — those
  mappings are covered by table assertions only; TIFF / GEOTIFF-only
  deliveries are not handled (the entry file is the `.h5`, and the orbit,
  incidence-angle and polarisation values live in its attributes); the
  overview PNG is written from the HDF5 `S0n/QLK` dataset in native
  acquisition orientation, with no re-orientation.

## COSMO-SkyMed specifics (`cosmoskymed_json`)

Per "EOPF-EOS SPECIALIZATION FOR COSMO-SKYMED PRODUCTS". Differences worth
knowing, all in `pylib/converters/cosmoskymed_json/`:

- **Entry file**: the native `.h5` (cfg `[Search] FILES_EXTPATTERN=^\.h5$`).
  Every manifest value comes from its attribute tree (root + `S0n` beam group +
  image dataset); the DFDN / DFAS XML sidecars are only carried over as
  delivered content. Needs `h5py`.
- **Product type code**: the ten codes the spec allows, keyed by mode family
  (STRIPMAP HIMAGE/PINGPONG -> SM, SCANSAR WIDEREGION/HUGEREGION -> SC) in
  `product_cosmoskymed.TYPECODE_MAP`: `L1ASMU_SCS`, `L1ASMB_SCS`,
  `L1BSM__DGM`, `L1CSM__GEC`, `L1DSM__GTC`, `L1ASCU_SCS`, `L1ASCB_SCS`,
  `L1BSC__DGM`, `L1CSC__GEC`, `L1DSC__GTC`. An unknown native product type or
  acquisition mode fails the conversion instead of inventing a code.
- **Overview**: COSMO-SkyMed ships its quicklook as an HDF5 dataset, so the
  converter writes `<EO name>.PNG` next to the manifest in OUTSPACE and the
  packager zips that file — it does not look for a browse file in the native
  delivery.
- **Manifest shapes chosen where the spec contradicts itself**: the wavelength
  block is `acquisitionParameters[0].wavelengths[0]` (plural), and the lineage
  source follows the normative Table 16
  (`source[0].sourceCitation.title` + `source[0].processedLevel.code`), not the
  spec's own example. `resolution` is the worst of range and azimuth
  resolution; `acquisitionAngles.incidenceAngle` is the mean of the image near
  and far incidence angles.
