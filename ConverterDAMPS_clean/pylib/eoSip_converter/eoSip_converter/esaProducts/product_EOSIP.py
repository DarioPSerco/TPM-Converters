"""This class represent a EoSIP product (ZIP directory product) it contains:
 - a product
 - a product metadata report file
 - zero or more browse image
 - zero or more browse metadata report
 - zero or one sip volume description

 it uses:
 - one metadata object for the product metadata
 - one browse_metadata object for each browse metadata

This class will create a eo-sip product (not read it at this time)
2015/01 update: start to read an eoSip product
"""
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import traceback
from io import StringIO

from eoSip_converter import fileHelper, xmlHelper
from eoSip_converter.base.geo.geoInfo import GeoInfo
from eoSip_converter.esaProducts.namingConvention import NamingConvention
from eoSip_converter.esaProducts.product import Product
from eoSip_converter.esaProducts.product_directory import Product_Directory
from eoSip_converter.serviceClients import xmlValidateServiceClient
from eoSip_converter.esaProducts import (
    browse_metadata, definitions_EoSip, eosip_product_helper, formatUtils,
    metadata
)
from xml_nodes import (
    alt_EarthObservation, atm_EarthObservation, eop_EarthObservation,
    eop_browse, gin_EarthObservation, lmb_EarthObservation,
    opt_EarthObservation, rep_browseReport, sar_EarthObservation, sipBuilder
)

# the zipfile or wrapper module, which is set using the setUsePythonZipLib method
# zipfile as default
global zipfile
import zipfile

# list of supported validation schema type
BROWSE_SCHEMA_TYPE = "BI"
PRODUCT_SCHEMA_TYPE = "MD"
QUALITY_SCHEMA_TYPE = "QR"
SIP_SCHEMA_TYPE = "SI"

# ways of storing original productSRC_PRODUCT_AS_FILE="SRC_PRODUCT_AS_FILE"
SRC_PRODUCT_AS_ZIP = "SRC_PRODUCT_AS_ZIP"
SRC_PRODUCT_AS_DIR = "SRC_DIR_PRODUCT_AS_DIR"
SRC_PRODUCT_AS_DIR = "SRC_PRODUCT_AS_DIR"
SRC_PRODUCT_AS_TAR = "SRC_PRODUCT_AS_TAR"
SRC_PRODUCT_AS_TGZ = "SRC_PRODUCT_AS_TGZ"
SRC_PRODUCT_AS_FILE = "SRC_PRODUCT_AS_FILE"
SRC_PRODUCT_AS_FILE_INTO_EOZIP = "SRC_PRODUCT_AS_FILE_INTO_EOZIP"

# the version of the SIP.XML info file
DEFAULT_SIP_INFO_TYPE = 2.0  # 2.0 is the concise XML
EXTENDED_SIP_INFO_TYPE = 2.1  # 2.1 is the more complete XML
EXTENDED_SIP_INFO_TYPE_30 = 3.0  # 3.0
GIN_SIP_INFO_TYPE = 2.2  # 2.2 is the gin namespace XML

SERVICE_XML_VALIDATION = "xmlValidate"  # list if supported services
PRODUCT_SIZE_NOT_SET = -999999999999


class Product_EOSIP(Product_Directory):
    # browse matadata dictionnary: key=browsePath, value=browse_metadata object
    browse_metadata_dict = None

    # xml node used mapping
    xmlMappingBrowse = None
    xmlMappingMetadata = None

    # xml tag that have to be replaced
    # BROWSE_CHOICE is in browse report
    # LOCAL_ATTR is in metadata report
    # block pattern
    NODES_AS_TEXT_BLOCK = ["<BROWSE_CHOICE/>", "<LOCAL_ATTR/>", "<BROWSES/>", "<BROWSE_CHOICE></BROWSE_CHOICE>",
                           "<LOCAL_ATTR></LOCAL_ATTR>", "<BROWSES></BROWSES>"]

    # replacing text, if None it can not be defaulted.
    NODES_AS_TEXT_BLOCK_DEFAULT = [""] * 6

    # keywords that meens the value was not found
    NOT_DEFINED_VALUES = [sipBuilder.VALUE_UNKNOWN, sipBuilder.VALUE_NONE, sipBuilder.VALUE_NOT_PRESENT]

    LIST_OF_SRC_PRODUCT_STORE_TYPE = [
        SRC_PRODUCT_AS_DIR, SRC_PRODUCT_AS_ZIP, SRC_PRODUCT_AS_TAR,
        SRC_PRODUCT_AS_TGZ, SRC_PRODUCT_AS_FILE, SRC_PRODUCT_AS_FILE_INTO_EOZIP
    ]

    xmlMapping = {
        metadata.METADATA_START_DATE_TIME: '/phenomenonTime/TimePeriod/beginPosition',
        metadata.METADATA_STOP_DATE_TIME: '/phenomenonTime/TimePeriod/endPosition',
        metadata.METADATA_TIME_POSITION: '/resultTime/TimeInstant/timePosition',
        metadata.METADATA_PLATFORM: '/procedure/EarthObservationEquipment/platform/Platform/shortName',
        metadata.METADATA_PLATFORM_ID: '/procedure/EarthObservationEquipment/platform/Platform/serialIdentifier',
        metadata.METADATA_INSTRUMENT: '/procedure/EarthObservationEquipment/instrument/Instrument/shortName',
        metadata.METADATA_SENSOR_TYPE: '/procedure/EarthObservationEquipment/sensor/Sensor/sensorType',
        metadata.METADATA_SENSOR_OPERATIONAL_MODE: '/procedure/EarthObservationEquipment/sensor/Sensor/operationalMode',
        metadata.METADATA_RESOLUTION: '/procedure/EarthObservationEquipment/sensor/Sensor/resolution',
        metadata.METADATA_ORBIT: '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitNumber',
        metadata.METADATA_ORBIT_DIRECTION: '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitDirection',
        metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED: '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/wrsLongitudeGrid',
        metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED: '/procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/wrsLatitudeGrid',
        metadata.METADATA_BROWSES_TYPE: '/result/EarthObservationResult/browse/BrowseInformation/type',
        metadata.METADATA_PRODUCT_SIZE: '/result/EarthObservationResult/product/ProductInformation/size',
        metadata.METADATA_IDENTIFIER: '/metaDataProperty/EarthObservationMetaData/identifier',
        metadata.METADATA_PARENT_IDENTIFIER: '/metaDataProperty/EarthObservationMetaData/parentIdentifier',
        metadata.METADATA_ACQUISITION_TYPE: '/metaDataProperty/EarthObservationMetaData/acquisitionType',
        metadata.METADATA_TYPECODE: '/metaDataProperty/EarthObservationMetaData/productType',
        metadata.METADATA_STATUS: '/metaDataProperty/EarthObservationMetaData/status',
        metadata.METADATA_ACQUISITION_CENTER: '/metaDataProperty/EarthObservationMetaData/downlinkedTo/DownlinkInformation/acquisitionStation',
        metadata.METADATA_PROCESSING_CENTER: '/metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/processingCenter',
        metadata.METADATA_PROCESSING_TIME: '/metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/processingDate',
        metadata.METADATA_PROCESSING_LEVEL: '/metaDataProperty/EarthObservationMetaData/processing/ProcessingInformation/processingLevel'
    }

    def __init__(self, path=None):
        super(Product_EOSIP, self).__init__(path)

        if self.debug != 0:
            print(" init class Product_EOSIP, path=%s" % path)

        self.browse_metadata_dict = {}

        if path is not None:
            self.path = path

        self.generationTime = None
        self.type = Product.TYPE_EOSIP

        # the namingConvention class used
        # for sip gpackage name
        # and eo product name
        self.namingConventionSipPackage = None
        self.namingConventionEoPackage = None

        # Eo product name (as in final eoSip product): is contained (as zip or
        # tar or folder or tgz ...) inside the package.
        # no extension. So == identifier
        self.eoProductName = None
        # Eo package name (as in final eoSip product): is contained (as zip or
        # tar or folder or tgz ...) inside the package
        # has extension, like:
        # AL1_OPER_AV2_OBS_11_20090517T025758_20090517T025758_000000_E113_N000.ZIP
        self.eoPackageName = None
        self.eoPackageExtension = None  # Eo package extension
        self.sipProductName = None  # the Sip product name, has no extension
        self.sipPackageName = None  # the Sip package name, has extension

        # the Sip package extention (.ZIP normally)
        self.sipPackageExtension = 'ZIP'

        # the sip package full extension (ZIP normally, but also SIP.ZIP). created in buildEoNames
        # self.sipPackageFullExtension=self.sipPackageExtension
        # the compression of the eoSip zip
        self.src_product_stored_compression = None
        # and the eo product part
        self.src_product_stored_eo_compression = None

        # the sip package full path
        self.sipPackagePath = None

        # the identified: product name minus extension, like:
        # AL1_OPER_AV2_OBS_11_20090517T025758_20090517T025758_000000_E113_N000
        self.identifier = None

        # the path of the source browses that are in this EoSip
        self.sourceBrowsesPath = []

        # the source product full path
        self.sourceProductPath = None

        # the browse shortName (as in final eoSip product)
        self.browses = []

        # browse file information (list or dict)
        self.browsesInfo = []

        # the generated xml reports:
        self.sipReport = None  # sip report xml data
        self.productReport = None  # the product report xml data
        self.browsesReportPath = None  # the browse report path. A list []
        self.browseBlockDisabled = False  # browse block removed from MD.XML
        self.additionalContent = {}  # additional files we want in the eoSip
        self.reportFullPath = None
        self.qualityReportFullPath = None
        self.sipFullPath = None

        # if product done using converter: the process information
        self.processInfo = None

        # the way the original product is stored in this eoSip
        self.src_product_stored = SRC_PRODUCT_AS_ZIP
        self.src_product_stored_compression = True

        # needed to be able to read EoSip:
        # EoSip helper class
        self.eoSipHelper = None

        # eoSip product can be:
        # - created: converter build it
        # - read: read from eoSip.ZIP package
        # if read, can be worked on in some tmpDir. If so it has the flag
        # workingOn=True
        self.created = True
        self.loaded = False
        self.workingOn = False
        self.loadedFromPath = None
        self.workingOnFolder = None
        # interresting loading message
        self.loadingMessage = None

        # eoSip loaded pieces
        self.eoPieces = []

        # can be:
        # - the eoSip folder in the workfolder
        self.tmpFolder = None

        # used if source file not present in working folder eosip folder
        self.contentListPath = {}

        # used in case we create a temporary zip
        self.tmpZipSize = -1

        self.metContent = None

        # tmp file to be removed when eosip is done
        self.toBeRemovedFiles = []

        # the type of SIP.XML cleated
        self.SipInfoType = DEFAULT_SIP_INFO_TYPE

        self.normalZip = True  # Use normal ziplib as default

    def setTmpZipFile(self, s):
        self.tmpZipSize = s

    def getTmpZipFile(self):
        return self.tmpZipSize

    def setGenerationTime(self, t):
        self.generationTime = t

    def setSipInfoType(self, v):
        self.SipInfoType = v

    def getPath(self):
        return self.path

    def setUsePythonZipLib(self, boolean):
        """set use normal ziplib (b=True), or wrapped version (b=False)"""
        global zipfile

        self.normalZip = boolean
        print(" setUsePythonZipLib:%s" % self.normalZip)
        if self.normalZip:
            print("  setUsePythonZipLib: python zipfile imported:%s" % dir(zipfile))
        else:
            from ..wrappers import zipfileWrapper as zipfile
            print("  setUsePythonZipLib: zipfileWrapper imported:%s" % dir(zipfile))

    def getUsePythonZipLib(self):
        """get used ziplib version"""
        return self.normalZip

    def setTypology(self, t):
        self.TYPOLOGY = t

    def getSipProductName(self):
        return self.sipProductName

    def getSipPackageName(self):
        return self.sipPackageName

    def getEoProductName(self):
        return self.eoProductName

    def getEoPackageName(self):
        return self.eoPackageName

    def setSipProductName(self, n):
        print(" change sipProductName from:%s to %s" % (self.sipProductName, n))
        self.sipProductName = n
        # set also itentifier
        self.identifier = self.eoProductName
        # set in metadata
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.eoProductName)

    def setSipPackageName(self, n):
        print(" change sipPackageName from:%s to %s" % (self.sipPackageName, n))
        self.sipPackageName = n
        # set in metadata
        self.metadata.setMetadataPair(metadata.METADATA_FULL_PACKAGENAME, self.sipPackageName)

    def setSipPackageExtension(self, n):
        """Set full extension can be like: 'SIP.ZIP' or 'ZIP'"""
        print(" change setSipPackageExtension from:%s to %s" % (self.sipPackageExtension, n))
        self.sipPackageExtension = n

    def setSipPackageFullExtension(self, n):
        """Set full extension can be like: 'SIP.ZIP' or 'ZIP'"""
        print(" change sipPackageFullExtension from:%s to %s" % (self.sipPackageExtension, n))
        self.sipPackageExtension = n

    def setEoPackageExtension(self, n):
        """Set full extension can be like: 'ZIP' or '.GZ'"""
        print(" change setEoPackageExtension from:%s to %s" % (self.eoPackageExtension, n))
        self.eoPackageExtension = n

    def setEoProductName(self, n):
        """
        Set the EO product name + EO package name
        - used in case we have a EO product name that don't follow a naming convention
        """
        print(" change eoProductName from:%s to %s" % (self.eoProductName, n))
        self.eoProductName = n
        #
        self.eoPackageName = "%s.%s" % (self.eoProductName, self.eoPackageExtension)

    def addAdditionalContent(self, path, name):
        print(" add additional content: path=%s; name=%s" % (path, name))
        self.additionalContent[name] = path

    def addPiece(self, p):
        """Add a piece"""
        self.eoPieces.append(p)

    def addContentAndPath(self, anAias, aPath):
        """Add a content + path"""
        if anAias in self.contentList:
            raise Exception("addContentAndPath: %s already present in contentList" % anAias)
        if anAias in list(self.contentListPath.keys()):
            raise Exception("addContentAndPath: %s already present in contentListPath" % anAias)
        self.contentList.append(anAias)
        self.contentListPath[anAias] = aPath

    def hasPiece(self, n):
        """Test if has a piece"""
        present = False
        for item in self.eoPieces:
            if item.name == n:
                present = True
                break
        return present

    def getPiece(self, n):
        """Get a piece"""
        for item in self.eoPieces:
            if item.name == n:
                return item

    def getPieceNames(self):
        """Get pieces list"""
        names = []
        for item in self.eoPieces:
            names.append(item.name)
        return names

    def getPieceContent(self, n):
        """Get a piece content"""
        for item in self.eoPieces:
            if item.name == n:
                if not self.created:  # get from loaded zip
                    with open(self.path, 'r') as ff:
                        with zipfile.ZipFile(ff) as zh:
                            data = zh.read(n)
                    return data
                else:
                    raise NotImplementedError(
                        "getPieceContent: not implemented for created eoSip"
                    )

    def addToProcessInfoLog(self, mess):
        """Add to proces info log"""
        if self.processInfo is not None:
            self.processInfo.addLog(mess)

    def setNamingConventionSipInstance(self, namingConventionInstance):
        """Set the sip package naming convention"""
        if namingConventionInstance is None:
            raise Exception("can not set Sip namingConvention because is None")
        if not isinstance(namingConventionInstance, type(NamingConvention())):
            raise Exception("Sip namingConvention is not instance of class NamingConvention but:%s; type:%s" % (
                namingConventionInstance, type(namingConventionInstance)))
        self.namingConventionSipPackage = namingConventionInstance
        if self.debug != 0:
            print(" setNamingConventionSipInstance to:%s" % self.namingConventionSipPackage)

    def setNamingConventionEoInstance(self, namingConventionInstance):
        """Set the eo package naming convention"""
        if namingConventionInstance is None:
            raise Exception("can not set Eo namingConvention because is None")
        if not isinstance(namingConventionInstance, type(NamingConvention())):
            raise Exception("Eo namingConvention is not instance of class NamingConvention but:%s; type:%s" % (
                namingConventionInstance, type(namingConventionInstance)))
        self.namingConventionEoPackage = namingConventionInstance
        if self.debug != 0:
            print(" setNamingConventionEoInstance to:%s" % self.namingConventionEoPackage)

    def getNamingConventionSipInstance(self):
        return self.namingConventionSipPackage

    def setFolder(self, f):
        """Set the source product folder path"""
        self.folder = f
        self.parentFodler = os.path.dirname(self.folder)

    # moved here from Ingester
    # (parentFolder == pInfo.workFolder)
    def makeFolder(self, parentFolder):
        self.setFolder("%s%s%s" % (parentFolder, os.sep, self.getSipProductName()))
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        return self.folder

    def loadProduct(self):
        """
        Load content from a EoSip product, test the item compression,
        try to get the MD, SI, QR, EO product pieces
        """
        self.created = False
        # create a processInfo if not exists
        if self.processInfo is None:
            from ..base import processInfo

            aProcessInfo = processInfo.processInfo()
            aProcessInfo.srcPath = self.path
            aProcessInfo.num = 0
            # set some usefull flags
            # self.setProcessInfo(aProcessInfo)

        if not os.path.exists(self.path):
            raise Exception("EoSIp product does not exists:%s" % self.path)

        self.loadingMessage = ''

        # extract sip package and name info
        self.sipPackagePath = self.path
        self.SipPackageName = os.path.basename(self.path)
        self.SipProductName = self.SipPackageName.replace(definitions_EoSip.getDefinition('EOSIP_PRODUCT_EXT'), '')

        # package name(without extension). WORKS ONLY WHEN ONE FILENAMECONVENTION USED! TODO solve pb
        # is it a .SIP.ZIP?
        pos = self.SipPackageName.find(definitions_EoSip.getDefinition('SIP'))
        if pos > 0:
            if self.debug != 0:
                print(" loadProduct: ZIP in ZIP case")
            self.eoProductName = self.SipPackageName.replace(".%s.%s" % (
                definitions_EoSip.getDefinition('SIP'), definitions_EoSip.getDefinition('EOSIP_PRODUCT_EXT')),
                                                             ".%s" % definitions_EoSip.getDefinition(
                                                                 'EOSIP_PRODUCT_EXT'))
        else:
            if self.debug != 0:
                print(" loadProduct: NOT ZIP in ZIP case")
            self.eoProductName = self.SipPackageName.replace(definitions_EoSip.getDefinition('EOSIP_PRODUCT_EXT'),
                                                             ".%s" % definitions_EoSip.getDefinition(
                                                                 'EOSIP_PRODUCT_EXT'))

        # read zip content
        if not os.path.exists(self.path):
            raise Exception("file not found:%s" % self.path)
        self.contentList = []
        with open(self.path, 'rb') as fh:
            with zipfile.ZipFile(fh) as z:
                n = 0
                d = 0
                firstLevel = True
                storeCompressedItem = 0
                storeNonCompressedItem = 0
                for name in z.namelist():
                    n = n + 1
                    if self.debug != 0:
                        print("  zip content[%d]:%s" % (n, name))
                    if name.endswith('/'):
                        d = d + 1
                        firstLevel = False

                    # check for known parts
                    piece = EoPiece(name)
                    piece.compressed = self.__testZipEntryCompression(self.path, name)
                    if piece.compressed:
                        storeCompressedItem = storeCompressedItem + 1
                    else:
                        storeNonCompressedItem = storeNonCompressedItem + 1

                    if firstLevel and name.endswith(definitions_EoSip.getDefinition('MD_EXT')):
                        self.reportFullPath = name
                        piece.type = definitions_EoSip.getDefinition('MD_EXT')

                    elif firstLevel and name.endswith(definitions_EoSip.getDefinition('SI_EXT')):
                        self.sipFullPath = name
                        piece.type = definitions_EoSip.getDefinition('SI_EXT')

                    elif firstLevel and name.endswith(definitions_EoSip.getDefinition('QR_EXT')):
                        self.qualityReportFullPath = name
                        piece.type = definitions_EoSip.getDefinition('QR_EXT')

                    elif firstLevel and (
                            name.endswith(definitions_EoSip.getDefinition('JPG_EXT')) or
                            name.endswith(definitions_EoSip.getDefinition('JPEG_EXT')) or
                            name.endswith(definitions_EoSip.getDefinition('PNG_EXT'))
                    ):
                        self.sourceBrowsesPath.append(name)
                        piece.type = 'BI'

                    elif firstLevel and name == self.eoProductName:
                        self.sourceProductPath = name
                        self.__testZipEntryCompression(self.path, name)

                    self.eoPieces.append(piece)
                    self.contentList.append(name)

        if self.processInfo is not None:
            self.processInfo.addLog("EoSip product read: %s" % self.path)

        self.loadingMessage = "%s%s\n" % (self.loadingMessage, "zip uncompressed items:%s; compressed items:%s" % (
            storeNonCompressedItem, storeCompressedItem))

        self.loaded = True

    def __testZipEntryCompression(self, path, name):
        if self.eoSipHelper is None:
            self.eoSipHelper = eosip_product_helper.Eosip_product_helper(self)
        compressed = self.eoSipHelper.isZipFileItemCompressed(path, name)
        if self.debug != 0:
            print("  __testZipEntryCompression: is zip entry '%s' compressed:%s" % (name, compressed))
        return compressed

    def startWorkingOn(self):
        """
        start working on the product:
        - content copied in 'workFolder/workingOn' folder
        """
        if self.created:
            raise Exception("can not work on EoSip being created")

        self.workingOn = True
        self.processInfo.addLog("start working on EoSip:%s" % self.path)
        self.workingOnFolder = '%s/workingOn' % self.processInfo.workFolder

        if not os.path.exists(self.workingOnFolder):  # create it
            self.addToProcessInfoLog("  will make workingOn folder:%s" % self.workingOnFolder)
            os.makedirs(self.workingOnFolder)
            self.addToProcessInfoLog("  workingOn folder created:%s\n" % self.workingOnFolder)
        else:
            self.addToProcessInfoLog("  workingOn folder exists:%s" % self.workingOnFolder)

    def getEoSipHelper(self):
        return self.eoSipHelper

    def getMetadataInfo(self):
        self.addToProcessInfoLog(" getMetadataInfo")
        filename, xmlData = self.eoSipHelper.getMdPart()
        return xmlData

    def extractMetadata(self, met=None):
        self.addToProcessInfoLog(" extractMetadata")

        # create metadata and eoSipHelper if needed
        self.metContent = None
        if self.eoSipHelper is None:
            self.eoSipHelper = eosip_product_helper.Eosip_product_helper(self)
        self.addToProcessInfoLog(" eoSipHelper created")

        self.metContent = self.getMetadataInfo()

        # get typology
        typology = self.eoSipHelper.getTypologyFromMdContent(self.metContent)  # is like: eop, sar, lmb...
        # set in ingester as supported type: EOP, SAR, LMB...
        supportedTypology = None
        n = 0
        for item in sipBuilder.TYPOLOGY_REPRESENTATION:
            if item == typology:
                supportedTypology = sipBuilder.TYPOLOGY_REPRESENTATION
                break
            n += 1

        if supportedTypology is None:
            raise Exception("unknown typology:%s" % typology)

        if self.processInfo is not None and self.processInfo.ingester is not None:
            self.processInfo.ingester.TYPOLOGY = sipBuilder.TYPOLOGY_REPRESENTATION_SUFFIX[n]
        met.setMetadataPair(metadata.METADATA_TYPOLOGY, typology)

        # extact metadata from MD.XML
        # NEW for LANDSAT1-7: if there is an alias set in EoSipHelper, set with setMdXmlAlias(), then call  EoSipHelper to get the 'standard' XML to be parsed
        helper = xmlHelper.XmlHelper()
        if self.eoSipHelper.getXmlAdapter() is not None:
            print("##@@##@@## use getXmlAdapter")
            newMetContent = self.eoSipHelper.getXmlAdapter().generateMdXml(self.metContent)
            self.metContent = newMetContent
        helper.setData(self.metContent)
        helper.parseData()

        # get fields
        op_element = helper.getRootNode()
        num_added = 0

        reportBuilder = eop_EarthObservation.eop_EarthObservation()
        n = 0
        for field in self.xmlMapping:
            # take care of the case we have a metadata name in the path: like '/...../....../$TYPECODE$_abcd/.../'
            mapping = self.xmlMapping[field]
            mappingOk = mapping
            pos = mappingOk.find('$')
            if pos >= 0:
                pos2 = mappingOk.find('$', pos + 1)
                if pos2 > 0:
                    metadataName = mappingOk[pos + 1:pos2]
                    value = met.getMetadataValue(metadataName)
                    mappingOk = mapping.replace("$%s$" % metadataName, value)

            # attribute case
            if mappingOk.find("@") >= 0:
                attr = mappingOk.split('@')[1]
                path = mappingOk.split('@')[0]
            else:
                attr = None
                path = mappingOk

            #
            if self.debug != 0:
                print("  xml node path:%s" % path)

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData is None:
                aValue = None
            else:
                if attr is None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  -->%s=%s" % (field, aValue))
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

            n = n + 1

        self.metadata = met
        # refine metadata
        self.refineMetadata()

        return num_added, helper

    def refineMetadata(self):
        """Refine the metadata"""
        # separate date and time from datetTimeZ stored in METADATA_START_DATE_TIME
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE_TIME)
        if tmp.find('T') > 0:
            date = tmp.split('T')[0]
            time = tmp.split('T')[1]
            if tmp.find('Z') > 0:
                time = time.replace('Z', '')
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, time)
            if self.debug != 0:
                print("  refineMetadata: start date:%s  time:%s" % (date, time))

        tmp1 = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE_TIME)
        if tmp.find('T') > 0:
            date = tmp1.split('T')[0]
            time = tmp1.split('T')[1]
            if tmp.find('Z') > 0:
                time = time.replace('Z', '')
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, time)
            if self.debug != 0:
                print("  refineMetadata: stop date:%s  time:%s" % (date, time))

        # set track and frame
        tmp = self.metadata.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, tmp)
        tmp = self.metadata.getMetadataValue(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED)
        self.metadata.setMetadataPair(metadata.METADATA_FRAME, tmp)

    def setSrcProductStoreType(self, t):
        """
        How will we store the source product in the destination eoSip?
        ZIP, TGZ,...
        """
        self.LIST_OF_SRC_PRODUCT_STORE_TYPE.index(t)
        self.src_product_stored = t

    def getSrcProductStoreType(self):
        return self.src_product_stored

    def setSrcProductStoreCompression(self, b):
        """Set if the eoSip zip compressed"""
        self.src_product_stored_compression = b

    def getSrcProductStoreCompression(self):
        return self.src_product_stored_compression

    def setSrcProductStoreEoCompression(self, b):
        """Set if the eo product is compressed"""
        self.src_product_stored_eo_compression = b

    def getSrcProductStoreEoCompression(self):
        return self.src_product_stored_eo_compression

    def setXmlMappingMetadata(self, dict1, dict2):
        if self.debug != 0:
            print((" setXmlMappingMetadata:%s; %s" % (dict1, dict2)))
        self.xmlMappingMetadata = dict1.copy()
        self.xmlMappingBrowse = dict2.copy()
        # put it in metadata
        self.metadata.xmlNodeUsedMapping = dict1.copy()

    def setProcessInfo(self, p):
        self.processInfo = p

    def getProcessInfo(self):
        return self.processInfo

    def getMetadataAsString(self):
        return self.metadata.toString()

    def getNamesInfo(self):
        data = ''
        data = "%sSip product name (no ext):%s\n" % (data, self.getSipProductName())
        data = "%sSip package name (with ext):%s\n" % (data, self.sipPackageName)
        data = "%sEo product name (no ext):%s\n" % (data, self.eoProductName)
        data = "%sEo package name (with ext):%s\n" % (data, self.eoPackageName)
        return data

    def addSourceBrowse(self, path=None, addInfo=None):
        """Add a source browse, create the corresponding report info"""
        if self.debug != 0:
            print("#############$$$$$$$$$$$$$$$ add source browse file[%d]:%s" % (len(self.sourceBrowsesPath), path))
            print("#############$$$$$$$$$$$$$$$ add source browse info[%d]:%s" % (len(self.browsesInfo), addInfo))

        # test already present
        if path in self.sourceBrowsesPath:
            raise Exception("cannot add several time the same browse:%s" % path)

        self.sourceBrowsesPath.append(path)
        self.browsesInfo.append(addInfo)
        shortName = os.path.split(path)[1]
        # create browse metadata info
        bMet = browse_metadata.Browse_Metadata()
        # set typology
        bMet.setOtherInfo("TYPOLOGY_SUFFIX", self.metadata.getOtherInfo("TYPOLOGY_SUFFIX"))

        # set xml node used map
        bMet.setUsedInXmlMap(self.xmlMappingBrowse)
        if self.debug != 0:
            print("################################## set bmet xmlMappingBrowse to: %s" % bMet.getUsedInXmlMap())

        bMet.setMetadataPair(browse_metadata.BROWSE_METADATA_FILENAME, shortName)
        pos = shortName.rfind('.')
        tmp = shortName
        if pos >= 0:
            tmp = tmp[0:pos]
        bMet.setMetadataPair(browse_metadata.BROWSE_METADATA_NAME, tmp)
        # set metadata for browse: these one are the same as for product
        bMet.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER,
                             self.metadata.getMetadataValue(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER))
        bMet.setMetadataPair(metadata.METADATA_START_DATE, self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        bMet.setMetadataPair(metadata.METADATA_START_TIME, self.metadata.getMetadataValue(metadata.METADATA_START_TIME))
        bMet.setMetadataPair(metadata.METADATA_STOP_DATE, self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE))
        bMet.setMetadataPair(metadata.METADATA_STOP_TIME, self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME))
        # change last 2 last typecode digit in: BP
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
        tmp = tmp[0:len(tmp) - 2]
        tmp = "%sBP" % tmp
        bMet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_TYPE, tmp)
        bMet.setMetadataPair(
            'METADATA_GENERATION_TIME',
            self.metadata.getMetadataValue(metadata.METADATA_GENERATION_TIME)
        )
        bMet.setMetadataPair('METADATA_RESPONSIBLE', self.metadata.getMetadataValue('METADATA_RESPONSIBLE'))
        bMet.setMetadataPair('BROWSE_METADATA_IMAGE_TYPE', self.metadata.getMetadataValue('BROWSE_METADATA_IMAGE_TYPE'))
        self.browse_metadata_dict[path] = bMet
        if self.debug != 0:
            print("%%%%%%%%%%%%%%%%%%%% ADDED BMET for browse at path:%s;  DUMP:%s" % (path, bMet.toString()))

    def setEoExtension(self, ext):
        self.eoPackageExtension = ext

    def getEoExtension(self):
        return self.eoPackageExtension

    def setSipExtension(self, ext):
        self.sipPackageExtension = ext

    def getSipExtension(self):
        return self.sipPackageExtension

    def setFileAMtime(self, fullPath):
        # set atime and mtime to self.generationTime if any
        if hasattr(self, 'generationTime') and self.generationTime is not None:
            if self.debug != 0:
                print(" self.generationTime used:'%s'; type:%s" % (self.generationTime, type(self.generationTime)))
            aFileHelper = fileHelper.FileHelper()
            aFileHelper.setAMtime(fullPath, self.generationTime, self.generationTime)
        else:
            if self.debug != 0:
                print(" self.generationTime not used")

    def buildProductReportFile(self):
        """Build the product metadata report, running the class rep_metadataReport"""
        if self.debug != 0:
            print("\n build product metadata report")
            print(" Eo-Sip metadata dump:\n%s" % self.metadata.toString())

        # make the report xml data
        typologyUsed = self.metadata.getOtherInfo("TYPOLOGY_SUFFIX")
        if self.debug != 0:
            print("############## typologyUsed:" + typologyUsed)
        if typologyUsed == '':
            typologyUsed = 'EOP'

        if typologyUsed == 'EOP':
            productReportBuilder = eop_EarthObservation.eop_EarthObservation()
        elif typologyUsed == 'OPT':
            productReportBuilder = opt_EarthObservation.opt_EarthObservation()
        elif typologyUsed == 'ALT':
            productReportBuilder = alt_EarthObservation.alt_EarthObservation()
        elif typologyUsed == 'LMB':
            productReportBuilder = lmb_EarthObservation.lmb_EarthObservation()
        elif typologyUsed == 'SAR':
            productReportBuilder = sar_EarthObservation.sar_EarthObservation()
        elif typologyUsed == 'ATM':
            productReportBuilder = atm_EarthObservation.atm_EarthObservation()
        elif typologyUsed == 'GIN':
            productReportBuilder = gin_EarthObservation.gin_EarthObservation()
        else:
            raise Exception("EoSip unsupported typology:%s" % typologyUsed)

        xmldata = productReportBuilder.buildMessage(self.metadata, "%s:EarthObservation" % typologyUsed.lower())

        # add the BROWSE block. just for first browse (if any) at this time. TODO: loop all browses?
        browseBlock = ''
        if len(self.browse_metadata_dict) > 0:
            print(" @@ there is %s browse(s)" % len(self.browse_metadata_dict))

            n = 0
            for bmet in list(self.browse_metadata_dict.values()):
                if self.debug != 0:
                    print("%%%%%%%%%%%%%%%%%%%% BMET[%s] DUMP:%s" % (n, bmet.toString()))

                browseBlockBuilder = eop_browse.eop_browse()
                if len(browseBlock) > 0:
                    browseBlock = "%s\n" % browseBlock
                browseBlock = "%s%s" % (browseBlock, browseBlockBuilder.buildMessage(bmet, "eop:browse"))

        else:
            print(" there is no browse")

        if self.debug != 0:
            print(" browseBlock content start\n%s\n@@##@@ browseBlock content end\n" % browseBlock)
            print(" xmldata:\n%s\n\n" % xmldata)

        # replace BROWSES block if any and wanted
        # 1: test if it is disabled in dest product, so this one
        localBrowseBlockDisabled = False
        if self.debug:
            print(" browse block Disabled part 1 ? test self.browseBlockDisabled")
        if self.browseBlockDisabled:
            if self.debug:
                print(" browse block Disabled from dest product? self.browseBlockDisable=%s" % self.browseBlockDisabled)
            localBrowseBlockDisabled = True
        else:
            # 2: test if it is disabled in used map:, look for '..../<BROSWSE>' = UNUSED in map
            if self.debug:
                print(" browse block Disabled part 2 ? test used map")
            usedMap = self.metadata.getUsedInXmlMap()
            n = 0
            for key in usedMap:
                if self.debug != 0:
                    print(" test mapping_MD_MTF key[%s]:'%s'" % (n, key))
                if key.endswith('/BROWSES'):
                    if usedMap[key] == 'UNUSED':
                        localBrowseBlockDisabled = True
                    break
                n += 1
        if not localBrowseBlockDisabled:
            self.processInfo.addLog(" <BROWSES></BROWSES> block USED:\n%s" % browseBlock)
        else:
            self.processInfo.addLog("<BROWSES></BROWSES> block UNUSED")
            browseBlock = ''

        # replace '<BROWSES/>' in XML
        if xmldata.find('<BROWSES></BROWSES>') > 0:
            xmldata = xmldata.replace('<BROWSES></BROWSES>', browseBlock)
        elif xmldata.find('<BROWSES/>') > 0:
            xmldata = xmldata.replace('<BROWSES/>', browseBlock)
        else:
            raise Exception("no BROWSES block in xml report!")
        if self.debug != 0:
            print(" xmldata after BROWSE block replace:\n%s\n\n\n" % xmldata)
            self.processInfo.addLog(" xmldata after BROWSE block replace:\n%s\n\n\n" % xmldata)

        # add the local attributes
        attr = self.metadata.getLocalAttributes()
        if len(attr) > 0:
            n = 0
            res = ""  # <eop:vendorSpecific><eop:SpecificInformation>"
            for adict in attr:
                key = list(adict.keys())[0]
                value = adict[key]
                res = "%s<eop:vendorSpecific><eop:SpecificInformation><eop:localAttribute>%s</eop:localAttribute><eop:localValue>%s</eop:localValue></eop:SpecificInformation></eop:vendorSpecific>" % (
                    res, key, value)
                n = n + 1
            pos = xmldata.find("<LOCAL_ATTR></LOCAL_ATTR>")
            if pos >= 0:
                xmldata = xmldata.replace("<LOCAL_ATTR></LOCAL_ATTR>", res)
        else:
            xmldata = xmldata.replace("<LOCAL_ATTR></LOCAL_ATTR>", "")
        if self.debug != 0:
            self.processInfo.addLog(" xmldata after LOCAL ATTRIBUTE set:\n%s\n\n\n" % xmldata)

        # sanitize test
        tmp = self.productReport = self.sanitizeXml(xmldata, 'productReport')
        if self.processInfo.ingester.sanitize_xml:
            tmp = self.productReport = self.sanitizeXmlBis(tmp, 'productReport')

        # verify xml, build file name
        self.productReport = self.formatXml(tmp, 'product_report')
        if self.debug != 0:
            print(" product report content:\n%s" % self.productReport)
        ext = definitions_EoSip.getDefinition("MD_EXT")
        reportName = "%s.%s" % (self.eoProductName, ext)
        if self.debug != 0:
            print("   product report name:%s" % reportName)

        # write it
        self.reportFullPath = "%s%s%s" % (self.folder, os.sep, reportName)
        with open(self.reportFullPath, "wb") as fd:
            fd.write(self.productReport)

        if self.debug != 0:
            print("   product report written at path:%s" % self.reportFullPath)

        # set atime and mtime to self.generationTime if any
        self.setFileAMtime(self.reportFullPath)

        if self.processInfo.verify_xml:
            print("  call external xml validator:%s" % self.processInfo.verify_xml)
            # call xml validator service
            try:
                validator = xmlValidateServiceClient.XmlValidateServiceClient(self.processInfo)
                validator.useXmlValidateService(self.processInfo, PRODUCT_SCHEMA_TYPE, self.reportFullPath)
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                self.processInfo.addLog(
                    "use Xml Validation failure; \n####\n#### START\n%s \n####\n#### END FIRST\n %s \n####\n#### STOP\n" % (
                        exc_type, exc_obj))
                self.processInfo.addLog("Xml Validation failure; %s %s type:%s" % (exc_type, exc_obj, type(exc_obj)))
                print("Xml Validation failure; %s %s type:%s" % (exc_type, exc_obj, type(exc_obj)))
                raise Exception("Xml Validation failure; %s %s" % (exc_type, exc_obj))
        else:
            print(" dont use external xml validator")

        return self.reportFullPath

    def buildBrowsesReportFile(self):
        """
        Build the browse metadata reports one per browse and return the
        filename of the browse report files
        """
        if self.debug != 0:
            print(" build browse metadata reports")

        self.browsesReportPath, browseReport, browseReportName = [], None, None
        n, i = 0, 0
        for browsePath in self.sourceBrowsesPath:
            bmet = self.browse_metadata_dict[browsePath]
            if self.debug != 0:
                print(" build browse metadata report[%d]:%s\n%s" % (n, browsePath, bmet.toString()))

            browseReportName = "%s.%s" % (
                bmet.getMetadataValue(browse_metadata.BROWSE_METADATA_NAME), definitions_EoSip.getDefinition('XML_EXT'))
            bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_REPORT_NAME, browseReportName)
            if self.debug != 0:
                print("  browse metadata report[%d] name:%s" % (n, browseReportName))

            browseReportBuilder = rep_browseReport.rep_browseReport()
            browseReport = self.formatXml(browseReportBuilder.buildMessage(bmet, "rep:browseReport"),
                                          'browse_report_%d' % i)

            # add BROWSE_CHOICE block, original block may have be altered by prettyprint...
            if browseReport.find('<BROWSE_CHOICE></BROWSE_CHOICE>') > 0:
                browseReport = browseReport.replace('<BROWSE_CHOICE></BROWSE_CHOICE>', bmet.getMetadataValue(
                    browse_metadata.BROWSE_METADATA_BROWSE_CHOICE))
            elif browseReport.find('<BROWSE_CHOICE/>') > 0:
                browseReport = browseReport.replace('<BROWSE_CHOICE/>', bmet.getMetadataValue(
                    browse_metadata.BROWSE_METADATA_BROWSE_CHOICE))
            if self.debug != 0:
                print(" browse report content:\n%s" % browseReport)

            #
            browseReport = self.sanitizeXml(browseReport, 'browseReport')
            if self.processInfo.ingester.sanitize_xml:
                browseReport = self.sanitizeXmlBis(browseReport, 'browseReport')
            browseReport = self.formatXml(browseReport, 'browse')

            # write it
            thisBrowseReportFullPath = "%s/%s" % (self.folder, browseReportName)
            self.browsesReportPath.append(thisBrowseReportFullPath)

            with open(thisBrowseReportFullPath, "wb") as fd:
                fd.write(browseReport)

            if self.debug != 0:
                print("   browse report written at path:%s" % thisBrowseReportFullPath)

            # set atime and mtime to self.generationTime if any
            self.setFileAMtime(thisBrowseReportFullPath)

            if self.processInfo.verify_xml:
                print(" call external xml validator:%s" % self.processInfo.verify_xml)
                # call xml validator service
                validator = xmlValidateServiceClient.XmlValidateServiceClient(self.processInfo)
                validator.useXmlValidateService(self.processInfo, BROWSE_SCHEMA_TYPE, thisBrowseReportFullPath)
            else:
                print(" dont use external xml validator")

            i += 1

        return self.browsesReportPath

    def buildSipReportFile(self):
        """Build the sip report"""

        SIPInfo = None
        sipReportBuilder = None
        if self.SipInfoType == DEFAULT_SIP_INFO_TYPE:
            import xml_nodes.SIPInfo as SIPInfo
            sipReportBuilder = SIPInfo.SIPInfo()
        elif self.SipInfoType == EXTENDED_SIP_INFO_TYPE:
            import xml_nodes.SIPInfo21 as SIPInfo21
            sipReportBuilder = SIPInfo21.SIPInfo21()
        elif self.SipInfoType == EXTENDED_SIP_INFO_TYPE_30:
            import xml_nodes.SIPInfo30 as SIPInfo30
            sipReportBuilder = SIPInfo30.SIPInfo30()
        elif self.SipInfoType == GIN_SIP_INFO_TYPE:
            import xml_nodes.SIPInfo22 as SIPInfo22
            sipReportBuilder = SIPInfo22.SIPInfo22()
        else:
            raise Exception("unknown SIP Info version:%s" % self.SipInfoType)

        if self.debug != 0:
            print(" build sip report")

        self.sipReport = self.formatXml(sipReportBuilder.buildMessage(self.metadata, "SIPInfo"), 'sip_report')

        if self.debug != 0:
            print(" sip report content:\n%s" % self.sipReport)

        ext = definitions_EoSip.getDefinition("SI_EXT")
        sipName = "%s.%s" % (self.eoProductName, ext)

        if self.debug != 0:
            print("   sip report name:%s" % sipName)

        if self.processInfo.ingester.sanitize_xml:
            self.sipReport = self.sanitizeXmlBis(self.sipReport, 'sipReport')

        # write it
        self.sipFullPath = "%s/%s" % (self.folder, sipName)
        with open(self.sipFullPath, "wb") as fd:
            fd.write(self.sipReport)

        if self.debug != 0:
            print("   sip report written at path:%s" % self.sipFullPath)

        # set atime and mtime to self.generationTime if any
        self.setFileAMtime(self.sipFullPath)

        return self.sipFullPath

    def getOutputFolders(self, basePath=None, final_path_list=None):
        """
        Build the output path relative path(s)
        depend on configuration OUTPUT_RELATIVE_PATH_TREES=["getMetadataValue('frameBowsesRetrieved')"]
        """
        if self.debug != 0:
            print("  getOutputFolders: basePath=%s, final_path_list=%s" % (basePath, final_path_list))
        folders = []
        if basePath[-1] != '/':
            basePath = "%s/" % basePath
        if len(final_path_list) == 0:
            #    raise Exception("final_path_list is empty")
            folders.append(basePath)
            print("  getOutputFolders: no path rule; final path is:'%s'" % basePath)

        # parse the config string , separated:
        # ["getMetadataValue('frameBowsesRetrieved')"],
        # ["getMetadataValue('METADATA_START_DATE')[0:4]]
        i = 0
        blocks = final_path_list.split(',')
        for rule in blocks:
            if self.debug != 0:
                print("  getOutputFolders: doing rule[%s]:'%s'" % (i, rule))
            if rule[0] == '[':
                rule = rule[1:]
            if rule[-1] == ']':
                rule = rule[0:-1]
            rule = rule.replace('"', '')
            if self.debug != 0:
                print("  getOutputFolders: resolve path rule[%d/%d]:%s" % (i, len(blocks), rule))
            if len(rule) > 0:
                if rule.find('/') >= 0:
                    toks = rule.split('/')
                    new_rulez = basePath
                    n = 0
                    for tok in toks:
                        new_rulez = "%s%s/" % (new_rulez, self.metadata.eval(tok))
                        n += 1
                    if self.debug != 0:
                        print("  getOutputFolders: resolved path (with /) new_rulez[%d]:%s" % (i, new_rulez))
                    folders.append(new_rulez)
                else:
                    new_rulez = basePath
                    new_rulez = "%s%s/" % (new_rulez, self.metadata.eval(rule))
                    if self.debug != 0:
                        print("  getOutputFolders: resolved path (whitout /) new_rulez:%s" % new_rulez)
                    folders.append(new_rulez)
                i = i + 1
            else:
                folders.append(basePath)

        return folders

    def writeEoProductAsFile(self, zipf):
        """
        Store EoProduct in the EoSip ZIP package as file(s)
        if files are not in working folder, use the 'piece' mapping
        """

        if self.debug != 0:
            print(("## content list size: %s" % len(self.processInfo.srcProduct.contentList)))
            n = 0
            for _ in self.processInfo.srcProduct.contentList:
                print(("  ## content[%s]: %s" % (n, self.processInfo.srcProduct.contentList)))
                n += 1

        self.processInfo.addLog("eoSip store as FILE")

        if len(self.processInfo.srcProduct.contentList) > 0:
            for name in self.processInfo.srcProduct.contentList:
                self.processInfo.addLog("eoSip store:%s" % name)
                # test if the file is in the workfolder, or if it is a reference in a piece
                piece = None
                localPath = "%s/%s" % (self.processInfo.workFolder, name)
                alias = name
                if self.hasPiece(name):  # a piece
                    piece = self.getPiece(name)

                    if piece.localPath is not None:
                        localPath = piece.localPath
                        self.processInfo.addLog(" is a piece: localPath=%s" % localPath)
                    if piece.alias is not None:
                        alias = piece.alias
                        self.processInfo.addLog("  has an alias=%s" % alias)
                else:
                    self.processInfo.addLog(
                        "writeEoProductAsFile strange: content name :%s not present in EoSip pieces" % name)
                    self.processInfo.addLog("writeEoProductAsFile strange: list of pieces:%s" % self.getPieceNames())
                    print("writeEoProductAsFile strange: content name :%s not present in EoSip pieces" % name)
                    print("writeEoProductAsFile strange: list of pieces:%s" % self.getPieceNames())

                if self.src_product_stored_eo_compression:
                    self.processInfo.addLog("deflated: %s" % name)
                    zipf.write(localPath, "%s" % alias, zipfile.ZIP_DEFLATED)
                else:
                    self.processInfo.addLog("stored: %s" % alias)
                    zipf.write(localPath, "%s" % alias, zipfile.ZIP_STORED)

        else:
            self.processInfo.addLog("eoSip store: nothing in contentList")

    def writeEoProductAsFileIntoEoZip(self, zipf):
        """
        Store EoProduct in the EoSip ZIP package as file(s). Into an EO
        .ZIP fileif files are not in working folder, use the 'piece'
        mapping

        need to create a tmp file, as for .TGZ case
        """
        self.processInfo.addLog(">> eoSip store as FILE into Eo ZIP")
        #
        if len(self.processInfo.srcProduct.contentList) > 0:
            tmpZipProductPath = "%s/%s" % (self.folder, self.eoPackageName)
            self.processInfo.addLog(" writeEoProductAsFileIntoEoZip tmpZipProductPath:%s" % tmpZipProductPath)
            if os.path.exists(tmpZipProductPath):
                os.remove(tmpZipProductPath)
            tzipf = zipfile.ZipFile(tmpZipProductPath, mode='w', allowZip64=True)

            n = 0
            for name in self.processInfo.srcProduct.contentList:
                self.processInfo.addLog(" eoSip store contentList[%s]:%s" % (n, name))
                # test if the file is in the workfolder, or if it is a reference in a piece
                piece = None
                localPath = "%s/%s" % (self.processInfo.workFolder, name)
                alias = name
                if self.hasPiece(name):  # a piece
                    piece = self.getPiece(name)

                    if piece.localPath is not None:
                        localPath = piece.localPath
                        self.processInfo.addLog(" is a piece: localPath=%s" % localPath)
                    if piece.alias is not None:
                        alias = piece.alias
                        self.processInfo.addLog("  has an alias=%s" % alias)
                else:
                    self.processInfo.addLog(
                        " writeEoProductAsFileIntoEoZip strange: content name :%s not present in EoSip pieces" % name)
                    self.processInfo.addLog(
                        " writeEoProductAsFileIntoEoZip strange: list of pieces:%s" % self.getPieceNames())
                    print("writeEoProductAsFileIntoEoZip strange: content name :%s not present in EoSip pieces" % name)
                    print("writeEoProductAsFileIntoEoZip strange: list of pieces:%s" % self.getPieceNames())

                if self.src_product_stored_eo_compression:
                    self.processInfo.addLog(" piece deflated into tmpZip: %s" % name)
                    tzipf.write(localPath, "%s" % alias, zipfile.ZIP_DEFLATED)
                else:
                    self.processInfo.addLog(" piece stored into tmpZip: %s" % alias)
                    tzipf.write(localPath, "%s" % alias, zipfile.ZIP_STORED)
                n += 1

            tzipf.close()
            self.setFileAMtime(tmpZipProductPath)

            self.tmpZipSize = os.stat(tmpZipProductPath).st_size
            self.processInfo.addLog(" #### tmp zip file size:%s" % self.tmpZipSize)

            if self.src_product_stored_eo_compression:
                self.processInfo.addLog(" deflated: %s" % self.eoPackageName)
                zipf.write(tmpZipProductPath, self.eoPackageName, zipfile.ZIP_DEFLATED)
            else:
                self.processInfo.addLog(" stored: %s" % self.eoPackageName)
                zipf.write(tmpZipProductPath, self.eoPackageName, zipfile.ZIP_STORED)

        else:
            self.processInfo.addLog(" !! eoSip store: nothing in contentList")

    def writeEoProductAsDir(self, zipf):
        """
        Store EoProduct in the EoSip ZIP package as directory

        AT THIS TIME: store workfolder files
        """
        self.processInfo.addLog("eoSip store as DIR")

        for name in self.processInfo.srcProduct.contentList:
            self.processInfo.addLog("eoSip store:%s" % name)
            if self.src_product_stored_eo_compression:
                self.processInfo.addLog("deflated: %s" % name)
                zipf.write(
                    "%s/%s" % (self.processInfo.workFolder, name),
                    "%s/%s" % (self.eoProductName, name),
                    zipfile.ZIP_DEFLATED
                )
            else:
                self.processInfo.addLog("stored: %s" % name)
                zipf.write(
                    "%s/%s" % (self.processInfo.workFolder, name),
                    "%s/%s" % (self.eoProductName, name),
                    zipfile.ZIP_STORED
                )

    def writeEoProductAsZip(self, zipf):
        """
        Store EoProduct in the EoSip ZIP package as ZIP file

        Two cases:
        - single file: ref in self.sourceProductPath
        - multiple files: refs inf self.contentList

        Two cases:
        - source is already a zip file ==> just rename it
        - source is not a zip file ==> compress(or not) into a temporary
          zip
        """
        self.processInfo.addLog("eoSip store as ZIP")
        if len(self.getContentList()) > 0:
            print(" self.contentList:\n%s" % self.getContentList())
        else:
            print(" self.contentList is empty")

        extract_and_rezip_raw_product = False
        if self.sourceProductPath is not None:  # single source file case
            # source product is ZIP case
            self.processInfo.addLog(" eoSip store as ZIP: single file case")
            print(" eoSip store as ZIP: single file case")

            # Determine if the product is a zip file (has a .zip/.ZIP extension)
            pkg_zip_ext = definitions_EoSip.getDefinition('PACKAGE_EXT').upper()
            source_product_is_zip_file = (self.sourceProductPath.upper().endswith(pkg_zip_ext))

            if source_product_is_zip_file:
                # Check source product's contents' compression statuses
                # with zipfile.ZipFile(self.sourceProductPath, 'r') as zipf2:
                zipf2 = zipfile.ZipFile(self.sourceProductPath, 'r')
                src_product_compressions = {
                    info.filename: info.compress_type for info in zipf2.infolist()
                }
                zipf2.close()

                # Determine overall compression status of raw product .zip
                if all(value == zipfile.ZIP_DEFLATED for value in src_product_compressions.values()):
                    src_product_compression = 'full'
                elif all(value == zipfile.ZIP_STORED for value in src_product_compressions.values()):
                    src_product_compression = 'none'
                else:
                    src_product_compression = 'partial'

                # Check compression of raw .zip matches compression requested
                # for raw .zip inside final product
                matching_raw_and_final_compressions = (
                    (
                        src_product_compression == 'full'
                        and
                        self.src_product_stored_eo_compression
                    ) or (
                        src_product_compression == 'none'
                        and
                        not self.src_product_stored_eo_compression
                    )
                )

                self.processInfo.addLog(
                    "raw source zip file compression: %s; "
                    "eoSip source zip file (%s) compression required: %s" % (
                        src_product_compression,
                        self.eoPackageName,
                        'full' if self.src_product_stored_eo_compression else 'none'
                    )
                )

                # If matching, just copy the raw .zip and rename inside final product
                if matching_raw_and_final_compressions:
                    self.processInfo.addLog(
                        "eoSip %s source zip file: %s; compression: %s" % (
                            'deflate' if self.src_product_stored_eo_compression else 'store',
                            self.eoPackageName,
                            self.src_product_stored_eo_compression
                        )
                    )

                    self.writeInZip(
                        zipf,
                        self.sourceProductPath,
                        self.eoPackageName,
                        self.src_product_stored_eo_compression
                    )
                # If not matching, ensure raw product will be extracted, and
                # zipped with requested compression (below)
                else:
                    extract_and_rezip_raw_product = self.sourceProductPath

            else:  # zip source product, at this time: assume it is a single file
                self.processInfo.addLog("eoSip store source file: %s" % self.sourceProductPath)

                # zip source inside tmp zip
                tmpProductZippedPath = "%s/zipWrapperSingleFile.zip" % self.folder
                with zipfile.ZipFile(tmpProductZippedPath, 'w') as zipTmpSingleFileProduct:
                    # set tmp zip folder in case we use the wrapper
                    if hasattr(zipTmpSingleFileProduct, 'setTmpFolder'):
                        print(' zip library used is wrapped one')
                        self.processInfo.addLog('zip library used is wrapped one')
                        tmp = "%s/zipWrapperSingleFileProduct.tmp" % self.parentFodler
                        zipTmpSingleFileProduct.setTmpFolder(tmp)
                        print('zipTmpSingleFileProduct setTmpFolder done at path:%s' % tmp)
                        self.processInfo.addLog('zipTmpSingleFileProduct setTmpFolder done at path:%s' % tmp)
                    else:
                        print(' ziplibrary used is the python one')
                        self.processInfo.addLog('zip library used is the python one')

                    if self.src_product_stored_eo_compression:
                        zipTmpSingleFileProduct.write(
                            self.sourceProductPath,
                            os.path.split(self.sourceProductPath)[1],
                            zipfile.ZIP_DEFLATED
                        )
                        self.processInfo.addLog("deflated: %s" % self.sourceProductPath)
                    else:
                        zipTmpSingleFileProduct.write(
                            self.sourceProductPath,
                            os.path.split(self.sourceProductPath)[1],
                            zipfile.ZIP_STORED
                        )
                        self.processInfo.addLog("stored: %s" % self.sourceProductPath)

                # set atime and mtime to self.generationTime if any
                self.setFileAMtime(tmpProductZippedPath)

                # use tmp zip
                if self.src_product_stored_eo_compression:
                    zipf.write(tmpProductZippedPath, self.eoPackageName, zipfile.ZIP_DEFLATED)
                    self.processInfo.addLog("deflated: %s" % self.sourceProductPath)
                else:
                    zipf.write(tmpProductZippedPath, self.eoPackageName, zipfile.ZIP_STORED)
                    self.processInfo.addLog("stored: %s" % self.sourceProductPath)

                # if size is not set in metadata, calculate it from the tmp zip file
                if self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE) == PRODUCT_SIZE_NOT_SET:
                    self.processInfo.addLog(" #### need to retrieve tmp zip file size")
                    self.tmpZipSize = os.stat(tmpProductZippedPath).st_size
                    self.processInfo.addLog(" #### tmp zip file size:%s" % self.tmpZipSize)

                # delete tmp zip
                self.toBeRemovedFiles.append(tmpProductZippedPath)

        # Source is either:
        #   - list of files (self.sourceProductPath is None) stored in
        #     self.contentList and maybe self.contentListPath map (if source
        #     not extracted in working folder)
        #   - .zip file with incorrect compression for final product
        #     (extract_and_rezip_raw_product == True)
        if self.sourceProductPath is None or extract_and_rezip_raw_product:
            self.processInfo.addLog("############### eoSip store as ZIP: multiple files case")
            print("############### eoSip store as ZIP:  multiple files case")
            self.processInfo.addLog("eoSip store multiple source files: size=%s" % len(self.contentList))

            # zip sources inside tmp zip
            tmpProductZippedPath = "%s/zipWrapperMultipleFiles.zip" % self.folder
            zipTmpMultipleFilesProduct = zipfile.ZipFile(tmpProductZippedPath, 'w', allowZip64=True)
            # set tmp zip folder in case we use the wrapper
            if hasattr(zipTmpMultipleFilesProduct, 'setTmpFolder'):
                print(' zipfile is wrapped one')
                self.processInfo.addLog('zipfile is wrapped one')
                tmp = "%s/zipWrapperMultipleFiles.tmp" % self.parentFodler
                zipTmpMultipleFilesProduct.setTmpFolder(tmp)
                print('zipTmpMultipleFilesProduct setTmpFolder set at path:%s' % tmp)
                self.processInfo.addLog('zipTmpMultipleFilesProduct setTmpFolder done at path:%s' % tmp)
            else:
                print(' zipfile is the python one')
                self.processInfo.addLog('zipfile is the python one')

            if extract_and_rezip_raw_product:
                temp_dir = tempfile.mkdtemp(dir=self.processInfo.workFolder)
                zip_ref = zipfile.ZipFile(extract_and_rezip_raw_product, 'r')
                zip_ref.extractall(temp_dir)
                content_list_path = {rel_path: f"{temp_dir}{os.sep}{rel_path}" for rel_path in zip_ref.namelist()}
                content_list = zip_ref.namelist()
                zip_ref.close()
            else:
                temp_dir = None
                content_list = self.contentList
                content_list_path = self.contentListPath

            for item in content_list:
                nameInZip = item
                srcPath = item
                if item in content_list_path:
                    srcPath = content_list_path[item]
                if self.src_product_stored_eo_compression:
                    print("  ZIP_DEFLATED in tmpZip: %s as %s" % (srcPath, nameInZip))
                    zipTmpMultipleFilesProduct.write(srcPath, nameInZip, zipfile.ZIP_DEFLATED)
                    self.processInfo.addLog("deflated: %s as %s" % (srcPath, nameInZip))
                else:
                    print("  ZIP_STORED in tmpZip: %s as %s" % (srcPath, nameInZip))
                    zipTmpMultipleFilesProduct.write(srcPath, nameInZip, zipfile.ZIP_STORED)
                    self.processInfo.addLog("stored:  %s as %s" % (srcPath, nameInZip))

            if temp_dir is not None:
                shutil.rmtree(temp_dir)

            # close tmp zip object. it will remove tmp files in case wrapper is used
            zipTmpMultipleFilesProduct.close()

            # set atime and mtime of tmp zip file to self.generationTime if any
            self.setFileAMtime(tmpProductZippedPath)

            # if size is not set in metadata, calculate it from the tmp zip file
            if self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE) == PRODUCT_SIZE_NOT_SET:
                self.processInfo.addLog(" #### need to retrieve tmp zip file size")
                self.tmpZipSize = os.stat(tmpProductZippedPath).st_size
                self.processInfo.addLog(" #### tmp zip file size:%s" % self.tmpZipSize)

            # use tmp zip
            if self.src_product_stored_eo_compression:
                zipf.write(tmpProductZippedPath, self.eoPackageName, zipfile.ZIP_DEFLATED)
                self.processInfo.addLog("deflated: %s" % self.sourceProductPath)
            else:
                zipf.write(tmpProductZippedPath, self.eoPackageName, zipfile.ZIP_STORED)
                self.processInfo.addLog("stored: %s" % self.sourceProductPath)

            # delete tmp zip
            self.toBeRemovedFiles.append(tmpProductZippedPath)

    def writeEoProductAsTgz(self, zipf):
        """
        Store EoProduct in the EoSip ZIP package as TGZ

        AT THIS TIME: store workfolder files
        """
        self.processInfo.addLog("eoSip store as TGZ")

        # create a temporary tar file
        tmpProductTarredPath = "%s/%s.%s" % (
            self.folder,
            self.eoProductName,
            definitions_EoSip.getDefinition('TAR_EXT')
        )
        if os.path.exists(tmpProductTarredPath):
            os.remove(tmpProductTarredPath)

        tar_mode = "w:gz" if self.src_product_stored_eo_compression else "w"
        with tarfile.open(tmpProductTarredPath, tar_mode) as tar:
            for name in self.processInfo.srcProduct.contentList:
                if self.src_product_stored_eo_compression:
                    self.processInfo.addLog("deflated: %s" % name)
                    tar.add("%s/%s" % (self.processInfo.workFolder, name), name)
                else:
                    self.processInfo.addLog("stored: %s" % name)
                    tar.add("%s/%s" % (self.processInfo.workFolder, name), name)

        # if compressed rename as TGZ
        if self.src_product_stored_eo_compression:
            tmpProductTarredPath1 = tmpProductTarredPath.replace(
                definitions_EoSip.getDefinition('TAR_EXT'),
                definitions_EoSip.getDefinition('TGZ_EXT')
            )
            if os.path.exists(tmpProductTarredPath1):
                os.remove(tmpProductTarredPath1)
            os.rename(tmpProductTarredPath, tmpProductTarredPath1)
            tmpProductTarredPath = tmpProductTarredPath1

        # add temporary tar in zip
        if self.src_product_stored_eo_compression:
            zipf.write(tmpProductTarredPath, self.eoPackageName, zipfile.ZIP_DEFLATED)
            self.processInfo.addLog("deflated: %s" % tmpProductTarredPath)
        else:
            zipf.write(tmpProductTarredPath, self.eoPackageName, zipfile.ZIP_STORED)
            self.processInfo.addLog("stored: %s" % tmpProductTarredPath)

    def writeToFolder(self, p=None, overwrite=None):
        """
        Write the Eo-Sip package in a folder.
        p: path of the output folder
        """
        if self.eoProductName is None:
            raise Exception("Eo-Sip product has no productName")

        if self.debug != 0:
            print("\n will write EoSip product at folder path:%s" % p)

        p = p.replace('/' if os.sep == '\\' else '\\', os.sep)

        # create destination path
        self.path = "%s%s%s" % (p.rstrip(os.sep), os.sep, self.sipPackageName)
        if self.debug != 0:
            print(" full eoSip path:%s" % self.path)

        # already exists?
        # should also test the .part suffix case that can append in multiprocess mode
        pathWithPart = "%s.part" % self.path
        if os.path.exists(self.path) and (overwrite is None or not overwrite):
            raise Exception("refuse to overwrite existing product:%s" % self.path)
        if os.path.exists(pathWithPart) and (overwrite is None or not overwrite):
            raise Exception("refuse to overwrite being written product:%s" % pathWithPart)

        # create folder needed
        # Note that in multiprocess mode, another process can create the folder
        # at the same instant, resulting in OSError: [Errno 17] File exists
        #
        # the next 2 actions can fail in multiprocess mode
        #
        # create folder neeedd
        if not os.path.exists(p):
            try:
                os.makedirs(p)
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("Error making destination folder '%s': %s; %s" % (p, exc_type, exc_obj))

        # remove precedent zip if any
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except:
                print("Warning: problem removing previous eoSip:%s" % self.path)
        if os.path.exists("%s.part" % self.path):
            try:
                os.remove("%s.part" % self.path)
            except:
                print("Warning: problem removing previous eoSip:%s.part" % self.path)

        # create zip, use temporary .part suffix
        # using zipfile or zip wrapper
        # store message and value used:
        store_type = None
        storeMessage = None
        if self.src_product_stored_compression:
            store_type = zipfile.ZIP_DEFLATED
            storeMessage = 'deflated: '
        else:
            store_type = zipfile.ZIP_STORED
            storeMessage = 'stored: '

        zipf = zipfile.ZipFile("%s.part" % self.path, mode='w', allowZip64=True, compression=store_type)
        # set tmp zip folder in case we use the wrapper
        if hasattr(zipf, 'setTmpFolder'):
            print(' zipfile is wrapped one')
            self.processInfo.addLog('zipfile is wrapped one')
            tmp = "%s/zipWrapperEoSip.Tmp" % self.parentFodler
            zipf.setTmpFolder(tmp)
            print('zipfile setTmpFolder done at path:%s' % tmp)
            self.processInfo.addLog('zipfile setTmpFolder done at path:%s' % tmp)
        else:
            print(' zipfile is the python one')
            self.processInfo.addLog('zipfile is the python one')

        # write product itself
        if self.debug != 0:
            print("  write EoSip content[0]; product itself:%s  as:%s" % (self.sourceProductPath, self.eoProductName))

        # two case:
        # - source is already a zip file ==> just rename it
        # - source is not a zip file ==> compress(or not) into a zip
        print("  will store original product as:%s" % self.src_product_stored)
        self.processInfo.addLog("eoSip store type:%s" % self.src_product_stored)
        self.processInfo.addLog("eoSip store compression:%s" % self.src_product_stored_compression)
        # self.processInfo.addLog("eoSip store compression flag type is bool?:%s" % isinstance(self.src_product_stored_compression, bool))

        # store as FILES
        if self.src_product_stored == SRC_PRODUCT_AS_FILE:
            self.writeEoProductAsFile(zipf)
        elif self.src_product_stored == SRC_PRODUCT_AS_FILE_INTO_EOZIP:
            self.writeEoProductAsFileIntoEoZip(zipf)

        # store as ZIP       
        elif self.src_product_stored == SRC_PRODUCT_AS_ZIP:
            self.writeEoProductAsZip(zipf)

        # store as FOLDER
        elif self.src_product_stored == SRC_PRODUCT_AS_DIR:
            self.writeEoProductAsDir(zipf)

        # store as TGZ
        elif self.src_product_stored == SRC_PRODUCT_AS_TGZ:
            self.writeEoProductAsTgz(zipf)

        # store as TAR
        elif self.src_product_stored == SRC_PRODUCT_AS_TAR:
            self.writeEoProductAsTgz(zipf)

        # store as FOLDER. old code disabled
        elif self.src_product_stored == 'disabled_if':  # SRC_PRODUCT_AS_DIR:
            self.processInfo.addLog("eoSip store as DIR")
            for name in self.processInfo.srcProduct.contentList:
                self.processInfo.addLog("eoSip store:%s" % name)
                zipf.write("%s/%s" % (self.processInfo.workFolder, name), "%s/%s" % (self.eoProductName, name),
                           store_type)
                self.processInfo.addLog(" eoSip stored; %s%s" % (storeMessage, name))
        else:
            raise Exception("unsupported store type:%s" % self.src_product_stored)

        # write browses images + reports
        for browsePath in self.sourceBrowsesPath:
            folder = os.path.split(browsePath)[0]
            bmet = self.browse_metadata_dict[browsePath]
            #
            extension = formatUtils.getFileExtension(browsePath)
            if self.debug != 0:
                print("\n\n\n browsePath=%s; folder=%s; extension=%s;" % (browsePath, folder, extension))
            name = "%s.%s" % (self.eoProductName, extension)
            if not self.processInfo.test_dont_do_browse:
                if self.debug != 0:
                    print("   write EoSip browse[n]:%s  as:%s" % (browsePath, name))

                zipf.write(browsePath, name, store_type)
                self.processInfo.addLog(" eoSip stored browse src:%s %s%s" % (browsePath, storeMessage, name))
            else:
                print("   dont' do browse flag is set, so don't write EoSip browse[n]:%s  as:%s" % (browsePath, name))

            # if we have build the browse reports
            if self.browsesReportPath is not None:
                name = bmet.getMetadataValue(browse_metadata.BROWSE_METADATA_REPORT_NAME)
                path = "%s/%s" % (folder, name)
                zipf.write(path, name, store_type)
                self.processInfo.addLog(" eoSip stored browse report; %s%s" % (storeMessage, name))

        #
        # write product reports
        # handle case when we have calculated the eo product size after the report was created (tmp zip case)
        #
        if self.tmpZipSize == -1:
            self.processInfo.addLog(
                " ! real product size known from source product:%s" % self.metadata.getMetadataValue(
                    metadata.METADATA_PRODUCT_SIZE))
            zipf.write(self.reportFullPath, os.path.split(self.reportFullPath)[1], store_type)
            self.processInfo.addLog(" eoSip tmpSip %s%s" % (storeMessage, os.path.split(self.reportFullPath)[1]))
        else:
            # substitute 'eosip_product.PRODUCT_SIZE_NOT_SET' value in xmlfile
            self.processInfo.addLog(" ! set product size from tmp zip archive: %s" % self.tmpZipSize)
            zipf.writestr(
                os.path.split(self.reportFullPath)[1],
                self.productReport.replace(
                    str(PRODUCT_SIZE_NOT_SET).encode(),
                    str(self.tmpZipSize).encode()
                ),
                store_type
            )
            self.processInfo.addLog(" eoSip tmpSip %s%s" % (storeMessage, os.path.split(self.reportFullPath)[1]))

        # write sip report
        if self.sipReport is not None:
            zipf.write(self.sipFullPath, os.path.split(self.sipFullPath)[1], store_type)
            self.processInfo.addLog(
                " eoSip stored sip report %s%s" % (storeMessage, os.path.split(self.sipFullPath)[1]))

        # write additional content
        if self.additionalContent is not None and len(self.additionalContent) > 0:
            self.processInfo.addLog("will write additionalContent:%s" % self.additionalContent)
            n = 0
            for item in list(self.additionalContent.keys()):
                fullPath = self.additionalContent[item]
                self.processInfo.addLog(" write additionalContent[%s]:%s" % (n, item))
                zipf.write(fullPath, item, store_type)
                self.processInfo.addLog(" %s%s" % (storeMessage, os.path.split(fullPath)[1]))
                n += 1

        zipf.close()

        # remove temporary part extension
        try:
            os.rename(pathWithPart, self.path)
        except:
            self.processInfo.addLog(".part rename error: %s" % os.listdir(os.path.dirname(pathWithPart)))
            sys.exit(-1)

        # remove tmp files (zip wrapper)
        for item in self.toBeRemovedFiles:
            print("  remove tmp file:%s" % item)
            os.remove(item)

        return self.path

    def formatXml(self, data=None, atype=None):
        """Control that the xml is well formatted, if not save it on disk"""
        res = None
        try:
            # pretty print it
            helper = xmlHelper.XmlHelper()
            helper.parseData(data)
            # this will verify that xml is correct:
            res = helper.prettyPrintAll()

        except Exception as e:
            # write it for DEBUG
            self.writeFaultyXml(data, None, atype)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("xml format error: %s   %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
            raise e
        return res

    def sanitizeXml(self, mess, atype=None):
        """
        Verify that the xml doesn't have anymore BLOCK_NODE that should
        have been substituted. If there still are, default them if
        possible, if not, raise error
        """
        try:
            # eliminate the pattern blocks
            n = 0
            for pattern in self.NODES_AS_TEXT_BLOCK:
                pos = mess.find(pattern)
                if pos > 0:
                    if self.debug != 0:
                        print("  sanitizeXml: block pattern[%d]:'%s' found at pos:%s; can be substituted with:'%s'" % (
                            n, pattern, pos, self.NODES_AS_TEXT_BLOCK_DEFAULT[n]))
                    if self.NODES_AS_TEXT_BLOCK_DEFAULT[n] is None:
                        raise Exception("sanitizeXml: block %s can not be defaulted!" % pattern)
                    else:
                        # TODO: should delete backward up to precedent newline...
                        mess = mess.replace(pattern, self.NODES_AS_TEXT_BLOCK_DEFAULT[n])
                n = n + 1
                return mess
        except Exception as e:
            # write it for DEBUG
            self.writeFaultyXml(mess, None, atype)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("xml error: %s   %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
            raise e

    def sanitizeXmlBis(self, mess, atype=None):
        """Look for NOT_DEFINED_VALUES in xml"""
        import re

        if self.debug != 0:
            print(" sanitizeXmlBis on:%s" % mess)
        try:
            # look for not defined values
            n = 0
            for pattern in self.NOT_DEFINED_VALUES:
                if self.debug != 0:
                    print("  sanitizeXmlBis; do pattern:%s" % pattern)

                # pos = (mess.decode() if isinstance(mess, bytes) else mess).find(pattern)
                # if pos > 0:
                #     print("  sanitizeXmlBis: not defined value pattern[%d]:'%s' found at pos:%s" % (n, pattern, pos))
                #     raise Exception(
                #         "sanitizeXmlBis: not defined value pattern[%d]:'%s' found at pos:%s" % (n, pattern, pos))
                matches = re.findall(
                    rf"<([\w:]+)[^>]*>{pattern}</\1>",
                    mess.decode() if isinstance(mess, bytes) else mess
                )
                if matches:
                    msg = (
                        "sanitizeXmlBis: not defined value pattern[%d]: '%s' found for XML tag(s): %s" %
                        (n, pattern, ', '.join(matches))
                    )
                    print(msg)
                    raise ValueError(msg)
                n = n + 1
        except Exception as e:
            # write it for DEBUG
            self.writeFaultyXml(mess, None, atype)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("xml error: %s   %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
            raise e
        return mess

    def writeFaultyXml(self, data, path=None, atype=None):
        """Write a faulty xml in the workfolder"""
        if path is None:
            path = self.folder
        apath = "%s/faulty_%s.xml" % (path, atype)
        print("xml faulty xml of type:%s  dumped at path:%s" % (atype, path))
        print("\n\n\n%s\n\n\n" % data)
        with open(apath, 'w') as fd:
            fd.write(data.decode() if isinstance(data, bytes) else data)

    def testValueIsDefined(self, v):
        """Check if a value is not in the not defined list"""
        return v not in self.NOT_DEFINED_VALUES

    def buildEoNames(self, namingConvention=None, changeFileCounter=False):  # , ext=None, eoExt=None ):
        """Build package and EoProduct names. namingConvention is the
        class instance used. ext is the extension of the eoProduct (what
        is inside the eoSip package). If not specified, use default
        EoSip extension: .ZIP

        changeFileCounter to be set to True in case of fileCounter
        duplicate loop
        """
        if self.src_product_stored != SRC_PRODUCT_AS_FILE and self.src_product_stored != SRC_PRODUCT_AS_DIR and self.src_product_stored != SRC_PRODUCT_AS_FILE_INTO_EOZIP and self.eoPackageExtension is None:
            raise Exception("eoPackageExtension not defined")

        if self.namingConventionSipPackage is None:
            raise Exception("namingConvention sip instance is None")

        if self.namingConventionEoPackage is None:
            raise Exception("namingConvention eo instance is None")

        # build sip product and package names
        if self.debug != 0:
            print(" ## build eo product names, SIP package: pattern=%s, eoExt=%s, sipExt=%s" % (
                self.namingConventionSipPackage.usedPattern, self.eoPackageExtension, self.sipPackageExtension))

        self.sipPackageName = self.namingConventionSipPackage.buildProductName(self.metadata, self.sipPackageExtension)
        self.sipProductName = self.sipPackageName.split('.')[0]
        if self.debug != 0:
            print(" # self.sipPackageName:%s" % self.sipPackageName)
            print(" # self.sipProductName:%s" % self.sipProductName)

        # build eoProductName
        if self.debug != 0:
            print(" ## build eo product names, EO package: pattern=%s, eoExt=%s, sipExt=%s" % (
                self.namingConventionEoPackage.usedPattern, self.eoPackageExtension, self.sipPackageExtension))

        # eoProductName could be already defined, in case we want to keep original product name for example
        # in this case, we don't change it  
        tmpEoProductName = self.namingConventionEoPackage.buildProductName(self.metadata, self.eoPackageExtension)
        if self.debug != 0:
            print(" build eo product names, eo pattern=%s, eo ext=%s" % (
                self.namingConventionEoPackage.usedPattern, self.eoPackageExtension))
            print(" tmpEoProductName:%s" % tmpEoProductName)

        eoNameDefined = False
        if self.eoProductName is None or changeFileCounter:
            self.eoPackageName = tmpEoProductName
            self.eoProductName = tmpEoProductName.split('.')[0]
            eoNameDefined = True
            self.processInfo.addLog(" eo product name built")

        else:
            # if we have an extension in eoProductName, set the choosed one
            pos = self.eoProductName.find('.')
            if pos < 0:
                self.eoPackageName = "%s.%s" % (self.eoProductName, self.eoPackageExtension)
            else:
                self.eoPackageName = "%s.%s" % (self.eoProductName[0:pos], self.eoPackageExtension)
                self.eoProductName = self.eoProductName[0:pos]
            self.processInfo.addLog(" eo product predefined, use it:  eo product name=%s\n eo product name=%s" % (
                self.eoProductName, self.sipProductName))

        if self.debug != 0:
            print("self.eoProductName:%s" % self.eoProductName)

        self.identifier = self.eoProductName
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.eoProductName)
        self.metadata.setMetadataPair(metadata.METADATA_PACKAGENAME, self.sipProductName)
        if self.debug != 0:
            print(" ==> builded product/package product=%s; package=%s" % (self.eoProductName, self.sipProductName))

        # test zip in zip case
        if eoNameDefined and self.eoPackageExtension == definitions_EoSip.getDefinition('PACKAGE_EXT'):
            print(" we are in zip in zip case: eoNameDefined=%s; self.eoPackageExtension=%s; definitions_EoSip.getDefinition('PACKAGE_EXT')=%s" % (
                eoNameDefined, self.eoPackageExtension, definitions_EoSip.getDefinition('PACKAGE_EXT')))
            self.setSipPackageWithExtension = "%s.%s" % (
                definitions_EoSip.getDefinition('SIP'), definitions_EoSip.getDefinition('PACKAGE_EXT'))
            self.sipPackageName = "%s.%s" % (self.sipProductName, self.setSipPackageWithExtension)
        else:
            print(" we are NOT in zip in zip case: eoNameDefined=%s; self.eoPackageExtension=%s; definitions_EoSip.getDefinition('PACKAGE_EXT')=%s" % (
                eoNameDefined, self.eoPackageExtension, definitions_EoSip.getDefinition('PACKAGE_EXT')))
            self.sipPackageName = "%s.%s" % (self.sipProductName, self.sipPackageExtension)

        self.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, self.identifier)
        self.metadata.setMetadataPair(metadata.METADATA_FULL_PRODUCTNAME, self.eoPackageName)
        self.metadata.setMetadataPair(metadata.METADATA_FULL_PACKAGENAME, self.sipPackageName)

        return self.sipPackageName

    def usePythonZipLib(self, normalZipb=True):
        """Use python zipfile or my wrapper"""
        if normalZipb:
            print("will use python zipfile...")
            import zipfile
            print(" using python zipfile !")
        else:
            print("will use zipfileWrapper...")
            try:
                from ..wrappers import zipfileWrapper as zipfile
                print(" using zipfileWrapper !")
            except:  # fatal
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print(" error importing zipfileWrapper:%s %s" % (exc_type, exc_obj))
                traceback.print_exc(file=sys.stdout)
                sys.exit(20)

    def getContentList(self):
        """Return self.contentList"""
        out = StringIO()
        n = 0
        for item in self.contentList:
            print("item[%s]:%s" % (n, item), file=out)
            n += 1
        return out.getvalue()

    def getContentListPath(self):
        """Return self.contentListPath"""
        out = StringIO()
        n = 0
        for key in list(self.contentListPath.keys()):
            print("item[%s]: %s=%s" % (n, key, self.contentListPath[key]), file=out)
            n += 1
        return out.getvalue()

    def info(self):
        """Return information on the EoSip product"""
        return self.info_impl()

    def agregateGeoInfo(self, pInfo):
        if pInfo.srcProduct.origName in list(pInfo.ingester.footprintAgregator.productGeoInfoMap.keys()):
            print((" #### Product %s is already present" % pInfo.srcProduct.origName))
            return
        geoInfo = GeoInfo(pInfo.srcProduct.origName)
        geoInfo.setFootprint(pInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        geoInfo.setBoundingBox(pInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))
        print((" ## agregateGeoInfo; FOOTPRINT:%s" % geoInfo.getFootprint()))
        print((" ## agregateGeoInfo; BOUNDINGBOX:%s" % geoInfo.getBoundingBox()))

        # default
        props = {
            'BatchId': pInfo.ingester.fixed_batch_name,
            'ItemId': pInfo.num
        }

        # wanted metadata
        n = 0
        print((" adding %s metadata" % len(pInfo.ingester.footprintAgregator.wantedMetadata)))
        for mName in pInfo.ingester.footprintAgregator.wantedMetadata:
            v = pInfo.srcProduct.metadata.getMetadataValue(mName)
            props[mName] = v
            print((" adding metadata[%s]:%s=%s" % (n, mName, v)))
            n += 1

        geoInfo.setProperties(props)
        pInfo.ingester.footprintAgregator.productGeoInfoMap[pInfo.srcProduct.origName] = geoInfo

    def info_impl(self):
        """Return information on the EoSip product"""
        out = StringIO()
        print("\n\n#########################################", file=out)
        print("####### START EOSIP Product Info ########", file=out)
        if self.created:
            print("# created ?                       :True #", file=out)
        else:
            print("# created ?                       :False#", file=out)

        if self.loaded:
            print("# loaded ?                        :True #", file=out)
            print("# loaded from:%s" % self.path, file=out)
            print("# folder:%s" % self.folder, file=out)
            print("#  %s" % self.loadingMessage[0:-1], file=out)
            if len(self.eoPieces) > 0:
                n = 0
                print("#", file=out)
                for item in self.eoPieces:
                    print("#  piece[%d]:%s" % (n, item.info()), file=out)
                    n = n + 1
        else:
            print("# loaded ?                        :False#", file=out)

        if self.workingOn:
            print("# working on ?                    :True #", file=out)
        else:
            print("# working on ?                    :False#", file=out)
        if self.workingOn:
            print("working on folder:%s" % self.workingOnFolder, file=out)

        print(" product stored as:%s" % self.src_product_stored, file=out)
        print(" product stored compression:%s" % self.src_product_stored_compression, file=out)
        print(" product stored eo compression:%s" % self.src_product_stored_eo_compression, file=out)
        print("\n  eop:identifier:%s" % self.identifier, file=out)

        print("  eo package extension:%s" % self.eoPackageExtension, file=out)
        print("  Sip package extension:%s" % self.sipPackageExtension, file=out)

        print("  Sip info file version:%s" % self.SipInfoType, file=out)

        print("  Sip product name:%s" % self.sipProductName, file=out)
        print("  Sip package name (with ext):%s" % self.sipPackageName, file=out)
        print("  eo product name:%s" % self.eoProductName, file=out)
        print("  eo package name (with ext):%s" % self.eoPackageName, file=out)
        print("\n  source product path:%s" % self.sourceProductPath, file=out)

        print("\n  START content list:\n%s" % self.getContentList(), file=out)
        print("  STOP content list", file=out)

        print("\n  START content list paths:\n%s" % self.getContentListPath(), file=out)
        print("  STOP content list paths", file=out)

        if self.created:
            if hasattr(self, 'folder'):
                print("   product tmp folder:%s\n" % self.folder, file=out)
            else:
                print("   product tmp folder: PROBLEM: no folder\n", file=out)
        else:
            if hasattr(self, 'folder'):
                print("   product folder:%s\n" % self.folder, file=out)
            else:
                print("   product tmp folder: PROBLEM: no folder\n", file=out)

        if hasattr(self, 'sourceBrowsesPath'):
            if len(self.sourceBrowsesPath) == 0:
                print("   no sourceBrowsesPath", file=out)
            else:
                n = 0
                for item in self.sourceBrowsesPath:
                    print("   sourceBrowsesPath[%d]:%s" % (n, item), file=out)
                    n = n + 1
        else:
            print("   PROBLEM: no sourceBrowsesPath", file=out)

        if hasattr(self, 'browsesInfo'):
            if len(self.browsesInfo) == 0:
                print("   no browse report", file=out)
            else:
                n = 0
                for item in self.browsesInfo:
                    print("   browse report info[%d]:%s" % (n, item), file=out)
                    n = n + 1
        else:
            print("   PROBLEM: no browsesInfo", file=out)

        print("\n   reportFullPath:%s" % self.reportFullPath, file=out)
        print("   qualityReportFullPath:%s" % self.qualityReportFullPath, file=out)
        print("\n   sipFullPath:%s" % self.sipFullPath, file=out)
        print("######## END EOSIP Product Info #########\n#########################################\n", file=out)
        return out.getvalue()


class EoPiece:
    """A piece of EoSip archive"""
    def __init__(self, name):
        self.compressed = False
        self.name = name
        # path on local filesystem
        self.localPath = None
        self.alias = None
        self.type = None
        self.content = None

    def info(self):
        out = StringIO()
        print(" name:%s" % self.name, file=out)
        print(" type:%s" % self.type, file=out)
        print(" compressed:%s" % self.compressed, file=out)
        print(" localPath:%s" % self.localPath, file=out)
        print(" alias:%s" % self.alias, file=out)
        if self.content is not None:
            print(" content length:%s" % len(self.content), file=out)
        else:
            print(" content: None", file=out)
        return out.getvalue()


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        # landsat1-7 without MD.XML but MTR.XML
        # eoSipProduct=Product_EOSIP("/home/gilles/shared/WEB_TOOLS/MISSIONS/Landsat/TM_GEO_1P/LS05_RKSE_TM__GEO_1P_20110525T104102_20110525T104121_144838_0201_0022_2BBB.ZIP")
        # landsat1-7 with MD.XML
        eoSipProduct = Product_EOSIP(
            "/home/gilles/shared//WEB_TOOLS/MISSIONS/Landsat/TM_GTC_1P/L05_RKSE_TM__GTC_1P_19900721T104307_19900721T104335_033974_0206_0024_0001.SIP.ZIP")
        # eoSipProduct=Product_EOSIP("/home/gilles/shared/WEB_TOOLS/MISSIONS/Landsat1-7/TDS/SRC/LS07_RNSG_ETM_GTC_1P_19991117T090444_19991117T090513_003142_0184_0036_52E7.ZIP")
        # eoSipProduct.setDebug(1)

        eoSipProduct.loadProduct()
        print("EoSip info:\n%s" % eoSipProduct.info())

        met = metadata.Metadata()
        numAdded, helper = eoSipProduct.extractMetadata(met)
        print(" number of metadata added:%s" % numAdded)
        print("\n###\n###\n###\nMETADATA:%s\n###\n###\n###\n" % met.toString())

    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
