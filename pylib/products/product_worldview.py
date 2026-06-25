# -*- coding: cp1252 -*-
#
# this class represent a worldview 'block' product: based on the generated 'eoSipProductOrder_orderId.xml'
# it will parse this xml to find the block structure + metadata
# then generate 1 EoSip per block
#
#
import os
import re
import sys
import tarfile
import time
import traceback
from subprocess import call

from lxml import etree

from . import browse_metadata
import eoSip_converter.fileHelper as fileHelper
#
import eoSip_converter.imageUtil as imageUtil
from . import formatUtils
from . import metadata
from . import product_EOSIP
from . import products_EOSIP_multiple
from .browseImage import BrowseImage
from eoSip_converter.base.footprintAgregator import FootprintAgregator
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts.data.worldview2.tileBlock import TileBlock
from eoSip_converter.esaProducts.product_directory import Product_Directory
from .namingConvention_hightres import NamingConvention_HightRes
from xml_nodes import rep_footprint

NODE_ID = 'id'
NODE_NUMBLOCK = 'numBlocks'
NODE_BLOCK = 'block'
NODE_FOOTPRINT = 'footprint'
NODE_CENTER = 'center'
NODE_PATH = 'path'
#
NODE_TILE = 'tile'
NODE_TILEFOOTPRINT = 'tileFootprint'
NODE_TIF = 'tif'

# gdal commands
GDAL_STEP_0 = 'gdal_translate -b 2 -outsize 50% 50% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 3 -outsize 50% 50% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 5 -outsize 50% 50% @SRC @DEST3'
# no resize
GDAL_STEP_N0 = 'gdal_translate -b 2 @SRC @DEST1'
GDAL_STEP_N1 = 'gdal_translate -b 3 @SRC @DEST2'
GDAL_STEP_N2 = 'gdal_translate -b 5 @SRC @DEST3'

GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
# GDAL_STEP_4='gdal_translate @DEST4 -scale 0 650 -ot Byte @DEST5'
GDAL_STEP_4 = 'gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'

GM_STEP_1 = 'gm convert @SRC -transparent black @DEST'

#
MANIFEST_PATTERN = '^.*VHR1-2_Urban_Atlas_.*$'

#
ns = {'gsc': 'http://earth.esa.int/gsc',
      'gml': 'http://www.opengis.net/gml',
      'eop': 'http://earth.esa.int/eop',
      'opt': 'http://earth.esa.int/opt'}


#
#
#
def untar_progress(members):
    for member in members:
        # this will be the current file being extracted
        print(("  extracting product member name:%s" % member.name))
        yield member


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
class Product_Worldview(Product_Directory):
    xmlMapping = {metadata.METADATA_START_DATE: 'start',
                  metadata.METADATA_STOP_DATE: 'stop',
                  metadata.METADATA_CLOUD_COVERAGE: 'cloudCover',
                  metadata.METADATA_PRODUCT_VERSION: 'version',
                  # metadata.METADATA_COUNTRY:'country',
                  # metadata.METADATA_CITY:'town',
                  # metadata.METADATA_PHONE:'phone',
                  NODE_ID: 'id',
                  NODE_NUMBLOCK: 'numBlocks'
                  }

    #
    xmlMapping_XPATH = {
        #
        metadata.METADATA_RESPONSIBLE: '//gsc:responsibleOrgName',
        metadata.METADATA_START_DATE: '//gsc:opt_metadata/gml:validTime/gml:TimePeriod/gml:beginPosition',
        metadata.METADATA_STOP_DATE: '//gsc:opt_metadata/gml:validTime/gml:TimePeriod/gml:endPosition',
        metadata.METADATA_PLATFORM: '//gsc:opt_metadata/gml:using/eop:EarthObservationEquipment/eop:platform/eop:Platform/eop:shortName',
        metadata.METADATA_PLATFORM_ID: '//gsc:opt_metadata/gml:using/eop:EarthObservationEquipment/eop:platform/eop:Platform/eop:serialIdentifier',
        metadata.METADATA_INSTRUMENT: '//gsc:opt_metadata/gml:using/eop:EarthObservationEquipment/eop:instrument/eop:Instrument/eop:shortName',
        metadata.METADATA_INSTRUMENT_ID: '//gsc:opt_metadata/gml:using/eop:EarthObservationEquipment/eop:sensor/eop:Sensor/eop:sensorType',
        # metadata.METADATA_FOOTPRINT: '//gsc:opt_metadata/gml:target/eop:Footprint/gml:multiExtentOf/gml:MultiSurface/gml:surfaceMembers/gml:Polygon/gml:exterior/gml:LinearRing/gml:posList',
        metadata.METADATA_CLOUD_COVERAGE: '//gsc:opt_metadata/gml:resultOf/opt:EarthObservationResult/opt:cloudCoverPercentage',
        metadata.METADATA_CLOUD_COVERAGE_QUOTATION_MODE: '//gsc:opt_metadata/gml:resultOf/opt:EarthObservationResult/opt:cloudCoverPercentageQuotationMode',
        'SOURCE_FOOTPRINT': '//gsc:opt_metadata/gml:target/eop:Footprint/gml:multiExtentOf/gml:MultiSurface/gml:surfaceMembers/gml:Polygon/gml:exterior/gml:LinearRing/gml:posList',

    }

    #
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
        self.ORIGINAL_PATH = path
        self.helper = None
        self.metContent = None
        self.debug = 0
        # dictionnary of blocks
        self.blocks = {}
        self.eosips = {}
        self.multipleEoSip = None
        self.luzId = None
        self.town = None
        self.country = None
        self.testMode = False
        #
        self.strip = None
        print(" init class Product_Worldview")

    #
    # extract the product
    #
    def extractToPath(self, folder=None, pInfo=None):
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)

        self.EXTRACTED_PATH = "%s/EO_PRODUCT/" % folder

        if self.debug != 0:
            print(" will exttact directory product '%s' to path:%s" % (self.path, self.EXTRACTED_PATH))

        self.tmpSize = os.stat(self.path).st_size

        aFileHelper = fileHelper.FileHelper()

        if not pInfo.ingester.test_mode:
            if not os.path.exists(self.EXTRACTED_PATH):
                os.makedirs(self.EXTRACTED_PATH)
            else:
                print((" erase existing EO_PRODUCT folder:%s" % self.EXTRACTED_PATH))
                # aFileHelper.eraseFolder(self.EXTRACTED_PATH, False)

        if not pInfo.ingester.test_mode:
            if not pInfo.test_dont_extract:
                start = time.time()
                # tar = tarfile.open(self.path, 'r')
                # tar.extractall(self.EXTRACTED_PATH)
                # tar.close()
                with tarfile.open(self.path, 'r') as tarball:
                    tarball.extractall(path=self.EXTRACTED_PATH, members=untar_progress(tarball))
                duration = time.time() - start
                print((" extract done; inside:%s in %s sec" % (self.EXTRACTED_PATH, duration)))
                pInfo.addLog("extract done; inside:%s in %s sec" % (self.EXTRACTED_PATH, duration))
            else:
                print(" dont_extract flag is set!!")

        re1Prog = re.compile(MANIFEST_PATTERN)
        aList = aFileHelper.list_files(self.EXTRACTED_PATH, re1Prog, None)
        print((" worldview2 manifest found:%s" % aList))
        if len(aList) != 1:
            raise Exception("found not 1 manifest but:%s" % len(aList))

        pInfo.srcPath = aList[0]
        pInfo.path = aList[0]
        pInfo.srcProduct.path = aList[0]

        # os._exit(1)

    #
    # normally this is done in the ingester, but because we create multiples eoSips from one source we want to do it here
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None, logger=None):
        startTime = time.time()
        n = 0
        for anEosipKey in self.multipleEoSip.getEoSipKeys():
            anEosip = self.multipleEoSip.getEoSip(anEosipKey)
            print(("\n\n\n will output Eosip[%s]; key:%s; EoSip:%s" % (n, anEosipKey, anEosip.info())))

            # copy eoSip in first path
            # make links in other paths
            outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)
            if len(outputProductResolvedPaths) == 0:
                processInfo.addLog("   ERROR: no product resolved path")
                if logger != None:
                    logger.info(" ERROR: no product resolved path")
                raise Exception("no product resolved path")
            else:
                # output in first path
                firstPath = outputProductResolvedPaths[0]
                processInfo.addLog("  Eo-Sip product will be writen in folder:%s" % firstPath)
                if logger != None:
                    logger.info("  Eo-Sip product will be writen in folder:%s" % firstPath)
                productPath = anEosip.writeToFolder(firstPath, overwrite)
                processInfo.addLog("  ok, writen well")
                if logger != None:
                    logger.info(" ok, writen well")

                # output link in other path
                i = 0
                for item in outputProductResolvedPaths:
                    if i > 0:
                        otherPath = "%s" % item
                        if logger != None:
                            logger.info("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                        processInfo.addLog("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                        anEosip.writeToFolder(basePath, overwrite)
                        processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                        if logger != None:
                            logger.info("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                    i = i + 1
            n = n + 1

        duration = time.time() - startTime
        print(" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Eo-Sip product written in %s sec" % duration)
        # os._exit(0)
        processInfo.addLog(" @@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Eo-Sip product written in %s sec" % duration)

        # return only last eosip written, TODO: change it??
        return productPath

    #
    # normally this is done in the ingester, but because we create multiples eoSips from one source we want to do it here
    #
    # does:
    # - create one or several destination EoSip, depending of the output of the tileGrouper
    # - set celInfo var in Eosip: contains the list of used tiles for each EoSip
    #
    def createDestinationProducts(self, processInfo, namingConvention):
        print(" createDestinationProducts: use naming convention:%s" % namingConvention)
        processInfo.addLog("    createDestinationProducts: use naming convention:%s" % namingConvention)

        # create a 'multiple eosip' eoSip product
        self.multipleEoSip = products_EOSIP_multiple.Products_EOSIP_Multiple()
        processInfo.destProduct = self.multipleEoSip
        self.multipleEoSip.setCommonProductName(
            "%s_%s" % (products_EOSIP_multiple.DEFAULT_MULTIPLE_EOSIP_NAME, self.orderId))

        print((" ###### will create %s destination products" % len(list(self.strip.cellsMap.keys()))))
        i = 0
        for aCellKey in list(self.strip.cellsMap.keys()):
            if self.debug != 0:
                print(" doing destination product[%s] corresponding to cell:%s" % (i, aCellKey))
            processInfo.addLog("    doing destination product[%s] corresponding to cell:%s" % (i, aCellKey))
            eosipP = product_EOSIP.Product_EOSIP()

            # use SRC_PRODUCT_AS_ZIP. With sourceProductPath None and EoSip contentList + contentListPath
            eosipP.contentList.append(os.path.basename(processInfo.srcPath))
            eosipP.contentListPath[os.path.basename(processInfo.srcPath)] = processInfo.srcPath

            # eosipP.setUsePythonZipLib(False)

            # set naming convention instance
            namingConventionSip = NamingConvention_HightRes(namingConvention)
            namingConventionSip.debug = 0
            eosipP.setNamingConventionSipInstance(namingConventionSip)
            eosipP.setNamingConventionEoInstance(namingConventionSip)

            # set cells info in eoSip, contains used tiles
            eosipP.cellsInfo = self.strip.cellsMap[aCellKey]

            # set strip enveloppe
            if self.debug:
                print(("strip:%s" % self.strip.getInfo()))

            stripEnveloppe = self.strip.calculateEnveloppe()
            processInfo.stripEnveloppe = stripEnveloppe
            eosipP.stripEnveloppe = stripEnveloppe
            if self.debug:
                print(("strip enveloppe:%s" % stripEnveloppe))
            # os._exit(1)

            #
            eosipP.commonContent = self.strip.commonContent

            eosipP.setEoExtension(definitions_EoSip.getDefinition('PACKAGE_EXT'))

            self.multipleEoSip.addEoSip(i, eosipP)
            i += 1

        self.refineMetadata(processInfo)

    #
    # normally this is done in the ingester, but because we create multiples eoSips we want to do it here
    #
    # use gdal to extract band 2,3,5 from tif, strech histogram and merge all
    #
    #
    def makeBrowses(self, processInfo):
        print(" makeBrowses")
        processInfo.addLog("    makeBrowses")

        cellIndex = 0
        commandAllBlocks = ''
        fullBrowseToBeMerged = []
        for aCellKey in list(self.strip.cellsMap.keys()):
            if self.debug != 0:
                print("\n doing browse[%s] corresponding to cell:%s; tiles:%s" % (
                cellIndex, aCellKey, self.strip.cellsMap[aCellKey]))
            processInfo.addLog("    doing browse[%s] corresponding to cell:%s" % (cellIndex, aCellKey))
            anEosip = self.multipleEoSip.getEoSip(cellIndex)
            tileBlock = anEosip.tileBlock
            allImages = tileBlock.getAllTilesFilePath()
            print(("    all tiles filepath (n:%s): %s" % (len(allImages), allImages)))
            print(("    tileBlock path: %s; order:%s" % (tileBlock.path, tileBlock.order)))

            block_browse_command = ''

            n = 0
            block_command = ''
            blocksTileNames = ''
            toBeMerged = []
            for tifName in allImages:
                # MUL TIF path is at : path / order.split('_')[0:1] / order_MUL / tileFileName
                mulTifSrcPath = "%s/%s/%s_MUL/%s" % (
                tileBlock.path, '_'.join(tileBlock.order.split('_')[0:2]), tileBlock.order, tifName)
                print(("      MUL tif[%s] path: %s" % (n, mulTifSrcPath)))

                # not in all case: 50 conversion failure
                # second PAN TIF path is at : path / order.split('_')[0:1] / order_PAN / tileFileName.replace('-M2', '-P2')
                panTifSrcPath = "%s/%s/%s_PAN/%s" % (
                tileBlock.path, '_'.join(tileBlock.order.split('_')[0:2]), tileBlock.order,
                tifName.replace('-M2', '-P2'))
                print(("      PAN tif[%s] path: %s" % (n, panTifSrcPath)))
                if not os.path.exists(panTifSrcPath):
                    print(("      PAN tif[%s] at path: %s DOSN'T exists" % (n, panTifSrcPath)))
                    # look by cellid
                    aPath = "%s/%s/%s_PAN" % (
                    tileBlock.path, '_'.join(tileBlock.order.split('_')[0:2]), tileBlock.order)
                    cell = tifName.split('_')[-4]
                    print((" ####### look for cell:'' in PAN folder:%s" % (cell, aPath)))
                    for panItem in os.listdir(aPath):
                        if panItem.find("_%s_" % cell) > 0:
                            panTifSrcPath = "%s/%s" % (aPath, panItem)
                            break
                    os._exit(1)

                    # add tile tif file to eoSip contentList + contentListPath
                mulArchivePath = "%s/%s_MUL/%s" % ('_'.join(tileBlock.order.split('_')[0:2]), tileBlock.order, tifName)
                panArchivePath = "%s/%s_PAN/%s" % (
                '_'.join(tileBlock.order.split('_')[0:2]), tileBlock.order, tifName.replace('-M2', '-P2'))

                # if not in test mode
                if not processInfo.ingester.isInTestMode():
                    anEosip.addContentAndPath(mulArchivePath, mulTifSrcPath)
                    anEosip.addContentAndPath(panArchivePath, panTifSrcPath)

                #

                # tif conversion command
                # don't resize 1 pixel TIF
                resize = True
                w, h = imageUtil.get_image_size(mulTifSrcPath)
                if w == 1 or h == 1:
                    resize = False

                cellBrowseBase = "%s/browse_cellKey_%s_tile%s" % (anEosip.folder, aCellKey, n)
                if resize:
                    command = GDAL_STEP_0.replace('@SRC', mulTifSrcPath)
                    command1 = command.replace('@DEST1', "%s_b2.tif" % cellBrowseBase)
                    command2 = GDAL_STEP_1.replace('@SRC', mulTifSrcPath)
                    command2 = command2.replace('@DEST2', "%s_b3.tif" % cellBrowseBase)
                    command3 = GDAL_STEP_2.replace('@SRC', mulTifSrcPath)
                else:
                    command = GDAL_STEP_N0.replace('@SRC', mulTifSrcPath)
                    command1 = command.replace('@DEST1', "%s_b2.tif" % cellBrowseBase)
                    command2 = GDAL_STEP_N1.replace('@SRC', mulTifSrcPath)
                    command2 = command2.replace('@DEST2', "%s_b3.tif" % cellBrowseBase)
                    command3 = GDAL_STEP_N2.replace('@SRC', mulTifSrcPath)
                command3 = command3.replace('@DEST3', "%s_b5.tif" % cellBrowseBase)
                # @DEST1 @DEST2 @DEST3 -o @DEST4
                command4 = GDAL_STEP_3.replace('@DEST1', "%s_b5.tif" % cellBrowseBase).replace('@DEST2',
                                                                                               "%s_b3.tif" % cellBrowseBase).replace(
                    '@DEST3', "%s_b2.tif" % cellBrowseBase)
                command4 = command4.replace('@DEST4', "%s_bmerged.tif" % cellBrowseBase)
                command5 = GDAL_STEP_4.replace('@DEST4', "%s_bmerged.tif" % cellBrowseBase).replace('@DEST5',
                                                                                                    "%s_merged.tif" % cellBrowseBase)

                toBeMerged.append("%s_merged.tif" % cellBrowseBase)

                commands = "%s%s%s%s%s" % (
                    writeShellCommand(command1, True), writeShellCommand(command2, True),
                    writeShellCommand(command3, True),
                    writeShellCommand(command4, True), writeShellCommand(command5, True))
                commands = "%s\necho\necho\necho 'block %s tile %s done'" % (commands, cellIndex, n)

                commandFile = "%s/command_tile_%s_%s.sh" % (processInfo.workFolder, cellIndex, n)
                fd = open(commandFile, 'w')
                fd.write(commands)
                fd.close()

                block_command = "%s\n%s" % (block_command, writeShellCommand("/bin/sh -f %s" % commandFile, True))

                n += 1

            # make the block browse image: one PNG and one TIF
            tmp_command = "gdal_merge.py"
            for item in toBeMerged:
                if self.debug:
                    print("add to block_command:%s" % item)
                tmp_command = "%s %s" % (tmp_command, item)

            tmp_command = "%s -o %s/block_%s_%s.TIF" % (tmp_command, processInfo.workFolder, cellIndex, tileBlock.order)
            fullBrowseToBeMerged.append("%s/block_%s_%s.TIF" % (processInfo.workFolder, cellIndex, tileBlock.order))

            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))
            # PNG not transparent
            # tmp_command = "%s  %s/block_%s.TIF %s/block_%s.PNG" % (self.tifToPngExe, processInfo.workFolder, key, processInfo.workFolder, key)
            # new use stretcherApp
            tmp_command = "%s -transparent %s/block_%s_%s.TIF %s/block_%s_transparent_%s.png 0xff000000" % (
                self.stretcherApp, processInfo.workFolder, cellIndex, tileBlock.order, processInfo.workFolder,
                cellIndex, tileBlock.order)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            tmp_command = "%s -stretch %s/block_%s_transparent_%s.png %s/block_%s_stretch_%s.png 0.01" % (
                self.stretcherApp, processInfo.workFolder, cellIndex, tileBlock.order, processInfo.workFolder,
                cellIndex, tileBlock.order)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            tmp_command = "%s -autoBrighten %s/block_%s_stretch_%s.png %s/block_%s_final_%s.png 85" % (
                self.stretcherApp, processInfo.workFolder, cellIndex, tileBlock.order, processInfo.workFolder,
                cellIndex, tileBlock.order)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            # real browse name
            browseDestPath = "%s/%s.%s" % (anEosip.folder, anEosip.getSipProductName(),
                                           definitions_EoSip.getBrowseExtension(0, definitions_EoSip.getDefinition(
                                               'BROWSE_PNG_EXT')))
            tmp_command = "cp %s/block_%s_final_%s.png %s" % (
            processInfo.workFolder, cellIndex, tileBlock.order, browseDestPath)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            block_command = "%s\necho\necho\necho 'block_%s_%s done'" % (block_command, cellIndex, tileBlock.order)

            blocksTileNames = "%s %s/block_%s_%s.png" % (
            blocksTileNames, processInfo.workFolder, cellIndex, tileBlock.order)
            tileBlock.browseFilename = blocksTileNames
            if self.debug:
                print("############### blocksTileNames:%s" % blocksTileNames)
            commandFile = "%s/command_block%s_%s.sh" % (processInfo.workFolder, cellIndex, tileBlock.order)
            fd = open(commandFile, 'w')
            fd.write(block_command)
            fd.close()

            #
            # add to eoSip
            #
            processInfo.addLog(
                "    makeBrowse[%s]; browseSrcPath=%s; browseDestPath=%s" % (n, mulTifSrcPath, browseDestPath))

            anEosip.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  browse image[%s] created:%s" % (n, browseDestPath))

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[browseDestPath]
            print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            #
            if self.debug:
                print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug:
                print("browseChoiceBlock:%s" % browseChoiceBlock)
            bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

            # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
            # if specified in configuration
            tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
            if tmp != None:
                bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

            processInfo.addLog("  browse image[%s] choice 2created:%s" % (n, browseChoiceBlock))

            # if we want to make the strip full browse
            commandAllBlocks = "%s\n%s" % (commandAllBlocks, writeShellCommand("/bin/sh -f %s" % commandFile, True))

            # if not in test mode; add common content
            if not processInfo.ingester.isInTestMode():
                k = 0
                for item in anEosip.commonContent:
                    realPath = "%s/%s/%s" % (tileBlock.path, '_'.join(tileBlock.order.split('_')[0:2]), item)
                    anEosip.addContentAndPath("%s/%s" % ('_'.join(tileBlock.order.split('_')[0:2]), item), realPath)
                    if self.debug:
                        print("  added common content[%s]:%s=%s" % (k, item, realPath))
                    k += 1

            cellIndex += 1

        # for debug
        if 1 == 2:
            # merge block into strip browse
            fullMerge = 'gdal_merge.py'
            for blockBrowse in fullBrowseToBeMerged:
                fullMerge = "%s %s" % (fullMerge, blockBrowse)
            commandAllBlocks = "%s\n%s -o %s/strip_browse.TIF" % (commandAllBlocks, fullMerge, processInfo.workFolder)

        commandFile = "%s/command_all_blocks.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(commandAllBlocks)
        fd.close()

        # disable for debug purpose
        if not processInfo.ingester.isInTestMode():
            # launch the main make_browse script:
            command = "/bin/bash -i -f %s 2>&1 | tee %s/make_browses.stdout" % (commandFile, processInfo.workFolder)
            retval = call(command, shell=True)
            print("  external make browse exit code:%s" % retval)
            processInfo.addLog("  external make browse exit code:%s" % retval)
            if retval != 0:
                raise Exception("Error generating browse, exit coded:%s" % retval)

    #
    # run external command to generate the browse
    #
    def externalCall(self, src=None):
        pass

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # get product tiles contents:
    #
    def getTilesList(self, blockId):
        print("##### getTilesList for block:%s" % blockId)
        tilesPath = []
        for name in self.blocks["%s" % blockId].tiles:
            tilesPath.append("%s/%s" % (self.blocks["%s" % blockId].path, name))
        return tilesPath

    #
    # get product content that will be in every EoSip:
    # - everything except the TIF
    # 
    #
    def getCommonContent(self, pinfo):
        pass

    #
    # get product content that will be in every EoSip:
    # - everything except the TIF
    # 
    #
    def getCommonContent_bis(self, pinfo):
        print(" ################ @@@@@@@@@@@@@@@@@@ getCommonContent_bis ")
        # use the manifest file, that is in the parent folder of the order
        # this manifest is (normally) a  list of file, as ls -1
        #   Q: from old code seems manifest is different, is there two types ??
        print("##### self.path:%s; self.folder:%s; orderFolder:%s; order id:%s" % (
        self.path, self.folder, self.orderFolder, self.orderId))

        manifestFile = "%s/%s.MAN" % (self.orderFolder, self.orderId)
        if os.path.exists(manifestFile):
            pinfo.addLog("    get common content from manifest file:%s" % manifestFile)
            fd = open(manifestFile, "r")
            self.manifest_info = fd.read()
            fd.close()
            lines = self.manifest_info.split('\n')
        else:
            topDir = "%s/%s" % (self.orderFolder, self.orderId)
            pinfo.addLog("    get common content by looking for files inside:%s" % topDir)
            aFileHelper = fileHelper.FileHelper()
            files = aFileHelper.list_files(topDir, None, None)
            lines = []
            for item in files:
                line = item.replace(topDir, '')[1:]
                lines.append("%s/%s" % (self.orderId, line))
                print("recreated manifest:%s" % line)
            # os._exit(1)

        currentPath = ''
        self.commonFiles = []
        for line in lines:
            # normaly useless
            line = line.strip().replace('\\', '/')

            # normaly useless
            if len(line) == 0:
                if self.debug != 0:
                    print(" MANIFEST LINE length:%s" % len(line))
            else:
                if self.debug >= 0:
                    print("   MANIFEST LINE:%s" % line)
                # normaly useless
                if line.find('Directory of ') >= 0:
                    print("   MANIFEST LINE -->directory:%s" % line)

                    pos = line.find(':')
                    if pos > 0:
                        currentPath = line[pos + 1:]
                        print("  MANIFEST LINE -->currentPath:%s" % currentPath)

                elif len(line) == 0 or line.find(' ') >= 0 or line == '[.]' or line == '[..]' or line[0] == '[':
                    pass

                else:
                    fileLocalPath = "%s%s/%s" % (self.orderFolder, currentPath, line)
                    print("  MANIFEST LINE final path; fileLocalPath:%s" % fileLocalPath)
                    if not fileLocalPath.endswith('.TIF'):
                        print("  MANIFEST LINE final path not a TIF, added:%s" % fileLocalPath)
                        self.commonFiles.append(fileLocalPath)

    #
    # read metadata file
    #
    def getMetadataInfo(self):
        return

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    # get metadata: common to all blocks
    #
    def extractMetadata(self, met=None, processInfo=None):
        if self.strip is None:
            raise Exception("No strip defined, something went wrong!")

        num_added = 0
        start = time.time()
        self.rootXmlNode = etree.parse(self.path)
        for key in self.xmlMapping_XPATH:
            print(" ###################### will use xml XPATH mapping:%s using path:%s" % (
            key, self.xmlMapping_XPATH[key]))
            met.setMetadataPair(key, self.getXmlNodeValueAtPath(self.xmlMapping_XPATH[key]))

        duration = time.time() - start
        print(" ########################################  METADATA EXTACT DURATION:%s; found:%s" % (duration, num_added))

        self.orderId = self.strip.id
        met.setMetadataPair(metadata.METADATA_ORDER_ID, self.strip.id)

        self.metadata = met

    #
    # refine the metadata, should perform in order:
    # - normalise date and time
    # - for every EoSip calculate block of used tiles: enveloppe, METADATA_WRS_xxx_GRID_NORMALISED, LuzId, Country, Town
    # - put tilBlock in each EoSip
    #
    def refineMetadata(self, processInfo):
        print(" refineMetadata")

        # platform is now EW02?
        plat = self.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
        if plat == 'EW02':
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'WorldView')
        if plat != 'WorldView':
            processInfo.addLog("Strange: platform not EW02 or WorldView but:%s" % plat)
            self.metadata.setMetadataPair(metadata.METADATA_PLATFORM, 'WorldView')

        # start is like: 2011-08-10T11:13:17Z
        # want seconds at 00
        start = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        toks = start.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, toks[1][0:-1])

        #
        # stop time = start time + 5 sec
        stopOld = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        stop = formatUtils.datePlusMsec(start, 5000)
        toks = stop.split('.')
        stop = "%sZ" % toks[0]
        print(" change stop time to start + 5 sec: start=%s; orig stop=%s; changed stop=%s" % (start, stopOld, stop))

        toks = stop.split('T')
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, toks[1][0:-1])

        # build timePosition from endTime + endDate
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set file version to product_version
        self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                      self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_VERSION))

        # refine metadata for every dest EoSip
        #
        # will create new block structure
        #
        print(" will refineMetadata on eosips with index:%s" % self.multipleEoSip.getEoSipKeys())
        n = 0
        for eoSipId in self.multipleEoSip.getEoSipKeys():
            anEosip = self.multipleEoSip.getEoSip(eoSipId)
            print("\n\n\n  refineMetadata on eosip[%s]:%s" % (n, anEosip))
            print("    eosip[%s] cell info map:%s" % (n, anEosip.cellsInfo))

            anEosipMetadata = self.metadata.clone()

            block = TileBlock()
            blockpath = None
            blockOrder = None
            j = 0
            for aTile in anEosip.cellsInfo:
                print("    eosip[%s] cell[%s]:%s" % (n, j, aTile.getInfo()))
                block.addTile(aTile, aTile.col, aTile.row)

                if blockpath is None:
                    blockpath = aTile.tileBlock.path
                else:
                    if aTile.tileBlock.path != blockpath:
                        raise Exception("tileBlock path inconsistancy at EoSip %s index %s: %s VS %s" % (
                        n, j, aTile.tileBlock.path, blockpath))

                if blockOrder is None:
                    blockOrder = aTile.tileBlock.order
                else:
                    if aTile.tileBlock.order != blockOrder:
                        raise Exception("tileBlock order inconsistancy at EoSip %s index %s: %s VS %s" % (
                        n, j, aTile.tileBlock.order, blockOrder))

                j += 1

            # set orig block path into new block
            block.path = blockpath
            block.order = blockOrder

            # this will retrieve the block LUZINFO
            # if not resolved, it will use the strip enveloppe(that was set during the TileGrouper activity)
            block.computeInfo(processInfo)
            if block.LuzId == 'Not-Resolved':
                print(("LuzInfo not resolved on block:%s" % block.getInfo()))
                raise Exception("Cannot resolve block '%s' LuzInfo" % block.id)

            boundinbBox = block.getEnveloppe()
            print("    eosip[%s] block enveloppe:%s" % (n, boundinbBox))
            anEosipMetadata.setMetadataPair(metadata.METADATA_FOOTPRINT, boundinbBox)
            anEosipMetadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, boundinbBox)

            anEosipMetadata.setMetadataPair('LuzId', block.LuzId)
            anEosipMetadata.setMetadataPair('town', block.town)
            anEosipMetadata.setMetadataPair('country', block.country)
            # set METADATA_WRS_LATITUDE_GRID_NORMALISED to town
            # set METADATA_WRS_LONGITUDE_GRID_NORMALISED to country
            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, block.country)
            # set METADATA_WRS_LONGITUDE_GRID_NORMALISED to town
            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, block.town)

            browseImage = BrowseImage()
            browseImage.setFootprint(boundinbBox)
            browseImage.calculateBoondingBox()

            lat, lon = browseImage.getCenter()
            lat = float(lat)
            lon = float(lon)
            ilat = int(lat)
            imlat = abs(int((lat - ilat) * 1000))
            simlat = "%s" % formatUtils.normaliseNumber("%s" % imlat, 3, '0')
            print(" refineMetadata[%s] ilat=%s; imlat=%s; simlat=%s" % (n, ilat, imlat, simlat))
            if ilat < 0:
                silat = "%s" % abs(ilat)
                slat = "S%s" % formatUtils.normaliseNumber(silat, 2, '0')
            else:
                silat = "%s" % abs(ilat)
                slat = "N%s" % formatUtils.normaliseNumber(silat, 2, '0')

            ilon = int(lon)
            imlon = abs(int((lon - ilon) * 1000))
            simlon = "%s" % formatUtils.normaliseNumber("%s" % imlon, 3, '0')
            print(" refineMetadata[%s] ilon=%s; imlon=%s; simlon=%s" % (n, ilon, imlon, simlon))
            if ilon < 0:
                silon = "%s" % abs(ilon)
                slon = "W%s" % formatUtils.normaliseNumber(silon, 3, '0')
            else:
                silon = "%s" % abs(ilon)
                slon = "E%s" % formatUtils.normaliseNumber(silon, 3, '0')

            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, slat)
            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, slon)
            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, simlat)
            anEosipMetadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, simlon)

            # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
            # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
            # So we mark it and will substitute with good value before product report write
            anEosipMetadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

            # scene center
            anEosipMetadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lat, lon))

            # local attributes
            anEosipMetadata.addLocalAttribute("boundingBox", boundinbBox)
            anEosipMetadata.addLocalAttribute("URAU", block.LuzId)
            anEosipMetadata.addLocalAttribute("originalName", os.path.basename(self.ORIGINAL_PATH))
            print(("originalName:%s" % os.path.basename(self.ORIGINAL_PATH)))

            # os._exit(0)

            anEosip.metadata = anEosipMetadata
            anEosip.tileBlock = block

            # for info: make a geoJson with the source footprint
            order = anEosipMetadata.getMetadataValue(metadata.METADATA_ORDER_ID)
            footprint = anEosipMetadata.getMetadataValue('SOURCE_FOOTPRINT')
            try:
                footprintAgregator = FootprintAgregator()
                aPath = "%s/%s_%s_source_footprint.json" % (
                processInfo.workFolder, processInfo.ingester.batchName, order)
                fd = open(aPath, 'w')
                props = {}
                props['order'] = order
                res = footprintAgregator.makeSingleJsonShape(order, footprint, props)
                fd.write(res)
                fd.flush()
                fd.close()
            except Exception as e:
                print(("ERROR making source product geoJson:%s" % e))
                processInfo.addLog("ERROR making source product geoJson:%s" % e)
                traceback.print_exc(file=sys.stdout)
                os._exit(1)

            # for info: make a geoJson with the source footprint
            footprint = anEosipMetadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
            country = anEosipMetadata.getMetadataValue('country')
            town = anEosipMetadata.getMetadataValue('town')
            LuzId = anEosipMetadata.getMetadataValue('LuzId')
            try:
                footprintAgregator = FootprintAgregator()
                aPath = "%s/%s_eoSip_%s_on_%s_footprint.json" % (
                processInfo.workFolder, processInfo.ingester.batchName, n, len(self.multipleEoSip.getEoSipKeys()))
                fd = open(aPath, 'w')
                props = {}
                props['eoSipIndex'] = n
                props['country'] = country
                props['town'] = town
                props['LuzId'] = LuzId
                res = footprintAgregator.makeSingleJsonShape(order, footprint, props)
                fd.write(res)
                fd.flush()
                fd.close()
            except Exception as e:
                print(("ERROR making source product geoJson:%s" % e))
                processInfo.addLog("ERROR making source product geoJson:%s" % e)
                traceback.print_exc(file=sys.stdout)
                os._exit(1)

            n += 1

    #
    # extract quality: use .XML for all product type
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
        return
        keys = list(self.blocks.keys())
        keys2 = list(self.eosips.keys())
        keys.sort()
        keys2.sort()
        n = 0
        print(" extractFootprint for block key:%s" % keys2)
        for key in keys2:
            anEoSip = self.eosips[key]
            aBlock = self.blocks[key]
            print(" extractFootprint[%s] anEoSip=%s; aBlock=%s" % (n, anEoSip, aBlock))

            # make sure the footprint is CCW
            browseIm = BrowseImage()
            browseIm.setFootprint(aBlock.enveloppe)
            browseIm.calculateBoondingBox()
            # browseIm.setColRowList(rowCol)
            print("extractFootprint[%s] browseIm:%s" % (n, browseIm.info()))
            if not browseIm.getIsCCW():
                print("############### reverse the footprint; before:%s; colRowList:%s" % (footprint, rowCol))
                browseIm.reverseFootprint()
                print("###############             after;%s; colRowList:%s" % (
                browseIm.getFootprint(), browseIm.getColRowList()))
                anEoSip.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
            else:
                anEoSip.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
                pass

            anEoSip.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, aBlock.enveloppe)

            # aBlock.enveloppe is closed, suppress 2 last coords
            coords = aBlock.enveloppe.split(' ')
            boundingBox = ''
            for i in range(len(coords) - 2):
                if len(boundingBox) > 0:
                    boundingBox = "%s " % boundingBox
                boundingBox = "%s%s" % (boundingBox, coords[i])

            anEoSip.metadata.addLocalAttribute("boundingBox", boundingBox)

    def toString(self):
        res = "Worldview_Product_block"
        return res

    def dump(self):
        res = "Worldview_Product_block"
        print(res)

    #
    #
    #
    def getXmlNodeValueAtPath(self, aXpath):
        aNodeList = self.rootXmlNode.xpath(aXpath, namespaces=ns)
        if len(aNodeList) == 1:
            if not aNodeList[0].text:
                print((" #### NOT FOUND:%s; not text element:%s" % (aNodeList, aNodeList[0])))
                return None
            else:
                print((" #### FOUND:%s; text=%s" % (aNodeList, aNodeList[0].text)))
                return aNodeList[0].text
        else:
            print((" #### NOT FOUND:%s; list empty" % aNodeList))
            return None


#
#
#
class Block:

    def __init__(self, id):
        self.id = id
        self.tiles = []
        # the tiles footprint
        self.footprint = []
        # the enveloppe: the outside of all tiles (== bbox)
        self.enveloppe = None
        self.center = None
        self.path = None
        self.centerLat = None
        self.centerLon = None

    def addTif(self, path, name, footprint):
        self.path = path
        self.tiles.append(name)
        self.footprint.append(footprint)

    def toString(self):
        res = "block id=%s" % self.id
        res = "%s\n path=%s" % (res, self.path)
        res = "%s\n enveloppe=%s" % (res, self.enveloppe)
        res = "%s\n center string=%s" % (res, self.center)
        res = "%s\n center lat=%s; lon=%s" % (res, self.centerLat, self.centerLon)
        res = "%s\n num tiles=%s" % (res, len(self.tiles))
        res = "%s\n num footprint=%s" % (res, len(self.footprint))
        n = 0
        for item in self.tiles:
            res = "%s\n   tile[%s]=%s" % (res, n, item)
            n = n + 1
        return res
