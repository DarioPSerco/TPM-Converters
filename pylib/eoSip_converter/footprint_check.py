import sys
import matplotlib.pylab as plt

from pathlib import Path
from eoSip_converter.utils.coordinates import GeodeticCoordinate, plot_eo_outline
from eoSip_converter.xmlHelper import XmlHelper


def extract_xml_element_value(md_xml_file, xml_path_from_root):
    with open(md_xml_file, 'rt') as f:
        metContent = f.read()

    helper = XmlHelper()
    helper.setData(metContent)
    helper.parseData()

    return helper.getNodeText(helper.getFirstNodeByPath(path=xml_path_from_root))


footprint_tree = 'featureOfInterest/Footprint/multiExtentOf/MultiSurface/surfaceMember/Polygon/exterior/LinearRing/posList'
center_coord_tree = 'featureOfInterest/Footprint/centerOf/Point/pos'

if len(sys.argv) == 1:
    xml_directory = '/mount/damps/hsm/PSI/TPM_EOSIP/test_datasets/converted/spot_spotview/out/unzipped'
    xml_directory = '/mount/damps/hsm/PSI/TPM_EOSIP/test_datasets/converted/radarsat1/out/unzipped'
    xml_directory = Path(xml_directory)
    md_xml_files = [file for file in xml_directory.iterdir() if file.name.endswith('.MD.XML')]
    plot_output_dir = Path('.').resolve()

elif len(sys.argv) > 2:
    md_xml_files = [Path(xml_file).resolve() for xml_file in sys.argv[1:-1]]
    plot_output_dir = Path(sys.argv[-1]).resolve()

else:
    raise ValueError('Usage: python footprint_check.py path_to_xml_file1.xml ... path_to_output_dir/')

for md_xml_file in md_xml_files:
    footprint_str = extract_xml_element_value(md_xml_file, footprint_tree)
    center_str = extract_xml_element_value(md_xml_file, center_coord_tree)
    # footprint_str = '55.02257696366172 -3.5968157491832358 54.93236752869279 -3.6275127792703756 54.91608010817513 -3.441677793993108 55.00689208252719 -3.4176581366409664 55.02257696366172 -3.5968157491832358'
    # center_str = "54.9693814898911 -3.519372716968917"
    # footprint_str = "35.4504 76.8472 36.2114 76.6827 36.1446 76.2148 35.3833 76.3841 35.4504 76.8472"
    lats = [float(_) for _ in footprint_str.split()[::2]]
    lons = [float(_) for _ in footprint_str.split()[1::2]]
    footprint_coords = [GeodeticCoordinate(*pair) for pair in zip(lats, lons)]
    # center_str = f'{sum(lats) / len(lats)} {sum(lons) / len(lons)}'

    center_coord = GeodeticCoordinate(*[float(_) for _ in center_str.split()])

    fig, ax = plot_eo_outline(center_coord, footprint_coords)

    plot_file = plot_output_dir / (md_xml_file.name.split('.')[0] + '_footprint.pdf')
    if len(sys.argv) > 1:
        print('Saving to ' + str(plot_file))
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    else:
        plt.show()
