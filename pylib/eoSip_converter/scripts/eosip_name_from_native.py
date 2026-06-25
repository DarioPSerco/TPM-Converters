import argparse
import os
import tempfile
import shutil
import sys
import logging

logging.disable(logging.INFO)

if sys.version_info[0] >= 3:
    from pathlib import Path
else:
    from pathlib2 import Path
    FileNotFoundError = IOError


def get_xml_nodes_version_from_config(config_file_path):
    import configparser

    config_parser = configparser.RawConfigParser()
    config_parser.optionxform = str
    config_parser.read(config_file_path)

    return config_parser.get('eoSip', 'VERSION')


def parse_command_line_args(cl_args):
    """Parses command line arguments using argparse module"""
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config",
        dest="configFile",
        required=True,
        help="path of the configuration file",
    )
    parser.add_argument(
        "-l",
        "--list",
        dest="productListFile",
        help="path of the file containing the products list",
    )
    parser.add_argument(
        "--doneList",
        dest="doneProductListFile",
        help="path of the file containing the products already done list",
    )
    parser.add_argument(
        "-b", "--batch", dest="batchName", help="name of the batch job"
    )
    parser.add_argument(
        "-i", "--batchId", dest="batchId", type=int, help="index of the batch job"
    )
    parser.add_argument(
        "--fileCounter",
        dest="fileCounter",
        type=int,
        help="file counter number, one digit only!",
    )
    parser.add_argument("--inbox", dest="inbox", help="inbox folder")
    parser.add_argument("-o", "--outspace", dest="outbox", help="output folder")
    parser.add_argument("-t", "--tmpspace", dest="tmpbox", help="tmp folder")
    parser.add_argument("--donespace", dest="donebox", help="done folder")
    parser.add_argument("--failedspace", dest="failedbox", help="failed folder")
    parser.add_argument("-m", "--max", dest="max", help="max product to do")
    parser.add_argument(
        "-d",
        "--daemon",
        dest="daemon",
        action="store_true",
        help="run in daemon mode, remotely controlled",
    )
    parser.add_argument(
        "--daemonClass", dest="daemonClass", help="daemon server class"
    )
    parser.add_argument(
        "--multiprocessing",
        dest="multiprocessing",
        action="store_true",
        help="run in multiprocessing mode",
    )
    parser.add_argument(
        "-s",
        "--single",
        dest="singleProduct",
        help="process a single product given in argument",
    )
    parser.add_argument("--joborder", dest="joborder", help="process a job order")
    parser.add_argument(
        "--eraseTmp",
        dest="erase",
        action="store_true",
        help="erase tmp and workfolder after job done",
    )
    parser.add_argument(
        "--move",
        dest="move",
        action="store_true",
        help="move source product (in done folder)",
    )
    parser.add_argument(
        "--buildInTmp",
        dest="buildInTmp",
        action="store_true",
        help="build the final product in tmp folder, then move it to output folder",
    )
    parser.add_argument(
        "-k", "--kmz", dest="createKmz", action="store_true", help="create kmz file"
    )

    # In case first argument is the ingester .py file
    args = parser.parse_args(
        cl_args[1:] if cl_args[0].endswith(".py") else cl_args
    )

    return args


def _import_library_to_name(library_init_path, import_name):
    if sys.version_info[0] >= 3:
        import importlib.util

        spec = importlib.util.spec_from_file_location(import_name, library_init_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[import_name] = module  # critical for submodules
        spec.loader.exec_module(module)
    else:
        import imp
        if not library_init_path.exists():
            library_init_path = library_init_path.parent
        # module = imp.load_source(import_name, str(library_init_path.resolve()))
        # sys.modules[import_name] = module
        sys.path.insert(0, str(library_init_path.parent.parent))  # library_root contains eoSip_converter
        module = __import__(import_name, fromlist=[''])

    return module

def import_eosip_converter(eosip_converter_path):
    return _import_library_to_name(eosip_converter_path / "__init__.py", 'eoSip_converter')

def import_xml_nodes(eosip_converter_path, xml_nodes_version='101'):

    return _import_library_to_name(
        eosip_converter_path / 'esaProducts' / 'definitions_EoSip' / ('v%s' % xml_nodes_version) / 'xml_nodes' / "__init__.py",
        'xml_nodes'
    )

# def import_ingester(ingester_file):
#     from abc import ABCMeta
#
#     spec = importlib.util.spec_from_file_location("ingester_module", ingester_file)
#     mod = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(mod)
#
#     for attr in mod.__dict__.keys():
#         if type(getattr(mod, attr)) is ABCMeta and attr.lower().startswith('ingester'):
#             return getattr(mod, attr)

def import_ingester(ingester_file):
    from abc import ABCMeta

    if sys.version_info[0] >= 3:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ingester_module", ingester_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    else:
        import imp
        mod = imp.load_source("ingester_module", str(ingester_file.resolve()))
        sys.modules[ingester_file.name.replace('.py', '')] = mod

    for attr, value in mod.__dict__.items():
        if isinstance(value, ABCMeta) and attr.lower().startswith("ingester"):
            return value


def setup_arg_parser():
    arg_parser = argparse.ArgumentParser(description='Determine the EOSIP product name from a native product')
    arg_parser.add_argument('converter_location', type=str, help='Path to eoSip_converter library used by ingester')
    arg_parser.add_argument('ingester_file', type=str, help='Ingester file used as EOSIP converter entry point')
    arg_parser.add_argument("-c", "--config", help="Path to config file")
    arg_parser.add_argument('-l', "--native-product-list", type=str,
                            help='Native product list over which to deduce the EOSIP product names')
    arg_parser.add_argument('-s', "--native-product", type=str,
                            help='Native product for which to deduce the EOSIP product names. Overrides native-product-list')
    arg_parser.add_argument('--write-to-json', type=str, nargs='?', const=Path(__file__).with_suffix('.json').name,
                            default=None, help="Write results to a JSON file (optional)")

    return arg_parser


if __name__ == '__main__':
    args = setup_arg_parser().parse_args()
    converter_location = Path(args.converter_location).resolve()
    ingester_file = Path(args.ingester_file).resolve()
    config_file = Path(args.config).resolve()
    native_product = Path(args.native_product).resolve() if args.native_product else None
    native_product_list = Path(args.native_product_list).resolve() if args.native_product_list else None
    mission = config_file.name.replace('.cfg', '').split('_')[-1]
    write_to_json = args.write_to_json

    native_product_list = None if native_product else native_product_list

    for required_file in (converter_location, ingester_file, config_file, native_product_list if not native_product else native_product):
        if not required_file.exists():
            raise FileNotFoundError(str(required_file) + " does not exist")

    if native_product_list is not None:
        with open(str(native_product_list.resolve()), 'rt') as fd:
            native_products = [_.strip() for _ in fd.readlines()]
    else:
        native_products = [native_product]

    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')

    xml_nodes = import_xml_nodes(converter_location, get_xml_nodes_version_from_config(config_file))
    eoSip_converter = import_eosip_converter(converter_location)
    ingester_cls = import_ingester(ingester_file)

    import eoSip_converter.base.processInfo as processInfo
    from eoSip_converter.esaProducts import metadata
    from eoSip_converter.esaProducts import definitions_EoSip
    import name_from_native_missions as nfnm


    def get_eosip_name_from_native(native_product):
        tmp_dir = tempfile.mkdtemp(prefix='eosip_name_from_native_')

        try:
            ingester = ingester_cls()
            # Remove any logging to STDOUT
            for handler in ingester.logger.handlers[:]:  # copy list to avoid mutation issues
                ingester.logger.removeHandler(handler)
                handler.close()

            ingester.args = [
                str(ingester_file),
                "-c", str(config_file),
                "-s", str(native_product),
                "-t", tmp_dir,
                "-o", tmp_dir
            ]

            for attr in ('LOG_FOLDER', 'TMPSPACE', 'OUTSPACE', 'DONESPACE', 'FAILEDSPACE'):
                setattr(ingester, attr, tmp_dir)

            ingester.options = parse_command_line_args(ingester.args)
            ingester.readConfig(ingester.options.configFile)
            ingester.singleProduct = str(native_product)
            ingester.productList = [ingester.singleProduct]

            ingester.makeFolders()
            ingester.getMissionDefaults()
            ingester.batchName = "batch_tmp_0"
            ingester.afterStarting()
            ingester.file_toBeDoneList = "%s/%s" % (tmp_dir, "product_list.txt")
            ingester.writeToBeDoneProduct()

            process_info = processInfo.processInfo()
            process_info.srcPath = str(native_product)
            process_info.num = '1'
            process_info.ingester = ingester

            ingester.setProcessInfo(process_info)
            ingester.createSourceProduct(process_info)
            ingester.createDestinationProduct(process_info)
            process_info.srcProduct.processInfo = process_info
            process_info.workFolder = tmp_dir
            process_info.srcProduct.EXTRACTED_PATH = tmp_dir

            met = metadata.Metadata(ingester.mission_metadatas)
            met.setMetadataPair(metadata.METADATA_ORIGINAL_NAME, process_info.srcProduct.origName)

            mission_submodule = getattr(nfnm, mission, None)
            if mission_submodule is not None:
                modify_src_product = getattr(mission_submodule, "modify_src_product", None)
                if callable(modify_src_product):
                    modify_src_product(process_info.srcProduct)

            ingester.extractMetadata(met, process_info)

            process_info.destProduct.metadata = met
            process_info.destProduct.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))
            process_info.destProduct.processInfo = process_info

            if mission_submodule is not None:
                modify_dest_product = getattr(mission_submodule, "modify_dest_product", None)
                if callable(modify_dest_product):
                    modify_dest_product(process_info.destProduct)

            process_info.destProduct.buildEoNames()

            return process_info.destProduct.sipPackageName

        except Exception as err:
            raise err

        finally:
            shutil.rmtree(tmp_dir)

    mappings = []
    for native_product in native_products:
        result = {'eosip': None, 'error': None, 'native': native_product}
        try:
            result['eosip'] = get_eosip_name_from_native(native_product)
        except Exception as err:
            result['error'] = '%s: %s' % (err.__class__.__name__, str(err))
        finally:
            mappings.append(result)

    # Restore STDOUT stream to print EOSIP product name
    sys.stdout.close()
    sys.stdout = old_stdout

    if write_to_json:
        import json

        with open(write_to_json, 'wt') as fd:
            json.dump(mappings, fd, indent=2)
    else:
        # print('\n'.join([_['eosip'] if _['eosip'] else 'EOSIP converter error' for _ in mappings]))
        print('\n'.join([_['eosip'] if _['eosip'] else _['error'] for _ in mappings]))
