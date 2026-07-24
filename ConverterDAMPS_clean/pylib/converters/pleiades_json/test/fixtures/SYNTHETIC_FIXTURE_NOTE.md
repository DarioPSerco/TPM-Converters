# SYNTHETIC FIXTURE — NOT REAL DATA

`synthetic_pl1/DIM_PHR1A_MS_SYNTH.XML` is a hand-written DIMAP metadata file,
faithful to the native Pleiades structure only as far as
`product_pleiades.py` reveals it (xmlMapping paths, LINEAGE component,
Dataset_Extent, Raster_Dimensions, SOFTWARE version). All values are
invented. The test zips it together with a PIL-generated preview JPG and a
dummy IMG_PHR1 entry into a fake native package.

It proves pipeline + JSON structure ONLY — value-correctness on real
Pleiades data is PENDING TDS (none available).
