# -*- coding: cp1252 -*-
#
# this class represent a worldview 'block' product: based on the generated 'eoSipProductOrder_orderId.xml'
# it will parse this xml to find the block structure + metadata
# then generate 1 EoSip per block
#
#
import os
import shutil
import sys
import time
import traceback
from subprocess import call

from . import browse_metadata
from . import definitions_EoSip
import eoSip_converter.fileHelper as fileHelper
#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
from . import product_EOSIP
from . import products_EOSIP_multiple
from .browseImage import BrowseImage
from eoSip_converter.serviceClients import luzResolverClient
from .namingConvention_hightres import NamingConvention_HightRes
from .product_directory import Product_Directory
from xml_nodes import rep_footprint, sipBuilder

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
GDAL_STEP_0 = 'gdal_translate -b 2 -outsize 15% 15% @SRC @DEST1'
GDAL_STEP_1 = 'gdal_translate -b 3 -outsize 15% 15% @SRC @DEST2'
GDAL_STEP_2 = 'gdal_translate -b 5 -outsize 15% 15% @SRC @DEST3'
GDAL_STEP_3 = 'gdal_merge.py -co "PHOTOMETRIC=rgb" -separate @DEST1 @DEST2 @DEST3 -o @DEST4'
# GDAL_STEP_4='gdal_translate @DEST4 -scale 0 650 -ot Byte @DEST5'
GDAL_STEP_4 = 'gdal_translate @DEST4 -scale 0 2048 -ot Byte @DEST5'

GM_STEP_1 = 'gm convert @SRC -transparent black @DEST'

MANIFEST_SUFFIX = 'Masterlisting.txt'


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
class Product_Worldview_Block(Product_Directory):
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
    #
    #
    def __init__(self, path=None):
        Product_Directory.__init__(self, path)
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
        print(" init class Product_Worldview_Block")

    #
    # normally this is done in the ingester, but because we create multiples eoSips from one source we want to do it here
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None, logger=None):
        startTime = time.time()
        n = 0
        productPath = None
        for key in list(self.eosips.keys()):
            aBlock = self.blocks[key]
            anEosip = self.eosips[key]
            print(" output_eoSip[%s]: basePath:%s; key:%s; eoSip_%s; block:%s" % (n, basePath, key, anEosip, aBlock))
            processInfo.addLog(
                "    output_eoSip[%s]: basePath:%s;key:%s; eoSip_%s; block:%s" % (n, basePath, key, anEosip, aBlock))
            processInfo.addLog(" EoSip DUMP:\n%s" % anEosip.info())

            # add list of tiles in EoSip contentList
            t = 0
            # the MUL TIFs
            # normally the PAN TIFs are same number and identical path, so pick them using path substitution
            # 2015/09/03: this is not true for every worldview
            #
            aFileHelper = fileHelper.FileHelper()
            firstTif = True
            print(" self.testMode:%s" % self.testMode)
            # os._exit(1)
            for aTifPath in self.getTilesList(key):
                # for MUL:
                # build the correct path in eoSip: what is after the orderId
                pos = aTifPath.find(self.orderId)
                pathInProduct = aTifPath[(pos + len(self.orderId) + 1):]
                #
                processInfo.addLog(" block has MUL tif[%s] tile: path=%s" % (t, aTifPath))
                if not self.testMode or firstTif:
                    anEosip.contentList.append(pathInProduct)
                    anEosip.contentListPath[pathInProduct] = aTifPath
                    processInfo.addLog(
                        " added a MUL tif[%s] tile: path=%s; pathInProduct=%s" % (t, aTifPath, pathInProduct))
                firstTif = False

                # for PAN:
                # build the correct path in eoSip: what is after the orderId
                # consider that path can also contains '-', so use basename
                aTifPath = aTifPath.replace('MUL', 'PAN')
                basename = aFileHelper.basename(aTifPath)
                dirname = aFileHelper.dirname(aTifPath)
                # pos=aTifPath.find('-')
                # aTifPath = aTifPath[0:pos+1]+'P'+aTifPath[pos+2:]
                pos = basename.find('-')
                panName = basename[0:pos + 1] + 'P' + basename[pos + 2:]
                aTifPath = "%s/%s" % (dirname, panName)

                # change: look for identical PAN cell
                toks = aTifPath.split('/')[-1].split('_')
                rc = toks[1].split('-')[0]
                row = rc[1:].split('C')[0]
                col = rc[1:].split('C')[1]
                if self.debug != 0:
                    print("\n################################  WIL LOOK FOR ROW:'%s'  AND COL:'%s' " % (row, col))

                basePathProduct = '/'.join(aTifPath.split('/')[0:-1])
                if self.debug != 0:
                    print("################################  basePathProduct:%s " % basePathProduct)
                panName = None
                for item in os.listdir(basePathProduct):
                    if item[-3:].upper() == 'TIF':
                        if self.debug != 0:
                            print("################################  TEST PAN:%s " % item)
                        toks = item.split('_')
                        rc = toks[1].split('-')[0]
                        arow = rc[1:].split('C')[0]
                        acol = rc[1:].split('C')[1]
                        if self.debug != 0:
                            print("################################  PAN ROW:'%s'  AND COL:'%s' " % (arow, acol))
                        if acol == col and arow == row:
                            panName = item
                            if self.debug != 0:
                                print("################################  PAN MATCH:%s " % panName)
                            break

                if panName is None:
                    raise Exception("can not find PAN for MULT:%s" % aTifPath)

                aTifPath = "%s/%s" % (basePathProduct, panName)
                if self.debug != 0:
                    print("################################  PAN FULL PATH:%s " % aTifPath)

                # print "PAN tif should be at path:%s" % aTifPath
                # sys.exit(0)

                pos = aTifPath.find(self.orderId)
                pathInProduct = aTifPath[(pos + len(self.orderId) + 1):]
                #
                processInfo.addLog(" block has PAN tif[%s] tile: path=%s" % (t, aTifPath))
                if not self.testMode or firstTif:
                    anEosip.contentList.append(pathInProduct)
                    anEosip.contentListPath[pathInProduct] = aTifPath
                    processInfo.addLog(
                        " added a PAN tif[%s] tile: path=%s; pathInProduct=%s" % (t, aTifPath, pathInProduct))
                t = t + 1

            # copy eoSip in first path
            # make links in other paths
            outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(basePath, pathRules)
            if len(outputProductResolvedPaths) == 0:
                processInfo.addLog("   ERROR: no product resolved path")
                if logger is not None:
                    logger.info(" ERROR: no product resolved path")
                raise Exception("no product resolved path")
            else:
                # output in first path
                firstPath = outputProductResolvedPaths[0]
                processInfo.addLog("  Eo-Sip product will be writen in folder:%s" % firstPath)
                if logger is not None:
                    logger.info("  Eo-Sip product will be writen in folder:%s" % firstPath)
                productPath = anEosip.writeToFolder(firstPath, overwrite)
                processInfo.addLog("  ok, writen well")
                if logger is not None:
                    logger.info(" ok, writen well")

                # output link in other path
                i = 0
                for item in outputProductResolvedPaths:
                    if i > 0:
                        otherPath = "%s" % item
                        if logger is not None:
                            logger.info("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                        processInfo.addLog("  create also (linked?) eoSip product at tree path[%d] is:%s" % (i, item))
                        anEosip.writeToFolder(basePath, overwrite)
                        processInfo.addLog("  Eo-Sip product link writen in folder[%d]:%s\n" % (i, otherPath))
                        if logger is not None:
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
    # from the 
    #
    def createDestinationProducts(self, processInfo, namingConvention):
        print(" createDestinationProducts: use naming convention:%s" % namingConvention)
        processInfo.addLog("    createDestinationProducts: use naming convention:%s" % namingConvention)

        # create a 'multiple eosip' eoSip product. it will be a 'fake' dest product, and will contains the 'real' EoSip products
        self.multipleEoSip = products_EOSIP_multiple.Products_EOSIP_Multiple()
        processInfo.destProduct = self.multipleEoSip
        self.multipleEoSip.setCommonProductName(
            "%s_%s" % (products_EOSIP_multiple.DEFAULT_MULTIPLE_EOSIP_NAME, self.orderId))

        # raise Exception("STOP")

        tmp = int(self.metadata.getMetadataValue(NODE_NUMBLOCK))
        for i in range(tmp):
            if self.debug != 0:
                print(" doing destination product[%s]" % i)
            processInfo.addLog("    doing destination product[%s]" % i)
            eosipP = product_EOSIP.Product_EOSIP()
            eosipP.sourceProductPath = processInfo.srcPath
            eosipP.setUsePythonZipLib(False)

            # set naming convention instance
            namingConventionSip = NamingConvention_HightRes(namingConvention)
            eosipP.setNamingConventionSipInstance(namingConventionSip)
            eosipP.setNamingConventionEoInstance(namingConventionSip)

            # create corresponding block
            block = Block(i)
            blockNodeList = self.helper.getNodeChildrenByName(self.helper.getRootNode(), "%s_%s" % (NODE_BLOCK, i))
            if self.debug != 0:
                print(" blockNodeList[%s]; length:%s =%s" % (i, len(blockNodeList), blockNodeList))

            # path
            path = self.helper.getFirstNodeByPath(blockNodeList[0], NODE_PATH)

            # tile node
            tileList = self.helper.getNodeChildrenByName(blockNodeList[0], NODE_TILE)
            for tile in tileList:
                tileFootprintNode = self.helper.getFirstNodeByPath(tile, NODE_TILEFOOTPRINT)
                tilePathNode = self.helper.getFirstNodeByPath(tile, NODE_TIF)
                aTileFootprint = self.helper.getNodeText(tileFootprintNode)
                aTilePath = self.helper.getNodeText(tilePathNode)
                block.addTif(self.helper.getNodeText(path), aTilePath, aTileFootprint)

            # tile footprint
            # footprintList = self.helper.getNodeChildrenByName(blockNodeList[0], NODE_TILEFOOTPRINT)
            # if self.DEBUG!=0:
            #    print " footprintList[%s]; length:%s =%s" % (i, len(footprintList), footprintList)

            # tile tif path
            # tifList = self.helper.getNodeChildrenByName(blockNodeList[0], NODE_TIF)
            # if self.DEBUG!=0:
            #    print " tifList[%s]; length:%s =%s" % (i, len(tifList), tifList)

            # enveloppe
            enveloppe = self.helper.getFirstNodeByPath(blockNodeList[0], NODE_FOOTPRINT)
            block.enveloppe = self.helper.getNodeText(enveloppe)

            # center
            center = self.helper.getFirstNodeByPath(blockNodeList[0], NODE_CENTER)
            block.center = self.helper.getNodeText(center)

            # if len(footprintList) == len(tifList):
            #    for n in range(len(tifList)):
            #        tmp1=self.helper.getNodeText(tifList[n])
            #        tmp2=self.helper.getNodeText(footprintList[n])
            #        block.addTif(self.helper.getNodeText(path), tmp1, tmp2)
            #        
            # else:
            #    raise Exception("tiff length != footprint length: %s vs %s" % (len(tifList), len(footprintList)))

            self.eosips["%s" % i] = eosipP
            self.blocks["%s" % i] = block
            print("\n\n added block[%s]:\n%s" % (i, block.toString()))

            self.multipleEoSip.addEoSip(i, eosipP)

    #
    # normally this is done in the ingester, but because we create multiples eoSips we want to do it here
    #
    # use gdal to extract band 2,3,5 from tif, strech histogram and merge all
    #
    #
    def makeBrowses(self, processInfo):
        # for now use the pre done block_x.tif files that are in the tmpfolder
        # TODO: use real creation
        print(" makeBrowses")
        processInfo.addLog("    makeBrowses")

        # launch the main make_browse script:
        command = "/bin/sh -f %s/command_all_blocks.sh" % processInfo.workFolder
        # disable browse generation for test; TODO : re enable it
        retval = call(command, shell=True)
        # retval=0
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        n = 0
        keys = list(self.eosips.keys())
        keys.sort()
        for key in keys:
            anEosip = self.eosips[key]
            browseSrcPath = "%s/../../block_%s.png" % (anEosip.folder, key)
            # browseDestPath = "%s/%s.BI.PNG" % (anEosip.folder, anEosip.getSipProductName())
            browseDestPath = "%s/%s.%s" % (anEosip.folder, anEosip.getSipProductName(),
                                           definitions_EoSip.getBrowseExtension(0, definitions_EoSip.getDefinition(
                                               'BROWSE_PNG_EXT')))
            processInfo.addLog(
                "    makeBrowse[%s]; browseSrcPath=%s; browseDestPath=%s" % (n, browseSrcPath, browseDestPath))
            shutil.copyfile(browseSrcPath, browseDestPath)
            anEosip.addSourceBrowse(browseDestPath, [])
            processInfo.addLog("  browse image[%s] created:%s" % (n, browseDestPath))

            # create browse choice for browse metadata report
            bmet = anEosip.browse_metadata_dict[browseDestPath]
            print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

            reportBuilder = rep_footprint.rep_footprint()
            #
            print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
            browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                           "rep:browseReport/rep:browse/rep:footprint").strip()
            if self.debug != -1:
                print("browseChoiceBlock:%s" % browseChoiceBlock)
            bmet.setMetadataPair(browse_metadata.BROWSE_METADATA_BROWSE_CHOICE, browseChoiceBlock)

            # set the browse type (if not default one(i.e. product type code))for the product metadata report BROWSES block
            # if specified in configuration
            tmp = self.metadata.getMetadataValue(metadata.METADATA_BROWSES_TYPE)
            if tmp is not None:
                bmet.setMetadataPair(metadata.METADATA_BROWSES_TYPE, tmp)

            # idem for METADATA_CODESPACE_REFERENCE_SYSTEM
            tmp = self.metadata.getMetadataValue(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM)
            if tmp is not None:
                bmet.setMetadataPair(metadata.METADATA_CODESPACE_REFERENCE_SYSTEM, tmp)

            processInfo.addLog("  browse image[%s] choice created:%s" % (n, browseChoiceBlock))
            n = n + 1

    #
    #
    #
    # def makeBrowseChoiceBlock(self, processInfo, metadata):
    #    pass

    #
    #
    #
    def prepareBrowseCommands(self, processInfo):
        print(" prepareBrowseCommands")
        processInfo.addLog("    prepareBrowseCommands")
        n = 0
        keys = list(self.eosips.keys())
        keys.sort()
        commandAllTiles = ''
        blocksTileNames = ''
        # for key in range(1): # keys:
        for key in keys:
            print("    prepareBrowseCommands[%s]; key=%s" % (n, key))
            processInfo.addLog("    prepareBrowseCommands[%s]; key=%s" % (n, key))

            block = self.blocks[key]
            # block = self.blocks["%s" % key]
            i = 0
            toBeMerged = []
            block_command = ''
            for item in block.tiles:
                destPath = "%s/%s_%s" % (processInfo.workFolder, key, i)
                srcPath = "%s/%s" % (block.path, item)

                # has to test the src image size, to not resize two small images
                tifTooSmall = False
                print("    prepareBrowseCommands[%s]; test image size:%s" % (i, srcPath))
                if os.path.getsize(srcPath) < 2000000:
                    print("  @@@@@@@@@@@@@@@@@@@@@@@###########################@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@###############################  prepareBrowseCommands[%s]; don't reduce image because source tiff too small:%s" % (
                        i, os.path.getsize(srcPath)))
                    tifTooSmall = True
                else:
                    print("  @@@@@@@@@@@@@@@@@@@@@@@###########################@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@###############################  prepareBrowseCommands[%s]; reduce image because source tiff is big:%s" % (
                        i, os.path.getsize(srcPath)))
                # os._exit(1)

                # use imageUtil to get real image size. TODO : OK OR NOT??
                # imw, imh = imageUtil.get_image_size(srcPath)
                # print "    prepareBrowseCommands[%s]; image size:%s %s" % (i, imw, imh)
                # tifTooSmall=True

                # gdal_translate -b 2 @SRC @DEST1
                if tifTooSmall:
                    command = GDAL_STEP_0.replace('@SRC', srcPath).replace('-outsize 15% 15%', '')
                else:
                    command = GDAL_STEP_0.replace('@SRC', srcPath)
                command1 = command.replace('@DEST1', "%s_b2.tif" % destPath)

                if tifTooSmall:
                    command2 = GDAL_STEP_1.replace('@SRC', srcPath).replace('-outsize 15% 15%', '')
                else:
                    command2 = GDAL_STEP_1.replace('@SRC', srcPath)

                command2 = command2.replace('@DEST2', "%s_b3.tif" % destPath)

                if tifTooSmall:
                    command3 = GDAL_STEP_2.replace('@SRC', srcPath).replace('-outsize 15% 15%', '')
                else:
                    command3 = GDAL_STEP_2.replace('@SRC', srcPath)

                command3 = command3.replace('@DEST3', "%s_b5.tif" % destPath)

                # @DEST1 @DEST2 @DEST3 -o @DEST4
                command4 = GDAL_STEP_3.replace('@DEST1', "%s_b5.tif" % destPath).replace('@DEST2', "%s_b3.tif" % (
                    destPath)).replace('@DEST3', "%s_b2.tif" % destPath)
                command4 = command4.replace('@DEST4', "%s_bmerged.tif" % destPath)

                command5 = GDAL_STEP_4.replace('@DEST4', "%s_bmerged.tif" % destPath).replace('@DEST5',
                                                                                              "%s_merged.tif" % (
                                                                                                  destPath))

                commands = "%s%s%s%s%s" % (
                    writeShellCommand(command1, True), writeShellCommand(command2, True),
                    writeShellCommand(command3, True),
                    writeShellCommand(command4, True), writeShellCommand(command5, True))
                commands = "%s\necho\necho\necho 'tile %s done'" % (commands, i)

                commandFile = "%s/command_%s_%s_%s.sh" % (processInfo.workFolder, key, i, item)
                fd = open(commandFile, 'w')
                fd.write(commands)
                fd.close()
                toBeMerged.append("%s_merged.tif" % destPath)
                # toBeMerged.append("%s_bmerged.tif" % (destPath))
                block_command = "%s\n%s" % (block_command, writeShellCommand("/bin/sh -f %s" % commandFile, True))

                i = i + 1
                # if i==3:
                #    break

            # make the block browse image: one PNG and one TIF
            # block_command = "%s\n\ngdal_merge.py" % (block_command)
            # TIF
            tmp_command = "gdal_merge.py"
            for item in toBeMerged:
                print("add to block_command:%s" % item)
                tmp_command = "%s %s" % (tmp_command, item)
            tmp_command = "%s -o %s/block_%s.TIF" % (tmp_command, processInfo.workFolder, key)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))
            # PNG not transparent
            # tmp_command = "%s  %s/block_%s.TIF %s/block_%s.PNG" % (self.tifToPngExe, processInfo.workFolder, key, processInfo.workFolder, key)
            # new use stretcherApp 
            tmp_command = "%s -transparent %s/block_%s.TIF %s/block_transparent_%s.png 0xff000000" % (
                self.stretcherApp, processInfo.workFolder, key, processInfo.workFolder, key)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            tmp_command = "%s -stretch %s/block_transparent_%s.png %s/block_0_%s.png 0.01" % (
                self.stretcherApp, processInfo.workFolder, key, processInfo.workFolder, key)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            tmp_command = "%s -autoBrighten %s/block_0_%s.png %s/block_%s.png 85" % (
                self.stretcherApp, processInfo.workFolder, key, processInfo.workFolder, key)
            block_command = "%s\n\n%s" % (block_command, writeShellCommand(tmp_command, True))

            block_command = "%s\necho\necho\necho 'block %s done'" % (block_command, key)

            blocksTileNames = "%s %s/block_%s.png" % (blocksTileNames, processInfo.workFolder, key)
            print("############### blocksTileNames:%s" % blocksTileNames)
            commandFile = "%s/command_block_%s.sh" % (processInfo.workFolder, key)
            fd = open(commandFile, 'w')
            fd.write(block_command)
            fd.close()

            commandAllTiles = "%s\n%s" % (commandAllTiles, writeShellCommand("/bin/sh -f %s" % commandFile, True))

            n = n + 1

        print("############### blocksTileNames:%s" % blocksTileNames)

        commandAllTiles = "%s\n%s" % (commandAllTiles, writeShellCommand(
            "gdal_merge.py %s -o %s/browse.tif" % (blocksTileNames, processInfo.workFolder), True))
        commandFile = "%s/command_all_blocks.sh" % processInfo.workFolder
        fd = open(commandFile, 'w')
        fd.write(commandAllTiles)
        fd.close()

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
        if self.debug != 0:
            print(" matadata source is itself:%s" % self.path)
        fd = open(self.path, 'r')
        metadata_info = fd.read()
        fd.close()
        if self.debug != 0:
            print(" extract metadata from:%s" % metadata_info)

        return metadata_info

    #
    # not neeed
    #
    def extractToPath(self, folder=None, dont_extract=False):
        pass

    #
    #
    #
    def buildTypeCode(self):
        pass

    #
    # get metadata: common to all blocks
    #
    def extractMetadata(self, met=None, pinfo=None):
        if met is None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        self.metContent = self.getMetadataInfo()

        # extact metadata
        self.helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        self.helper.setData(self.metContent)
        self.helper.parseData()

        # get common files
        # get manifest file path
        tmpNodes = []
        self.helper.getNodeByPath(None, 'block_0/path', None, tmpNodes)
        if len(tmpNodes) == 0:
            raise Exception('can not get first block path')
        tmp = self.helper.getNodeText(tmpNodes[0])
        print("order path:%s" % tmp)

        # this is NOT the orderId but the short version used to name the order folder
        self.orderId = os.path.basename(tmp)
        self.orderFolder = os.path.dirname(tmp[0:-len(self.orderId)])
        print(" NOW 0: self.orderFolder:%s; self.orderId=%s" % (self.orderFolder, self.orderId))
        self.orderId = os.path.basename(self.orderFolder)

        # get real orderId from xml, should be like the short one above + '_P0001'
        tmpNodes = []
        self.helper.getNodeByPath(None, 'id', None, tmpNodes)
        if len(tmpNodes) == 0:
            raise Exception('can not get order id')
        self.realOrderId = self.helper.getNodeText(tmpNodes[0])

        self.orderFolder = os.path.dirname(self.orderFolder)
        print("order: self.orderFolder=%s;  self.orderId:%s; self.realOrderId:%s" % (
            self.orderFolder, self.orderId, self.realOrderId))

        self.getCommonContent_bis(pinfo)

        # get fields
        resultList = []
        op_element = self.helper.getRootNode()
        num_added = 0

        for field in self.xmlMapping:
            attr = None
            path = self.xmlMapping[field]

            aData = self.helper.getFirstNodeByPath(None, path, None)
            print(" HELLO3 %s:%s" % (path, aData))
            if aData is None:
                aValue = None
            else:
                if attr is None:
                    aValue = self.helper.getNodeText(aData)
                else:
                    aValue = self.helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  -->%s=%s" % (field, aValue))
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        met.label = "worldview product block"

        # get LUZ and other info info
        aData = self.helper.getFirstNodeByPath(None, 'block_0/luzId', None)
        if aData is None:
            self.luzId = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.luzId = self.helper.getNodeText(aData)
        aData = self.helper.getFirstNodeByPath(None, 'block_0/country', None)
        if aData is None:
            self.country = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.country = self.helper.getNodeText(aData)
        aData = self.helper.getFirstNodeByPath(None, 'block_0/town', None)
        if aData is None:
            self.town = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.town = self.helper.getNodeText(aData)
        aData = self.helper.getFirstNodeByPath(None, 'block_0/phone', None)
        if aData is None:
            self.phone = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.phone = self.helper.getNodeText(aData)
        aData = self.helper.getFirstNodeByPath(None, 'block_0/utmZone', None)
        if aData is None:
            self.utmZone = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.utmZone = self.helper.getNodeText(aData)
        aData = self.helper.getFirstNodeByPath(None, 'block_0/orbit', None)
        if aData is None:
            self.orbit = sipBuilder.VALUE_NOT_PRESENT
        else:
            self.orbit = self.helper.getNodeText(aData)
        print(" HELLO4: got luzId=%s; country=%s; town=%s; phone=%s; utmZone=%s; orbit=%s" % (
            self.luzId, self.country, self.town, self.phone, self.utmZone, self.orbit))

        self.metadata = met

    #
    # refine the metadata, should perform in order:
    # - normalise date and time
    # - get block scene center 'normalized' METADATA_WRS_LONGITUDE_DEG_NORMALISED, METADATA_WRS_LONGITUDE_MDEG_NORMALISED, long...
    # - build type code
    #
    def refineMetadata(self, processInfo):
        print(" refineMetadata")
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

        # set file version to product_version
        self.metadata.setMetadataPair(metadata.METADATA_SIP_VERSION,
                                      self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_VERSION))

        # blocks scene center
        print(" will refineMetadata on eosips:%s" % list(self.eosips.keys()))
        print(" will refineMetadata on blocks:%s" % list(self.blocks.keys()))
        keys = list(self.blocks.keys())
        keys2 = list(self.eosips.keys())
        keys.sort()
        keys2.sort()
        n = 0
        print(" refineMetadata for block key:%s" % keys2)
        for key in keys2:
            print(" refineMetadata for keys:%s" % key)
            anEoSip = self.eosips[key]
            aBlock = self.blocks[key]
            print(" refineMetadata[%s] anEoSip=%s; aBlock=%s" % (n, anEoSip, aBlock))

            latLonCenter = aBlock.center
            lat = float(latLonCenter.split(' ')[0])
            aBlock.centerLat = lat
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

            lon = float(latLonCenter.split(' ')[1])
            aBlock.centerLon = lon
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

            self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, slat)
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, slon)
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, simlat)
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, simlon)

            # set size to product_EOSIP.PRODUCT_SIZE_NOT_SET: we want to get the EoPackage zip size, which will be available only when
            # the EoSip package will be constructed. in EoSipProduct.writeToFolder().
            # So we mark it and will substitute with good value before product report write
            self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, product_EOSIP.PRODUCT_SIZE_NOT_SET)

            # scene center
            self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, latLonCenter)

            # build timePosition from endTime + endDate
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
                self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
                self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

            # try to resolve tile luz info, if resolution fail use stril info
            try:
                # self.luzIdTile, self.townTile, self.countryTile = self.getLuzInfo(aBlock, processInfo)
                self.luzId, self.town, self.country = self.getLuzInfo(aBlock, processInfo)
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("tile luz info can not be resolved, use block info. Error:%s; %s\n%s" % (
                    exc_type, exc_obj, traceback.format_exc()))
                processInfo.addLog("tile luz info can not be resolved, use block info. Error:%s; %s\n%s" % (
                    exc_type, exc_obj, traceback.format_exc()))

            self.metadata.setMetadataPair('LuzId', self.luzId)
            self.metadata.setMetadataPair('town', self.town)
            self.metadata.setMetadataPair('country', self.country)
            # set METADATA_WRS_LONGITUDE_GRID_NORMALISED to luzid
            # set METADATA_WRS_LONGITUDE_GRID_NORMALISED to country 
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, self.country)
            # set METADATA_WRS_LONGITUDE_GRID_NORMALISED to town
            self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, self.town)

            # add utmZone
            self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, self.utmZone)

            # add orbit
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT, self.orbit)

            # clone current metadata into child eoSip
            anEoSip.metadata = self.metadata.clone()
            # anEoSip.metadata.addLocalAttribute("country", self.country)
            anEoSip.metadata.addLocalAttribute("URAU", self.luzId)
            anEoSip.metadata.addLocalAttribute("originalName", self.realOrderId)

            n = n + 1

        self.extractQuality(self.helper, None)

        self.extractFootprint(self.helper, None)

    #
    # request is like:
    #  http://localhost:7001/luzResolver?FOOTPRINT=52.23165364%208.76142652%2052.05466425%208.76142652%2052.05466425%209.01463051%2052.23165364%209.01463051%2052.23165364%208.76142652
    # reply is like:
    # """wfsInfo[0]
    # DE017L|Bielefeld|Bielefeld|DE|Germany
    # Done in 217 mSec"""
    #
    # reply is 3 strings: luzId, town, country. Like 017, Bielefeld, Germany
    #
    #
    def getLuzInfo(self, aBlock, processInfo):
        # use client
        client = luzResolverClient.LuzResolverClient(processInfo)
        client.setDebug(self.debug)

        print("getLuzInfo; aBlock=%s" % aBlock.toString())

        params = []
        params.append(aBlock.enveloppe)
        data = client.callWfsService(processInfo, params)
        print("getLuzInfo; data=%s" % data)
        lines = data.split('\n')
        if len(lines) > 1:
            if lines[0].find('wfsInfo[0]') >= 0:
                toks = lines[1].split('|')
                return toks[0][2:-1], toks[1], toks[4]
            else:
                raise Exception("LUZ not resolved:%s" % data)

    #
    # extract quality: use .XML for all product type
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
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
                print("############### reverse the footprint; before:%s; colRowList:%s" % (browseIm.footprint, '?'))
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
