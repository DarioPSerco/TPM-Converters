__version__ = '1.2.0'
EOSIP_CONVERTER_LIBRARY_VERSION_REQ = ">=1.1.0"
VERSION_CHANGES = {
    '1.1.0': 'Start of version tracking',
    '1.2.0': 'EOPF-EOS Specialization for PLEIADES products 1.01',
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