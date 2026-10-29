"""Counter of the <bbvv> package name field for Beijing-1 / NigeriaSat-1 /
UK-DMC-1 products, per "EOPF-EOS Specialization for Beijing-1, Nigeriasat-1
and UK-DMC-1 products" 1.0, section 2.2: <bbvv> = two digits product /
processor baseline (default 00) + two digits counter [00..99].

The same acquisition is delivered in several variants (p / s view, region,
CRS, reduced-resolution QL copy) that share platform, level and sensing time,
so they would get the same package name. The counter keeps them apart: the
first native product to need a name gets counter 01, the next one with the
same name 02, and so on.

Assigned names are kept in a JSON registry, {native dataset name: package
name}, so that a native product converted again gets its name back and a
name is never given to two native products, even after OUTSPACE / PRODUCTS
have been emptied. The registry path is the cfg [Mission-specific-values]
DMC_NAME_REGISTRY; the file must be kept with the conversion outputs.
"""
import json
import os

from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

REGISTRY_KEY = 'DMC_NAME_REGISTRY'
PRODUCT_BASELINE = '00'
FIRST_COUNTER = 1
LAST_COUNTER = 99


class NameRegistry:

    def __init__(self, path):
        self.path = path
        self.names = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fd:
                try:
                    self.names = json.load(fd)
                except ValueError as e:
                    # never start again from an empty registry: names already
                    # given would be given again
                    raise Exception("name registry %s is not valid JSON: %s" % (path, e))
            if not isinstance(self.names, dict):
                raise Exception("name registry %s is not a JSON object" % path)

    def version_for(self, native, name_for):
        """<bbvv> for the native dataset name. name_for(version) builds the
        package name with that version. A native product already in the
        registry gets its own name back; a new one gets the first counter
        whose name is not taken, and is recorded."""
        if native in self.names:
            name = self.names[native]
            version = name[-4:]
            rebuilt = name_for(version)
            if rebuilt != name:
                raise Exception("native %s is registered as %s but now builds %s: "
                                "its metadata changed" % (native, name, rebuilt))
            return version
        taken = set(self.names.values())
        for counter in range(FIRST_COUNTER, LAST_COUNTER + 1):
            version = "%s%02d" % (PRODUCT_BASELINE, counter)
            name = name_for(version)
            if name not in taken:
                self.names[native] = name
                self.save()
                return version
        raise Exception("counter limit %02d reached: no free package name for %s"
                        % (LAST_COUNTER, native))

    def save(self):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fd:
            json.dump(self.names, fd, indent=2, sort_keys=True)
        os.replace(tmp, self.path)


def assign_version(met, native, eo_pattern, registry_path=None):
    """Set METADATA_PRODUCT_VERSION for the native dataset name from the
    registry (path from the cfg DMC_NAME_REGISTRY unless given)."""
    path = registry_path or met.getMetadataValue(REGISTRY_KEY)
    if not met.valueExists(path):
        raise Exception("no %s in the cfg [Mission-specific-values]" % REGISTRY_KEY)

    def name_for(version):
        met.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)
        return NamingConvention_HightRes(eo_pattern).buildProductName(met, None)

    version = NameRegistry(path).version_for(native, name_for)
    met.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, version)
    return version
