#
# This is a Beijing-1 / NigeriaSat-1 / UK-DMC-1 (SLIM6) ingester class.
#
# For Esa/lite dissemination project
#
# JSON (EOPF-EOS) converter, built on the same structure as the other
# mission converters in pylib/converters/*_json.
#
import os
import sys
import traceback

from eoSip_converter.base import processInfo as pinfo
from eoSip_converter.base import ingester
from eoSip_converter.esaProducts import product_EOSIP
from eoSip_converter.esaProducts import definitions_EoSip, metadata
from eoSip_converter.esaProducts.namingConvention_hightres import NamingConvention_HightRes

from dmc_json import __version__, product_dmc, json_emitter, name_registry

# minimum config version that can be use
MIN_CONFIG_VERSION = 1.0
VERSION = f"Beijing-1 / NigeriaSat-1 / UK-DMC-1 converter V:{__version__}"

# EOPF-EOS package name reference, spec section 2.2:
# <MMM>_<CCCC>_<TTTTTTTTTT>_<yyyymmddThhmmss>_<YYYYMMDDTHHMMSS>_<bbvv>
# (<bbvv> counter from name_registry)
# <TTTTTTTTTT> is the 10-character type code (L1_OPT_MS_), then the '_' separator.
EO_REF_NAME = 'UK1_OPER_L1_OPT_MS__20170424T134911_20170424T135111_0001'


class ingester_dmc(ingester.Ingester):

    # JSON converter: disable all eoSIP/XML output at the base-ingester level.
    # The cfg also sets TEST_JUST_EXTRACT_METADATA=True; this is the defensive default.
    test_just_extract_metadata = True

    #
    #
    #
    def getVersionImpl(self):
        return VERSION

    #
    #
    #
    def afterStarting(self, **kargs):
        self.test_just_extract_metadata = True

    #
    # Build and write the JSON metadata manifest (replaces XML/eoSIP output).
    # No overview is written here: the packager re-encodes the quicklook JPEG
    # named by the .dim as previews/overviews/<EO name>.PNG
    # (product_dmc.extractToPath has already checked that it exists).
    #
    def _emit_json(self, processInfo):
        eoName = processInfo.destProduct.getEoProductName()
        outDir = self.outputProductResolvedPaths[0] if self.outputProductResolvedPaths else processInfo.workFolder
        os.makedirs(outDir, exist_ok=True)
        jsonPath = json_emitter.emit(
            processInfo.destProduct.metadata,
            processInfo.srcProduct,
            eoName,
            outDir,
            native_product_name=os.path.basename(processInfo.srcPath),
        )
        processInfo.addLog("  JSON metadata manifest written: %s" % jsonPath)
        self.logger.info("  JSON metadata manifest written: %s" % jsonPath)
        return jsonPath

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
    # JSON-only mode: report/output stages downstream are disabled, so emit
    # the JSON manifest here (this hook still runs in extract-metadata mode).
    #
    def beforeReportsDone(self, processInfo):
        self._emit_json(processInfo)

    #
    # called after having done the various reports
    # JSON-only mode: no XML reports and no eoSIP piece list are produced.
    #
    def afterReportsDone(self, processInfo):
        pass

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self, processInfo):
        pass

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):
        # force setEoExtension to ZIP: the delivery is a .ZIP package.
        processInfo.destProduct.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))
        # <bbvv>: the counter that keeps the variants of one acquisition apart
        name_registry.assign_version(processInfo.destProduct.metadata,
                                     processInfo.srcProduct.dataset_name,
                                     self.OUTPUT_EO_PATTERN)
        #
        self.buildEoNamesDefault(processInfo, namingConvention)

        # JSON-only mode: only the EO product name is used (it names the
        # package, the manifest and the overview), so only it is checked.
        anEoName = processInfo.destProduct.getEoProductName()
        if len(anEoName) != len(EO_REF_NAME):
            print(("Ref EO name:%s" % EO_REF_NAME))
            print(("EO name    :%s" % anEoName))
            raise Exception("EO name has incorrect length:%s VS %s" % (len(anEoName), len(EO_REF_NAME)))

        if anEoName.find('@') >= 0 or anEoName.find('#') >= 0:
            raise Exception("EoProductName incomplet:%s" % anEoName)

    #
    # Override
    # this is the first function called by the base ingester
    #
    # as input we have the DIMAP header <dataset>.dim in the unzipped delivery
    # folder; the folder is the native product
    #
    def createSourceProduct(self, processInfo):
        processInfo.srcPath = processInfo.srcPath.replace('\\', '/')
        product = product_dmc.Product_DMC(processInfo.srcPath)
        if self.test_mode:
            product.setDebug(1)
        processInfo.srcProduct = product
        product.processInfo = processInfo

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        eosipP = product_EOSIP.Product_EOSIP()
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
        eosipP.setSipInfoType(product_EOSIP.EXTENDED_SIP_INFO_TYPE)

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

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        # fill metadata object
        processInfo.srcProduct.extractMetadata(met, processInfo)

        # use method in base converter
        self.getGenerationTime(met)

        self.keepInfo('level', met.getMetadataValue(product_dmc.PROCESSED_LEVEL_CODE))
        self.keepInfo('typecode', met.getMetadataValue(metadata.METADATA_TYPECODE))
        self.keepInfo('platform', met.getMetadataValue(metadata.METADATA_PLATFORM))

    #
    #
    #
    def makeBrowseChoiceBlock(self, processInfo, metadata):
        pass

    #
    # Override
    # JSON-only mode: no eoSIP browse is produced; the packager writes the
    # overview PNG.
    #
    def makeBrowses(self, processInfo: pinfo.processInfo, ratio=50):
        pass

    #
    # Override
    #
    # JSON-only mode: emit the JSON metadata manifest instead of an eoSIP
    # .SIP.ZIP package. No XML and no ZIP packaging is written. (Not reached
    # in normal JSON mode - output is gated off by TEST_JUST_EXTRACT_METADATA
    # and emission happens in beforeReportsDone. Kept JSON-only so no eoSIP
    # packaging code remains.)
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        self.logger.info("  output_eoSip (JSON): basePath=%s" % (basePath))
        return self._emit_json(processInfo)


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            ingester = ingester_dmc()

            ingester.DEBUG = 1
            exitCode = ingester.starts(sys.argv)

            ingester.makeConversionReport("Beijing-1 / NigeriaSat-1 / UK-DMC-1 conversion report")

            sys.exit(exitCode)

        else:
            print("syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]")
            sys.exit(1)

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
