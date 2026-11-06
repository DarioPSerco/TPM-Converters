# PlanetScope test fixtures

`synthetic_psc/` holds four SYNTHETIC native PlanetScope items, written by
`make_synthetic_psc.py` (re-runnable, needs `tifffile`). Each item is the Planet
item metadata `<id>_metadata.json`, the asset XML
`<id>_<asset>_metadata.xml` (Planet `ps:EarthObservation`, reduced to the
elements the converter reads and their usual neighbours) and 16x12 GeoTIFF
rasters instead of the real ones, so the whole extraction -> manifest ->
overview pipeline runs in a test.

| item | layout | asset | product type | proves |
|---|---|---|---|---|
| `20170424_134911_0e19` | Orders API, flat `order_7d1c/PSScene/` | `_3B_Visual.tif` (8-bit RGB) | `L3_VO__MS_` MS3B | values of the specialization's example manifest (footprint, times, sun/incidence angles); visual overview; item files picked by prefix out of a shared folder |
| `20210314_070803_29_2262` | same folder as above | `_3B_AnalyticMS_SR_8b.tif` | `L3_SRO_MS_` MS8B | SuperDove, 8-band wavelengths, `cloud_percent`, SR image described by the analytic 8b XML |
| `20190801_093015_1018` | legacy Data API, one sub-folder per asset | `_1B_AnalyticMS.tif` | `L1BAB__MS_` MS4B | Dove-R, basic level 1B, no CRS and no cloud cover (both left out), clockwise footprint turned counter-clockwise, measurements href into a sub-folder |
| `1234567_3357220_2017-04-24_0e19` | `ortho_tile/<id>/` | `_BGRN_Analytic.tif` | `L3_OT__MS_` MS4B | `PSOrthoTile` item, native level L3A, MultiPolygon footprint -> bounding box |

Real-product provenance: NONE. No real PlanetScope TDS product has been
converted yet. The JSON property names follow the Planet Data API item
properties and the XML follows the Planet `ps:EarthObservation` metadata
schema as published in the Planet product specification; element names and
value formats still have to be checked against a real delivery. In
particular, the level 1A asset name (`_1A_AnalyticMS`) is an assumption.

`order_7d1c/manifest.json` is an order-level file: it must stay out of every
item's measurements/.
