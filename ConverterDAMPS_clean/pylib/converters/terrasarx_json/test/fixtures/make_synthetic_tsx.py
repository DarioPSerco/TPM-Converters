"""Build the synthetic TerraSAR-X fixtures from real products.

Usage: python make_synthetic_tsx.py <folder holding the real DIMS deliveries>

Each real product folder (the one holding ``<product name>.xml``) found
under the given folder gives one fixture folder ``synthetic_tsx/<variant>_<mode>/``
(a short name: the real folder name, repeated in the annotation file name,
would bring the fixture paths near the Windows 260-character limit) with:

- the main annotation, cut down to the elements the converter reads
  (generalHeader, productComponents, productInfo and, for a geocoded product,
  productSpecific/geocodedImageInfo/mapProjection), values unchanged;
- ``PREVIEW/BROWSE.tif``: the real browse image shrunk to at most 64 pixels;
- the image data files named by the annotation, as 16-byte placeholders
  (the real ones are hundreds of MB).
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent / "synthetic_tsx"
KEEP = ("generalHeader", "productComponents", "productInfo")
BROWSE_MAX = 64


def component_path(component):
    path = component.findtext("file/location/path").strip()
    name = component.findtext("file/location/filename").strip()
    return Path(name) if path == "." else Path(path) / name


def make_one(xml_path):
    name = xml_path.stem
    # TSX1_SAR__SSC______SL_S_SRA_... -> SSC_SL
    dest = HERE / ("%s_%s" % (name[10:13], name[19:21]))
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for child in list(root):
        if child.tag in KEEP:
            continue
        if child.tag == "productSpecific":
            projection = child.find("geocodedImageInfo/mapProjection")
            for grandchild in list(child):
                child.remove(grandchild)
            if projection is not None:
                ET.SubElement(child, "geocodedImageInfo").append(projection)
            continue
        root.remove(child)

    dest.mkdir(parents=True, exist_ok=True)
    tree.write(dest / xml_path.name, encoding="utf-8", xml_declaration=False)

    for image in root.findall("productComponents/imageData"):
        target = dest / component_path(image)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"SYNTHETIC IMAGE\n")

    browse = component_path(root.find("productComponents/browseImage"))
    target = dest / browse
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(xml_path.parent / browse) as image:
        image.thumbnail((BROWSE_MAX, BROWSE_MAX))
        image.save(target, "TIFF")
    print("fixture: %s" % dest)


if __name__ == "__main__":
    for xml_path in sorted(Path(sys.argv[1]).rglob("T[SD]X1_SAR__*.xml")):
        if xml_path.stem == xml_path.parent.name:
            make_one(xml_path)
