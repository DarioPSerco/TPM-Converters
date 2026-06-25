import os


def modify_src_product(src_product):
    from eoSip_converter.esaProducts.product_worldview123 import TIFF_SUFFIX

    src_product.contentList = []
    paths = os.walk(src_product.EO_FOLDER, topdown=False)
    paths = sorted(paths, key=lambda x: x[0])  # sort by root directory
    paths = [(_[0], _[1], sorted(_[-1])) for _ in paths]  # sort files by name (latest timestamp goes last)
    for root, dirs, files in paths:
        for name in files:
            eoFile = "%s/%s" % (root, name)

            if name.endswith(TIFF_SUFFIX):
                src_product.tif_matadata_map[name] = eoFile.replace(TIFF_SUFFIX, ".IMD")
                if eoFile.find("_MUL/") > 0:
                    src_product.mulTifPath = eoFile
                    src_product.mulTilPath = eoFile.replace(TIFF_SUFFIX, ".IMD")

            relPath = os.path.join(root, name)[len(src_product.EO_FOLDER) + 1:]
            src_product.contentList.append(relPath)

    if src_product.mulTilPath is None: # look for first .IMD found
        for item in src_product.contentList:
            if item.endswith(".IMD"):
                src_product.mulTilPath = "%s/%s" % (src_product.EO_FOLDER, item)


def modify_dest_product(dest_product):
    pass
