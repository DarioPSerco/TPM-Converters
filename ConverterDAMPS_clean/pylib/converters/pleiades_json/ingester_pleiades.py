# Ingester class for the Pleiades mission
import os
import sys
import traceback
from io import StringIO

from eoSip_converter.base import ingester, reportMaker
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

from pleiades_json import __version__, product_pleiades, json_emitter

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = f"Pleiades converter V:{__version__}"
REF_NAME = 'PL1_OPER_HIR_MS__1A_20001122T112233_N20-882_E095-939_0001.SIP.ZIP'


class ingester_pleiades(ingester.Ingester):

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
    def beforeReportsDone(self, processInfo):
        # remove leading _ from
        sensor_mode = processInfo.destProduct.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        tmp = sensor_mode
        while sensor_mode.endswith('_'):
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
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = product_pleiades.Product_Pleiades(processInfo.srcPath)
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
        # d'ont want an Eosip > 2gb done using python zip lib
        if aSize > 1900 * 1024 * 1024:
            processInfo.addLog(" ## zip: will use wrapped library because size >=1.9 gb: %s" % (aSize))
            eosipP.setUsePythonZipLib(False)
        else:
            processInfo.addLog(" ## zip: will use python library because size <1.9 gb: %s" % (aSize))
        #
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionEoInstance(namingConventionSip)

        processInfo.destProduct.setNamingConventionEoInstance(namingConventionSip)

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
        if processInfo.srcProduct.isPleiades:
            # if processInfo.srcProduct.isSpot6:
            #    processInfo.addInfo("SPOT6", processInfo.srcProduct.origName)
            # elif processInfo.srcProduct.isSpot7:
            #    processInfo.addInfo("SPOT7", processInfo.srcProduct.origName)
            pass
        else:
            raise Exception("is not a pleiades product")

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
            ingester = ingester_pleiades()

            # ingester.DEBUG=1
            exitCode = ingester.starts(sys.argv)

            ingester.makeConversionReport("Pleiades conversion report")

            sys.exit(exitCode)

        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)