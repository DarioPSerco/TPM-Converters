# KOMPSAT test fixtures

`synthetic_ko/` holds three SYNTHETIC native KOMPSAT products, written by
`make_synthetic_ko.py` (re-runnable, needs `tifffile` and `pillow`). Each
product is the ASCII AUX metadata `<image stem>.txt` of each component and
16x12 rasters instead of the real ones, so the whole extraction -> manifest ->
overview -> package pipeline runs in a test.

| folder | product | layout | proves |
|---|---|---|---|
| `k2_flat/` | `MSC_100607044108_21000_10731074PN11_1G` | PAN + one 4-band MS image in one folder, plus an `_rpc.txt` | `L1_GEO_BDL`; values of the specialization's example manifest (footprint, angles); the MS component's own times; overview rendered from the MS image; the RPC text is packaged but is not an entry |
| `k2_split/MSC_090415014422_15130_11831188_1R/` | `..PN00_1R` | `PAN/` + `MS/` with one image per band (`M1`..`M4`), native `_br.jpg` browse | `L1_OPT_BDL`; product root = scene folder; `BEGIN_`/`END_` groups; `UL/UR/LR/LL` corner keys; no end time, no processing date, no angles; cloud cover `-1` left out; overview from the native browse |
| `k1_ortho/` | `EOC_020101121314_00042_L1B` | one PAN GeoTIFF | `L1BORT_PAN`; KOMPSAT-1 angles (mandatory) |

Real-product provenance: NONE. No real KOMPSAT product has been converted
yet, and the specialization does not describe the native format. The layout,
the file names and the AUX keys are written from memory of the KOMPSAT-2
product documentation (the AUX key names the GDAL KOMPSAT metadata reader
uses: `AUX_SATELLITE_NAME`, `AUX_SATELLITE_SENSOR`, `AUX_STRIP_ACQ_DATE_UT`,
`AUX_STRIP_ACQ_START_UT`, `AUX_CLOUD_STATUS`). They have to be checked against
a real delivery. In particular:

- the KOMPSAT-1 EOC file naming and metadata: assumed to be an AUX `.txt`
  like KOMPSAT-2, with an `EOC_` prefix;
- the KOMPSAT-2 bundle layout: PAN and MS components side by side, or in
  sibling folders of one scene folder; mode tokens `PN`, `MS`, `M1`..`M4`;
- the names of the keys read through token search, first match wins:
  orbit direction (`AUX_ORBIT_DIRECTION`, values `A`/`D` or full words),
  processing date (`AUX_PROCESSING_DATE` + `_TIME`), sun angles (key with
  `SUN` and `AZIMUTH` / `ELEVATION`), incidence angles (key with `ALONG` /
  `ACROSS` and `INCIDENCE` / `VIEW` / `TILT`), footprint corners
  (`TL/TR/BR/BL` or `UL/UR/LR/LL` with `LAT` / `LON`, decimal degrees,
  `_DEC` keys first);
- the MS band order of a 4-band image (read as B, G, R, NIR), used for the
  overview only;
- a `AUX_CLOUD_STATUS` outside 0-100 meaning "not assessed".
