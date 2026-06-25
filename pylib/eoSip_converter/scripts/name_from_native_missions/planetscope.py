import os


def modify_src_product(src_product):
    import importlib.util
    import os
    import inspect

    # Suppose you have an instance
    path = inspect.getfile(src_product.__class__)

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("dynamic_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Now you can access its symbols
    TYPECODE_XML_ENDINGS = module.TYPECODE_XML_ENDINGS
    XML_SUFFIX = module.XML_SUFFIX
    XML_SUFFIX2 = module.XML_SUFFIX2

    determined_typecode = src_product.determineTypeCode()

    raw_xml_endings_order = (
        TYPECODE_XML_ENDINGS[determined_typecode],
        XML_SUFFIX,
        XML_SUFFIX2,
    )

    n = 0
    for root, dirs, files in os.walk(src_product.EO_FOLDER, topdown=False):
        root = root.replace('/' if os.sep == '\\' else '\\', os.sep)
        dirs = [d.replace('/' if os.sep == '\\' else '\\', os.sep) for d in dirs]
        files = [f.replace('/' if os.sep == '\\' else '\\', os.sep) for f in files]

        xml_metadata_found = False
        for name in files:
            for ending in raw_xml_endings_order:
                if name.endswith(ending):
                    xml_metadata_found = True
                    src_product.xml_metadata_path = "%s%s%s" % (root, os.sep, name)
                    with open(src_product.xml_metadata_path, 'rt') as fd:
                        src_product.xml_metadata = fd.read()
                    break
            if xml_metadata_found:
                break


def modify_dest_product(dest_product):
    pass
