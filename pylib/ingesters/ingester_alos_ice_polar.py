#
# This class represents an Alos Ice Polar product
#
# For Esa/lite dissemination project
#
# Serco 08/2018
# Lavaux Gilles
#
# 06/08/2018: V: 0.1
#
#
#
import sys
import traceback
from subprocess import call

import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.base import ingester
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts import metadata, browse_metadata
from eoSip_converter.esaProducts import product_EOSIP, product_alos_ice_polar
from eoSip_converter.esaProducts.namingConvention_DDOT import NamingConvention_DDOT
from xml_nodes import rep_footprint

# minumunm config version that can be used
MIN_CONFIG_VERSION = 1.0
VERSION = "Alos Ice Polar converter V:1.0.0 2018-09-19. Lavaux Gilles @ Serco"

#
GDAL_STEP_0 = "gdal_translate -of png -outsize 25% 25% @SRC @DEST1"

#
SIP_REF_NAME = "L01_RKSE_MSS_GTC_1P_19990522T101026_19990522T101041_041049_0480_1914_0001_v0100.SIP.ZIP"
EO_REF_NAME = "L01_RKSE_MSS_GTC_1P_19990522T101026_19990522T101041_041049_0480_1914_0001_v0100.ZIP"


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


#
#
#
class ingester_alos_ice_polar(ingester.Ingester):

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
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        #
        self.alterReportXml(processInfo)

    #
    # add namespace in: <eop:operationalMode "
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
        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            " alterReportXml: product report changed at path:'%s'"
            % processInfo.destProduct.reportFullPath
        )
        # set AM timne if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        #
        self.logger.info(" buildEoNames")
        processInfo.addLog(" buildEoNames")
        processInfo.destProduct.buildEoNames(namingConvention)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(SIP_REF_NAME):
            print("ref EoSip name:%s" % SIP_REF_NAME)
            print("EoSip name:%s" % aName)
            raise Exception(
                "EoSip name has incorrect length:%s VS %s"
                % (len(aName), len(SIP_REF_NAME))
            )

        if 1 == 2 and len(aName) != len(SIP_REF_NAME):
            print("ref EO name:%s" % EO_REF_NAME)
            print("EO name:%s" % aName)
            raise Exception(
                "EO name has incorrect length:%s VS %s" % (len(aName), len(EO_REF_NAME))
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
        product = product_alos_ice_polar.Product_Alos_Ice_Polar(processInfo.srcPath)
        product.setDebug(1)
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
        namingConventionSip = NamingConvention_DDOT(self.OUTPUT_SIP_PATTERN)
        processInfo.destProduct.setNamingConventionSipInstance(namingConventionSip)
        namingConventionEo = NamingConvention_DDOT(self.OUTPUT_EO_PATTERN)
        processInfo.destProduct.setNamingConventionEoInstance(namingConventionEo)
        #
        processInfo.destProduct.setSipInfoType(2.1)

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
        processInfo.addLog(
            "[ingester_alos_special.prepareProducts] Prepare product in: %s"
            % (processInfo.workFolder)
        )
        self.logger.info(" Prepare product")

        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")
        processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

        processInfo.srcProduct.extractToPath(
            processInfo.workFolder, processInfo.test_dont_extract
        )

        processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # use method in base converter
        self.getGenerationTime(met)

        # refine
        processInfo.srcProduct.refineMetadata()

    #
    #
    #
    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    #
    #
    #
    def makeBrowses(self, processInfo):
        print(" runBrowseCommands")
        processInfo.addLog("    runBrowseCommands")
        #
        # Building input/output paths.
        browseSrcPath = processInfo.srcProduct.image_path
        browseExtension = definitions_EoSip.getBrowseExtension(
            0, definitions_EoSip.getDefinition("BROWSE_PNG_EXT")
        )
        browseDestPath = "%s/%s.%s" % (
            processInfo.destProduct.folder,
            processInfo.destProduct.eoProductName,
            browseExtension,
        )
        print(
            "prepareBrowseCommands: src=%s; dest=%s" % (browseSrcPath, browseDestPath)
        )

        # convert to png
        destPathBase = browseDestPath.replace(".PNG", "_")
        command = GDAL_STEP_0.replace("@SRC", browseSrcPath)
        command1 = command.replace("@DEST1", "%s_0.png" % (destPathBase))

        command2 = "%s -transparent %s %s 0xff000000" % (
            self.stretcherAppExe,
            "%s_0.png" % (destPathBase),
            "%s_1.png" % (destPathBase),
        )

        command3 = "%s -stretch %s %s 0.01" % (
            self.stretcherAppExe,
            "%s_1.png" % (destPathBase),
            browseDestPath,
        )

        commands = "%s%s%s" % (
            writeShellCommand(command1, True),
            writeShellCommand(command2, True),
            writeShellCommand(command3, True),
        )
        commands = "%s\necho\necho\necho 'browse 2 done'" % (commands)

        commandFile = "%s/command_browse.sh" % (processInfo.workFolder)
        fd = open(commandFile, "w")
        fd.write("""#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\nset\n\n""")
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        command = "/bin/bash -f %s 2>&1 > %s/command_browse.log" % (
            commandFile,
            processInfo.workFolder,
        )
        #
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        # set AM timne if needed
        processInfo.destProduct.setFileAMtime(browseDestPath)

        # Adding browse to destination product.
        processInfo.destProduct.addSourceBrowse(browseDestPath, [])

        # create browse choice for browse metadata report
        bmet = processInfo.destProduct.browse_metadata_dict[browseDestPath]
        print(
            "###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s"
            % (bmet.toString())
        )

        reportBuilder = rep_footprint.rep_footprint()
        #
        print(
            "###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s"
            % (processInfo.destProduct.metadata.toString())
        )
        browseChoiceBlock = reportBuilder.buildMessage(
            processInfo.destProduct.metadata,
            "rep:browseReport/rep:browse/rep:footprint",
        ).strip()
        if self.debug != -1:
            print("browseChoiceBlock:%s" % (browseChoiceBlock))
        bmet.setMetadataPair(
            browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock
        )

        # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
        # if specified in configuration
        tmp = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_BROWSES_TYPE
        )
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

        # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
        tmp = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_REFERENCE_SYSTEM
        )
        if tmp != None:
            bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

        processInfo.addLog("  browse image choice created:%s" % browseChoiceBlock)

    #
    # Override
    # Extracts the PNG browse image from the native ALOS product.
    #
    def makeBrowses_UNUSED(self, processInfo, ratio=50):

        # Building input/output paths.
        browseSrcPath = processInfo.srcProduct.image_path
        browseExtension = definitions_EoSip.getBrowseExtension(
            0, definitions_EoSip.getDefinition("BROWSE_PNG_EXT")
        )
        browseDestPath = "%s/%s.%s" % (
            processInfo.destProduct.folder,
            processInfo.destProduct.eoProductName,
            browseExtension,
        )

        command = "gdal_translate -of png %s %s" % (browseSrcPath, browseDestPath)
        print("browse generation command:%s" % command)
        retval = call(command, shell=True)

        if self.debug:
            print(
                "[alos_special_product.makeBrowses] External make browse exit code: %s"
                % retval
            )

        if retval != 0:
            raise Exception(
                "[alos_special_product.makeBrowses] Error generating browse, exit code: %s"
                % retval
            )
        print(
            "[alos_special_product.makeBrowses] External make browse exit code :%s"
            % retval
        )

        # Adding browse to destination product.
        processInfo.destProduct.addSourceBrowse(browseDestPath, [])

        # Create browse choice for browse metadata report
        bmet = processInfo.destProduct.browse_metadata_dict[browseDestPath]
        print("######\n######\n%s" % dir(definitions_EoSip))

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):

        self.logger.info("  output_eoSip: basePath=%s" % (basePath))
        # copy eoSip in first path; make links in other paths:

        # now done before in base_ingester.doOneProduct
        self.outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(
            basePath, pathRules
        )

        #
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = self.outputProductResolvedPaths[0]
            processInfo.addLog("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            self.logger.info("  Eo-Sip product writen in folder:%s\n" % (firstPath))
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)

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
    exitCode = -1

    try:
        if len(sys.argv) > 1:
            ingester = ingester_alos_ice_polar()
            # ingester.debug=1
            exitCode = ingester.starts(sys.argv)

            #
            ingester.makeConversionReport("Alos-Ice-Polar_conversion_report", ".")

            sys.exit(exitCode)
        else:
            print(
                "syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]"
            )
            sys.exit(1)

    except SystemExit as e:
        sys.exit(e)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)

    sys.exit(exitCode)
