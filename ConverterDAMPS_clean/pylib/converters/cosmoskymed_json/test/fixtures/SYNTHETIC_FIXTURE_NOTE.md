# COSMO-SkyMed test fixtures

`synthetic_csk/` holds two SYNTHETIC native products, written by
`make_synthetic_csk.py` (re-runnable). They carry the real HDF5 attribute tree
(root attributes + `S0n` beam group + image dataset + `QLK` quicklook) with
4x4 / 6x8 rasters instead of the multi-gigabyte real ones, so the whole
extraction -> manifest pipeline runs in a test.

| fixture | mode | level | polarisation |
|---|---|---|---|
| `CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301` | STRIPMAP HIMAGE | 1B (DGM_B) | single, HH |
| `CSKS4_SCSU_PP_01_HH_RA_FF_20200704101010_20200704101020` | STRIPMAP PINGPONG | 1A (SCS_U) | dual, HH + VV |

The HIMAGE fixture's attribute VALUES are copied from the real TDS product
`CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301` (delivery
`736299-502923`), on which the converter and the packager were run end to end
on 2026-09-24: manifest
`CS__OPER_L1BSM__DGM_20170515T172253_20170515T172301_0001.JSON` + overview PNG
in OUTSPACE, and a 632.3 MB delivery ZIP in PRODUCTS. So the HIMAGE values ARE
real-product values; the PINGPONG fixture is invented (no dual-pol TDS yet) and
proves the dual-pol / Level 1A / type-code branches only.

No SCANSAR (WIDEREGION / HUGEREGION) and no Second Generation (CSG) product
has been seen yet: those mappings are covered by unit assertions on the
mapping tables, not by a product run.
