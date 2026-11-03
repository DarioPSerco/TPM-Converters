# SYNTHETIC FIXTURES — NOT REAL DATA

No real RADARSAT-2 delivery was available. `synthetic_rs2/` holds four
product folders written by `make_synthetic_rs2.py` (re-runnable). Their
`product.xml` follows the RADARSAT-2 product schema (default namespace
`http://www.rsi.ca/rs2/prod/xml/schemas`, element paths as read by the legacy
eoSIP converter `pylib/products/product_radarsat.py` on `main`), reduced to
the elements `product_radarsat2.py` reads. Values are invented but
plausible. `BrowseImage.tif` is a small grey gradient; the
`imagery_<pol>.tif` files are 16-byte placeholders.

| fixture (beam) | product type | what it covers |
|---|---|---|
| `F0W2` Wide Fine SLC | L1_BSWFSLC | dual pol (HH HV), orbit from `orbitDataFile`, EPSG:4326 |
| `S3` Standard SGF | L1_BS__SGF | single pol, orbit from a `.prodReport`, descending |
| `FQ14` Fine Quad-Pol SSG | L2_BSF_SSG | quad pol, level 2, UTM 33N map projection |
| `SCWA` ScanSAR Wide SCW | L1_SCW____ | dual pol (VV VH -> "VH, VV"), left looking |

They prove the pipeline and the JSON structure ONLY. To check on the first
real RADARSAT-2 deliveries:

- the delivery layout (product folder, ZIP wrapping, NITF instead of GeoTIFF);
- the `orbitDataFile` value and whether a `.prodReport` comes with it (the
  orbit number is not in `product.xml`; else cfg `METADATA_ORBIT` = 0 with a
  WARNING);
- the beam mode mnemonics met and their fold on the spec's operational modes
  (`MODE_RULES`);
- the resolutions computed from the look bandwidths against the RADARSAT-2
  Product Description nominal values;
- the `mapProjection` element of SSG / SPG products (only UTM is handled);
- the footprint corner order and the browse image orientation.
