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
import zipfile
from io import StringIO

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP, product_radarsat
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts.namingConvention_hightres import (
    NamingConvention_HightRes,
)
import eoSip_converter.xmlHelper as xmlHelper

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = "Radarsat converter V:1.0.0"
SIP_REF_NAME = "RS2_OPER_SAR_FW_SLC_20170912T104523_N31-049_E110-329_0000_v0100.SIP.ZIP"
EO_REF_NAME = "RS2_OPER_SAR_FW_SLC_20170912T104523_N31-049_E110-329_0000"

# test: run without the WFS service, LUZ, country etc. will not be resolved
ALLOW_NO_SERVICE = True


#
#
#
class ingester_radarsat(ingester.Ingester):

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

        if processInfo.srcProduct.useBbox == False:
            processInfo.addLog("############ browse node unused !!")
            print("############ browse node unused !!")
            processInfo.destProduct.browseBlockDisabled = True

        # keep some info
        self.keepInfo("resolvedBeamMesg", processInfo.srcProduct.resolvedBeamMesg)

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):

        if 1 == 2:
            #
            # build the EO zip package. content is in srcProduct.contentList
            newContentList = []
            n = 0
            zipFilePath = "%s/%s.%s" % (
                processInfo.workFolder,
                processInfo.destProduct.eoProductName,
                processInfo.destProduct.sipPackageExtension,
            )
            zipFilePathWithPart = "%s.part" % zipFilePath
            zipf = zipfile.ZipFile(zipFilePathWithPart, mode="w", allowZip64=True)
            print(("\n\n @@@@@ EO tmp zip file is:%s" % (zipFilePath)))

            # was extracted in EO_product folder
            if 1 == 1:  # TODO: uncomment
                for name in processInfo.srcProduct.contentList:
                    eoPiecePath = "%s/%s" % (processInfo.srcProduct.folder, name)
                    print(
                        (
                                " @@@@@ add to EO contentList[%s]:%s at path %s"
                                % (n, name, eoPiecePath)
                        )
                    )
                    zipf.write(eoPiecePath, name, zipfile.ZIP_DEFLATED)
                    n += 1

            #
            zipf.close()
            # remove temporary part extension
            try:
                os.rename(zipFilePathWithPart, zipFilePath)
            except:
                processInfo.addLog(
                    ".part rename error: %s"
                    % os.listdir(os.path.dirname(zipFilePathWithPart))
                )
                raise Exception(
                    ".part rename error: %s"
                    % os.listdir(os.path.dirname(zipFilePathWithPart))
                )

            # set AM time if needed
            processInfo.destProduct.setFileAMtime(zipFilePath)

            #
            processInfo.destProduct.tmpZipSize = os.stat(zipFilePath).st_size

            if 1 == 2:  #
                # add EO zip as a piece
                piece = product_EOSIP.EoPiece(os.path.basename(zipFilePath))
                piece.alias = os.path.basename(zipFilePath)
                piece.localPath = zipFilePath
                newContentList.append(piece.alias)
                processInfo.destProduct.addPiece(piece)
                processInfo.srcProduct.contentList = newContentList
            # set tmp zip to be used as eo single file
            processInfo.srcProduct.contentList = newContentList
            newContentList.append(os.path.basename(zipFilePath))

            #
            # processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_KMZ_USE_BOOUNDINGBOX, True)
            # processInfo.addLog(" afterReportsDone: kmz will use boundingBox")

        # alter MD.XML
        self.alterReportXml(processInfo)

        # build piece list
        # source file are not in the working, folder, they are a product path
        n = 0
        newContentList = []
        for relPath in processInfo.srcProduct.contentList:
            # print(" @@@@@ check contentList[%s]:%s" % (n, relPath))
            piece = product_EOSIP.EoPiece(relPath)
            piece.alias = relPath
            eoPiecePath = "%s/%s" % (processInfo.srcProduct.folder, relPath)
            piece.localPath = eoPiecePath
            newContentList.append(piece.alias)
            processInfo.destProduct.addPiece(piece)
            n += 1
        processInfo.srcProduct.contentList = newContentList

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    # add namespace in: <eop:operationalMode
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog(" alterReportXml: product report parsed")
        if self.debug != 0:
            print(" alterReportXml: product report parsed")

        # add namespace:
        codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE
        )
        # codeSpaceOpMode=codeSpaceOpMode.replace('@OPM@', processInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE))

        if self.debug != 0:
            print(("alterReportXml: codeSpaceOpMode='%s'" % codeSpaceOpMode))
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
            print((" new XML: %s " % formattedXml))
        with open(processInfo.destProduct.reportFullPath, "w") as fd:
            fd.write(formattedXml.decode() if isinstance(formattedXml, bytes) else formattedXml)
            fd.flush()

        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

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
        if len(aName) != len(SIP_REF_NAME):
            print(("ref name:%s" % SIP_REF_NAME))
            print(("EoSip name:%s" % aName))
            raise Exception(
                "EoSip name has incorrect length:%s VS %s"
                % (len(aName), len(SIP_REF_NAME))
            )

        if aName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

        anEoName = processInfo.destProduct.getEoProductName()
        if len(anEoName) != len(EO_REF_NAME):
            print(("ref EO name:%s" % EO_REF_NAME))
            print(("EO name:%s" % anEoName))
            raise Exception(
                "EO name has incorrect length:%s VS %s"
                % (len(anEoName), len(EO_REF_NAME))
            )

        if anEoName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("EoProductName incomplet:%s" % aName)

        som = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_SENSOR_OPERATIONAL_MODE
        )
        opm = product_radarsat.operationalMode[som]
        print((" -> sensor operational mode string:%s" % opm))
        processInfo.srcProduct.metadata.setMetadataPair(
            metadata.METADATA_SENSOR_OPERATIONAL_MODE, opm
        )

    #
    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        #
        processInfo.srcPath = processInfo.srcPath.replace("\\", "/")
        product = product_radarsat.Product_Radarsat(processInfo.srcPath)

        # product.setDebug(1)
        processInfo.srcProduct = product

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.sourceProductPath = processInfo.srcPath
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE)
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEo = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        eosipP.setNamingConventionEoInstance(namingConventionEo)

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
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # use method in base converter
        self.getGenerationTime(met)

        # refine
        processInfo.srcProduct.refineMetadata(processInfo)

        # the one using bbox or not
        if processInfo.srcProduct.useBbox:
            self.keepInfo("useBbox", processInfo.srcProduct.path)
        else:
            self.keepInfo("dontUseBbox", processInfo.srcProduct.path)

        # orbit direction
        tmp = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_ORBIT_DIRECTION
        )
        self.keepInfo(tmp, processInfo.srcProduct.path)

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


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_radarsat()

            commandLineInfo = ingester.getCommandLineInfo()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Radarsat conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Radarsat_conversion_report.txt"
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
