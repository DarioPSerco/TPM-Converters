# EOPF-EOS converter for Beijing-1, NigeriaSat-1 and UK-DMC-1 (SLIM6) products,
# per "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1 and UK-DMC-1 products" 1.0.
#
# Pending items are tagged TODO(DMC-PENDING:<ID>) across this package:
#   NATIVE-META   NigeriaSat-1 / UK-DMC-1 platform values (no sample yet)
__version__ = '1.0.0'

EOSIP_CONVERTER_LIBRARY_VERSION_REQ = ">=1.1.0"
VERSION_CHANGES = {
    '1.0.0': "First issue, per EOPF-EOS Specialization for Beijing-1, "
             "Nigeriasat-1 and UK-DMC-1 products v1.0",
}

def ensure_eosip_converter_version_is_valid(required_version):
    from packaging.version import Version
    from packaging.specifiers import SpecifierSet
    import eoSip_converter

    spec = SpecifierSet(required_version)
    installed_version = Version(eoSip_converter.__version__)

    if not installed_version in spec:
        raise ImportError(f"eoSip_converter {installed_version} does not satisfy {spec}")


ensure_eosip_converter_version_is_valid(EOSIP_CONVERTER_LIBRARY_VERSION_REQ)
