# SYNTHETIC fixture — `synthetic_qb2/`

**NOT real QuickBird-2 data.** No real native QuickBird-2 product ships in the
tree (`quickbird/` has no test data; there is no legacy QuickBird converter
under `to_be_converted/`). Hand-authored to match the native structure
`product_quickbird.py` parses:

- `010787518010_01_README.XML` — top README (read; `satId` comes from the `.IMD`).
- `05NOV21054629-M2AS-010787518010_01_P001.IMD` — DigitalGlobe-style `.IMD`;
  parsed for times, sun angles, cloud, corners, spacings, level/descriptor,
  `satId` (must be `QB02`); `BEGIN_GROUP = BAND_*` counted for bands.
- `...-BROWSE.JPG` — ASCII placeholder; `extractToPath` reads it in text mode.

Resolves to type code **BGI_PAN_2A** (QuickBird-2, panchromatic, Standard 2A),
0.6 m GSD, scene centred near N13 / W100. Values invented but plausible.
