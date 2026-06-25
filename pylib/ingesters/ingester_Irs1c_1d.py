#
# For Esa/lite dissemination project
#
# Serco 02/2015 Lavaux Gilles
#
# 03/03/2015: V: 0.1
#
#
#
#
import os
import sys
import traceback

from eoSip_converter.base import ingester
from eoSip_converter.esaProducts import product_EOSIP, product_Irs1c_1d
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention import NamingConvention
import eoSip_converter.xmlHelper as xmlHelper

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0

REF_NAME = (
    "I1C_OPER_PAN_P___1A_19960702T092345_19960702T092345_007505_0033_0019_0001.SIP.ZIP"
)


# REF_SIP_NAME='I1C_OPER_PAN_P___1A_19960702T092345_19960702T092345_007505_0033_0019_0001.ZIP'


class ingester_Irs1c_1d(ingester.Ingester):

    #
    #
    #
    def afterStarting(self, **kargs):
        pass

    #
    # config version is like: name_floatVersion
    #
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    #
    # prepare metadata from a browse report generation
    #
    def prepareBrowseMetadata(self, processInfo):
        pass

    #
    # called before doing the various reports
    #
    def beforeReportsDone(self, processInfo):
        # set platform id to 2 digit 1C or 1D. Can not do it at metadata refine time because EoSip package name use another convention. bah...
        tmp = processInfo.destProduct.metadata.getMetadataValue(
            "orig_METADATA_PLATFORM"
        )
        if self.debug != 0:
            print("  change platform id tmp:%s" % tmp)
        # os._exit(-1)
        mid = tmp.split("-")[1].upper()
        processInfo.destProduct.metadata.setMetadataPair(
            metadata.METADATA_PLATFORM_ID, mid
        )
        if self.debug != 0:
            print("  change platform id:%s" % mid)
        # alter href mapping
        processInfo.destProduct.metadata.alterMetadataMaping(
            "href", metadata.METADATA_FULL_PACKAGENAME
        )
        # set angle unit to deg
        processInfo.destProduct.metadata.setValidValue("UNIT_ANGLE", "deg")

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        # populate dest eoSip with src product self.additionalContent
        # n=0
        # for item in processInfo.srcProduct.additionalContent.keys():
        #    path = processInfo.srcProduct.additionalContent[item]
        #    print " EoSip additional content[%s]; name=%s; path=%s" % (n, item, path)
        #    processInfo.destProduct.addAdditionalContent(path, item)

        # trigger EoSip write multiple files case
        processInfo.destProduct.sourceProductPath = None

        self.alterReportXml(processInfo)

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        # self.makeKmz(processInfo)
        pass

    #
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog(" alterReportXml: product report parsed")
        if self.debug != 0:
            print(" alterReportXml: product report parsed")

        # add namespace: <eop:operationalMode codeSpace="urn:esa:eop:IRS:PAN:Mode"
        codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE
        )
        if self.debug != 0:
            print("alterReportXml: codeSpaceOpMode='%s'" % codeSpaceOpMode)
        if not processInfo.destProduct.testValueIsDefined(codeSpaceOpMode):
            raise Exception("codeSpaceOpMode is not defined")
        aNode = helper.getFirstNodeByPath(
            None,
            "procedure/EarthObservationEquipment/sensor/Sensor/operationalMode",
            None,
        )
        helper.setNodeAttributeText(aNode, "codeSpace", codeSpaceOpMode)

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(helper.prettyPrint())
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print(" new XML: %s " % formattedXml)
        fd = open(processInfo.destProduct.reportFullPath, "w")
        fd.write(formattedXml)
        fd.flush()
        fd.close()
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        if not processInfo.ingester.want_duplicate:
            if self.debug != 0:
                print("  buildEoNames")
            processInfo.addLog(" buildEoNames")
            # processInfo.destProduct.setDebug(1)
            processInfo.destProduct.buildEoNames(namingConvention)
            if not self.product_overwrite:
                exists, dummy, finalPath = self.checkDestinationAlreadyExists(
                    processInfo
                )
                if exists:
                    raise Exception("will create a unwanted duplicate:%s" % finalPath)
            # os._exit(1)

        else:
            if 1 == 2:
                #
                processInfo.destProduct.buildEoNames(namingConvention)

            #
            ok = False
            loopNum = 0
            while not ok and loopNum < 10:
                if self.debug != 0:
                    print("  buildEoNames loop:%s" % loopNum)
                processInfo.addLog(" buildEoNames loop:%s" % loopNum)
                # processInfo.destProduct.setDebug(1)
                if loopNum == 0:
                    processInfo.destProduct.buildEoNames(namingConvention, False)
                else:
                    processInfo.destProduct.buildEoNames(namingConvention, True)
                # processInfo.destProduct.setDebug(0)
                if not self.product_overwrite:
                    # test for duplicate
                    exists, newFileCounter, finalPath = (
                        self.checkDestinationAlreadyExists(processInfo)
                    )
                    if exists:
                        print(
                            "  buildEoNames; destination exists:%s; newFileCounter:%s; finalPath=%s"
                            % (exists, newFileCounter, finalPath)
                        )
                        processInfo.addLog(
                            "buildEoNames exists:%s; newFileCounter:%s"
                            % (exists, newFileCounter)
                        )
                        if newFileCounter > 9:
                            raise Exception(
                                "newFileCounter limit reached: %s" % newFileCounter
                            )

                        # set new file counter
                        processInfo.destProduct.metadata.setMetadataPair(
                            metadata.METADATA_FILECOUNTER, "%s" % newFileCounter
                        )
                        # set new METADATA_PRODUCT_VERSION, because it's what is used in the NamingConvention
                        tmp = processInfo.destProduct.metadata.getMetadataValue(
                            metadata.METADATA_PRODUCT_VERSION
                        )
                        if self.debug != 0:
                            print("  buildEoNames exists: current version:%s" % (tmp))
                        processInfo.addLog(
                            " buildEoNames loop: current version:%s" % (tmp)
                        )
                        tmp = "%s%s" % (tmp[0:3], newFileCounter)
                        if self.debug != 0:
                            print("  buildEoNames exists: new version:%s" % (tmp))
                        processInfo.addLog(" buildEoNames loop: new version:%s" % (tmp))
                        processInfo.destProduct.metadata.setMetadataPair(
                            metadata.METADATA_PRODUCT_VERSION, tmp
                        )
                    else:
                        if self.debug != 0:
                            print(
                                "  buildEoNames does not exists:%s; newFileCounter:%s; finalPath=%s"
                                % (exists, newFileCounter, finalPath)
                            )
                        ok = True
                else:
                    ok = True
                loopNum += 1
            #
            if not ok:
                raise Exception(
                    "error creating product filename: duplicate test reach loop limit at %s"
                    % loopNum
                )

            # test EoSip package name
            aName = processInfo.destProduct.getSipPackageName()
            if len(aName) != len(REF_NAME):
                print("ref name:%s" % REF_NAME)
                print("EoSip name:%s" % aName)
                raise Exception(
                    "EoSip name has incorrect length:%s VS %s"
                    % (len(aName), len(REF_NAME))
                )
            if aName.find("@") >= 0 or aName.find("#") > 0:
                raise Exception("SipProductName incomplet:%s" % aName)

    #
    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace("\\", "/")
        product = product_Irs1c_1d.Product_Irs1c_1d(processInfo.srcPath)
        # product.setDebug(1)
        processInfo.srcProduct = product

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention(self.OUTPUT_SIP_PATTERN)
        # namingConventionSip.setDebug(1)
        processInfo.destProduct.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionEoInstance(namingConventionSip)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionSip)

        self.logger.info(" Eo-Sip product created")
        processInfo.addLog(" Eo-Sip product created")

    #
    # Override
    #
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" verifying product:%s" % (processInfo.srcPath))
        self.logger.info(" verifying product")

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog(" prepare product in:%s" % (processInfo.workFolder))
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(
            processInfo.workFolder, processInfo.test_dont_extract
        )

        processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

        # self.imageutilsExe = self.ressourcesProvider.getRessourcePath('imageutilsExe')
        # processInfo.srcProduct.imageutilsExe = self.imageutilsExe

        # self.stretcherAppExe = self.ressourcesProvider.getRessourcePath('stretchAppExe')
        # processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

    #
    #
    #
    def makeImageryHdr(self, path, processInfo):
        fd = open("%s/metadata.xml" % processInfo.workFolder, "r")
        data = fd.read()
        fd.close()
        helper = xmlHelper.XmlHelper()
        helper.setData(data)
        helper.parseData()

        aNode = helper.getFirstNodeByPath(None, "Image/COLUMNS", None)
        rows = None
        cols = None
        if aNode is None:
            raise Exception("can not find node Image/COLUMNS in xml data")
        cols = helper.getNodeText(aNode)

        aNode = helper.getFirstNodeByPath(None, "Image/ROWS", None)
        if aNode is None:
            raise Exception("can not find node Image/ROWS in xml data")
        rows = helper.getNodeText(aNode)

        data = """BYTEORDER     M
LAYOUT        BIL
NROWS         %s
NCOLS         %s
NBANDS        4
NBITS         8
SKIPBYTES     0
""" % (
            rows,
            cols,
        )
        print("imagery.hdr data:\n%s" % data)

        fd = open(path, "w")
        fd.write(data)
        fd.close()
        print("imagery.hdr writen at:%s" % path)
        # os._exit(0)

    #
    #
    #
    def makeImageryblw(self, path, processInfo):
        fd = open("%s/metadata.xml" % processInfo.workFolder, "r")
        data = fd.read()
        fd.close()
        helper = xmlHelper.XmlHelper()
        helper.setData(data)
        helper.parseData()

        aNode = helper.getFirstNodeByPath(None, "GeoInformation/XGEOREF", None)
        XGEOREF = None
        YGEOREF = None
        if aNode is None:
            raise Exception("can not find node GeoInformation/XGEOREF in xml data")
        XGEOREF = helper.getNodeText(aNode)

        aNode = helper.getFirstNodeByPath(None, "GeoInformation/YGEOREF", None)
        if aNode is None:
            raise Exception("can not find node GeoInformation/YGEOREF in xml data")
        YGEOREF = helper.getNodeText(aNode)

        XCELLRES = None
        YCELLRES = None
        aNode = helper.getFirstNodeByPath(None, "GeoInformation/XCELLRES", None)
        if aNode is None:
            raise Exception("can not find node GeoInformation/XCELLRES in xml data")
        XCELLRES = helper.getNodeText(aNode)

        YCELLRES = None
        aNode = helper.getFirstNodeByPath(None, "GeoInformation/YCELLRES", None)
        if aNode is None:
            raise Exception("can not find node GeoInformation/YCELLRES in xml data")
        YCELLRES = helper.getNodeText(aNode)

        data = """\t%s
\t0.000000
\t0.000000
\t-%s
\t%s
\t%s
""" % (
            XCELLRES,
            YCELLRES,
            XGEOREF,
            YGEOREF,
        )
        print("imagery.blw data:\n%s" % data)

        fd = open(path, "w")
        fd.write(data)
        fd.close()
        print("imagery.blw writen at:%s" % path)
        # os._exit(0)

    #
    # Override
    # + check if there is a imagery.hdr present, if not, create it
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # met.setMetadataPair(metadata.METADATA_GENERATION_TIME, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        # use method in base converter
        self.getGenerationTime(met)

        # keep some info
        mode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_SENSOR_OPERATIONAL_MODE
        )
        self.keepInfo("sensor mode", mode)
        sensor = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_INSTRUMENT
        )
        self.keepInfo("sensor", sensor)
        typecode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_TYPECODE
        )
        self.keepInfo("typecode", typecode)

        softVersion = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_SOFTWARE_VERSION
        )
        self.keepInfo("softVersion", softVersion)
        softName = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_SOFTWARE_NAME
        )
        self.keepInfo("softName", softName)

    #
    #
    #
    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    #
    # Override
    # make the Jpeg (or Png) browse image from the TIFF image. We want Jpeg
    # construct the browse_metadatareport footprint block: it is the rectifedBrowse for tropforest
    #
    def makeBrowses(self, processInfo, ratio=50):
        processInfo.srcProduct.makeBrowses(processInfo)

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip: basePath=%s" % (basePath))
        #
        if 1 == 1:
            if self.debug != 0:
                print(
                    " processInfo.srcProduct.relBasePaths:%s"
                    % processInfo.srcProduct.relBasePaths
                )
            n = 0
            for (
                    item
            ) in (
                    processInfo.srcProduct.contentList
            ):  # contains the full path of the src (folder) product. (Nothing to do with working folder)
                print("  SET SOURCE FILE[%s]:%s in EoSip" % (n, item))
                relBasePath = processInfo.srcProduct.relBasePaths[item]
                print(
                    "  SET SOURCE FILE[%s]:%s in EoSip contentList as name:%s"
                    % (n, item, relBasePath)
                )
                # set zip_content relative name in EoSIp
                processInfo.destProduct.contentList.append(relBasePath)
                processInfo.destProduct.contentListPath[relBasePath] = item
                n += 1
        # os._exit(-1)

        #
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            self.logger.info("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addIngesterLog(
                "  write done:%s" % processInfo.destProduct.path, "PROGRESS"
            )

            # output link in other path
            i = 0
            for item in self.outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % (item)
                    self.logger.info("  eoSip product tree path[%d] is:%s" % (i, item))
                    processInfo.destProduct.writeToFolder(basePath, overwrite)
                    processInfo.addLog(
                        "  Eo-Sip product link writen in folder[%d]:%s\n"
                        % (i, otherPath)
                    )
                    self.logger.info(
                        "  Eo-Sip product link writen in folder[%d]:%s\n"
                        % (i, otherPath)
                    )
                i = i + 1
        self.logger.info("  done")
        return productPath

    #
    # create a kmz, use the bounding box
    # created in the log folder
    #
    # NEW: done in ingester
    #
    def makeKmz_DEPRECATED(self, processInfo):
        if not self.test_dont_write:
            processInfo.ingester.logger.info("WILL CREATE KMZ")
            import kmz

            outPath = "%s/kmz" % processInfo.ingester.LOG_FOLDER
            if not os.path.exists(outPath):
                self.logger.info("  will make kmz folder:%s" % outPath)
                os.makedirs(outPath)
            kmzPath = kmz.eosipToKmz.makeKmlFromEoSip_new(False, outPath, processInfo)
            print(" KMZ created at path:%s" % kmzPath)
            if kmzPath != None:
                processInfo.addLog("KMZ created at path:%s" % kmzPath)
            else:
                processInfo.addLog("KMZ was NOT CREATED!")
                raise Exception("KMZ was NOT CREATED!")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_Irs1c_1d()
            ingester.debug = 0
            exitCode = ingester.starts(sys.argv)
            #
            ingester.makeConversionReport("ingester_Irs1c_conversion_report", ".")

            sys.exit(exitCode)
        else:
            print(
                "syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]"
            )
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
