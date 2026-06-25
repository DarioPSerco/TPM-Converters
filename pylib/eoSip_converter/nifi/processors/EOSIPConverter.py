import configparser
import importlib.util
import os
import sys

from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Union

from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import ExpressionLanguageScope, PropertyDescriptor, StandardValidators


def _get_cfg_file_key_value(cfg_file: Path, key: Union[str, Tuple[str]]) -> str:    
    if isinstance(key, str):
        key = (key, )

    config = configparser.ConfigParser()
    config.read(cfg_file)

    return config.get(*key)

def get_converter_version_from_cfg(converter_config: Path) -> str:
    return _get_cfg_file_key_value(converter_config, ('Mission-specific-values', 'METADATA_SIP_SOFTWARE_VERSION'))

def get_eosip_spec_version(converter_config):
    return _get_cfg_file_key_value(converter_config, ('Mission-specific-values', 'METADATA_SIP_VERSION'))

def restore_original_sys_path(func):
    """Decorator to restore the original sys.path after the function call"""
    def wrapper(*args, **kwargs):
        original_sys_path = sys.path.copy()
        try:
            return func(*args, **kwargs)
        finally:
            sys.path = original_sys_path
    return wrapper

def sha256sum(path: Union[Path, str]) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def format_timestamp_as_iso_utc(timestamp):
    """Convert a timestamp to ISO 8601 format in UTC"""
    return datetime.fromtimestamp(timestamp)\
                   .replace(tzinfo=timezone.utc)\
                   .astimezone(timezone.utc)\
                   .isoformat().replace('+00:00', 'Z')

# def import_ingester_class(ingester_module_path: Path, ingester_class_name: str):
#     print(f"[DEBUG] Checking if module path exists: {ingester_module_path}")
#     if not ingester_module_path.exists():
#         raise FileNotFoundError(f"Module path does not exist: {ingester_module_path}")

#     print(f"[DEBUG] Attempting to load module spec from: {ingester_module_path}")
#     spec = importlib.util.spec_from_file_location(
#         ingester_module_path.stem, str(ingester_module_path)
#     )

#     if spec is None:
#         raise ImportError(f"[ERROR] Could not create module spec from path: {ingester_module_path}")
#     if spec.loader is None:
#         raise ImportError(f"[ERROR] Spec loader is None for module: {ingester_module_path}")

#     print(f"[DEBUG] Creating module from spec...")
#     module = importlib.util.module_from_spec(spec)

#     print(f"[DEBUG] Executing module...")
#     try:
#         spec.loader.exec_module(module)
#     except Exception as e:
#         raise RuntimeError(f"[ERROR] Failed to execute module {ingester_module_path}: {e}")

#     print(f"[DEBUG] Looking for class '{ingester_class_name}' in module...")
#     if not hasattr(module, ingester_class_name):
#         raise AttributeError(f"[ERROR] Module does not contain class '{ingester_class_name}'")

#     print(f"[DEBUG] Class '{ingester_class_name}' successfully loaded.")
#     return getattr(module, ingester_class_name)


class EOSIPConverter(FlowFileTransform):
    class ConverterProperty(Enum):
        """Enum for property names"""
        CONVERTER_DCY = 'converter_dcy'
        INGESTER = 'ingester'
        INGESTER_CLASS = 'ingester_class'
        CONVERTER_CONFIG = 'converter_config'
        EOSIP_VERSION_DCY = 'eosip_version_dcy'
        OUT_DCY = 'out_dcy'
        TMP_DCY = 'tmp_dcy'

    class Java:
        implements = ['org.apache.nifi.python.processor.FlowFileTransform']

    class ProcessorDetails:
        version = '0.0.1b'
        description = 'A processor to test the implementation of EOSIP converter code as a NiFi processor'
        tags = ['converter']

    def __init__(self, **kwargs):
        super().__init__()
        
        self._converter_dcy = PropertyDescriptor(
            name=self.ConverterProperty.CONVERTER_DCY.value,
            display_name="Converter Directory",
            description="Full path to the converter directory, 'eoSip_converter'",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )

        self._ingester = PropertyDescriptor(
            name=self.ConverterProperty.INGESTER.value,
            display_name="Ingester",
            description="Full path to the ingester file, 'ingester_*.py'",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )

        self._ingester_class = PropertyDescriptor(
            name=self.ConverterProperty.INGESTER_CLASS.value,
            display_name="Ingester Class",
            description="Name of the ingester class within the ingester file",
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )

        self._converter_config = PropertyDescriptor(
            name=self.ConverterProperty.CONVERTER_CONFIG.value,
            display_name="Converter Configuration",
            description="Full path to the converter configuration file, 'ingest_*.cfg'",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )
        
        self._eosip_version_dcy = PropertyDescriptor(
            name=self.ConverterProperty.EOSIP_VERSION_DCY.value,
            display_name="EOSIP version path",
            description="Full path to the EOSIP version definition directory, e.g. '/path/to/xml_nodes/v101'",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )
        
        self._out_dcy = PropertyDescriptor(
            name=self.ConverterProperty.OUT_DCY.value,
            display_name="Out directory", 
            description="Full path to the directory in which to write the EOSIP products",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )

        self._tmp_dcy = PropertyDescriptor(
            name=self.ConverterProperty.TMP_DCY.value,
            display_name="Temporary directory",
            description="Full path to the temporary directory in which to write "
            "intermediate/temporary products of the conversion pipeline. A "
            "sub-directory by the name of the flowfile's UUID will be created "
            "to house each conversion's intermediate products",
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            required=True,
            expression_language_scope=ExpressionLanguageScope.ENVIRONMENT
        )

    @staticmethod
    def get_property_value(property_name, context, flowfile) -> str:
        """Helper function to get the value of a property"""
        return context.getProperty(property_name).evaluateAttributeExpressions(flowfile).getValue()

    def get_converter_dcy(self, context, flowfile) -> Path:
        """Property for the converter directory"""
        return Path(self.get_property_value(self.ConverterProperty.CONVERTER_DCY.value, context, flowfile)).resolve()

    def get_ingester(self, context, flowfile) -> Path:
        """Property for the ingester file"""
        return Path(self.get_property_value(self.ConverterProperty.INGESTER.value, context, flowfile)).resolve()

    def get_ingester_class_name(self, context, flowfile) -> str:
        """Property for the ingester class name"""
        return self.get_property_value(self.ConverterProperty.INGESTER_CLASS.value, context, flowfile)
    
    def get_converter_config(self, context, flowfile) -> Path:
        """Property for the converter configuration file"""
        return Path(self.get_property_value(self.ConverterProperty.CONVERTER_CONFIG.value, context, flowfile)).resolve()

    def get_eosip_version_dcy(self, context, flowfile) -> Path:
        """Property for the EOSIP version directory"""
        return Path(self.get_property_value(self.ConverterProperty.EOSIP_VERSION_DCY.value, context, flowfile)).resolve()

    def get_out_dcy(self, context, flowfile) -> Path:
        """Property for the EOSIP product (out) directory"""
        return Path(self.get_property_value(self.ConverterProperty.OUT_DCY.value, context, flowfile)).resolve()

    def get_tmp_dcy(self, context, flowfile) -> Path:
        """Property for the temporary directory"""
        return Path(self.get_property_value(self.ConverterProperty.TMP_DCY.value, context, flowfile)).resolve()

    @property
    def descriptors(self):
        """Returns a list of property descriptors for the processor for use by NiFi"""
        return [
            self._converter_dcy,
            self._ingester,
            self._ingester_class,
            self._converter_config,
            self._eosip_version_dcy,
            self._out_dcy,
            self._tmp_dcy,
        ]

    def getPropertyDescriptors(self):
        """Required method for NiFi to be able to list defined properties"""
        return self.descriptors

    # Required method if we want to enable the user to define their own 
    # properties in the processor's browser interface
    def getDynamicPropertyDescriptor(self, propertyname):
        return PropertyDescriptor(
            name=propertyname,
            description="A user-defined property",
            dynamic=True
        )

    @staticmethod
    def get_ingester_version(ingester_module_path: Path, absent_value=None):
        import importlib.util

        # Load the module
        spec = importlib.util.spec_from_file_location(
            ingester_module_path.stem, ingester_module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the class
        version = getattr(module, "__version__", absent_value)
        
        if absent_value is None:
            raise AttributeError(f"{ingester_module_path.resolve()} has no __version__ attribute")

        return version

    @staticmethod
    def import_ingester_class(ingester_module_path: Path, ingester_class_name: str):
        import importlib.util

        # Load the module
        spec = importlib.util.spec_from_file_location(
            ingester_module_path.stem, ingester_module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the class
        return getattr(module, ingester_class_name)

    @restore_original_sys_path
    def transform(self, context, flowfile):
        # sys.exit calls cause the python process to hang indefinitely in NiFi
        # Therefore replace with properly raised RuntimeError
        def nifi_safe_exit(*args, **kwargs):
            raise RuntimeError(f"[FATAL] sys.exit() was called with args={args}, kwargs={kwargs}")

        sys.exit = nifi_safe_exit        

        converter_dcy = self.get_converter_dcy(context, flowfile)
        ingester_module = self.get_ingester(context, flowfile)
        eosip_version_dcy = self.get_eosip_version_dcy(context, flowfile)

        for path in (ingester_module.parent.parent, eosip_version_dcy, ingester_module.parent, converter_dcy):
            path = str(path.resolve())
            if path not in sys.path:
                sys.path.append(path)
        import eoSip_converter
        raise ValueError(f"python executable = {sys.executable}")
        
        # from ingester_terrasar_x import ingester_terrasar_x as ingester_cls
        converter_config = self.get_converter_config(context, flowfile)
        ingester_class_name = self.get_ingester_class_name(context, flowfile)
        ingester_cls = self.import_ingester_class(ingester_module, ingester_class_name)

        ingester = ingester_cls()
        ingester.setDebug = 0
        # ingester.logger = self.logger  # Causes NiFi errors when converter starts modifying logger instance

        # Returned attributes in the output FlowFile
        try:
            eosip_converter_version = get_converter_version_from_cfg(converter_config)
        except configparser.NoOptionError:
            eosip_converter_version = self.get_ingester_version(ingester_module, absent_value='NA')

        attrs = {
            "conversion.config": str(converter_config),
            "conversion.converter": str(Path(eoSip_converter.__file__).parent),
            "conversion.converterVersion": str(eosip_converter_version),
            "conversion.eosipSpecVersion": get_eosip_spec_version(converter_config),
            "conversion.eosipVersion": str(eosip_version_dcy),
            "conversion.ingesterClass": f"{ingester_cls.__module__}.{ingester_cls.__name__}",
            "conversion.ingesterFile": str(ingester_module),
        }

        self.logger.info("STARTING THE EOSIP CONVERSION")
        try:
            # TODO: Put out/tmp directories as processor properties
            exit_code = ingester.starts(
                [
                    str(ingester_module),
                    '-c', str(converter_config),
                    '-s', flowfile.getAttribute('nativeProduct'),
                    '-o', str(self.get_out_dcy(context, flowfile)),
                    '-t', str(self.get_tmp_dcy(context, flowfile) / flowfile.getAttribute("uuid")),
                ],
            )
        except Exception as e:
            pass

        eosip_product, conversion_success, error_message = None, False, None

        if not ingester.eosip_done:
            error_message = ingester.errorSrc
            # Don't use error as it shows up in the NiFi bulletins/processor
            self.logger.warning(f"No EOSIP product created -> {error_message}")

        elif len(ingester.eosip_done) == 1:
            eosip_product = ingester.eosip_done[0]
            conversion_success = True
            self.logger.info(f"EOSIP product created: {eosip_product}")

        else:
            eosips_str = '\n - '.join(ingester.eosip_done)
            error_message = f"Multiple EOSIP products created, which is not expected:\n - {eosips_str}"
            self.logger.warning(error_message)

        try:
            tmp_dir = Path(ingester.list_done[0].split('|')[1]).resolve()
        except:
            tmp_dir = ''

        attrs.update({
            "conversion.startTime": format_timestamp_as_iso_utc(ingester.runStartTime),
            "conversion.endTime": format_timestamp_as_iso_utc(ingester.runStopTime),
            "conversion.duration": format(ingester.runStopTime - ingester.runStartTime, '.2f'),
            "eosipProduct": eosip_product if eosip_product else '',
            "eosipProduct.name": Path(eosip_product).name if eosip_product else '',
            "eosipProduct.size":  str(os.stat(eosip_product).st_size) if eosip_product else '',
            "eosipProduct.sha256sum":  sha256sum(eosip_product) if eosip_product else '',
            "conversion.error": error_message if error_message else '',
            "conversion.tmpDir": str(tmp_dir),
        })

        return FlowFileTransformResult(
            relationship="success" if conversion_success else "failure",
            attributes=attrs
        )
