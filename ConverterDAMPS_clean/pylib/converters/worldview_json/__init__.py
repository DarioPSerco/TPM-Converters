__version__ = '1.0.0'
EOSIP_CONVERTER_LIBRARY_VERSION_REQ = ">=1.1.0"
VERSION_CHANGES = {
    '0.9.2': "Standalone shared (GeoEye-1, Quickbird, Worldview 123) Python 2 converter",
    '1.0.0': "Worldview v2.0 EOSIP specification (Worldview legion) and centralised for use with eoSip_converter common library"
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