#
# This is a Planetscope ingester class. 
#
# For Esa/lite dissemination project
#
# Serco 06/2021 Lavaux Gilles
#

import inspect
import os
import sys
import traceback
from io import StringIO
from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes
import eoSip_converter.xmlHelper as xmlHelper

from planetscope import __version__, product_planetscope

VERSION = f"PlanetScope converter V:{__version__}"

MIN_CONFIG_VERSION = 1.0

SIP_REF_NAME = 'PSC_OPER_PS2_AN3_3B_20200415T105622_N49-507_E008-502_4140_v0100.SIP.ZIP'
EO_REF_NAME = 'PSC_OPER_PS2_AN3_3B_20200415T105622_N49-507_E008-502_4140'


class ingester_planetscope(ingester.Ingester):

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
        processInfo.destProduct.metadata.alterMetadataMaping('href', metadata.METADATA_FULL_PACKAGENAME)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, '1')

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        # alter MD.XML
        self.alterReportXml(processInfo)

        n = 0
        newContentList = []
        for path in processInfo.srcProduct.contentList:
            print(" @@@@@ check contentList[%s]:%s" % (n, path))
            piece = product_EOSIP.EoPiece(path)
            piece.alias = path
            piece.localPath = "%s/%s" % (processInfo.srcProduct.EO_FOLDER, path)
            newContentList.append(piece.alias)
            processInfo.destProduct.addPiece(piece)
            n += 1

        n = 0
        determined_typecode = processInfo.srcProduct.determineTypeCode()
        EO_FOLDER = processInfo.srcProduct.EO_FOLDER
        EO_FOLDER = EO_FOLDER.replace('\\' if os.sep == '/' else '/', os.sep)

        is_new_native = True if processInfo.srcProduct.old_product_type_from_obsolete_native() is None else False
        if is_new_native:
            REQD_FOLDER_CONTENTS = product_planetscope.TYPECODE_REQD_FOLDER_CONTENTS[determined_typecode]
        else:
            REQD_FOLDER_CONTENTS = product_planetscope.OBSOLETE_TO_NEW_TYPECODE_REQS[determined_typecode]['assets']

        for root, dirs, files in os.walk(EO_FOLDER, topdown=False):
            root = root.replace('/' if os.sep == '\\' else '\\', os.sep)
            dirs = [d.replace('/' if os.sep == '\\' else '\\', os.sep) for d in dirs]
            files = [f.replace('/' if os.sep == '\\' else '\\', os.sep) for f in files]
            for name in files:
                # Take all files in root directory but be selective about assets that will be zipped up in EO component
                # of EOSIP
                if root != EO_FOLDER:
                    # If it is a new-style native product, take only select assets, otherwise (old-style) take
                    # everything
                    folder_name = os.path.basename(root)
                    if folder_name not in REQD_FOLDER_CONTENTS and REQD_FOLDER_CONTENTS != '*':
                        continue
                aPath = relPath = os.path.join(root, name)
                relPath = os.path.join(root, name)[len(processInfo.srcProduct.EO_FOLDER) + 1:]
                print("   content[%s] EO_FOLDER relative path:%s" % (n, relPath))

                piece = product_EOSIP.EoPiece(relPath)
                piece.alias = relPath
                piece.localPath = aPath
                newContentList.append(piece.alias)
                processInfo.destProduct.addPiece(piece)

        processInfo.srcProduct.contentList = newContentList

        # Produce footprint plot
        from pathlib import Path
        from eoSip_converter.utils.coordinates import GeodeticCoordinate, plot_eo_outline

        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()

        footprint_xml_tree = [
            'featureOfInterest', 'Footprint', 'multiExtentOf', 'MultiSurface',
            'surfaceMember', 'Polygon', 'exterior', 'LinearRing', 'posList'
        ]
        scene_center_xml_tree = ['featureOfInterest', 'Footprint', 'centerOf', 'Point', 'pos']
        md_props_xml_tree = ['metaDataProperty', 'EarthObservationMetaData', 'vendorSpecific', 'SpecificInformation']

        footprint = helper.getFirstNodeByPath(None, '/'.join(footprint_xml_tree), None).firstChild.data
        scene_center = helper.getFirstNodeByPath(None, '/'.join(scene_center_xml_tree), None).firstChild.data

        helper.getNodeByPath(None, '/'.join(md_props_xml_tree), None, md_props := [])
        bbox_md_prop = list(filter(lambda node: helper.getFirstNodeByPath(node, 'localAttribute').firstChild.data == 'boundingBox', md_props))[0]
        bbox = helper.getFirstNodeByPath(bbox_md_prop, 'localValue').firstChild.data

        scene_center = GeodeticCoordinate(*[float(_) for _ in scene_center.split()])
        footprint_coords = [float(c.strip()) for c in footprint.split()]
        footprint_coords = [GeodeticCoordinate(footprint_coords[i * 2], footprint_coords[i * 2 + 1]) for i in range(len(footprint_coords) // 2)]
        bbox_coords = [float(_) for _ in (bbox.split() if bbox is not None else [])]
        bbox_coords = [GeodeticCoordinate(bbox_coords[i * 2], bbox_coords[i * 2 + 1]) for i in range(len(bbox_coords) // 2)]
        bbox_coords.append(bbox_coords[0])

        try:
            azimuth = processInfo.srcProduct.metadata.getMetadataValue('azimuthAngle')
            azimuth = float(azimuth) if azimuth else None

            if azimuth is None:
                logger.warning("Spacecraft azimuth angle not available for footprint plot")

            fig, ax = plot_eo_outline(scene_center, footprint_coords, bbox_coords, spacecraft_bearing=azimuth)
            footprint_plot_name = f'{processInfo.destProduct.eoProductName}_footprint.pdf'
            fig.suptitle(f"{processInfo.destProduct.eoProductName} Footprint", fontsize=10)
            fig.savefig(Path(processInfo.srcProduct.EXTRACTED_PATH) / footprint_plot_name, dpi=300)
        except Exception as err:
            processInfo.logger.error(f"Could not create footprint plot pdf due to: {err.__class__.__name__ + ': ' + err.args[0]}")


    #
    # called at the end of the doOneProduct
    #
    def afterProductDone(self, processInfo):

        self.keepInfo('orbit_direction', processInfo.srcProduct.metadata.getMetadataValue('orbit_direction'))
        self.keepInfo('level', processInfo.srcProduct.metadata.getMetadataValue('level'))
        self.keepInfo(processInfo.srcProduct.productFolderName,
                      "footprint_json_num-pairs= %s" % processInfo.srcProduct.metadata.getMetadataValue(
                          'footprint_json_num-pairs'))

    #
    #
    #
    def alterReportXml(self, processInfo):
        helper = xmlHelper.XmlHelper()
        helper.setData(processInfo.destProduct.productReport)
        helper.parseData()
        processInfo.addLog("- alterReportXml: product report parsed")
        if self.debug != 0:
            print(" alterReportXml: product report parsed")

        # add namespace in sensor operational mode:
        codeSpaceOpMode = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_CODESPACE_SENSOR_OPERATIONAL_MODE)
        if 1 == 1 or self.debug != 0:
            print("alterReportXml: codeSpaceOpMode='%s'" % codeSpaceOpMode)
        if not processInfo.destProduct.testValueIsDefined(codeSpaceOpMode):
            raise Exception("codeSpaceOpMode is not defined")
        aNode = helper.getFirstNodeByPath(None, 'procedure/EarthObservationEquipment/sensor/Sensor/operationalMode',
                                          None)
        helper.setNodeAttributeText(aNode, 'codeSpace', codeSpaceOpMode)

        helper2 = xmlHelper.XmlHelper()
        helper2.setData(helper.prettyPrint())
        helper2.parseData()
        formattedXml = helper2.prettyPrintAll()
        if self.debug != 0:
            print(" new XML: %s " % formattedXml)
        with open(processInfo.destProduct.reportFullPath, 'w') as fd:
            fd.write(formattedXml if isinstance(formattedXml, str) else formattedXml.decode())

        processInfo.destProduct.productReport = formattedXml
        processInfo.addLog(
            "alterReportXml: product report changed at path:'%s'" % processInfo.destProduct.reportFullPath)
        # set AM time if needed
        processInfo.destProduct.setFileAMtime(processInfo.destProduct.reportFullPath)

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # force setEoExtension to ZIP. Because we use SRC_PRODUCT_AS_DIR to use several files as input, and we want a .SIP.ZIP package.
        processInfo.destProduct.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))
        #
        self.buildEoNamesDefault(processInfo, namingConvention)

    #
    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = product_planetscope.Product_Planetscope(processInfo.srcPath)
        if self.test_mode:
            product.setDebug(1)
        processInfo.srcProduct = product
        product.processInfo = processInfo

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        """# use wrapped zip if size ~ 2gb
        aSize = processInfo.srcProduct.getSize()
        # d'ont want an Eosip > 2gb done using python zip lib
        if aSize > 1900*1024*1024:
            processInfo.addLog(" ## zip: will use wrapped library because size >=1.9 gb: %s" % (aSize))
            eosipP.setUsePythonZipLib(False)
        else:
            processInfo.addLog(" ## zip: will use python library because size <1.9 gb: %s" % (aSize))
        #"""
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionEoInstance(namingConventionSip)

        namingConventionEo = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        eosipP.setNamingConventionEoInstance(namingConventionEo)
        processInfo.destProduct.setNamingConventionEoInstance(namingConventionEo)

        # long sip file
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE_30)

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
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)

        self.stretcherApp = self.ressourcesProvider.getRessourcePath('stretchAppExe')
        processInfo.srcProduct.stretcherApp = self.stretcherApp

        processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met, processInfo)

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
        # copy eoSip in first path
        # make links in other paths
        productPath = None
        if len(self.outputProductResolvedPaths) == 0:
            raise Exception("no product resolved path")

        # output in first path
        firstPath = self.outputProductResolvedPaths[0]
        processInfo.addLog("  Eo-Sip product writen in folder:%s\n" % (firstPath))
        self.logger.info("  Eo-Sip product writen in folder:%s\n" % (firstPath))

        # FIXME: THIS IS WHERE WE NEED TO INSERT LOGIC TO FILTER NON PRODUCT-TYPECODE FOLDERS OUT OF ZIPPED RAW
        #  PRODUCT WITHIN EO-SIP FINAL PRODUCT (product_EOSIP.writeToFolder method)
        productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
        processInfo.addIngesterLog("  write done:%s" % processInfo.destProduct.path, 'PROGRESS')

        # output link in other path
        i = 0
        for item in self.outputProductResolvedPaths:
            if i > 0:
                otherPath = "%s" % (item)
                self.logger.info("  eoSip product tree path[%d] is:%s" % (i, item))
                processInfo.destProduct.writeToFolder(basePath, overwrite)
                processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                self.logger.info("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
            i = i + 1

        self.logger.info("  done")
        return productPath

    #
    # create a kmz, use the bounding box
    # created in the log folder
    #
    def makeKmz__NOT_USED(self, processInfo):
        if not self.test_dont_write:
            processInfo.ingester.logger.info("WILL CREATE KMZ")
            from eoSip_converter import kmz
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


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_planetscope()

            commandLineInfo = ingester.getCommandLineInfo()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            out = StringIO()
            print(commandLineInfo, file=out)
            print("### Start of report\n", file=out)
            aReportMaker = reportMaker.ReportMaker()
            report = aReportMaker.makeReport(ingester)
            print("Planetscope conversion report", file=out)
            print(report, file=out)
            print("### End of report", file=out)
            # print out.getvalue()
            reportName = "Planetscope_conversion_report.txt"
            fd = open(reportName, 'w')
            fd.write(out.getvalue())
            fd.flush()
            fd.close()
            print("conversion report written well:%s" % reportName)

            sys.exit(exitCode)

        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)