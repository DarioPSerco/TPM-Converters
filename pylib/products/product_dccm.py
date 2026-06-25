# -*- coding: cp1252 -*-
#
# this class represent a dccm product (ideas thing)
#
#
import logging
import os

from . import definitions_EoSip
#
import eoSip_converter.xmlHelper as xmlHelper
from . import metadata
from .product import Product

#
# list of attributes and order
#
attributes_order = ['Description', 'ProductName', 'Instrument', 'ProcessingVersion', 'StartTime', 'StopTime',
                    'OrbitStart', 'OrbitStop', 'AcquisitionStation', 'ProductionCentre', 'GeographicalCoverage',
                    'GenerationTime', 'Quality', 'ANXTime', 'StateVectorVelocity', 'StateVectorPosition',
                    'PassDirection', 'ErrorMessage', 'ProductStatus', 'ServerName', 'ServerLocation', 'FilePath',
                    'Size', 'DatasetVersion', 'ProductVersion', 'DensityMap', 'CloudVote', 'QualityInformation']
attributes_list = {'Description': 'ProductName',
                   'ProductName': 'ProductName',
                   'Instrument': metadata.METADATA_INSTRUMENT,
                   'ProcessingVersion': metadata.METADATA_SOFTWARE_NAME,
                   'StartTime': metadata.METADATA_START_DATE,
                   'StopTime': metadata.METADATA_STOP_DATE,
                   'OrbitStart': metadata.METADATA_ORBIT,
                   'OrbitStop': metadata.METADATA_ORBIT,
                   'AcquisitionStation': metadata.METADATA_ACQUISITION_CENTER,
                   'ProductionCentre': metadata.METADATA_PROCESSING_CENTER,
                   'GeographicalCoverage': 'GeographicalCoverage',
                   'GenerationTime': metadata.METADATA_GENERATION_TIME,
                   'Quality': metadata.METADATA_QUALITY_STATUS,
                   'ANXTime': 'ANXTime',
                   'StateVectorVelocity': 'StateVectorVelocity',
                   'StateVectorPosition': 'StateVectorPosition',
                   'PassDirection': metadata.METADATA_ORBIT_DIRECTION,
                   'ErrorMessage': 'ErrorMessage',
                   'ProductStatus': 'ProductStatus',
                   'ServerName': 'ServerName',
                   'ServerLocation': 'ServerLocation',
                   'FilePath': 'FilePath',
                   'Size': metadata.METADATA_PRODUCT_SIZE,
                   'DatasetVersion': 'DatasetVersion',
                   'ProductVersion': 'ProductVersion',
                   'DensityMap': 'DensityMap',
                   'CloudVote': metadata.METADATA_CLOUD_COVERAGE,
                   'QualityInformation': metadata.METADATA_QUALITY_STATUS}

##
ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION = {'CPE': 'CPE',
                                                        'CUB': 'CUB',
                                                        'DSI': 'DSI',
                                                        'ESR': 'ESR',
                                                        'FUI': 'FUI',
                                                        'GAT': 'GAT',
                                                        'EPAC': 'E-PAC',
                                                        'GATN': 'GATN',
                                                        'Kiruna': 'Kiruna',
                                                        'KOU': 'KOU',
                                                        'KS': 'KS',
                                                        'KSE': 'KSE',
                                                        'KSS': 'KSS',
                                                        'LRAC': 'LRAC',
                                                        'MDA': 'MDA',
                                                        'MLD': 'MLD',
                                                        'MPS': 'MPS',
                                                        'MTI': 'MTI',
                                                        'NSG': 'NSG',
                                                        'OFB': 'OFB',
                                                        'OPF': 'OPF',
                                                        'PAS': 'PAS',
                                                        'PASS': 'PASS',
                                                        'PDHSE': 'PDHSE',
                                                        'PDHSK': 'PDHSK',
                                                        'TRS': 'TRS',
                                                        'IPAC': 'I-PAC',
                                                        'PDASM': 'PDAS-M',
                                                        'PDASF': 'PDAS-F',
                                                        'PDASS': 'PDAS-S',
                                                        'PDHS_E': 'PDHS-E',
                                                        'PDHS_K': 'PDHS-K'}
##
ICD_PRODUCT_INSTRUMENT_DICT_CODE_TO_DESCRIPTION = {'ERS1AMI': 'AMI', 'ENVISATRA2': 'RA-2', 'ERS2GOME': 'GOME',
                                                   'ENVISATMERIS': 'MERIS', 'ENVISATMIPAS': 'MIPAS',
                                                   'ALOSAVNIR2': 'AVNIR-2', 'ERS2ATSR2': 'ATSR-2', 'ERS2AMI': 'AMI',
                                                   'ERS1WSC': 'WSC', 'LANDSAT5TM': 'TM', 'ERS1RA1': 'RA1',
                                                   'ERS2RA2': 'RA2', 'ALOSPALSAR': 'PALSAR',
                                                   'LANDSAT1_2_3_4_MSS': 'MSS', 'ERS2WSC': 'WSC', 'LANDSAT7ETM': 'ETM',
                                                   'ALOSPRISM': 'PRISM', 'ENVISATAATSR': 'AATSR', 'ENVISATASAR': 'ASAR',
                                                   'ENVISATGOMOS': 'GOMOS', 'ALOSAuxiliary': 'Auxiliary',
                                                   'ENVISATAuxiliary': 'Auxiliary', 'ENVISATSCIAMACHY': 'SCIAMACHY',
                                                   'ERS1ATSR1': 'ATSR-1', 'ERS1Auxiliary': 'Auxiliary',
                                                   'ERS2Auxiliary': 'Auxiliary',
                                                   'LANDSAT1_2_3_4_Auxiliary': 'Auxiliary',
                                                   'LANDSAT5Auxiliary': 'Auxiliary', 'LANDSAT7Auxiliary': 'Auxiliary'}
##
ICD_QUALITY_DICT_CODE_TO_DESCRIPTION = {'Failed': 'Failed', 'Passed': 'Passed'}
##
ICD_PASS_DIRECTION_DICT_CODE_TO_DESCRIPTION = {'A': 'A', 'ASC': 'ASC', 'D': 'D', 'DSC': 'DSC', 'NNAA': 'NNAA'}
##
ICD_PRODUCT_STATUS_DICT_CODE_TO_DESCRIPTION = {'Available': 'Available', 'Corrupted': 'Corrupted', 'Deleted': 'Deleted'}

## auxName to be discarted
AUX_DISCARTED = ['NOT USED']

# remain from EoSip:
# ways of storing original productSRC_PRODUCT_AS_FILE="SRC_PRODUCT_AS_FILE"
SRC_PRODUCT_AS_ZIP = "SRC_PRODUCT_AS_ZIP"
SRC_PRODUCT_AS_DIR = "SRC_PRODUCT_AS_DIR"
SRC_PRODUCT_AS_TAR = "SRC_PRODUCT_AS_TAR"
SRC_PRODUCT_AS_TGZ = "SRC_PRODUCT_AS_TGZ"
SRC_PRODUCT_AS_FILE = "SRC_PRODUCT_AS_FILE"


class Product_Dccm(Product):
    #
    LIST_OF_SRC_PRODUCT_STORE_TYPE = [SRC_PRODUCT_AS_DIR, SRC_PRODUCT_AS_ZIP, SRC_PRODUCT_AS_TAR, SRC_PRODUCT_AS_TGZ,
                                      SRC_PRODUCT_AS_FILE]

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        #
        self.productParents = {}
        #
        self.productAux = {}
        #
        self.medias = {}
        #
        self.datasets = {}

        #
        # things that EoSip ingester use: need to keep them, or modify the ingester
        #

        # 
        # Eo product name (as in final eoSip product): is contained (as zip or tar or folder or tgz ...) inside the package
        # no extension. So == identifier
        self.eoProductName = None
        # Eo package name (as in final eoSip product): is contained (as zip or tar or folder or tgz ...) inside the package
        # has extension, like: AL1_OPER_AV2_OBS_11_20090517T025758_20090517T025758_000000_E113_N000.ZIP
        self.eoPackageName = None
        # Eo package extension
        self.eoPackageExtension = None

        # the Sip product name, has no extension
        self.sipProductName = None
        # the Sip package name, has extension
        self.sipPackageName = None
        # the package extention
        self.sipPackageExtension = 'xml'
        # the compression of the eoSip zip
        self.src_product_stored_compression = None
        # and the eo product part
        self.src_product_stored_eo_compression = None

        # the sip package full path
        self.sipPackagePath = None

        # the identified: product name minus extension, like: AL1_OPER_AV2_OBS_11_20090517T025758_20090517T025758_000000_E113_N000
        self.identifier = None
        #

        print(" init class Dccm_Product")

    #
    # needed by DCCM ICD:
    #
    # product has already the CODE
    #
    def setInstrument(self, instrument):
        if instrument not in ICD_PRODUCT_INSTRUMENT_DICT_CODE_TO_DESCRIPTION:
            raise Exception("unknown instrument:'%s'" % instrument)
        if self.debug != 0:
            print(" setInstrument:%s" % instrument)
        return instrument

    #
    # needed by DCCM ICD:
    #
    # product has the description, need to return the code
    #
    def setAcquisitionStation(self, acq):
        try:
            list(ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION.values()).index(acq)
        except:
            raise Exception("unknown production/acquisition center:'%s'" % acq)

        result = None
        for item in list(ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION.keys()):
            value = ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION[item]
            if value == acq:
                result = item
                break
        if result == None:
            raise Exception("can not find acquisition center code for description:'%s'" % acq)
        return result

    #
    # needed by DCCM ICD:
    #
    # product has the description, need to return the code
    #
    def setProductionCentre(self, center):
        try:
            list(ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION.values()).index(center)
        except:
            raise Exception("unknown production/acquisition center:'%s'" % center)

        result = None
        for item in list(ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION.keys()):
            value = ICD_ACQ_STATION_PROD_CENTER_DICT_CODE_TO_DESCRIPTION[item]
            if value == center:
                result = item
                break
        if result == None:
            raise Exception("can not find acquisition center code for description:'%s'" % center)
        return result

    #
    # needed by DCCM ICD:
    #
    def setQuality(self, quality):
        pass

    #
    # needed by DCCM ICD:
    #
    def setPassDirection(self, passDirection):
        pass

    #
    # needed by DCCM ICD:
    #
    def setProductStatus(self, status):
        pass

    #
    #
    #
    def addProductParent(self, name):
        print(" addProductParent:%s" % name)
        self.processInfo.addLog(" addProductParent:%s" % name)

        serverName = None
        serverLocation = None
        filePath = None
        parentNames = []
        for item in list(self.processInfo.ingester.dataProviders.keys()):
            if self.debug != 0:
                if self.debug != 0:
                    print(" use data from data provider:%s" % item)

            if item == 'PARENT_ProductName_child':  #
                adataProvider = self.processInfo.ingester.dataProviders[item]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ dataProviders match PARENT_ProductName_child:%s" % adataProvider)
                parentNames = adataProvider.getRowValues(name)
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ %s parentName:%s" % (name, parentNames))
            elif item == 'PARENT_ServerName_child':  #
                adataProvider = self.processInfo.ingester.dataProviders[item]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ dataProviders match PARENT_ServerName_child:%s" % adataProvider)
                serverNames = adataProvider.getRowValues(name)
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ %s serverNames:%s" % (name, serverNames))
            elif item == 'PARENT_ServerLocation_child':  #
                adataProvider = self.processInfo.ingester.dataProviders[item]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ dataProviders match PARENT_ServerLocation_child:%s" % adataProvider)
                serverLocation = adataProvider.getRowValues(name)
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ %s serverLocation:%s" % (name, serverLocation))
            elif item == 'PARENT_FilePath_child':  #
                adataProvider = self.processInfo.ingester.dataProviders[item]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ dataProviders match PARENT_FilePath_child:%s" % adataProvider)
                filePath = adataProvider.getRowValues(name)
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ %s filePath:%s" % (name, filePath))

        n = 0
        for pName in parentNames:
            pServer = serverNames[n]
            pServerLocation = serverLocation[n]
            pFilePath = filePath[n]
            n = n + 1
            self.productParents[name] = "%s|%s|%s|%s" % (pName, pServer, pServerLocation, pFilePath)

    #
    #
    #
    def addProductAux(self, name):
        print(" addProductAux:%s" % name)
        self.processInfo.addLog(" addProductAux:%s" % name)

        serverName = None
        serverLocation = None
        filePath = None
        for item in list(self.processInfo.ingester.dataProviders.keys()):
            try:
                AUX_DISCARTED.index(name)
            except:
                if self.debug != 0:
                    # self.processInfo.addLog(" use data from data provider:%s" % item)
                    print(" use data from data provider:%s" % item)
                if item == 'AUX_ServerName_child':  #
                    adataProvider = self.processInfo.ingester.dataProviders[item]
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ dataProviders match AUX_ServerName_child:%s" % adataProvider)
                    serverName = adataProvider.getRowValue(name)
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ %s serverName:%s" % (name, serverName))
                elif item == 'AUX_ServerLocation_child':  #
                    adataProvider = self.processInfo.ingester.dataProviders[item]
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ dataProviders match AUX_ServerLocation_child:%s" % adataProvider)
                    serverLocation = adataProvider.getRowValue(name)
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ %s serverLocation:%s" % (name, serverLocation))
                elif item == 'AUX_FilePath_child':  #
                    adataProvider = self.processInfo.ingester.dataProviders[item]
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ dataProviders match AUX_FilePath_child:%s" % adataProvider)
                    filePath = adataProvider.getRowValue(name)
                    if self.debug != 0:
                        print("@@@@@@@@@@@@@@@@@@@@ %s filePath:%s" % (name, filePath))

                self.productAux[name] = "%s|%s|%s|%s" % (name, serverName, serverLocation, filePath)

    #
    #
    #
    def addMedia(self, name):
        self.medias[name] = name
        self.processInfo.addLog(" addMedia:%s" % name)

    #
    #
    #
    def addDataset(self, name):
        self.datasets[name] = name
        self.processInfo.addLog(" addDataset:%s" % name)

    #
    # build package and peoductname
    # namingConvention is the class instance used
    # ext is the extension of the eoProduct (what is inside the eoSip package),if not specified, use default EoSip extension: .ZIP
    #
    def buildEoNames(self, namingConvention=None):  # , ext=None, eoExt=None ):
        if self.src_product_stored != SRC_PRODUCT_AS_FILE and self.src_product_stored != SRC_PRODUCT_AS_DIR and self.eoPackageExtension == None:
            raise Exception("eoPackageExtension not defined")

        if self.namingConventionSipPackage == None:
            raise Exception("namingConvention sip instance is None")

        if self.namingConventionEoPackage == None:
            raise Exception("namingConvention eo instance is None")

        if self.debug == 0:
            print(" build eo product names, pattern=%s, eoExt=%s, sipExt=%s" % (
            self.namingConventionEoPackage.usedPattern, self.eoPackageExtension, self.sipPackageExtension))

        # build sip product and package names
        if self.debug == 0:
            print(" build sip product names, pattern=%s,ext=%s" % (
            self.namingConventionSipPackage.usedPattern, self.sipPackageExtension))
        self.sipPackageName = self.namingConventionSipPackage.buildProductName(self.metadata, self.sipPackageExtension)
        # test no # in names
        if self.sipPackageName.find('#') >= 0:
            raise Exception("sipPackageName naming convention build is incomplet:" % self.sipPackageName)
        print("self.sipPackageName:%s" % self.sipPackageName)
        self.sipProductName = self.sipPackageName.split('.')[0]
        print("self.sipProductName:%s" % self.sipProductName)

        # build eoProductName
        # eoProductName coulb be already defined, in case we want to keep original product name for example
        # in this case, we don't change it
        if self.debug == 0:
            print(" build eo product names, pattern=%s,ext=%s" % (
            self.namingConventionEoPackage.usedPattern, self.eoPackageExtension))

        tmpEoProductName = self.namingConventionEoPackage.buildProductName(self.metadata, self.eoPackageExtension)
        # test no # in names
        if tmpEoProductName.find('#') >= 0:
            raise Exception("tmpEoProductName naming convention build is incomplet:" % tmpEoProductName)
        print("tmpEoProductName:%s" % tmpEoProductName)
        eoNameDefined = False
        if self.eoProductName == None:
            self.eoPackageName = tmpEoProductName
            #
            pos = tmpEoProductName.rfind('.')
            if pos > 0:
                self.eoProductName = tmpEoProductName[:pos]
            else:
                self.eoProductName = tmpEoProductName
            eoNameDefined = True
            self.processInfo.addLog(" eo product name built")

        else:
            # if we have an extension in eoProductName, set the choosed one
            pos = self.eoProductName.find('.')
            if pos < 0:
                self.eoPackageName = "%.%s" % (self.eoProductName, self.eoPackageExtension)
            else:
                self.eoPackageName = "%s.%s" % (self.eoProductName[0:pos], self.eoPackageExtension)
                self.eoProductName = self.eoProductName[0:pos]
            self.processInfo.addLog(" eo product predifined, use it:  eo product name=%s\n eo product name=%s" % (
            self.eoProductName, self.sipProductName))

        #
        self.identifier = self.eoProductName
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.eoProductName)
        self.metadata.setMetadataPair(metadata.METADATA_PACKAGENAME, self.sipProductName)
        if self.debug == 0:
            print(" ==> builded product/package product=%s; package=%s" % (self.eoProductName, self.sipProductName))

        if eoNameDefined and self.eoPackageExtension == definitions_EoSip.getDefinition('PACKAGE_EXT'):
            if self.debug != 0:
                print(" we are in zip in zip case: use .SIP.ZIP for eo package name")
            self.sipPackageName = "%s.%s.%s" % (
            self.sipProductName, definitions_EoSip.getDefinition('SIP'), definitions_EoSip.getDefinition('PACKAGE_EXT'))
        else:
            if self.debug != 0:
                print(" we are NOT in zip in zip case")
            self.sipPackageName = "%s.%s" % (self.sipProductName, self.sipPackageExtension)

        self.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, self.identifier)
        self.metadata.setMetadataPair(metadata.METADATA_FULL_PACKAGENAME, self.sipPackageName)

    #
    # set the sip package naming convention
    #
    def setNamingConventionSipInstance(self, namingConventionInstance):
        self.namingConventionSipPackage = namingConventionInstance

    #
    # set the eo package naming convention
    #
    def setNamingConventionEoInstance(self, namingConventionInstance):
        self.namingConventionEoPackage = namingConventionInstance

    #
    # how will we store the source product in the destination eoSip? ZIP, TGZ,...
    #
    def setSrcProductStoreType(self, t):
        self.LIST_OF_SRC_PRODUCT_STORE_TYPE.index(t)
        self.src_product_stored = t

    #
    #
    #
    def getSrcProductStoreType(self):
        return self.src_product_stored

    #
    #
    #
    def getSrcProductStoreType(self):
        return self.src_product_stored

    #
    #
    #
    def setSrcProductStoreEoCompression(self, b):
        self.src_product_stored_eo_compression = b

    #
    #
    #
    def getSrcProductStoreEoCompression(self):
        return self.src_product_stored_eo_compression

    #
    #
    #
    def setSrcProductStoreCompression(self, b):
        self.src_product_stored_compression = b

    #
    #
    #
    def getSrcProductStoreCompression(self):
        return self.src_product_stored_compression

    def setXmlMappingMetadata(self, dict1, dict2):
        pass

    def setProcessInfo(self, p):
        self.processInfo = p

    #
    # set the source product folder path
    #
    def setFolder(self, f):
        self.folder = f

    #
    #
    #
    def getSipProductName(self):
        return self.sipProductName

    #
    # moved here from Ingester
    # (parentFolder == pInfo.workFolder)
    #
    #
    def makeFolder(self, parentFolder):
        self.setFolder("%s/%s" % (parentFolder, self.getSipProductName()))
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        return self.folder

    #
    #
    #
    def getNamesInfo(self):
        data = ''
        data = "%sSip product name (no ext):%s\n" % (data, self.getSipProductName())
        data = "%sSip package name (with ext):%s\n" % (data, self.sipPackageName)
        data = "%sEo product name (no ext):%s\n" % (data, self.eoProductName)
        data = "%sEo package name (with ext):%s\n" % (data, self.eoPackageName)
        return data

    #
    #
    #
    def setEoExtension(self, ext):
        self.eoPackageExtension = ext

    #
    #
    #
    def setSipExtension(self, ext):
        self.sipProductExtension = ext

    #
    #
    #
    def getMetadataAsString(self):
        return self.metadata.toString()

    #
    #
    #
    def setTypology(self, t):
        self.TYPOLOGY = t

    #
    # called at the end of the doOneProduct
    #
    def afterProductDone(self):
        pass

    #
    # build the product metadata report: get it from src product
    #
    def buildProductReportFile(self):
        pass

    #
    # build the browse metadata reports: do nothing
    #
    def buildBrowsesReportFile(self):
        pass

    #
    # build the sip report: do nothing
    #
    def buildSipReportFile(self):
        pass

    #
    # write in a folder.
    # p: path of the output folder
    #
    def writeToFolder(self, p=None, overwrite=None):
        if self.debug == 0:
            print("\n will write product at folder path:%s" % p)
        if p[-1] != '/':
            p = p + '/'

        # create destination path
        self.path = "%s%s" % (p, self.sipPackageName)
        if self.debug == 0:
            print(" full eoSip path:%s" % self.path)

        # already exists?
        if os.path.exists(self.path) and (overwrite == None or overwrite == False):
            raise Exception("refuse to overwite existing product:%s" % self.path)

        helper = xmlHelper.XmlHelper()
        root = helper.createDoc('Product')
        root.setAttribute('action', 'create')

        doc = helper.getDomDoc()
        attributes = doc.createElement('Attributes')
        root.appendChild(attributes)

        # add attributes
        n = 0
        for key in attributes_order:
            metName = attributes_list[key]
            print(" attribute[%s] metName=%s" % (n, metName))
            try:
                value = self.metadata.getMetadataValue(metName)
            except:
                value = "no value for:%s" % metName
            print(" attribute[%s] %s=%s" % (n, key, value))
            node = doc.createElement(key)
            helper.setNodeText(node, "%s" % value)
            attributes.appendChild(node)
            n = n + 1

        # add parents
        if len(list(self.productParents.keys())) > 0:
            parents = doc.createElement('ProductParents')
            root.appendChild(parents)
            n = 0
            for key in list(self.productParents.keys()):
                tmp = self.productParents[key]
                toks = tmp.split('|')
                if len(toks) != 4:
                    raise Exception("aux has wrong number of fields:%s instead of 4" % len(toks))
                if self.debug != 0:
                    print(" productParent[%s] name=%s" % (n, tmp))
                node = doc.createElement('ProductParent')
                nodeName = doc.createElement('ProductName')
                helper.setNodeText(nodeName, toks[0])

                nodeServerName = doc.createElement('ServerName')
                helper.setNodeText(nodeServerName, toks[1])

                nodeServerLocation = doc.createElement('ServerLocation')
                helper.setNodeText(nodeServerLocation, toks[2])

                nodeFilePath = doc.createElement('FilePath')
                helper.setNodeText(nodeFilePath, toks[3])

                parents.appendChild(node)
                node.appendChild(nodeName)
                node.appendChild(nodeServerName)
                node.appendChild(nodeServerLocation)
                node.appendChild(nodeFilePath)
                n = n + 1

        # add aux
        if len(list(self.productAux.keys())) > 0:
            parents = doc.createElement('ProductAuxs')
            root.appendChild(parents)
            n = 0
            for key in list(self.productAux.keys()):
                tmp = self.productAux[key]
                toks = tmp.split('|')
                if len(toks) != 4:
                    raise Exception("aux has wrong number of fields:%s instead of 4" % len(toks))
                if self.debug != 0:
                    print(" productAux[%s] name=%s" % (n, tmp))
                node = doc.createElement('ProductAux')
                nodeName = doc.createElement('AuxName')
                helper.setNodeText(nodeName, toks[0])

                nodeServerName = doc.createElement('ServerName')
                helper.setNodeText(nodeServerName, toks[1])

                nodeServerLocation = doc.createElement('ServerLocation')
                helper.setNodeText(nodeServerLocation, toks[2])

                nodeFilePath = doc.createElement('FilePath')
                helper.setNodeText(nodeFilePath, toks[3])

                parents.appendChild(node)
                node.appendChild(nodeName)
                node.appendChild(nodeServerName)
                node.appendChild(nodeServerLocation)
                node.appendChild(nodeFilePath)
                n = n + 1

        # add media
        if len(list(self.medias.keys())) > 0:
            parents = doc.createElement('Medias')
            root.appendChild(parents)
            n = 0
            for key in list(self.medias.keys()):
                name = self.medias[key]
                print(" add media[%s] name=%s" % (n, name))
                node = doc.createElement('Media')
                nodeName = doc.createElement('OriginalLabel')
                helper.setNodeText(nodeName, "%s" % name)
                parents.appendChild(node)
                node.appendChild(nodeName)
                n = n + 1

        # add datasets
        if len(list(self.datasets.keys())) > 0:
            parents = doc.createElement('Datasets')
            root.appendChild(parents)
            n = 0
            for key in list(self.datasets.keys()):
                name = self.datasets[key]
                print(" add dataset[%s] name=%s" % (n, name))
                node = doc.createElement('Dataset')
                nodeName = doc.createElement('Code')
                helper.setNodeText(nodeName, "%s" % name)
                parents.appendChild(node)
                node.appendChild(nodeName)
                n = n + 1

        rawXml = helper.prettyPrint(None)
        helper2 = xmlHelper.XmlHelper()
        helper2.setData(rawXml)
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print("XML:%s" % formattedXml)

        # create folder neeedd
        if not os.path.exists(p):
            os.makedirs(p)

        # remove precedent zip if any
        if os.path.exists(self.path):
            os.remove(self.path)

        fd = open(self.path, 'w')
        fd.write('<?xml version="1.0" encoding="UTF-8"?>\n%s' % formattedXml)
        fd.flush()
        fd.close()

        return self.path

    #
    #
    #
    def getOutputFolders(self, basePath=None, final_path_list=None):
        # create directory trees according to the configuration path rules
        if self.debug != 0:
            print(" getOutputFolders: basePath=%s, final_path_list=%s" % (basePath, final_path_list))
        folders = []
        if basePath[-1] != '/':
            basePath = "%s/" % basePath

        if len(final_path_list) == 0 or final_path_list.strip() == '[]':
            # raise Exception("final_path_list is empty")
            folders.append(basePath)
            return folders

        i = 0
        blocks = final_path_list.split(',')
        if self.debug != 0:
            print(" getOutputFolders: final_path_list='%s'; length block=%s" % (final_path_list, len(blocks)))
        for rule in blocks:
            if rule[0] == '[':
                rule = rule[1:]
            if rule[-1] == ']':
                rule = rule[0:-1]
            rule = rule.replace('"', '')
            if self.debug != 0:
                print("  resolve path rule[%d/%d]:%s" % (i, len(blocks), rule))
            toks = rule.split('/')
            new_rulez = basePath
            n = 0
            for tok in toks:
                new_rulez = "%s%s/" % (new_rulez, self.metadata.eval(tok))
                n = n + 1
            if self.debug != 0:
                print("  resolved path rule[%d]:%s" % (i, new_rulez))
            folders.append(new_rulez)
            i = i + 1
        return folders

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    # return information on the EoSip product
    #
    def info(self):
        return self.info_impl()

    #
    # return information on the EoSip product
    #
    def info_impl(self):
        return 'some info'

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        p = Product_Dccm(
            "/home/gilles/shared2/Datasets/IDEAS/ifremer/MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1")
        p.read(1000)
    except Exception as err:
        log.exception('Error from throws():')
