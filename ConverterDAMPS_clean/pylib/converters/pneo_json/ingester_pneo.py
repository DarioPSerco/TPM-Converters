#
# This is a TEMPLATE ingester class. 
#
# For Esa/lite dissemination project
#
# Serco 02/2015 Lavaux Gilles
#
# 03/03/2015: V: 0.1
#
# TODO: add .SIP.ZIp in <ows:ServiceReference xlink:href="PH1_OPER_HIR_PMS_3__20130819T175900_N39-000_W105-000_0101">
# - add processing date
# - add version =   <Processing_Information> <Production_Facility> <SOFTWARE version="6">IMF</SOFTWARE>
# - remove leading _ from operational mode
#
import sys
import traceback
from io import StringIO
import os

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

from pneo_json import __version__, product_pneo, json_emitter

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = f"PNEO converter V:{__version__}"
REF_NAME = 'PLN_OPER_NEO_P_S_2__20210503T104900_N41-376_E002-153_01_v1021.SIP.ZIP'


class ingester_pneo(ingester.Ingester):

    # JSON converter: disable all eoSIP/XML output at the base-ingester level.
    # The cfg also sets TEST_JUST_EXTRACT_METADATA=True; this is the defensive default.
    test_just_extract_metadata = True

    def getVersionImpl(self):
        return VERSION

    def afterStarting(self, **kargs):
        self.test_just_extract_metadata = True

    # Build and write the JSON metadata manifest (replaces XML/eoSIP output).
    def _emit_json(self, processInfo):
        eoName = processInfo.destProduct.getEoProductName()
        outDir = self.outputProductResolvedPaths[0] if self.outputProductResolvedPaths else processInfo.workFolder
        os.makedirs(outDir, exist_ok=True)
        jsonPath = json_emitter.emit(
            processInfo.destProduct.metadata,
            processInfo.srcProduct,
            eoName,
            outDir,
            native_product_name=processInfo.srcProduct.origName,
        )
        processInfo.addLog("  JSON metadata manifest written: %s" % jsonPath)
        self.logger.info("  JSON metadata manifest written: %s" % jsonPath)
        return jsonPath

    # config version is like: name_floatVersion
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    # prepare metadata from a browse report generation
    def prepareBrowseMetadata(self, processInfo):
        pass

    # called before doing the various reports
    # JSON-only mode: report/output stages downstream are disabled, so emit
    # the JSON manifest here (this hook still runs in extract-metadata mode).
    # XML-report-only steps (href remap, angle unit) are dropped; the
    # operationalMode trailing-underscore strip is kept - it feeds the JSON.
    # NOTE the len-3 guard lets 'MS_' through with its padding underscore
    # (suspected pipeline bug, kept unchanged - see PLEIADES_PNEO_DEV.md).
    def beforeReportsDone(self, processInfo):
        # remove leading _ from
        sensor_mode = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        tmp = sensor_mode
        while sensor_mode.endswith('_'):
            if len(sensor_mode) == 3:
                break
            sensor_mode = sensor_mode[0:-1]
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@ sensor mode changed from '%s' to '%s'" % (tmp, sensor_mode))

        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, sensor_mode)

        self._emit_json(processInfo)

    # called after having done the various reports
    # JSON-only mode: no XML reports and no eoSIP piece list are produced.
    def afterReportsDone(self, processInfo):
        pass

    # called at the end of the doOneProduct, before the index/shopcart creation
    def afterProductDone(self, processInfo):
        pass

    def buildEoNames(self, processInfo, namingConvention=None):
        # test default in ingester
        self.buildEoNamesDefault(processInfo, namingConvention)

        # Ensure the platform ID doesn't make its way into identifiers/filenames
        # etc. which must start with 'PLN'
        if processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID) != 'N':
            sipProductName = 'PLN' + processInfo.destProduct.sipProductName[3:]
            sipPackageName = 'PLN' + processInfo.destProduct.sipPackageName[3:]
            eoProductName = 'PLN' + processInfo.destProduct.eoProductName[3:]
            eoPackageName = 'PLN' + processInfo.destProduct.eoPackageName[3:]
            identifier = 'PLN' + processInfo.destProduct.identifier[3:]

            processInfo.destProduct.identifier = identifier
            processInfo.destProduct.eoProductName = eoProductName
            processInfo.destProduct.eoPackageName = eoPackageName

            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_PRODUCTNAME, eoProductName)
            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, identifier)
            processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_FULL_PRODUCTNAME, eoPackageName)

        file_counter = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_FILECOUNTER)
        product_version = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SIP_VERSION)
        product_version_and_counter = f"{product_version}{file_counter}"
        processInfo.destProduct.sipProductName = f"{processInfo.destProduct.eoProductName}_v{product_version_and_counter}"
        processInfo.destProduct.sipPackageName = f"{processInfo.destProduct.sipProductName}.SIP.ZIP"

        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_PACKAGENAME, processInfo.destProduct.sipProductName)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_FULL_PACKAGENAME, processInfo.destProduct.sipPackageName)

        processInfo.destProduct.identifier = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_PACKAGENAME)
        processInfo.destProduct.metadata.setMetadataPair(metadata.METADATA_IDENTIFIER, processInfo.destProduct.identifier)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(REF_NAME):
            print("ref name:%s" % REF_NAME)
            print("EoSip name:%s" % aName)
            raise Exception("EoSip name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME)))
        if aName.find('@') >= 0 or aName.find('#') > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the manifest path. Need to use his parent for the product path
    def createSourceProduct(self, processInfo):
        global debug, logger
        processInfo.srcPath = processInfo.srcPath.replace('\\', os.sep)
        product = product_pneo.Product_Pneo(processInfo.srcPath)
        if self.test_mode:
            product.setDebug(1)
        processInfo.srcProduct = product
        product.processInfo = processInfo

    # Override
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        # use wrapped zip if size ~ 2gb
        aSize = processInfo.srcProduct.getSize()

        # don't want an Eosip > 2gb done using python zip lib
        if aSize > 1.9 * 1024 ** 3:
            msg = " ## zip: will use wrapped library because size >=1.9 gb: %s" % aSize
            print(msg)
            processInfo.addLog(msg)
            eosipP.setUsePythonZipLib(False)
        else:
            msg = " ## zip: will use python library because size <1.9 gb: %s" % aSize
            processInfo.addLog(msg)

        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)

        namingConventionEoInstance = NamingConvention_HightRes(self.OUTPUT_EO_PATTERN)
        eosipP.setNamingConventionEoInstance(namingConventionEoInstance)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionEoInstance)

        self.logger.info(" Eo-Sip product created")
        processInfo.addLog(" Eo-Sip product created")

    # Override
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" verifying product:%s" % (processInfo.srcPath))
        self.logger.info(" verifying product")

    # Override
    def prepareProducts(self, processInfo):
        processInfo.addLog(" prepare product in:%s" % (processInfo.workFolder))
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(processInfo.workFolder, processInfo.test_dont_extract)

        self.stretcherAppExe = self.ressourcesProvider.getRessourcePath("stretchAppExe")
        processInfo.srcProduct.stretcherAppExe = self.stretcherAppExe

        processInfo.addLog("  extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

    # Override
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # met.setMetadataPair(metadata.METADATA_GENERATION_TIME, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        # use method in base converter
        self.getGenerationTime(met)

        # keep some info
        # pleiade or not
        if processInfo.srcProduct.isPneo:
            # if processInfo.srcProduct.isSpot6:
            #    processInfo.addInfo("SPOT6", processInfo.srcProduct.origName)
            # elif processInfo.srcProduct.isSpot7:
            #    processInfo.addInfo("SPOT7", processInfo.srcProduct.origName)
            pass
        else:
            raise Exception("is not a pleiades-neo product")

        # number of preview
        numPreview = len(processInfo.srcProduct.previewContentName)
        processInfo.addInfo(processInfo.srcProduct.origName, "number of preview:%s" % numPreview)

        if self.debug != 0:
            print("metadata dump:\n%s" % met.dump())

    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    # Override
    # JSON-only mode: no browse image is produced.
    def makeBrowses(self, processInfo, ratio=50):
        pass

    # Override
    #
    # JSON-only mode: emit the JSON metadata manifest instead of an eoSIP
    # .SIP.ZIP package. No XML and no ZIP packaging is written. (Not reached
    # in normal JSON mode - output is gated off by TEST_JUST_EXTRACT_METADATA
    # and emission happens in beforeReportsDone. Kept JSON-only so no eoSIP
    # packaging code remains.)
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip (JSON): basePath=%s" % (basePath))
        return self._emit_json(processInfo)


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_pneo()

            exitCode = ingester.starts(sys.argv)

            ingester.makeConversionReport("Pneo conversion report")

            sys.exit(exitCode)

        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)