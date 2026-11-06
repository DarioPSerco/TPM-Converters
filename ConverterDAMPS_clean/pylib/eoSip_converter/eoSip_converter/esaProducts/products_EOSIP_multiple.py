# -*- coding: cp1252 -*-
#
# this class represent multiple EoSip
#
#
import os

# from xml_nodes import eop_EarthObservation, alt_EarthObservation, sar_EarthObservation, opt_EarthObservation, lmb_EarthObservation, atm_EarthObservation, rep_browseReport, eop_browse, SIPInfo, sipBuilder
# from eoSip_converter.serviceClients import xmlValidateServiceClient
import eoSip_converter.kmz as kmz
# from eoSip_converter.esaProducts.product import Product
# from eoSip_converter.esaProducts.product_directory import Product_Directory
# from eoSip_converter.esaProducts.namingConvention import NamingConvention
# import definitions_EoSip
# import eoSip_converter.xmlHelper
# import eosip_product_helper
# import formatUtils
from . import metadata
from eoSip_converter.base.geo.geoInfo import GeoInfo
#
from eoSip_converter.esaProducts.product_EOSIP import Product_EOSIP

DEFAULT_MULTIPLE_EOSIP_NAME = "MULTIPLE_EOSIP"


class Products_EOSIP_Multiple(Product_EOSIP):

    #
    # set defaults
    #
    def __init__(self, path=None):
        Product_EOSIP.__init__(self, path)
        #
        # key is: integer starting at 0
        #
        self.productsMap = {}
        self.commonProductName = "MULTIPLE_EOSIP"
        if self.debug != 0:
            print(" init class Products_EOSIP_Multiple")

    #
    # overwrite Product one
    # return a list
    #
    def getPath(self):
        paths = []
        for product in list(self.productsMap.values()):
            paths.append(product.getPath())
        return paths

    #
    # add a source browse, create the corresponding report info
    #
    # def addSourceBrowse(self, path=None, addInfo=None):

    #
    # set the common product name
    #
    def setCommonProductName(self, p):
        self.commonProductName = p

    #
    # get the common product name
    #
    def getCommonProductName(self):
        return self.commonProductName

    #
    # an a EoSip product 
    #
    def addEoSip(self, key, p):
        self.productsMap[key] = p

    #
    # get a EoSip product 
    #
    def getEoSip(self, key):
        return self.productsMap[key]

    #
    #
    #
    def getEoSipKeys(self):
        return list(self.productsMap.keys())

    #
    #
    #
    def getSipProductName(self):
        return self.commonProductName

    #
    #
    #
    def info(self):
        data = ''
        n = 0
        for product in list(self.productsMap.values()):
            data = "%sProduct[%s]info:\n%s" % (data, n, product.info())
            n = n + 1
        return data

    #
    #
    #
    def getMetadataAsString(self):
        data = ''
        n = 0
        for product in list(self.productsMap.values()):
            data = "%sProduct[%s] metadata toString:%s\n" % (data, n, product.metadata.toString())
            n = n + 1
        return data

    #
    #
    #
    def getNamesInfo(self):
        data = ''
        n = 0
        for product in list(self.productsMap.values()):
            data = "%sSip product[%s] name (no ext):%s\n" % (data, n, product.getSipProductName())
            data = "%sSip package[%s] name (with ext):%s\n" % (data, n, product.sipPackageName)
            data = "%sEo product[%s] name (no ext):%s\n" % (data, n, product.eoProductName)
            data = "%sEo package[%s] name (with ext):%s\n" % (data, n, product.eoPackageName)
            data = "%s\n" % data
            n = n + 1
        return data

    #
    # moved here from Ingester
    # (parentFolder == pInfo.workFolder)
    #
    #
    def makeFolder(self, parentFolder):
        data = '\n'
        n = 0
        for product in list(self.productsMap.values()):
            # product.tmpFolder = "%s/%s/%s" % (parentFolder, self.getSipProductName(), product.getSipProductName())
            # if not os.path.exists(product.tmpFolder):
            #        os.makedirs(product.tmpFolder)
            # data = '%s tmpFolder[%s]:%s\n' % (data, n, product.tmpFolder)
            product.setFolder("%s/%s/%s" % (parentFolder, self.getSipProductName(), product.getSipProductName()))
            if not os.path.exists(product.folder):
                os.makedirs(product.folder)
            data = '%s folder[%s]:%s\n' % (data, n, product.folder)
            n = n + 1
        return data

    #
    #
    #
    def setMetadata(self, met):
        # keep it in self for convenience
        self.metadata = met
        print("*********************** EOSIP_Multiple_Products.setMetadata (%s eoSipProducts) to:\n%s" % (
        len(self.productsMap), self.metadata.toString()))
        n = 0
        # set/merge it in every children
        for product in list(self.productsMap.values()):
            if product.metadata == None:  # .isMetadataDefined():
                product.setMetadata(met)
                print(" ****************  dest[%s] product metadata is NONE" % n)
            else:
                product.metadata.merge(met)
                print(" ****************  dest[%s] product metadata is NOT NONE" % n)

    #
    #
    #
    def getOneProductMetadata(self, index):
        return self.productsMap[index].metadata

    #
    #
    #
    def setFolder(self, f):
        for product in list(self.productsMap.values()):
            product.setFolder(f)

            #

    #
    #
    def setTypology(self, t):
        self.TYPOLOGY = t
        for product in list(self.productsMap.values()):
            product.setTypology(t)

    #
    # set the sip package naming convention
    #
    def setNamingConventionSipInstance(self, namingConventionInstance):
        for product in list(self.productsMap.values()):
            product.setNamingConventionSipInstance(namingConventionInstance)

    #
    # set the eo package naming convention
    #
    def setNamingConventionEoInstance(self, namingConventionInstance):
        for product in list(self.productsMap.values()):
            product.setNamingConventionEoInstance(namingConventionInstance)

    #
    #
    #
    def setEoExtension(self, ext):
        for product in list(self.productsMap.values()):
            product.setEoExtension(ext)

    #
    #
    #
    def setSipExtension(self, ext):
        for product in list(self.productsMap.values()):
            product.setSipExtension(ext)

    #
    #
    #
    def setSrcProductStoreType(self, t):
        for product in list(self.productsMap.values()):
            product.setSrcProductStoreType(t)

    #
    #
    #
    def setProcessInfo(self, p):
        self.processInfo = p
        for product in list(self.productsMap.values()):
            product.setProcessInfo(p)

    #
    #
    #
    def setXmlMappingMetadata(self, dict1, dict2):
        for product in list(self.productsMap.values()):
            product.setXmlMappingMetadata(dict1, dict2)

    #
    # set if the eoSip zip compressed
    #
    def setSrcProductStoreCompression(self, b):
        print(" HELLO: set store compression on num products:%s" % len(list(self.productsMap.values())))
        for product in list(self.productsMap.values()):
            product.setSrcProductStoreCompression(b)

    #
    # set if the eo product is compressed
    #
    def setSrcProductStoreEoCompression(self, b):
        print(" HELLO: set store EO compression on num products:%s" % len(list(self.productsMap.values())))
        for product in list(self.productsMap.values()):
            product.setSrcProductStoreEoCompression(b)

    #
    #
    #
    def writeToFolder(self, p=None, overwrite=None):
        for product in list(self.productsMap.values()):
            product.writeToFolder(p, overwrite)

    #
    # getter: info are common, take from first product
    #
    def getSrcProductStoreType(self):
        return list(self.productsMap.values())[0].getSrcProductStoreType()

    def getSrcProductStoreEoCompression(self, b):
        return list(self.productsMap.values())[0].getSrcProductStoreEoCompression()

    def getSrcProductStoreCompression(self, b):
        return list(self.productsMap.values())[0].getSrcProductStoreCompression()

    def getNamingConventionSipInstance(self):
        return list(self.productsMap.values())[0].getNamingConventionSipInstance()

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # build name in each children
        for product in list(self.productsMap.values()):
            if not processInfo.ingester.want_duplicate:
                # print " buildEoNames"
                processInfo.addLog(" buildEoNames")
                # processInfo.destProduct.setDebug(1)
                product.buildEoNames(namingConvention)

                # test EoSip package name
                aName = product.getSipPackageName()
                if len(aName) != len(processInfo.ingester.REF_NAME):
                    print("ref name:%s" % processInfo.ingester.REF_NAME)
                    print("EoSip name:%s" % aName)
                    raise Exception(
                        "EoSip name has incorrect length:%s VS %s" % (len(aName), len(processInfo.ingester.REF_NAME)))
                if aName.find('@') >= 0 or aName.find('#') > 0:
                    raise Exception("SipProductName incomplet:%s" % aName)

                if not processInfo.ingester.product_overwrite:
                    exists, dummy, finalPath = self.checkDestinationAlreadyExists(processInfo)
                    if exists:
                        raise Exception("will create a unwanted duplicate:%s" % finalPath)
            else:
                # as in ingester
                #
                ok = False
                loopNum = 0
                while not ok and loopNum < 10:
                    # print " buildEoNames loop:%s" % loopNum
                    processInfo.addLog(" buildEoNames loop:%s" % loopNum)
                    product.setDebug(1)
                    if loopNum == 0:
                        product.buildEoNames(namingConvention, False)
                    else:
                        product.buildEoNames(namingConvention, True)

                    # test EoSip package name
                    aName = product.getSipPackageName()
                    if len(aName) != len(processInfo.ingester.REF_NAME):
                        print("ref name:%s" % processInfo.ingester.REF_NAME)
                        print("EoSip name:%s" % aName)
                        raise Exception("EoSip name has incorrect length:%s VS %s" % (
                            len(aName), len(processInfo.ingester.REF_NAME)))
                    if aName.find('@') >= 0 or aName.find('#') > 0:
                        raise Exception("SipProductName incomplet:%s" % aName)

                    product.setDebug(0)
                    if not processInfo.ingester.product_overwrite:
                        # test for duplicate
                        exists, newFileCounter, finalPath = self.checkDestinationAlreadyExists(processInfo)
                        if exists:
                            print(" @@ buildEoNames exists:%s; newFileCounter:%s; finalPath=%s" % (
                            exists, newFileCounter, finalPath))
                            processInfo.addLog(" buildEoNames exists:%s; newFileCounter:%s" % (exists, newFileCounter))
                            if newFileCounter > 9:
                                raise Exception("newFileCounter limit reached: %s" % newFileCounter)

                            # set new file counter
                            product.metadata.setMetadataPair(metadata.METADATA_FILECOUNTER, "%s" % newFileCounter)
                            # set new METADATA_SIP_VERSION, because it's what is used in the hight res naming convention
                            tmp = product.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
                            print(" @@ buildEoNames exists: current version:%s" % tmp)
                            processInfo.addLog(" buildEoNames loop: current version:%s" % tmp)
                            tmp = "%s%s" % (tmp[0:3], newFileCounter)
                            print(" @@ buildEoNames exists: new version:%s" % tmp)
                            processInfo.addLog(" buildEoNames loop: new version:%s" % tmp)
                            product.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION, tmp)
                        else:
                            print(" @@ buildEoNames does not exists:%s; newFileCounter:%s; finalPath=%s" % (
                            exists, newFileCounter, finalPath))
                            ok = True
                    else:
                        ok = True
                    loopNum += 1
                #
                if not ok:
                    raise Exception("error creating product filename: duplicate test reach loop limit at %s" % loopNum)

    #
    # build the product metadata report
    #
    def buildProductReportFile(self):
        for product in list(self.productsMap.values()):
            product.buildProductReportFile()

    #
    # build the product sip report
    #
    def buildSipReportFile(self):
        for product in list(self.productsMap.values()):
            product.buildSipReportFile()

    #
    # build the product browse report
    #
    def buildBrowsesReportFile(self):
        for product in list(self.productsMap.values()):
            product.buildBrowsesReportFile()

    #
    # make the KMZ file, use the boundingbox
    #
    def makeKmz(self, processInfo):
        # for each children
        processInfo.ingester.logger.info("WILL CREATE MULTIPLE KMZ")
        n = 0
        for product in list(self.productsMap.values()):
            print(" ########################### make KMZ for multiple eoSip[%s]" % n)
            outPath = "%s/kmz" % processInfo.ingester.LOG_FOLDER
            if not os.path.exists(outPath):
                processInfo.ingester.logger.info("  will make kmz folder:%s" % outPath)
                os.makedirs(outPath)
            kmzPath = kmz.eosipToKmz.makeKmlFromEoSip_new(True, outPath, processInfo)
            print(" KMZ[%s] created at path:%s" % (n, kmzPath))
            if kmzPath != None:
                processInfo.addLog("KMZ[%s] created at path:%s" % (n, kmzPath))
            else:
                processInfo.addLog("KMZ[%s] was NOT CREATED!" % n)
                raise Exception("KMZ[%s] was NOT CREATED!" % n)
            n = n + 1

    #
    #
    #
    def agregateGeoInfo(self, pInfo):

        n = 0
        for productKey in list(self.productsMap.keys()):
            print((" ################## agregateGeoInfo for multi-EoSip[%s]:%s" % (n, productKey)))

            anEosip = self.productsMap[productKey]
            anEosipUniqueName = "%s____%s" % (self.getCommonProductName(), anEosip.sipProductName)

            if anEosipUniqueName in list(pInfo.ingester.footprintAgregator.productGeoInfoMap.keys()):
                print((" #### Product %s is already present" % anEosipUniqueName))
                os._exit(1)
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: HSHSHSHSHSHSH " % n))
            geoInfo = GeoInfo("%s__%s" % (anEosipUniqueName, n))
            geoInfo.setFootprint(anEosip.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
            geoInfo.setBoundingBox(anEosip.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: FOOTPRINT:%s" % (n, geoInfo.getFootprint())))
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: BOUNDINGBOX:%s" % (
            n, geoInfo.getBoundingBox())))
            props = {}
            # default
            props['BatchId'] = pInfo.ingester.fixed_batch_name
            props['SourceProduct_index'] = pInfo.num
            # wanted metadata
            i = 0
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: adding %s metadata" % (
            n, len(pInfo.ingester.footprintAgregator.wantedMetadata))))
            for mName in pInfo.ingester.footprintAgregator.wantedMetadata:
                v = anEosip.metadata.getMetadataValue(mName)
                props[mName] = v
                print((" ################## agregateGeoInfo for multi-EoSip[%s]: adding metadata[%s]:%s=%s" % (
                n, i, mName, v)))
                i += 1

            # add interresting info
            # name of the block png image
            props["Source footprint"] = pInfo.srcProduct.metadata.getMetadataValue('SOURCE_FOOTPRINT')
            props["SIP package name"] = anEosip.sipProductName
            props["EO package name"] = anEosip.eoProductName
            props["Block_browse_png"] = anEosip.tileBlock.browseFilename
            props["Block_LuzResponse"] = anEosip.tileBlock.LuzResponse
            props["Block_info"] = anEosip.tileBlock.getInfo()
            # add index in EoSip_multiple
            props["EoSipMultiple_index"] = n

            geoInfo.setProperties(props)
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: dfsadfasdfasdfasfdasdf " % n))
            pInfo.ingester.footprintAgregator.productGeoInfoMap[anEosipUniqueName] = geoInfo
            print((" ################## agregateGeoInfo for multi-EoSip[%s]: ujkghjkghjkghjkghjkghjkgh " % n))

            n += 1
