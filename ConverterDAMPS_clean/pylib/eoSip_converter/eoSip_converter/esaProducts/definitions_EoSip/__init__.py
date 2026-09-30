import sys

debug = 0
current_module = sys.modules[__name__]

# def name
FIXED__PACKAGE_EXT = 'PACKAGE_EXT'
FIXED__EOSIP_PRODUCT_EXT = 'EOSIP_PRODUCT_EXT'
FIXED__JPEG_EXT = 'JPEG_EXT'
FIXED__PNG_EXT = 'PNG_EXT'
FIXED__TGZ_EXT = 'TGZ_EXT'
FIXED__XML_EXT = 'XML_EXT'
FIXED__SIP = 'SIP'

FIXED__BROWSE_JPEG_EXT = 'BROWSE_JPEG_EXT'
FIXED__BROWSE_JPG_EXT = 'BROWSE_JPG_EXT'
FIXED__BROWSE_PNG_EXT = 'BROWSE_PNG_EXT'
FIXED__MD_EXT = 'MD_EXT'
FIXED__QR_EXT = 'QR_EXT'
FIXED__SI_EXT = 'SI_EXT'
FIXED__SSD_EXT = 'SSD_EXT'
FIXED__REPORT_EXT = 'REPORT_EXT'

# fixed:
__PACKAGE_EXT = 'ZIP'
__EOSIP_PRODUCT_EXT = 'ZIP'
__JPEG_EXT = 'JPEG'
__JPG_EXT = 'JPG'
__PNG_EXT = 'PNG'
__XML_EXT = 'XML'
__TAR_EXT = 'TAR'
__TGZ_EXT = 'TGZ'
__SIP = 'SIP'

# composed:
# TODO first one to be updated
__BROWSE_JPEG_EXT = 'BI.%s' % __JPG_EXT
__BROWSE_JPG_EXT = 'BI.%s' % __JPG_EXT
__BROWSE_PNG_EXT = 'BI.%s' % __PNG_EXT
__MD_EXT = 'MD.%s' % __XML_EXT
__QR_EXT = 'QR.%s' % __XML_EXT
__SI_EXT = 'SI.%s' % __XML_EXT
__SSM_EXT = 'SSM.%s' % __XML_EXT
__REPORT_EXT = __XML_EXT


class EOSIPVersionError(Exception):
    """Exception raised for errors in the module version."""

    def __init__(self, required_version, current_version):
        self.required_version = required_version
        self.current_version = current_version
        super().__init__(
            f"EOSIP (xml_nodes) version {current_version} in path, but required version is {required_version}."
        )



def getDefinition(name=None):
    """Get a definition value"""
    if hasattr(current_module, "__%s" % name):
        return getattr(current_module, "__%s" % name)
    else:
        # return "NO-EoSip-def:'%s'" % name
        raise Exception("EoSip definition not exists:'%s'" % name)


def getBrowseExtension(n=0, format=__BROWSE_JPEG_EXT, default=False, numerated=False):
    """Returns the extension of the nth browse.
    - add D if default and not numerated -> .BID.PNG
     - add n if numerated -> .BIn.PNG
     """
    result = ''
    if n == 0:  # we only have one browse
        if not default:
            result = format
            if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 0 format:%s" % (n, result))
        else:
            if not numerated:
                base = format
                pos = base.find('.')
                result = base[0:pos]
                result = "%sD.%s" % (result, base[pos + 1:])
                if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 1:%s" % (n, result))
            else:
                base = format
                pos = base.find('.')
                result = base[0:pos]
                result = "%s0.%s" % (result, base[pos + 1:])
                if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 2:%s" % (n, result))
    else:  #
        if not numerated:
            if n == 0:
                if default:
                    base = format
                    pos = base.find('.')
                    result = base[0:pos]
                    result = "%sD.%s" % (result, base[pos + 1:])
                    if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 3:%s" % (n, result))
                else:
                    result = format
                    if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 4 format:%s" % (n, result))
        else:
            if n == 0:
                if default:
                    base = format
                    pos = base.find('.')
                    result = base[0:pos]
                    result = "%sD.%s" % (result, base[pos + 1:])
                    if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 5:%s" % (n, result))
                else:
                    base = format
                    pos = base.find('.')
                    result = base[0:pos]
                    result = "%s0.%s" % (result, base[pos + 1:])
                    if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 6:%s" % (n, result))
            else:
                base = format
                pos = base.find('.')
                result = base[0:pos]
                result = "%s%s.%s" % (result, n, base[pos + 1:])
                if debug != 0: print(" ###@@@### getBrowseExtension(%s) returns 7:%s" % (n, result))
    return result
