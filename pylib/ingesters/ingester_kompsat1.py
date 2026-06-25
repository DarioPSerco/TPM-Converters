# Serco 02/2023 Lavaux Gilles, Lily Grogan
#
# 06/02/2023: V: 0.1
#
#
#
#
import os
import sys
import traceback
from io import StringIO

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP, product_kompsat1
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts.namingConvention_hightres import (
    NamingConvention_HightRes,
)
import eoSip_converter.xmlHelper as xmlHelper


# minimum config version that can be used
MIN_CONFIG_VERSION = 1.0
VERSION = "Kompsat-1 converter V:1.0.0"
#
# ref SIP name, used to check reconstructed filename, length
REF_NAME = "K01_OPER_EOC_PAN_1P_20000306T100700_N43-507_E008-502_02_v0100.SIP.ZIP"
# ref EO name, used to check reconstructed filename, length
REF_EO_NAME = "K01_OPER_PAN_1P_20000306T100700_N43-507_E008-502_01.ZIP"


class ingester_kompsat1(ingester.Ingester):

    #
    #
    #
    def getVersionImpl(self):
        return VERSION

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
        # alter href mapping
        processInfo.destProduct.metadata.alterMetadataMaping(
            "href", metadata.METADATA_FULL_PACKAGENAME
        )
        #
        # build piece list
        # just the src .tar.gz product, converted as zip
        #
        n = 0
        newContentList = []
        piece = product_EOSIP.EoPiece(processInfo.srcProduct.origName)
        piece.alias = processInfo.srcProduct.origName
        piece.localPath = processInfo.srcProduct.path
        newContentList.append(piece.alias)
        processInfo.destProduct.addPiece(piece)
        processInfo.srcProduct.contentList = newContentList
        # print("*********content list:%s" % contentList)
        # os._exit(1)

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        self.alterReportXml(processInfo)

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        # self.makeKmz(self, processInfo, metadata.METADATA_BOUNDING_BOX)
        pass

    #
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog(" alterReportXml: product report parsed")
        print(" alterReportXml: product report parsed")

        # add namespace: <eop:operationalMode codeSpace="urn:esa:eop:KOMPSAT:EOC:operationalMode
        aNode = helper.getFirstNodeByPath(
            None,
            "procedure/EarthObservationEquipment/sensor/Sensor/operationalMode",
            None,
        )
        helper.setNodeAttributeText(
            aNode, "codeSpace", "urn:esa:eop:KOMPSAT:EOC:operationalMode"
        )

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
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # force setEoExtension to ZIP. Because we use SRC_PRODUCT_AS_DIR to use several files as input, and we want a .SIP.ZIP package.
        processInfo.destProduct.setEoExtension(
            definitions_EoSip.getDefinition("PACKAGE_EXT")
        )
        # test default in ingester
        self.buildEoNamesDefault(processInfo, namingConvention)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(REF_NAME):
            print(("ref name:%s" % REF_NAME))
            print(("EoSip name:%s" % aName))
            raise Exception(
                "EoSip name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME))
            )
        if aName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("SipProductName incomplete:%s" % aName)

        anEoName = processInfo.destProduct.getEoProductName()

        # print("******************* eo name: %s" % anEoName)
        # os._exit(1)

        if anEoName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("EoProductName incomplete:%s" % aName)

    #
    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. No need to use his parent for the product path
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace("\\", "/")
        product = product_kompsat1.Product_Kompsat1(processInfo.srcPath)
        product.setDebug(1)
        processInfo.srcProduct = product

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        # eosipP.setUsePythonZipLib(False)
        eosipP.sourceProductPath = processInfo.srcPath
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE_30)
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        namingConventionSip.setDebug(1)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEo = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        namingConventionSip.setDebug(1)
        eosipP.setNamingConventionEoInstance(namingConventionEo)

        # processInfo.destProduct.setNamingConventionSipInstance(namingConventionSip)
        # processInfo.destProduct.setNamingConventionEoInstance(namingConventionEo)

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

        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")
        processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met, processInfo)

        # met.setMetadataPair(metadata.METADATA_GENERATION_TIME, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        # use method in base converter
        self.getGenerationTime(met)

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
        # return
        # copy eoSip in first path; make links in other paths:

        # now done before in base_ingester.doOneProduct
        # self.outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)

        #
        productPath = None
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
    def makeKmz_NOT_USED(self, processInfo):
        if not self.test_dont_write:
            from eoSip_converter import kmz

            processInfo.ingester.logger.info("WILL CREATE KMZ")

            outPath = "%s/kmz" % processInfo.ingester.LOG_FOLDER
            if not os.path.exists(outPath):
                self.logger.info("  will make kmz folder:%s" % outPath)
                os.makedirs(outPath)

            kmzPath = kmz.eosipToKmz.makeKmlFromEoSip_new(False, outPath, processInfo)
            print(" KMZ created at path:%s" % kmzPath)
            if kmzPath is not None:
                processInfo.addLog("KMZ created at path:%s" % kmzPath)
            else:
                processInfo.addLog("KMZ was NOT CREATED!")
                raise Exception("KMZ was NOT CREATED!")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_kompsat1()

            commandLineInfo = ingester.getCommandLineInfo()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Kompsat 1 conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            reportName = "Kompsat1_conversion_report.txt"
            fd = open(reportName, "w")
            fd.write(out.getvalue())
            fd.flush()
            fd.close()
            print(("conversion report written well:%s" % reportName))

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
