# DMC test fixtures

`synthetic_dmc/` holds four SYNTHETIC native Beijing-1 products, written by
`make_synthetic_dmc.py` (re-runnable, needs Pillow). Each product is an
unzipped delivery: the DIMAP header `<x>.dim`, the `<x>_meta.sip` zip with a
minimal `repository.xml`, a 16x12 quicklook JPEG and placeholder `.tif`,
`.htm` and `.xsl` bytes (the converter never reads them, the packager copies
them to measurements/).

Folder and file names are short (`l1r_p`, ...) to stay well inside the
Windows 260-character path limit; the dataset name the converter reads is the
`DATASET_NAME` inside each `.dim`.

| folder | DATASET_NAME | proves |
|---|---|---|
| `l1r_p` | `DS00001a_000000_010499_p_L1R_AA` | every value the converter reads (platform, level, scene time, footprint, sun angles, CRS, production date, resolution); first in its registry: counter `01` of `<bbvv>`; no cloud cover (left out); green quicklook |
| `l1r_s` | `DS00001a_000000_010499_s_L1R_BB` | same scene time as `l1r_p`: the name registry gives it counter `02`, which keeps the package names apart; cloud cover filled (written); clockwise frame turned counter-clockwise; red quicklook |
| `l1t_p` | `DS00002b_000000_010499_p_L1T_EPSG_4258_CC` | level `1T` -> `L1_ORT_MS_`; geographic CRS EPSG:4258 |
| `l1t_ql` | `DS00002b_000000_010499_p_L1T_QL_EPSG_2393_CC` | reduced-resolution QL copy of `l1t_p`, converted as a normal product: same scene time, counter `02` after `l1t_p`; projected CRS EPSG:2393, footprint from `FRAME_LON` / `FRAME_LAT`, not the `FRAME_X` / `FRAME_Y` metres |

The tests also derive failing products (unknown mission or level, no DATASET_NAME;
missing quicklook, `_meta.sip` or resolution; footprint in metres only; no
CRS) by editing copies.

Real-product provenance: the file set and the element paths of the `.dim`
and of `repository.xml` (GeoImage object) are those of seven real Beijing-1
deliveries (five L1R `DC00068e_*_L1R_FI / _SE / _NO`, two L1T
`DC000683_*_L1T_EPSG_4258_FI` and `_L1T_QL_EPSG_2393_FI`, delivered as flat
zips), reduced to the elements the converter reads and their parents. All
values and dataset names are synthetic; no real data is committed. The
clockwise frame of `l1r_s` was not seen in the real deliveries (their frames
are counter-clockwise) and is there to test the reversal.
