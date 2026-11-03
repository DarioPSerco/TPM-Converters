# ConverterDAMPS_clean — minimal runtime tree for the eight `_json` converters

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
| `pylib/converters/{geoeye1,worldview,quickbird,iceye,pleiades,pneo,geosat,cosmoskymed,planetscope,radarsat1,terrasarx,skysat,dmc,radarsat2}_json/` | the fourteen converters (code + `ingest_*.cfg` + packager + tests) |
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
.venv/Scripts/python pylib/converters/run_mission.py <geoeye1|worldview|quickbird|iceye|pleiades|pneo|geosat|cosmoskymed|planetscope|radarsat1|terrasarx|skysat|dmc|radarsat2>
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
| geoeye1_json, worldview_json, quickbird_json, iceye_json, cosmoskymed_json, planetscope_json, radarsat1_json, terrasarx_json, skysat_json, dmc_json, radarsat2_json | `pylib/xml_nodes/v101` |
| pleiades_json, pneo_json, geosat_json                    | `pylib/xml_nodes/v100`          |

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

293 tests (GE1 3, WV 2, QB2 3, ICEYE 4, PL1 22, PNEO 28, GEOSAT 42, CSK 12, PSC 19, RS1 13,
TSX 19, SSC 27, DMC 60, RS2 39). The
iceye/pleiades/pneo/geosat/cosmoskymed/planetscope/skysat/dmc suites read `TDS/template/*.json` via a relative
`parents[4]` hop — keep the tree depth as-is.

## Delivery-ZIP layout (all packagers)

```
<PRODUCT_ID>.ZIP            (all entries STORED)
├── <PRODUCT_ID>.JSON       manifest, byte-identical to the OUTSPACE JSON
├── measurements/           full native product tree (a COSMO-SkyMed .tgz
│                           delivery is expanded here, uncompressed)
└── preview/overviews/<PRODUCT_ID>.PNG
```

The manifest `links` hrefs (`measurements/...`, `preview/overviews/...`)
resolve inside the ZIP — packagers copy the manifest verbatim, no rewrite.

## Known limits

- ICEYE validated on real TDS (SM/SC/SLH). Pleiades and Pleiades NEO: see
  their sections below (PNEO: synthetic fixtures only, no real TDS yet).
- GEOSAT: synthetic fixtures only, no real TDS yet, see its section below.
- RADARSAT-2: synthetic fixtures only, no real TDS yet, see its section below.
- COSMO-SkyMed validated end to end on two real TDS products: CSK HIMAGE
  DGM_B (Level 1B, HDF5 delivery) and CSK WIDEREGION GEC_B (Level 1C,
  GeoTIFF-in-`.tgz` delivery). Open points: no PINGPONG and no Second
  Generation (CSG) product seen yet — those mappings are covered by fixtures
  and table assertions only; the overview PNG keeps the native quicklook
  orientation, with no re-orientation.

## COSMO-SkyMed specifics (`cosmoskymed_json`)

Per "EOPF-EOS SPECIALIZATION FOR COSMO-SKYMED PRODUCTS". Differences worth
knowing, all in `pylib/converters/cosmoskymed_json/`:

- **Entry file**: the native `.h5`, or the `.tgz` of a GeoTIFF delivery (cfg
  `[Search] FILES_EXTPATTERN=^\.(h5|tgz)$`). Both carry the SAME attribute
  names: the HDF5 attribute tree (root + `S0n` beam group + image dataset), or
  its XML dump `<name>.attribs.xml` inside the `.tgz`. Needs `h5py` for the
  HDF5 form. The DFDN / DFAS XML sidecars are only carried over as delivered
  content.
- **GeoTIFF deliveries**: the packager expands the `.tgz` INTO
  `measurements/` (the spec wants the native product uncompressed), so the ZIP
  holds `<name>.MBI.tif`, its `.tfw` / `.aux.xml`, the QLK GeoTIFF and
  `<name>.attribs.xml`. The lineage cites the delivered `.tgz`; the
  measurements link points at the `.MBI.tif` (`image/tiff`).
- **Polarisation**: one channel per DISTINCT `S0n` `Polarisation` — a ScanSAR
  product has one `S0n` group per subswath, all with the same polarisation, so
  it stays single-pol (`S`).
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
  spec's own example. `wavelengths[0]` holds only `spectralRange` "X" and
  `discreteWavelengths` `[0.0312284]` (Table 15); `polarisationChannels` is
  plural (Table 10). `operationalMode` is `HI` / `PP` / `SCW` / `SCH` and
  `resolution` is fixed per mode by Table 11 (3 / 15 / 30 / 100);
  `acquisitionAngles.incidenceAngle` is the mean of the image near and far
  incidence angles.
- **Overview path**: `previews/overviews/` (plural, spec section on the
  previews component), both in the manifest href and inside the ZIP.

## PlanetScope specifics (`planetscope_json`)

Per "EOPF-EOS SPECIALIZATION FOR PLANETSCOPE PRODUCTS" 1.0. Differences worth
knowing, all in `pylib/converters/planetscope_json/`:

- **Entry file**: the Planet item metadata `<item id>_metadata.json` (cfg
  `[Search] FILES_NAMEPATTERN=^.*_metadata$`, `FILES_EXTPATTERN=^\.json$`).
  One item = one EOPF-EOS product. The item files are every file under the
  entry folder whose name starts with the item id, so both the Orders API
  layout (several items flat in one folder) and the legacy Data API layout
  (one sub-folder per asset) work; the packager copies exactly that set into
  `measurements/`, sub-folders kept, and nothing else (no order
  `manifest.json`, no other item).
- **Metadata**: item JSON (footprint, `acquired`, `instrument`, sun angles,
  `view_angle`, `cloud_percent` / `cloud_cover`, `pixel_resolution` / `gsd`,
  `published`) plus the asset XML `<item id>_<asset>_metadata.xml`
  (`ps:EarthObservation`: validity period, orbit direction, incidence angle,
  processor name/version, native level, `numBands`, EPSG code). The XML is
  required. When both name the same second, the start time takes the item
  JSON milliseconds (the XML gives whole seconds).
- **Product type**: fixed by the main image asset, first match in
  `product_planetscope.IMAGE_ASSETS` (8 bands before 4, analytic before SR,
  basic, then 3-band analytic, visual) or `ORTHO_TILE_ASSETS` for a
  `PSOrthoTile` item. Mode MS3B/MS4B/MS8B from the band count, checked against
  spec Table 2; the XML `productType` must agree (it may only move a basic
  product between L1A and L1B).
- **Overview**: Planet delivers no browse, so the converter renders
  `<EO name>.PNG` (RGBA, max 1000 px) next to the manifest in OUTSPACE: the
  visual asset when the item has one, else the red/green/blue bands of the
  main image with a 2-98 percentile stretch; no-data is transparent. Reads the
  GeoTIFF with `tifffile` (+ `imagecodecs` for LZW/deflate), taking the
  smallest internal overview that is still >= 1000 px.
- **Manifest shapes chosen where the spec contradicts itself**: two lineage
  process steps (Planet processor, then the converter); `wavelengths`
  (plural) with `endWavelength`, one entry per spectralRange of Table 14;
  `orbitDirection` (camelCase); processedLevel code `L1A`/`L1B`/`L3B` (`L3A`
  for an ortho tile) in both steps. `cloudCover` and
  `referenceSystemIdentifier` only when the native item carries them; a
  MultiPolygon footprint becomes the bounding box Polygon. The lineage cites
  the entry file `<item id>_metadata.json`, so `run_mission.py` and the
  packager can find the native item back (`common.json_template.lineage_citation`
  now skips process steps whose source has no citation).
- **Not yet validated on a real product**: synthetic fixtures only, see
  `planetscope_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`.

## TerraSAR-X / TanDEM-X specifics (`terrasarx_json`)

Per "EOPF-EOS SPECIALIZATION FOR TERRASAR-X / TANDEM-X PRODUCTS" 1.01. Run
with `run_mission.py terrasarx`. Differences worth knowing, all in
`pylib/converters/terrasarx_json/`:

- **Entry file**: the main annotation `<product name>.xml` (cfg `[Search]
  FILES_NAMEPATTERN=^T[SD]X1_SAR__.*`, `FILES_EXTPATTERN=^\.xml$`). Extract
  the DLR DIMS `.tar.gz` into `INBOX/` first; the whole
  `dims_op_oc_dfd2_<order>/` folder is the unit moved to DONESPACE.
- **Measurements**: only the product folder
  (`TSX-1.SAR.L1B/<product name>/`) is the native product. The packager
  stores it as `measurements/<product name>/`; the DIMS `readme.html`,
  `iif/` and `tools/` are not packaged. `size` is the product folder size.
  The link points at the first image data file (GeoTIFF, or COSAR `.cos` as
  `application/octet-stream`).
- **Product type**: `(productVariant, imagingMode)` in
  `product_terrasarx.TYPECODE_MAP`. SL / HS / ST -> `SL`, SM -> `SM`,
  SC -> `SC`, WS -> `SCW`; SSC -> `SLC`. The spotlight MGD product is
  `L1BSL__MGC`, as the spec writes it.
- **Platform**: annotation mission TSX-1 -> package prefix `TSX`,
  `TerraSAR-X` / `TSX-1`; TDX-1 -> `TDX`, `TanDEM-X` / `TOR`.
- **Overview**: the native `PREVIEW/BROWSE.tif` re-encoded as
  `<EO name>.PNG` next to the manifest in OUTSPACE, orientation as delivered.
- **Manifest shapes chosen where the spec contradicts itself or is silent**:
  `wavelengths[0].discreteWavelengths` = `[0.0310666]`; lineage source per
  Table 16 (`sourceCitation.title` = annotation file name); no
  `wrsLatitudeGrid` (example only); `resolution` = worse of ground range
  and azimuth resolution; `referenceSystemIdentifier` = UTM / UPS EPSG code
  for GEC / EEC, EPSG:4326 for SSC / MGD.
- **Path length**: native paths reach ~252 characters under `INBOX/`; a
  deeper checkout can hit the Windows 260-character limit.
- Validated end to end on five real products (SSC SL, SSC HS, TDX MGD SL,
  GEC SC, EEC SC). No StripMap, Wide ScanSAR, staring spotlight or
  multi-polarisation product seen yet.

## SkySat specifics (`skysat_json`)

Per "EOPF-EOS SPECIALIZATION FOR SKYSAT PRODUCTS" 1.01. Run with
`run_mission.py skysat`. Same Planet delivery as PlanetScope, so the same
entry file and item-file rule; differences worth knowing, all in
`pylib/converters/skysat_json/`:

- **Entry file**: the Planet item metadata `<item id>_metadata.json` of a
  `SkySatScene` or `SkySatCollect` item. All metadata come from the item JSON
  (Planet ships no asset XML for SkySat); the CRS comes from the GeoKeys of
  the main GeoTIFF.
- **Product type**: a `SkySatScene` is typed by its main image asset, first
  match in `product_skysat.SCENE_ASSETS`: `_pansharpened` -> `L3_ORT_PSH`,
  `_analytic[_SR|_dn]` -> `L3_ORT_MS_`, `_visual` -> `L3_ORTVMS_`,
  `_panchromatic[_dn]` -> `L3_ORT_PAN`, `_basic_panchromatic[_dn]` ->
  `L1BBDN_MSP` (the `_basic_analytic[_dn]` image, if present, is a second
  measurements link), `_basic_analytic[_dn]` -> `L1BBDN_MS_`,
  `_basic_l1a_panchromatic_dn` -> `L1ABDN_PAN`. A `SkySatCollect` is
  `SYNORT_BDL`, one component per image kind found (visual, pansharpened,
  analytic, panchromatic). operationalMode and wavelengths follow Tables 2/3
  and 15/16.
- **Bundle**: one acquisitionParameters entry, one measurements link and one
  overview per component; overviews are `<EO name>_PSH3B.PNG`, `_PSH4B.PNG`,
  `_MS.PNG`, `_PAN.PNG` (section 4).
- **Overview**: rendered like PlanetScope (`<EO name>.PNG` next to the
  manifest); a panchromatic image gives a grey overview. The packager stores
  every PNG named by the manifest previews hrefs under `previews/overviews/`
  (plural, as this specialization writes it).
- **Manifest shapes chosen where the spec contradicts itself or is silent**:
  one lineage process step, source per Table 19 (`sourceCitation.title` = the
  entry file); processingLevel `1A`/`1B`/`3`, processedLevel code
  `L1A`/`L1B`/`L3B`/`SYN`; `processingDate` written (mandatory in Table 18);
  `endWavelength`, one entry per spectral range, discreteWavelengths = band
  centres (NIR 820 nm, the example says 870); `acrossTrackIncidenceAngle` =
  item `view_angle`; start = end = item `acquired`; link titles from Tables
  22/23. `cloudCover` and `referenceSystemIdentifier` only when available.
- **Not yet validated on a real product**: synthetic fixtures only, see
  `skysat_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`.

## Beijing-1 / NigeriaSat-1 / UK-DMC-1 specifics (`dmc_json`)

Per "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1 and UK-DMC-1
products" 1.0, one converter for the three satellites. Run with
`run_mission.py dmc`; workspace `TDS/DMC/`. Differences worth knowing, all in
`pylib/converters/dmc_json/`:

- **Delivery**: one flat `.zip` per product in INBOX, holding `<dataset>.dim`
  (DIMAP 1.1), `.tif`, `<dataset>_ql.jpg`, `<dataset>_meta.sip` (a zip with
  `repository.xml`), `.htm` and `.xsl`. The runner unzips it into
  `TMPSPACE/STAGE_<zip>/<zip>/`; the whole folder goes to `measurements/`.
- **Entry file**: the `.dim`. Platform, level, scene time, footprint, sun
  angles, CRS and production date come from it; resolution and cloud cover
  from `repository.xml` inside the `_meta.sip`.
- **Platform and product type**: `.dim` `MISSION`: `BEIJING` -> `BJ1`
  (Beijing-1), `NIGERIASAT` -> `NG1` (NigeriaSat-1), `UK-DMC` -> `UK1`
  (UK-DMC-1); any other value fails with "unsupported MISSION".
  `MISSION_INDEX` is optional (the NigeriaSat-1 / UK-DMC-1 `.dim` files have
  none); when present it must be `1`, as the spec covers only the -1
  satellites. `GEOMETRIC_PROCESSING` code before the first `_`: `1R` -> `L1R`
  -> `L1_OPT_MS_`, `1T` -> `L1T` -> `L1_ORT_MS_` (the rest, e.g. `_FI`,
  `_EPSG_4258_FI`, `_QL_EPSG_2393_FI`, is region / CRS / QL).
- **Package name counter**: the variants of one acquisition (`p` / `s`
  view, region `_FI` / `_SE` / `_NO`, CRS, reduced-resolution `QL` copy,
  converted as a normal product) share platform, level and scene time.
  `<bbvv>` = `00` + a counter [01..99]: the first native product to need a
  name gets `01`, the next one with the same name `02`, and so on, in
  processing order (alphabetical by zip name within a run). The names given
  are kept in the registry `TDS/DMC/dmc_names.json` (cfg
  `DMC_NAME_REGISTRY`), {native `DATASET_NAME`: package name}: a product
  converted again gets its name back. Keep that file with the outputs;
  deleting it lets a name be given again (`dmc_json/name_registry.py`).
- **Footprint**: the `Dataset_Frame` corners, `FRAME_LON` / `FRAME_LAT` when
  present (projected products, whose `FRAME_X` / `FRAME_Y` are metres), else
  `FRAME_X` / `FRAME_Y` in degrees; used as delivered, without coordinate
  conversion (ETRS89 is within 1 m of WGS 84, and projected products give
  their corners in degrees on the same basis).
- **Overview**: the JPEG named by the `.dim` `DATASET_QL_PATH`, re-encoded
  by the packager as `previews/overviews/<ID>.PNG` (plural, as this
  specialization writes it).
- **Manifest choices**: begin = end = `SCENE_CENTER_TIME`, taken as UTC,
  milliseconds `.000`; `processingDate` = `.dim` `DATASET_PRODUCTION_DATE`
  (the `repository.xml` date differs and is not used); measurements link and
  lineage source = the `.dim` (`application/xml`); `cloudCover` only when
  `repository.xml` fills it; `VIEWING_ANGLE` not mapped (the `.dim` does not
  say along or across track); no orbit fields. The readings chosen where
  the spec tables and its example differ are listed in `json_emitter.py`.
- **Validated** end to end on fifteen real Beijing-1 products (2007; L1R and
  L1T, regions FI / SE / NO, QL copies, two CRS) and three NigeriaSat-1 /
  UK-DMC-1 L1T products (one QL copy); the tests use synthetic fixtures, see
  `dmc_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`.
- **A zip with no `.dim`** (e.g. a zip of zips) is neither converted nor
  counted as a failure: it stays in `TMPSPACE/STAGE_*`. This holds for every
  mission whose zip the runner unpacks; check TMPSPACE after a run.

## Pleiades specifics (`pleiades_json`)

Per "EOPF-EOS SPECIALIZATION FOR PLEIADES PRODUCTS" 1.01. Run with
`run_mission.py pleiades`. Differences worth knowing, all in
`pylib/converters/pleiades_json/`:

- **Entry file**: the Airbus DIMAP delivery `.zip` itself (not unpacked by
  `run_mission`). It holds one `DIM_PHR1*.XML` per component: one for a
  PAN / MS / pansharpened product, two (P + MS) for a bundle. Orbit number
  and direction come from each component's `LINEAGE/STRIP_DS_*_DIM.XML`.
- **Product type** (Table 2): DIMAP `DATASET_TYPE` `RASTER_SENSOR` /
  `RASTER_PROJECTED` / `RASTER_ORTHO` -> `L1APRI` / `L2_PRO` / `L3_ORT`,
  `SPECTRAL_PROCESSING` `P` / `MS` / `PMS` (any `-N`/`-X` variant) -> `PAN`
  / `MS_` / `PSH`, P + MS -> `BDL`. Bundle types are `L2_PRO_BDL` /
  `L3_ORT_BDL` (Table 2 and the example), not Table 1's `L2_BNDLPRO` /
  `L3_BNDLORT`. A projected PAN or MS product, or any other component set,
  is outside the specialization and fails.
- **Package name**: `PL1_OPER_<type>_<start>_<stop>_0001`, start / stop the
  outer bounds of the scene times (`Located_Geometric_Values/TIME`).
- **Bundle**: one acquisitionParameters entry, one measurements link and one
  overview per component, MS first; overviews `<EO name>_MS.PNG` /
  `_PAN.PNG` (section 4.3).
- **Measurements**: the delivery ZIP is unpacked into `measurements/`
  (layout kept). Each link points at the component image; a tiled image links
  its DIMAP document (`application/xml`) instead. Link type from the EOF-EOS
  schema thesaurus: JPEG 2000 -> `application/octet-stream` (no `image/jp2`
  entry), TIFF -> `image/tiff` (the only GeoTIFF entry is cloud-optimized).
- **Overview**: the component `DATASET_QL_PATH` quicklook as PNG, written
  next to the manifest; the packager stores it under `previews/overviews/`.
- **Manifest shapes chosen where the spec contradicts itself or is silent**:
  one lineage step, source per Table 19 (`sourceCitation.title` = the
  delivery ZIP name, processedLevel `L1A`/`L2`/`L3`); processingLevel
  `1A`/`2`/`3`; `processingDate` = DIMAP `PRODUCTION_DATE`; `created` =
  conversion time; angles from the `Center` located values, each left out
  when absent; resolution = `RESAMPLING_SPACING`; wavelengths per Tables
  15/16, the PSH NIR row taken as 775-915 nm (Table 15 repeats the VNIR
  bounds there); link titles from Tables 21/22;
  `referenceSystemIdentifier` (EPSG URI from `PROJECTED_CRS_CODE`) for level
  2/3 only.
- **Validated** on one real L3 PMS delivery (`TDS/PLEIADES/INBOX`) end to
  end (convert + package) and on synthetic fixtures for every product type,
  see `pleiades_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`. No real
  bundle, L1A or L2 delivery seen yet.

## Pleiades NEO specifics (`pneo_json`)

Per "EOPF-EOS SPECIALIZATION FOR PLEIADES NEO PRODUCTS" 1.01. Run with
`run_mission.py pneo`. Same Airbus DIMAP family and same code layout as
`pleiades_json`; the differences, all in `pylib/converters/pneo_json/`:

- **Entry file**: the DIMAP delivery `.zip` itself (not unpacked by
  `run_mission`), one `DIM_PNEO*.XML` per component: one for a PAN / MS /
  pansharpened product, two (PAN + MS) for a bundle.
- **Product type** (Tables 1/2): `DATASET_TYPE` `RASTER_SENSOR` /
  `RASTER_PROJECTED` / `RASTER_ORTHO` -> `L1APRI` / `L2_PRO` / `L3_ORT`,
  `SPECTRAL_PROCESSING` `PAN` (or `P`) / `MS` / `PMS` (any `-FS`/`-N`/`-X`
  variant) -> `PAN` / `MS_` / `PSH`, PAN + MS -> `BDL`. All twelve types of
  the spec; the ortho bundle is `L2_ORT_BDL`, as the spec writes it in every
  table (not `L3_ORT_BDL`).
- **Package name**: `PLN_OPER_<type>_<start>_<stop>_0001` (`PLN` whatever
  the satellite).
- **Platform**: `MISSION_INDEX` 3 / 4 -> `Pleiades Neo-3` / `Pleiades Neo-4`
  (any other index fails); instrument `PNEO`.
- **Orbit** (mandatory): first `*ORBIT_NUMBER` / `*ORBIT_DIRECTION` element
  found in the DIMAP document or its `LINEAGE/*.XML` documents; if none, the
  cfg fallback `METADATA_ORBIT` / `METADATA_ORBIT_DIRECTION` (0 /
  DESCENDING) with a WARNING. To check on the first real delivery.
- **Wavelengths**: one entry per row of Table 15 (Table 16 for a bundle),
  discreteWavelengths = mean of the row's range (Table 14). Table 15 still
  names the old types (`L1AOPT_*`, `L2_GEO_*`): rows matched by PAN / MS /
  PSH. The bundle example's MS VNIR 525 nm and PAN 450-800 nm disagree with
  Table 16: the table is used (575 nm, 480-820 nm).
- **Manifest shapes**: processingLevel and processedLevel both
  `L1A`/`L2`/`L3` (Table 18; the example's `1A` is not an allowed value);
  `cloudCover` mandatory (Table 20, DIMAP `CLOUD_COVERAGE`, missing -> fail);
  `incidenceAngle` added to the Pleiades angle set (Table 13);
  `referenceSystemIdentifier` for L2/L3 from `PROJECTED_CRS_CODE`, else
  `GEODETIC_CRS_CODE`; lineage reference edition `1.01`. Bundle, links,
  overviews, measurements and packaging as Pleiades.
- **Not yet validated on a real product**: synthetic fixtures only, see
  `pneo_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`; also run end to end
  (`run_mission.py pneo`, convert + package) on synthetic bundle and PSH
  deliveries.

## GEOSAT specifics (`geosat_json`)

Per "EOPF-EOS SPECIALIZATION FOR GEOSAT PRODUCTS" 1.01 (GEOSAT-1 ex Deimos-1
SLIM6, GEOSAT-2 ex Deimos-2 HiRAIS). Run with `run_mission.py geosat`. Same
code layout as `pneo_json`; the differences, all in
`pylib/converters/geosat_json/`:

- **Entry file**: the DIMAP delivery `.zip` itself (not unpacked by
  `run_mission`), holding one `.dim` per product, or one per component (PAN +
  MS4 bundle, two-view stereo pair), the GeoTIFF image(s) and quicklook(s). A
  PM4 / STP product described by a single `.dim` is split by its image
  files (`DE2_PAN_...tif`, `DE2_MS4_...tif`).
- **Mode / level**: read from `DATASET_NAME` (else the `.dim` or ZIP name):
  `DE01_SL6_<22P|22S|22T>_<1R|1T|2T>_...` (GEOSAT-1),
  `DE2_<PAN|MS4|PSH|PS4|PM4|STP>_L<1B|1C|1D>_...` (GEOSAT-2), cross-checked
  with `Production/PRODUCT_TYPE` and `MISSION_INDEX`.
- **Product type** (Tables 2/3): GEOSAT-1 1R / 1T / 2T -> `L1_GEO_MS_` /
  `L1_ORT_MS_` / `L2_ORT_MS_`; GEOSAT-2 PAN `L1BORTRPAN` / `L1CORT_PAN`, MS4
  `L1BORTRMS_` / `L1CORT_MS_`, PSH (and PS4) `L1BORTRPSH` / `L1CORT_PSH` /
  `L1DORTEPSH`, bundle `L1BORTRBDL` / `L1CORT_BDL` / `L1DORTEBDL`, stereo
  `SYNSTERPAN` / `SYNSTERPSH`. Table 3 spells two of them `L1CRPC_PSH` and
  `L1DORT_PSH`; section 1.1's `L1CORT_PSH` / `L1DORTEPSH` are used (same
  pattern as the other types). PS3 (3-band pansharpened) has no type: fails.
- **Package name**: `DE1_` / `DE2_OPER_<type>_<start>_<stop>_0001` (cfg
  `METADATA_PLATFORM=DEIMOS` + `MISSION_INDEX`).
- **Levels**: processingLevel L1 (1R, 1T), L2 (2T), L1B / L1C / L1D, SYN
  (stereo); processedLevel code the native level (L1, L2T, L1B, L1C, L1D).
- **Orbit**: number mandatory: `*ORBIT_NUMBER` element or `*:ORB` quality
  parameter, else the `..._DE2_<orbit>_<id>` name part, else the cfg
  `METADATA_ORBIT` (0) with a WARNING (GEOSAT-1 names carry none). Direction
  from `GEOSAT:ORD` / `DEIMOS-IMAGING:ORD` / `SPACEMETRIC:HEADING`: mandatory
  for GEOSAT-2 (missing -> fail), left out for GEOSAT-1 when absent.
- **Optional values left out when absent**: cloudCover (`GEOSAT:CCP` /
  `DEIMOS-IMAGING:CCP`, negative = not computed), sun azimuth / elevation,
  `INCIDENCE_ANGLE`. referenceSystemIdentifier from `HORIZONTAL_CS_CODE`
  (else the WKT authority); missing on an ortho level (1T, 2T, 1C, 1D) -> fail.
- **Resolution**: `PIXEL_RESOLUTION_X`, else `THEORETICAL_RESOLUTION`, else
  the nominal value of Tables 2/3.
- **Wavelengths**: Table 16 rows by kind (MS3B 3 rows, PAN 1, MS4B / PSH 4);
  a bundle gets two entries (MS then PAN, both operationalMode `MS`), Table
  17's five rows split between them.
- **Manifest shapes** (tables over examples): lineage description `GEOSAT
  processor`, `source[0].sourceCitation.title` + `processedLevel.code`,
  output title the package name without extension, link titles `Native EO
  Product` / `Preview Image`. Overviews: `<ID>.PNG`, `<ID>_MS/_PAN.PNG`
  (bundle), `<ID>_1/_2.PNG` (stereo); from the quicklook, else from the
  GeoTIFF.
- **Not yet validated on a real product**: synthetic fixtures only, see
  `geosat_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`; also run end to end
  (`run_mission.py geosat`, convert + package) on synthetic GEOSAT-1, PAN and
  bundle deliveries.

## RADARSAT-2 specifics (`radarsat2_json`)

Per "EOPF-EOS SPECIALIZATION FOR RADARSAT-2 PRODUCTS" 1.0. Run with
`run_mission.py radarsat2`. Differences worth knowing, all in
`pylib/converters/radarsat2_json/`:

- **Entry file**: `product.xml` (cfg `[Search] FILES_NAMEPATTERN=^product$`,
  `FILES_EXTPATTERN=^\.xml$`) inside the MDA product folder
  `RS2_OK..._PK..._DK..._<beam>_<date>_<time>_<pols>_<type>/`; a ZIP of it in
  `INBOX/` is unpacked first. Every product has the same entry name, so the
  lineage citation (and the key the runner and packager use) is the product
  folder name: `common/spaces.find_native` accepts a folder citation and
  `run_mission.py` matches an entry by file or folder name.
- **Operational mode**: `sourceAttributes/beamModeMnemonic` folded on the
  spec's modes by `product_radarsat2.MODE_RULES`: Standard / Extended High-Low
  / Standard Quad-Pol -> `BS`; Fine / Ultra-Fine / Fine Quad-Pol -> `BSF`;
  Wide / Wide Standard Quad-Pol -> `BSW`; Wide Fine / Wide Ultra-Fine /
  Extra-Fine / Wide Fine Quad-Pol -> `BSWF`; Multi-Look Fine -> `ML`, Wide
  -> `MLW`; Spotlight -> `SL`; ScanSAR Narrow / Wide -> `SCN` / `SCW`. An
  unknown beam fails the conversion.
- **Product type**: `L<level>_<mode field><native type>`, 41 codes
  (`TYPECODE_MAP`): SLC / SGF / SGX level 1, SSG / SPG level 2; ScanSAR SCN /
  SCW (plain, `L1_SCN____`), SCF, SCS. `processingLevel` "1" / "2", lineage
  `processedLevel.code` "L1" / "L2". Polarisation mode S / D / Q from the
  number of channels, checked against Table 2 (ML / MLW / SL single only,
  ScanSAR no quad); channels in the schema's order (`"HH, HV"`).
- **Orbit number**: not in `product.xml`; the leading number of
  `orbitDataFile` (`13034_DEF.ORB`), else the `Orbit Number` line of a
  `*.prodReport`, else cfg `METADATA_ORBIT` (0) with a WARNING.
- **Resolution**: `product.xml` gives none; ground range =
  c / (2 rangeLookBandwidth sin(incidence)), azimuth = ground speed /
  azimuthLookBandwidth (state vector speed scaled to the ground);
  `resolution` the worse of the two. Incidence = mean of near / far range.
- **CRS**: UTM zone of an SSG / SPG map image (WGS84), else EPSG:4326.
  Footprint: the 4 corner tie points of the geolocation grid, CCW.
- **Manifest shapes** (tables over examples): wavelength `C`,
  `discreteWavelengths` `[0.0554658]` (Table 15; the example's 55.4558E-03
  is a typo); `source[0].sourceCitation.title` + `processedLevel.code`;
  `<bbvv>` = `0000` (Table 1 defaults); overview the native
  `BrowseImage.tif` as PNG.
- **Not yet validated on a real product**: synthetic fixtures only, see
  `radarsat2_json/test/fixtures/SYNTHETIC_FIXTURE_NOTE.md`; also run end to
  end (`run_mission.py radarsat2`, convert + package + move) on the four
  synthetic products.
