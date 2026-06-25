from pathlib import PosixPath
from eoSip_converter.imageUtil import create_mosaic_pyvips

raw_images_dir = PosixPath('/mount/damps/hsm/PSI/TPM_EOSIP/test_datasets/workspace/tmp/batch_p-neo_luigi__workfolder_0/000311041_1_2_STD_A/IMG_01_PNEO3_PMS-FS')

out_file = PosixPath(raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_MOSAIC.TIF')
image_arr = [
    [raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R1C1.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R1C2.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R1C3.TIF'],
    [raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R2C1.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R2C2.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R2C3.TIF'],
    [raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R3C1.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R3C2.TIF',
     raw_images_dir / 'IMG_PNEO3_202501150904036_PMS-FS_PRJ_PWOI_000311041_1_2_F_1_RGB_R3C3.TIF']
]
resize = True

import os
print(os.environ.get('TMPDIR'))
os.environ['TMPDIR'] = str(raw_images_dir.resolve())
create_mosaic_pyvips(image_arr, out_file, resize)
