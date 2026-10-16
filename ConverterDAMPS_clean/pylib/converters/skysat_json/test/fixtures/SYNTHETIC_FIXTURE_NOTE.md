# SkySat test fixtures

`synthetic_ssc/` holds five SYNTHETIC native SkySat items, written by
`make_synthetic_ssc.py` (re-runnable, needs `tifffile`). Each item is the Planet
item metadata `<id>_metadata.json` and 16x12 GeoTIFF rasters instead of the
real ones (the ortho ones carry GeoKeys with their EPSG code), so the whole
extraction -> manifest -> overview -> package pipeline runs in a test. Planet
ships no asset XML for SkySat.

| item | layout | assets | product type | proves |
|---|---|---|---|---|
| `20180428_125611_ssc3d2_0017` | Orders API, flat `order_5f3a/SkySatScene/` | `_pansharpened.tif`, `_visual.tif` | `L3_ORT_PSH` MS | values of the specialization's example manifests (footprint, sun angles, incidence 0.7, cloud 56); visual overview; EPSG from the GeoKeys; item files picked by prefix out of a shared folder |
| `20190612_101530_ssc7d3_0042` | same folder as above | `_panchromatic_dn.tif` | `L3_ORT_PAN` PAN | `cloud_percent`, grey overview of a 1-band image |
| `20160501_144606_ssc1d1_0005` | legacy Data API, one sub-folder per asset | `_basic_panchromatic_dn.tif`, `_basic_analytic_dn.tif` | `L1BBDN_MSP` MS | two measurements links, basic level 1B, no CRS and no cloud cover (both left out), `gsd` as resolution, clockwise footprint turned counter-clockwise |
| `20160501_144606_ssc1d1_0006` | one folder | `_basic_l1a_panchromatic_dn.tif` | `L1ABDN_PAN` PAN | values of the L1ABDN_PAN example manifest (incidence 35.1), level 1A |
| `20200619_094518_ssc11_u0001` | `collect/<id>/` | `_visual`, `_pansharpened`, `_analytic`, `_panchromatic` | `SYNORT_BDL` | `SkySatCollect` item: four components, four acquisitionParameters / measurements / overviews, MultiPolygon footprint -> bounding box |

The tests also derive `L1BBDN_MS_`, `L3_ORTVMS_` and `L3_ORT_MS_` items, and a
bundle with two components only, by copying subsets of these files.

Real-product provenance: NONE. No real SkySat TDS product has been converted
yet. The JSON property names follow the Planet Data API item properties of
`SkySatScene` / `SkySatCollect` and the asset file names follow the Planet
SkySat product specification ([RD01] of the specialization); both still have
to be checked against a real delivery. In particular the asset -> product type
mapping (`product_skysat.SCENE_ASSETS`, `BUNDLE_COMPONENTS`) is an assumption.

`order_5f3a/manifest.json` is an order-level file: it must stay out of every
item's measurements/.
