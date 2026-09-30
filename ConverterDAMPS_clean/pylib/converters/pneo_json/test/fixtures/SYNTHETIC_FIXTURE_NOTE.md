# SYNTHETIC FIXTURE — NOT REAL DATA

`synthetic_pln/DIM_PNEO1_MS_SYNTH.XML` is a hand-written DIMAP metadata file,
faithful to the native Pleiades-NEO structure only as far as
`product_pneo.py` reveals it (xmlMapping paths, LINEAGE/PROCESSING_PNEO
component, Dataset_Extent, Raster_Dimensions/NBANDS, DATASET_NAME/SOFTWARE
versions, CRS codes). All values are invented.

IMPORTANT: the `Solar_Incidences/SUN_AZIMUTH|SUN_ELEVATION` block is itself
[INFERRED from the Pleiades DIMAP layout] — the original pneo extraction
never read it, and no real PNEO DIMAP was available to confirm it exists.
The fixture uses the same inferred paths the new xmlMapping entries expect,
so the test proves NOTHING about those paths being right — only that the
pipeline works IF they are. Real-TDS confirmation is the top PENDING item.

It proves pipeline + JSON structure ONLY — value-correctness on real
PNEO data is PENDING TDS (none available).
