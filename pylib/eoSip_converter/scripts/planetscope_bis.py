import cv2
import pyvips
import matplotlib.pylab as plt
import numpy as np
from PIL import Image
from pathlib import Path
from eoSip_converter import imageUtil

rgb_images_dcy = Path('/home/converter/planetscope_rgb_images')
# with open('/opt/converter/pylib/eoSip_converter/planetscope_tif.list', 'rt') as fd:
#     for line in fd.readlines():
#         source_img = Path(line.strip())
#         nbands = imageUtil.get_nbands(source_img)
#         temp_img = None
#         if nbands >= 3:
#             new_rgb_img = rgb_images_dcy / (source_img.stem + 'RGB' + source_img.suffix)
#             img_data = imageUtil.get_detailed_img_info(source_img)
#
#             rgb_idxs = []
#             for colour in ('red', 'green', 'blue'):
#                 for band in img_data['bands']:
#                     if band['colorInterpretation'].lower() == colour:
#                         rgb_idxs.append(band['band'] - 1)
#                         break
#                 else:
#                     rgb_idxs.append(None)
#
#             imageUtil.extract_and_join_bands(source_img, new_rgb_img, rgb_idxs)

images = [im for im in rgb_images_dcy.iterdir() if im.is_file() and im.suffix == '.tif']
for im_file in images:
    print(im_file.stem)
    out_file = rgb_images_dcy / 'out' / (im_file.stem + '.png')
    if out_file.exists():
        out_file.unlink()

    img_arr = cv2.imread(im_file, cv2.IMREAD_UNCHANGED)
    orig_bit_depth = {'uint16': 16, 'uint8': 8}[str(img_arr.dtype)]
    grey_img_arr = np.mean(img_arr, axis=2)
    grey_img_arr = np.where(grey_img_arr != 0, grey_img_arr, np.nan)
    orig_stats = {
        r'mean': np.nanmean(grey_img_arr),
        r'std': np.nanstd(grey_img_arr),
        r'99%': np.nanpercentile(grey_img_arr, 99.),
        r'1%': np.nanpercentile(grey_img_arr, 1.)
    }
    print(orig_stats)
    orig_stats = {k: 100. * v / (2 ** orig_bit_depth - 1) for k, v in orig_stats.items()}
    label_str = '\n'.join([f"{k} = {v:.1f}%" for k, v in orig_stats.items()])

    imageUtil.makeBrowse_v2(
        type="PNG", src=im_file, dest=out_file, showTraceback=True,
    )

    mean, std = imageUtil.image_mean_and_std(out_file)
    if mean < std:
        imageUtil.boost_brightness_cv2(out_file, out_file, 0.3)

    mean, std = imageUtil.image_mean_and_std(out_file)
    if mean < std:
        out_file.unlink()
        im = pyvips.Image.new_from_file(im_file)
        im = im.extract_band(0, n=3)
        im = imageUtil.resize_img_pyvips(im, out_file, max_dim=1000)
        imageUtil.boost_brightness_cv2(out_file, out_file, 0.3)
        # imageUtil.cv2_clahe(out_file, out_file)
        img_arr = cv2.imread(out_file, cv2.IMREAD_UNCHANGED)
        bit_depth = {'uint16': 16, 'uint8': 8}[str(img_arr.dtype)]
        np_dtype = {16: np.uint16, 8: np.uint8}[bit_depth]
        img_arr = (img_arr / np.percentile(img_arr, 99.5) * (65535 if bit_depth == 16 else 255)).astype(np_dtype)
        cv2.imwrite(out_file, img_arr)

    # imageUtil.cv2_clahe(out_file, out_file)
    img_arr = cv2.imread(out_file, cv2.IMREAD_UNCHANGED)
    bit_depth = {'uint16': 16, 'uint8': 8}[str(img_arr.dtype)]
    plt.close('all')

    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
    ax.imshow(img_arr.astype(np.float32) / (65535 if bit_depth == 16 else 255))
    ax.text(0.95, 0.95, label_str, ha='right', va='top', transform=ax.transAxes, c='magenta', size=10)
    plt.savefig(rgb_images_dcy / 'out' / ('stats_' + im_file.stem + '.png'), dpi=300)
