# EOPF-EOS converter for IRS-P5 (Cartosat-1) and IRS-P6 (ResourceSat-1 LISS-III) products,
# per "EOPF-EOS Specialization for IRS-P5 (Cartosat-1) products" 1.0 (applied to IRS-P6 as well).
__version__ = '1.0.0'

EOSIP_CONVERTER_LIBRARY_VERSION_REQ = ">=1.1.0"
VERSION_CHANGES = {
    '1.0.0': "First issue, per EOPF-EOS Specialization for IRS-P5 (Cartosat-1) "
             "products v1.0, applied to IRS-P5 and IRS-P6",
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
