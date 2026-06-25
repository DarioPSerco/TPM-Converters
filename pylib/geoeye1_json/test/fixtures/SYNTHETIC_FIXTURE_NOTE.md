# SYNTHETIC fixture — `synthetic_ge1/`

**NOT real GeoEye-1 data.** No real native GeoEye-1 product ships in the tree
(`geoeye1/` has no test data; there is no legacy GeoEye-1 converter under
`to_be_converted/`). Hand-authored to match the native structure
`product_geoeye1.py` parses:

- `010787518010_01_README.XML` — top README (read but `satId` actually comes from the `.IMD`).
- `19AUG22104421-M2AS-010787518010_01_P001.IMD` — DigitalGlobe-style `.IMD`;
  parsed `key = value;` lines for times, sun angles, cloud, corners, spacings,
  level/descriptor, `satId` (must be `GE01`); `BEGIN_GROUP = BAND_*` counted for bands.
- `...-BROWSE.JPG` — ASCII placeholder; `extractToPath` raises if no preview is
  found, and reads it in text mode, so a real JPEG is not needed for the test.

Resolves to type code **GIS_PAN_2A** (GeoEye-1, panchromatic, Standard 2A),
scene centred near N13 / W100. Values invented but plausible.
