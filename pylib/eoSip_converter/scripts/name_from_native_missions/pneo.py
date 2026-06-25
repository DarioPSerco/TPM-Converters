import os
import zipfile


def modify_src_product(src_product):
    src_product.isPneo = True
    with open(src_product.path, "rb") as fh:
        with zipfile.ZipFile(fh) as z:
            for name in z.namelist():
                if name.find(src_product.METADATA_PREFIX) >= 0:
                    src_product.metContentName.append(name)
                    src_product.metContent.append(z.read(name))
                elif name.find(src_product.PREVIEW_PREFIX) >= 0 and name.upper().endswith(".JPG"):
                    src_product.previewContentName.append(name)
                    data = z.read(name)
                    parent = os.path.dirname(src_product.EXTRACTED_PATH + os.sep + name)

                    if not os.path.exists(parent):
                        os.makedirs(parent)

                    with open(src_product.EXTRACTED_PATH + os.sep + name, "wb") as outfile:
                        outfile.write(data)
    pass


def modify_dest_product(dest_product):
    from eoSip_converter.esaProducts import metadata
    dest_product.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, 'N')
