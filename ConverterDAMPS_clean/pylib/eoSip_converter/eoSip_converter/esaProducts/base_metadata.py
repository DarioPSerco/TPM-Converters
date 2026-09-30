# -*- coding: cp1252 -*-
#
# this class encapsulate the metadata info for products 
#
#
from io import StringIO

# type of metadata:
METADATATYPE_PRODUCT = 'METADATATYPE_PRODUCT'
METADATATYPE_BROWSE = 'METADATATYPE_BROWSE'
METADATATYPE_BASE = 'METADATATYPE_BASE'

# moved from sipBuilder
VALUE_OPTIONAL = "OPTIONAL"
VALUE_CONDITIONS = "CONDITIONS"
VALUE_UNKNOWN = "CONVERTER_UNKNOWN"
VALUE_NONE = "CONVERTER_None"
VALUE_NOT_PRESENT = "CONVERTER_NOT-PRESENT"


class Base_Metadata:
    NOT_DEFINED_VALUES = [VALUE_UNKNOWN, VALUE_NONE, VALUE_NOT_PRESENT]
    counter = 0
    debug = 0

    # the mapping of nodes used in xml report. keys is node path
    xmlNodeUsedMapping = {}

    # the mapping of nodes used in xml report. keys is node path
    xmlVarnameMapping = {}

    def __init__(self):
        # metadata dictionnary
        self.dict = {'__METADATATYPE__': METADATATYPE_BASE}
        # a counter, can be used to increment the gml_id in the xml reports
        self.counter = 0
        self.otherInfo = {}
        self.localAttributes = []
        self.label = 'no label'
        self.defined = False

        if self.debug != 0:
            print(' init Base_Metadata done')

    def valueExists(self, v):
        if v in (None, VALUE_NOT_PRESENT, VALUE_NONE, VALUE_UNKNOWN):
            return False
        return True

    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR Base_Metadata.setDebug: parameter is not an integer")
        self.debug = d

    def getDebug(self):
        return self.debug

    def isMetadataDefined(self):
        """
        Tells if the metadata are defined. used to prevent to set
        everything to None
        """
        return self.defined

    def setMetadataDefined(self, b):
        """Set if the metadata are defined"""
        self.defined = b

    def alterMetadataMaping(self, key, value):
        self.xmlVarnameMapping[key] = value

    def isMetadataMapingAltered(self):
        return len(list(self.xmlVarnameMapping.keys())) > 0

    def getMetadataMaping(self, key, origMappingMap):
        if key in self.xmlVarnameMapping:
            return self.xmlVarnameMapping[key]
        else:
            if key in origMappingMap:
                return origMappingMap[key]
            else:
                return None

    def setOtherInfo(self, key, value):
        self.otherInfo[key] = value

    def getOtherInfo(self, key):
        return self.otherInfo[key]

    def addLocalAttribute(self, name, value):
        """Add a local attribute"""
        self.localAttributes.append({name: value})

    def getLocalAttributes(self):
        """Get all local attributes"""
        return self.localAttributes

    def getLocalAttributeValue(self, name):
        """Get one local attribute"""
        for i in range(len(self.localAttributes)):
            adict = self.localAttributes[i]
            if name in adict:
                return adict[name]

    def removeLocalAttribute(self, name):
        """Remove a local attribute"""
        for i in range(len(self.localAttributes)):
            adict = self.localAttributes[i]
            if name in adict:
                self.localAttributes.remove(adict)
                break

    def localAttributeExists(self, name):
        """Test if local attribute exists"""
        return any([name in adict for adict in self.localAttributes])

    def setUsedInXmlMap(self, adict):
        """Set the dictionary of node used in the xml reports"""
        self.xmlNodeUsedMapping = adict

    def getUsedInXmlMap(self):
        """Get the dictionary of node used in the xml reports"""
        return self.xmlNodeUsedMapping

    def isFieldUsed(self, path=None, aDebug=False):
        """Test if a field is used in the xml report"""
        if self.debug >= 2 or aDebug:
            print("###########################\n###########################\n isFieldUsed: path:'%s'  len(exclusion):%d" % (
            path, len(self.xmlNodeUsedMapping)))
        n = 0
        for item in list(self.xmlNodeUsedMapping.keys()):
            if self.debug >= 2 or aDebug:
                print("########################### exclusion[%d]:%s=%s." % (n, item, self.xmlNodeUsedMapping[item]))
            n = n + 1

        if path in self.xmlNodeUsedMapping:
            if self.debug >= 2 or aDebug:
                print("   field at path:'%s' used flag:%s" % (path, self.xmlNodeUsedMapping[path]))
            if self.xmlNodeUsedMapping[path] == 'UNUSED':
                if self.debug >= 2 or aDebug:
                    print("########################### UNUSED")
                return 0
            else:
                if self.debug >= 2 or aDebug:
                    print("########################### USED")
                return 1
        else:
            if self.debug >= 2 or aDebug:
                print("########################### NO MAPPING; USED")
                print("  field with path:'%s' has no used map entry" % path)
            return 1

    def getMetadataNames(self):
        """Get metadata keys"""
        return sorted(self.dict.keys())

    def setMetadataPair(self, name=None, value=None):
        """Set a metadata name + value"""
        self.dict[name] = value

    def getMetadataValue(self, name=None):
        """Get a metadata value"""
        if name in self.dict:
            return self.dict[name]

        return VALUE_NOT_PRESENT

    def hasMetadataName(self, key):
        """Test if metadata name exists"""
        return key in self.dict

    def deleteMetadata(self, key):
        """Delete a metadata"""
        if key not in self.dict:
            raise Exception("metadata has no key:'%s'" % key)
        else:
            del self.dict[key]

    def merge(self, other, allowOverwrite=False):
        """Merge another metadata into this one"""
        print(" MERGE METADATA; self:%s\n\nVS\n\n%s" % (self.toString(), other.toString()))
        # merge dict, allow overwrite or not if value egual
        n = 0
        for key in list(other.dict.keys()):

            print(" MERGE METADATA key[%s]:%s; other.value=%s" % (n, key, other.dict[key]))
            if allowOverwrite:
                self.dict[key] = other.dict[key]
                print(" MERGE METADATA (overwrite) key[%s]:%s; self.value=%s; other.value=%s" % (
                n, key, self.dict[key], other.dict[key]))
            else:
                if key in list(self.dict.keys()):
                    ok = False
                    same = False
                    if self.dict[key] is None:
                        ok = True
                        print(" MERGE METADATA already present (not overwrite) ok because value is None")
                    elif self.dict[key] in self.NOT_DEFINED_VALUES:
                        ok = True
                        print(" MERGE METADATA already present (not overwrite) ok because value is in NOT_DEFINED_VALUES")
                    elif self.dict[key] == other.dict[key]:
                        ok = True
                        same = True
                        print(" MERGE METADATA already present (not overwrite) ok because value are equals")

                    if ok:
                        if not same:
                            self.dict[key] = other.dict[key]
                    else:
                        raise Exception("can not merge: collide on otherInfo key:%s; self.value=%s; other.value=%s" % (
                        key, self.dict[key], other.dict[key]))
                else:
                    self.dict[key] = other.dict[key]
                    print(" MERGED")
            n += 1

        # merge other info, allow overwrite or not if value egual
        n = 0
        for key in list(other.otherInfo.keys()):
            print(" MERGED METADATA otherKey[%s]=%s" % (n, key))
            if allowOverwrite:
                self.otherInfo[key] = other.otherInfo[key]
            else:
                # self.otherInfo.keys().index(key)
                valueOther = other.otherInfo[key]
                if key in self.otherInfo:
                    value = self.otherInfo[key]
                    if valueOther != valueOther:
                        self.otherInfo[key] = valueOther
                        print(" MERGED METADATA otherInfo pair: %s=%s" % (key, other.otherInfo[key]))
                    else:
                        raise Exception("can not merge: collide on otherInfo key:%s; value=%s" % (key, value))
                else:
                    print(" MERGED METADATA otherInfo pair: %s=%s" % (key, other.otherInfo[key]))
                    self.otherInfo[key] = valueOther
            n += 1

        # merge xmlNodeUsedMapping
        for key in list(other.xmlNodeUsedMapping.keys()):
            self.xmlNodeUsedMapping[key] = other.xmlNodeUsedMapping[key]
            print(" MERGED METADATA xmlNodeUsedMapping pair: %s=%s" % (key, other.xmlNodeUsedMapping[key]))

        # merge xmlNodeUsedMapping
        for key in list(other.xmlVarnameMapping.keys()):
            self.xmlVarnameMapping[key] = other.xmlVarnameMapping[key]
            print(" MERGED METADATA xmlVarnameMapping pair: %s=%s" % (key, other.xmlVarnameMapping[key]))

        # merge label
        self.label = "%s merged with:%s" % (self.label, other.label)
        print(" MERGED METADATA label: %s" % self.label)

        # merge localAttributes
        for item in other.localAttributes:
            if allowOverwrite:
                self.localAttributes.append(item)
                print(" MERGED localAttributes (overwrite) item: %s" % item)
            else:
                if item in self.localAttributes:
                    raise Exception("can not merge: collide on localAttribute:%s" % item)
                else:
                    self.localAttributes.append(item)
                    print(" MERGED localAttributes item: %s" % item)

    def clone__(self):
        """Clone this metadata into a new one, return it"""
        from copy import deepcopy

        return deepcopy(self)

        # clone = Base_Metadata()
        # clone.dict = self.dict.copy()
        # clone.counter = self.counter
        # clone.debug = self.debug
        # clone.xmlNodeUsedMapping = self.xmlNodeUsedMapping.copy()
        # clone.xmlVarnameMapping = self.xmlVarnameMapping.copy()
        # clone.otherInfo = self.otherInfo.copy()
        # clone.localAttributes = list(self.localAttributes)
        # clone.label = "%s" % self.label
        # clone.defined = self.defined
        # return clone

    def toString(self):
        out = StringIO()
        print('\n##################################\n#### START Metadata Info #########\n### Label:%s\n### Dict:' % self.label, file=out)
        for item in sorted(self.dict.keys()):
            print("%s=%s" % (item, self.dict[item]), file=out)

        if self.xmlNodeUsedMapping is not None:
            if len(list(self.xmlNodeUsedMapping.keys())) > 0:
                print("\n### Xml used mapping:", file=out)
                for item in sorted(self.xmlNodeUsedMapping.keys()):
                    print("%s=%s" % (item, self.xmlNodeUsedMapping[item]), file=out)
            else:
                print("\n### Xml mapping empty", file=out)
        else:
            print("\n### NO xml mapping", file=out)

        if self.otherInfo is not None:
            if len(list(self.otherInfo.keys())) > 0:
                print("\n### Other info:", file=out)
                for item in sorted(self.otherInfo.keys()):
                    print("%s=%s" % (item, self.otherInfo[item]), file=out)
            else:
                print("\n### Other info empty", file=out)
        else:
            print("\n### NO other info", file=out)

        if self.localAttributes is not None:
            if len(self.localAttributes) > 0:
                print("\n### local attribute:", file=out)
                for item in sorted(self.localAttributes, key=lambda x: list(x.keys())[0]):
                    print("%s" % item, file=out)
            else:
                print("\n### local attribute empty", file=out)
        else:
            print("\n### NO local attribute", file=out)

        print("#### END Metadata Info ###########\n##################################", file=out)
        return out.getvalue()

    def dump(self):
        tmp = self.toString()
        print(tmp)
        return tmp
