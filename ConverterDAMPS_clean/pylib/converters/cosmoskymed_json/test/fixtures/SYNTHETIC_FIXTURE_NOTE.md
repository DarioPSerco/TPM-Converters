# COSMO-SkyMed test fixtures

`synthetic_csk/` holds three SYNTHETIC native products, written by
`make_synthetic_csk.py` (re-runnable). They carry the real attribute tree (root
attributes + `S0n` beam groups + image / quicklook datasets) with 4x4 / 8x6
rasters instead of the multi-gigabyte real ones, so the whole extraction ->
manifest pipeline runs in a test.

| fixture | delivery | mode | level | polarisation |
|---|---|---|---|---|
| `CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301` | HDF5 `.h5` | STRIPMAP HIMAGE | 1B (DGM_B) | single, HH |
| `CSKS4_SCSU_PP_01_HH_RA_FF_20200704101010_20200704101020` | HDF5 `.h5` | STRIPMAP PINGPONG | 1A (SCS_U) | dual, HH + VV |
| `CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732` | GeoTIFF `.tgz` | SCANSAR WIDEREGION | 1C (GEC_B) | single, HH (4 subswaths) |

Real-product provenance: the HIMAGE and the WIDEREGION fixtures copy the
attribute VALUES of the two real TDS products the converter was run on end to
end on 2026-09-24:

| real product | manifest | delivery ZIP |
|---|---|---|
| `CSKS1_DGM_B_HI_01_HH_RD_SF_20170515172254_20170515172301` (`736299-502923`) | `CS__OPER_L1BSM__DGM_20170515T172253_20170515T172301_0001.JSON` | 632.3 MB |
| `CSKS1_GEC_B_WR_01_HH_RD_SF_20171007160717_20171007160732` (`1008699-756540`) | `CS__OPER_L1CSC__GEC_20171007T160717_20171007T160732_0001.JSON` | 219.4 MB |

So those two fixtures' values ARE real-product values. The PINGPONG fixture is
invented (no dual-pol TDS yet) and proves the dual-pol / Level 1A / SM type-code
branches only.

No HUGEREGION and no Second Generation (CSG) product has been seen yet: those
mappings are covered by assertions on the mapping tables, not by a product run.
