#
# This is a specialized class that ingest cosmos-skymed dataset
#
# For Esa/ lite dissemination project
#
# Serco
# Lavaux Gilles
#
# 03/08/2018: V: 0.1
#
#
# Changes:
#
#
import os
import shutil
import sys
import traceback
import zipfile as zipfile
from subprocess import call

import eoSip_converter.fileHelper as fileHelper
import eoSip_converter.osPlatform as osPlatform
import eoSip_converter.xmlHelper as xmlHelper
import numpy as np
from PIL import Image
from eoSip_converter.base import ingester
from eoSip_converter.esaProducts import definitions_EoSip
from eoSip_converter.esaProducts import metadata, browse_metadata
from eoSip_converter.esaProducts import product_cosmos_skymed, product_EOSIP
from eoSip_converter.esaProducts.namingConvention_hightres import (
    NamingConvention_HightRes,
)
from xml_nodes import rep_footprint

cv2_ready = False
try:
    import cv2 as cv

    cv2_ready = True
except ModuleNotFoundError:
    pass

pylab_ready = False
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pylab_ready = True
except ModuleNotFoundError:
    pass

# minimum config version that can be used
MIN_CONFIG_VERSION = 1.0
VERSION = "Cosmos-Skymed V:0.1.0 2018-09-xx. Lavaux Gilles @ Serco"
REF_NAME = "PR1_OPER_CHR_MO1_1P_20180409T065700_N23-001_E114-067_0001.SIP.ZIP"

DEBUG = True


#
#
#
def get_contour_verts(cn, width, heigh):
    left = []
    right = []
    top = []
    bottom = []
    contours = []
    # for each contour line
    n = 0
    for cc in cn.collections:
        if DEBUG:
            print("\n do collection:%s" % n)
        paths = []
        # for each separate section of the contour line
        j = 0
        for pp in cc.get_paths():
            if DEBUG:
                print("    do path:%s" % j)
            xy = []
            # for each segment of that section
            for vv in pp.iter_segments():
                if DEBUG:
                    print("      segment:%s; x=%s y=%s" % (vv, vv[0][0], vv[0][1]))

                if vv[0][0] <= 1:
                    left.append(vv[0][1])
                    if DEBUG:
                        print("      left coord: 0; %s:" % vv[0][1])

                if vv[0][0] >= width - 1:
                    right.append(vv[0][1])
                    if DEBUG:
                        print("      right coord: %s; %s:" % (width, vv[0][1]))

                if vv[0][1] <= 1:
                    top.append(vv[0][0])
                    if DEBUG:
                        print("      top coord: %s; %s:" % (vv[0][0], 0))

                if vv[0][1] >= heigh - 1:
                    bottom.append(vv[0][0])
                    if DEBUG:
                        print("      bottom coord: %s; %s:" % (vv[0][0], heigh))

                xy.append(vv[0])
            paths.append(np.vstack(xy))
            j += 1
        contours.append(paths)
        n += 1

    return contours, top, left, bottom, right


#
# when we have several browses composing one scene, we need to unwrap the merged png in order to get back non ortorectified image
#
def unwarpUsingPyLab(src, dest):
    if DEBUG:
        print("WILL read image:%s" % src)
    img = Image.open(src)
    width, height = img.size
    if DEBUG:
        print(" ####  image readed:%s; width=%s; height=%s" % (img, width, height))

    ima = np.array(img.convert("L"))
    if DEBUG:
        print("  image converted in array")

    # get contour
    cs = plt.contour(ima, levels=[1], colors="black", origin="lower")
    vertex, top, left, bottom, right = get_contour_verts(cs, width, height)
    if DEBUG:
        print(
            " ####  top:%s; left:%s; bottom:%s; right:%s" % (top, left, bottom, right)
        )
    topX = int(sum(top) / float(len(top)))
    leftY = int(sum(left) / float(len(left)))
    bottomX = int(sum(bottom) / float(len(bottom)))
    rightY = int(sum(right) / float(len(right)))
    print(
        " ####  CS image topX:%s; leftY:%s; bottomX:%s; rightY:%s"
        % (topX, leftY, bottomX, rightY)
    )

    # transform
    # im.transform(size, QUAD, data)
    # Data is an 8-tuple (x0, y0, x1, y1, x2, y2, y3, y3) which contain the upper left, lower left, lower right, and upper right corner of the source quadrilateral.
    quad1 = (topX, 0, 0, leftY, bottomX, height - 1, width - 1, rightY)

    #
    img2 = img.transform((width, height), Image.QUAD, quad1, Image.BILINEAR)
    img2.save(dest)

    # os._exit(1)


#
# when we have several browses composing one scene, we need to unwrap the merged png in order to get back non ortorectified image
# NOT USED: opencv2 not possible on TPM-IF because OS too old.
#
def unwarpUsingCv2(src, dest):
    im = cv.imread(src)
    imgray = cv.cvtColor(im, cv.COLOR_BGR2GRAY)
    ret, thresh = cv.threshold(imgray, 1, 255, 0)
    im2, contours, hierarchy = cv.findContours(
        thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE
    )
    # largest one
    c = max(contours, key=cv.contourArea)
    # determine the most extreme points along the contour
    extLeft = tuple(c[c[:, :, 0].argmin()][0])
    extRight = tuple(c[c[:, :, 0].argmax()][0])
    extTop = tuple(c[c[:, :, 1].argmin()][0])
    extBot = tuple(c[c[:, :, 1].argmax()][0])
    # height, width:
    rows, cols = im.shape[:2]
    pts1 = np.float32([extTop, extRight, extLeft, extBot])
    pts2 = np.float32([[0, 0], [cols, 0], [0, rows], [cols, rows]])
    at = cv.getPerspectiveTransform(pts1, pts2)
    im2 = cv.warpPerspective(im, at, (cols, rows))
    # cv.imwrite(mergedPath2, im2)

    # flip image on vertical axe
    im3 = cv.flip(im2, 1)
    cv.imwrite(dest, im3)


#
# flip image along horizontal axes
#
def flipImageArroundXaxis(src, dest):
    im = Image.open(src)
    # im_flip = ImageOps.flip(im)
    # im_flip.save(dest, quality=95)
    out = im.transpose(Image.FLIP_TOP_BOTTOM)
    # out = ImageOps.(im)
    out.save(dest, quality=95)


#
# flip image along vertical axes
#
def flipImageArroundYaxis(src, dest):
    im = Image.open(src)
    out = im.transpose(Image.FLIP_LEFT_RIGHT)
    # out = ImageOps.(im)
    out.save(dest, quality=95)


#
# rotate image 180
#
def rotateImage180(src, dest):
    im = Image.open(src)
    out = im.transpose(Image.ROTATE_180)
    # out = ImageOps.(im)
    out.save(dest, quality=95)


#
# don't include the test of command exit code, because gdal gives warning about metadata too big
#
def writeShellCommand(command, testExit=True, badExitCode=2):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


#
#
#
class ingester_cosmos_skymed(ingester.Ingester):

    #
    #
    #
    def getVersionImpl(self):
        return VERSION

    #
    # config version is like: name_floatVersion
    #
    def checkConfigurationVersion(self):
        global MIN_CONFIG_VERSION
        self._checkConfigurationVersion(self.CONFIG_VERSION, MIN_CONFIG_VERSION)

    #
    #
    #
    def afterStarting(self, **kargs):
        pass

    #
    # called before doing the various reports
    # # change the mapping of href to METADATA_PACKAGENAME
    #
    def beforeReportsDone(self, processInfo):
        pass
        processInfo.destProduct.metadata.alterMetadataMaping(
            "href", metadata.METADATA_FULL_PACKAGENAME
        )

        if processInfo.srcProduct.browseBlockDisabled:
            processInfo.addLog("############ browse node unused !!")
            print("############ browse node unused !!")
            processInfo.destProduct.browseBlockDisabled = True

    #
    # called after having done the various reports
    #
    def afterReportsDone(self, processInfo):
        #
        self.alterReportXml(processInfo)

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
        print("\n\n @@@@@ EO tmp zip file is:%s" % (zipFilePath))

        # was extracted io EO_product folder
        for name in processInfo.srcProduct.contentList:
            eoPiecePath = "%s/%s" % (processInfo.srcProduct.EXTRACTED_PATH, name)
            print(
                " @@@@@ add to EO contentList[%s]:%s at path %s"
                % (n, name, eoPiecePath)
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

        # add EO zip as a piece
        piece = product_EOSIP.EoPiece(os.path.basename(zipFilePath))
        piece.alias = os.path.basename(zipFilePath)
        piece.localPath = zipFilePath
        newContentList.append(piece.alias)
        processInfo.destProduct.addPiece(piece)
        processInfo.srcProduct.contentList = newContentList

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
        if not processInfo.destProduct.testValueIsDefined(codeSpaceOpMode):
            raise Exception("codeSpaceOpMode is not defined")
        if self.debug != 0:
            print("alterReportXml: codeSpace='%s'" % codeSpaceOpMode)
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

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    #
    def afterProductDone(self, processInfo):
        pass

    #
    #
    #
    def buildEoNames(self, processInfo, namingConvention=None):

        ## fuck: they want to use CS_ in all case, so we have to forse the _. The CS is defined as 2digit alias in config
        origValue = processInfo.srcProduct.metadata.getMetadataValue(
            metadata.METADATA_PLATFORM_ID
        )
        processInfo.srcProduct.metadata.setMetadataPair(
            metadata.METADATA_PLATFORM_ID, "_"
        )

        # force setEoExtension to ZIP. Because we use SRC_PRODUCT_AS_DIR to use several files as input, and we want a .SIP.ZIP package.
        processInfo.destProduct.setEoExtension(
            definitions_EoSip.getDefinition("PACKAGE_EXT")
        )
        self.buildEoNamesDefault(processInfo, namingConvention)

        # test EoSip package name
        aName = processInfo.destProduct.getSipPackageName()
        if len(aName) != len(REF_NAME):
            print("ref name:%s" % REF_NAME)
            print("EoSip name:%s" % aName)
            raise Exception(
                "EoSip name has incorrect length:%s VS %s" % (len(aName), len(REF_NAME))
            )
        if aName.find("@") >= 0 or aName.find("#") > 0:
            raise Exception("SipProductName incomplet:%s" % aName)

        ## put back real METADATA_PLATFORM_ID
        processInfo.srcProduct.metadata.setMetadataPair(
            metadata.METADATA_PLATFORM_ID, origValue
        )

    #
    # Override
    #
    def createSourceProduct(self, processInfo):
        global debug, logger
        cosmosP = product_cosmos_skymed.Product_Cosmos_Skymed(processInfo.srcPath)
        # cosmosP.setDebug(1)
        processInfo.srcProduct = cosmosP

    #
    # Override
    #
    def createDestinationProduct(self, processInfo):
        global debug, logger
        eosipP = product_EOSIP.Product_EOSIP()
        eosipP.sourceProductPath = processInfo.srcPath
        processInfo.destProduct = eosipP

        # set naming convention instance
        namingConventionSip = NamingConvention_HightRes(self.OUTPUT_SIP_PATTERN)
        eosipP.setNamingConventionSipInstance(namingConventionSip)
        eosipP.setNamingConventionEoInstance(namingConventionSip)

        self.logger.info(" Eo-Sip class created")
        processInfo.addLog("\n - Eo-Sip class created")

    #
    # Override
    #
    def verifySourceProduct(self, processInfo):
        processInfo.addLog(" - verifying product: %s" % (processInfo.srcPath))
        self.logger.info(" verifying product")
        fh = open(processInfo.srcPath, "rb")
        zf = zipfile.ZipFile(fh)
        ok = zf.testzip()
        fh.close()
        if ok is not None:
            self.logger.error("  Zip file is corrupt:%s" % processInfo.srcPath)
            self.logger.error("  First bad file in zip: %s" % ok)
            processInfo.addLog("  => Zip file is corrupt:%s" % processInfo.srcPath)
            raise Exception("Zip file is corrupt:%s" % processInfo.srcPath)
        else:
            self.logger.info("  Zip file is ok")
            processInfo.addLog("  => Zip file is ok")

    #
    # Override
    #
    def prepareProducts(self, processInfo):
        processInfo.addLog(
            "\n - prepare product, will extract inside working folder:%s"
            % (processInfo.workFolder)
        )
        self.logger.info(" prepare product")
        processInfo.srcProduct.extractToPath(
            processInfo.workFolder, processInfo.test_dont_extract
        )
        processInfo.addLog("  => extracted inside:%s" % (processInfo.workFolder))
        self.logger.info("  extracted inside:%s" % (processInfo.workFolder))

    #
    # Override
    #
    def extractMetadata(self, met, processInfo):
        processInfo.addLog("\n - will extract metadata from src product")
        self.logger.info(" will extract metadata from src product")
        # fill metadata object
        numAdded = processInfo.srcProduct.extractMetadata(met)

        # use method in base converter
        self.getGenerationTime(met)
        self.logger.debug("number of metadata added:%d" % numAdded)

        # refine
        processInfo.srcProduct.refineMetadata(processInfo)

    #
    # generate the browse PNG from the hdf5 file
    # they may be several browses, to be merged into one or not (depends of the footprint(s))
    #
    def makeBrowseFromHdf(self, processInfo):

        fd = open("%s/command_make_browse.sh" % (processInfo.workFolder), "w")
        block_command = ""

        print(" @@###@@ makeBrowseFromHdf")
        browsePath = None
        theHdfFile = processInfo.srcProduct.h5file

        # how many 'S0x' elements in the file
        num = len(list(theHdfFile.items()))
        print(" @@###@@ makeBrowseFromHdf; number of items:%s" % num)
        for n in range(num):
            name = str(list(theHdfFile.items())[n][0])
            print(
                " @@###@@ makeBrowseFromHdf; doing item[%s]; name=%s, type:%s"
                % (n, name, type(name))
            )
            # try sub items like /S01/QLK, or /S01/B001. Look for quicklook
            subpieces = True
            try:
                pieces = list(theHdfFile.items())[n][1].values()  # []
            except:
                subpieces = False

            if subpieces:
                print(
                    " @@###@@ makeBrowseFromHdf;  item %s has %s pieces"
                    % (name, len(pieces))
                )
                j = 0
                for piece in pieces:
                    if piece.name == "/%s/QLK" % (name):
                        print(
                            " @@###@@ makeBrowseFromHdf piece;  THIS IS A QUICKLOOK !!"
                        )

                        # fda=open("%s/image_%s.dat" % (processInfo.workFolder, j), 'w')
                        # fda.write(piece.value)
                        # fda.flush()
                        # fda.close()
                        # frombytes or fromstring is PIL version dependant...
                        if hasattr(Image, "frombytes"):
                            im = Image.frombytes(
                                "L", (piece.shape[1], piece.shape[0]), piece.value
                            )
                        elif hasattr(Image, "fromstring"):
                            im = Image.fromstring(
                                "L",
                                (piece.shape[1], piece.shape[0]),
                                piece.value,
                                "raw",
                                "L",
                                0,
                                1,
                            )
                        else:
                            raise Exception(
                                " Image has no frombytes or frombytes method!"
                            )
                        browsePath = "%s/%s.tif" % (
                            processInfo.workFolder,
                            piece.name.replace("/", "_"),
                        )
                        im.save(browsePath)
                        print(
                            " @@###@@ makeBrowseFromHdf piece;  QUICKLOOK  written at path:%s"
                            % browsePath
                        )

                        # run the gdal command to make geotiff
                        print(
                            " @@###@@     GDAL browses groups:%s"
                            % processInfo.srcProduct.gdalGroups
                        )
                        gdalGroupname = "_%s_QLK" % name
                        pieceGroup = processInfo.srcProduct.gdalGroups[gdalGroupname]
                        print(
                            " @@###@@     GDAL piece %s group:%s"
                            % (name, processInfo.srcProduct.gdalGroups[gdalGroupname])
                        )
                        commands = processInfo.srcProduct.gdalGroups[
                            gdalGroupname
                        ].getCommands()
                        k = 0
                        for command in commands:
                            print(
                                " @@###@@     should run piece %s GDAL command[%s]:%s"
                                % (
                                    name,
                                    k,
                                    command.replace(
                                        "{WIDTH}", str(piece.shape[1])
                                    ).replace("{HEIGHT}", str(piece.shape[0])),
                                )
                            )
                            block_command = "%s\n\n%s" % (
                                block_command,
                                writeShellCommand(
                                    command.replace(
                                        "{WIDTH}", str(piece.shape[1])
                                    ).replace("{HEIGHT}", str(piece.shape[0])),
                                    False,
                                ),
                            )
                            k += 1
                    j += 1
            else:
                print(" @@###@@ makeBrowseFromHdf;  item %s has no pieces" % name)
                if name == "QLK":
                    dataset = list(theHdfFile.items())[n][1]
                    print(
                        " @@###@@ makeBrowseFromHdf;  THIS IS A QUICKLOOK !!: %s"
                        % (dataset)
                    )
                    if hasattr(Image, "frombytes"):
                        im = Image.frombytes(
                            "L", (dataset.shape[1], dataset.shape[0]), dataset.value
                        )
                    elif hasattr(Image, "fromstring"):
                        im = Image.fromstring(
                            "L",
                            (dataset.shape[1], dataset.shape[0]),
                            dataset.value,
                            "raw",
                            "L",
                            0,
                            1,
                        )
                    else:
                        raise Exception(" Image has no frombytes or frombytes method!")
                    browsePath = "%s/%s.tif" % (
                        processInfo.workFolder,
                        name.replace("/", "_"),
                    )
                    im.save(browsePath)
                    print(
                        " @@###@@ makeBrowseFromHdf piece;  QUICKLOOK  written at path:%s"
                        % browsePath
                    )

                    # run the gdal command to make geotiff
                    print(
                        " @@###@@     GDAL browses groups:%s"
                        % processInfo.srcProduct.gdalGroups
                    )
                    pieceGroup = processInfo.srcProduct.gdalGroups[name]
                    print(
                        " @@###@@     GDAL piece %s group:%s"
                        % (name, processInfo.srcProduct.gdalGroups[name])
                    )
                    commands = processInfo.srcProduct.gdalGroups[name].getCommands()
                    k = 0
                    for command in commands:
                        print(
                            " @@###@@     should run piece %s GDAL command[%s]:%s"
                            % (
                                name,
                                k,
                                command.replace(
                                    "{WIDTH}",
                                    str(list(theHdfFile.items())[n][1].shape[1]),
                                ).replace("{HEIGHT}", str(dataset.shape[0])),
                            )
                        )
                        block_command = "%s\n\n%s" % (
                            block_command,
                            writeShellCommand(
                                command.replace(
                                    "{WIDTH}", str(dataset.shape[1])
                                ).replace("{HEIGHT}", str(dataset.shape[0])),
                                True,
                            ),
                        )
                        k += 1

        # merge, will create '%s/merged.tif'
        finalGroup = processInfo.srcProduct.gdalGroups["final"]
        if finalGroup is not None:
            print(" @@###@@     should run FINAL merge:%s" % finalGroup.getCommands())
            for command in finalGroup.getCommands():
                block_command = "%s\n\n%s" % (
                    block_command,
                    writeShellCommand(str(command), True),
                )
        fd.write(block_command)
        fd.flush()
        fd.close()
        print(
            " browse commands written in:%s"
            % "%s/command_make_browse.sh"
            % (processInfo.workFolder)
        )

        # launch the main make_browse script:
        # first remove any previous browse
        try:
            os.remove("%s/merged.tif" % (processInfo.workFolder))
        except:
            pass
        try:
            os.remove("%s/merged.png" % (processInfo.workFolder))
        except:
            pass
        try:
            os.remove("%s/merged2.tif" % (processInfo.workFolder))
        except:
            pass
        try:
            os.remove("%s/merged2.png" % (processInfo.workFolder))
        except:
            pass
        #
        # command = "/bin/bash -i -f %s/command_make_browse.sh >%s/command_browse.stdout 2>&1" % (processInfo.workFolder, processInfo.workFolder)
        command = (
                "/bin/bash -i -f %s/command_make_browse.sh >%s/command_browse.stdout 2>&1"
                % (processInfo.workFolder, processInfo.workFolder)
        )
        retval, out = osPlatform.runCommand(command, useShell=True)
        if self.debug != 0:  # and self.debug != 2:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:  # and self.debug != 2:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        # disable browse generation for test; TODO : re enable it
        # retval = call(command, shell=True)
        # retval=0
        # if self.debug!=0:
        #    print "  external make browse exit code:%s" % retval
        # if retval != 0:
        #    raise Exception("Error generating browse, exit coded:%s" % retval)
        # print " external make browse exit code:%s" % retval

        # os._exit(1)

        self.keepInfo(
            "orbitDirection",
            processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_ORBIT_DIRECTION
            ),
        )
        self.keepInfo(
            processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_ORBIT_DIRECTION
            ),
            processInfo.srcProduct.metadata.getMetadataValue(
                metadata.METADATA_FULL_PACKAGENAME
            ),
        )
        self.keepInfo("hdfGeotifFlag", processInfo.srcProduct.hdfGeotifFlag)
        self.keepInfo("topBottomCoordsFlipped", processInfo.srcProduct.topBottomFlipped)
        self.keepInfo("LeftRightFlipped", processInfo.srcProduct.LeftRightFlipped)

        # flip browses for product with topBottomFlipped. Not needed for geotiff browses
        # along x or y axis
        if processInfo.srcProduct.hdfGeotifFlag != "GEOTIFF":
            returnedPath = None
            if (
                    processInfo.srcProduct.metadata.getMetadataValue("topBottomFlipped")
                    == True
            ):
                processInfo.addLog("## flip non geotiff with topBottomFlipped==True")
                if processInfo.srcProduct.numberOfScene > 1:
                    self.keepInfo("numberOfScene", processInfo.srcProduct.numberOfScene)
                    mergedPath = "%s/merged.png" % (processInfo.workFolder)
                    mergedPath2 = "%s/merged2.png" % (processInfo.workFolder)

                    flipImageArroundXaxis(mergedPath, mergedPath2)
                    returnedPath = mergedPath2
                else:
                    self.keepInfo(
                        "numberOfScene", 1
                    )  # (flipped product ex) we know that it is not a geotiff and that it is flipped, and has 1 scene. So takes this path
                    # mergedPath = processInfo.srcProduct.browseOK
                    mergedPath = "%s/merged.png" % (processInfo.workFolder)
                    mergedPath2 = "%s/merged2.png" % (processInfo.workFolder)
                    flipImageArroundXaxis(mergedPath, mergedPath2)
                    returnedPath = mergedPath2
            else:
                processInfo.addLog(
                    "## dont flip non geotiff with topBottomFlipped==False"
                )
                returnedPath = "%s/merged.png" % (processInfo.workFolder)

            if (
                    processInfo.srcProduct.metadata.getMetadataValue("LeftRightFlipped")
                    == True
            ):
                processInfo.addLog("## flip non geotiff with LeftRightFlipped==True")
                if processInfo.srcProduct.numberOfScene > 1:
                    self.keepInfo("numberOfScene", processInfo.srcProduct.numberOfScene)
                    mergedPath = "%s/merged.png" % (processInfo.workFolder)
                    mergedPath2 = "%s/merged2.png" % (processInfo.workFolder)

                    flipImageArroundYaxis(mergedPath, mergedPath2)
                    returnedPath = mergedPath2
                else:
                    self.keepInfo("numberOfScene", 1)
                    mergedPath = processInfo.srcProduct.browseOK
                    mergedPath2 = "%s/merged2.png" % (processInfo.workFolder)
                    flipImageArroundYaxis(mergedPath, mergedPath2)
                    returnedPath = mergedPath2
            else:
                processInfo.addLog(
                    "## dont flip non geotiff with LeftRightFlipped==False"
                )
                # returnedPath = '%s/merged.png' % (processInfo.workFolder)
                returnedPath = returnedPath

            return returnedPath

        else:
            raise Exception("WRONG CASE: geotiff in HDF method")
            processInfo.addLog("## dont flip geotif browse")
            return "%s/merged.png" % (processInfo.workFolder)

    #
    # generate the browse PNG from the geoTiff
    #
    def makeBrowseFromGeoTiff(self, processInfo):
        fd = open("%s/command_make_browse.sh" % (processInfo.workFolder), "w")
        block_command = ""
        finalGroup = processInfo.srcProduct.gdalGroups["final"]
        if finalGroup is not None:
            print(" @@###@@     should run FINAL geotiff:%s" % finalGroup.getCommands())
            for command in finalGroup.getCommands():
                block_command = "%s\n\n%s" % (
                    block_command,
                    writeShellCommand(command, True),
                )
        fd.write(block_command)
        fd.flush()
        fd.close()
        print(
            " browse commands written in:%s"
            % "%s/command_make_browse.sh"
            % (processInfo.workFolder)
        )

        # launch the main make_browse script:
        # first remove any previous browse
        try:
            os.remove(processInfo.srcProduct.browseOK)
        except:
            pass
        #
        # command = "/bin/bash -i -f %s/command_make_browse.sh" % (processInfo.workFolder)
        command = (
                "/bin/bash -i -f %s/command_make_browse.sh >%s/command_browse.stdout 2>&1"
                % (processInfo.workFolder, processInfo.workFolder)
        )
        # disable browse generation for test; TODO : re enable it
        retval = call(command, shell=True)
        # retval=0
        if self.debug != 0:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)
        return processInfo.srcProduct.browseOK

    #
    # Override
    # copy the source browse image into work folder, or for better quality generate the browse from the TIF image
    # construct the browse_metadatareport footprint block(BROWSE_CHOICE): it is the rep:footprint for spot
    #
    def makeBrowses(self, processInfo):
        processInfo.addLog("\n - will make browse")
        self.logger.info(" will make browse")
        try:
            browseExtension = definitions_EoSip.getBrowseExtension(
                0, definitions_EoSip.getDefinition("BROWSE_PNG_EXT")
            )
            browseDestPath = "%s/%s.%s" % (
                processInfo.destProduct.folder,
                processInfo.destProduct.eoProductName,
                browseExtension,
            )

            browseSrcPath = None
            # test: just use output for hdf case. (is it somehoe grabbing geotiff case?) If not try printing out some of the values here to work it out.
            # processInfo.srcProduct.productHdf5SrcPath is not None: # hdf case
            """browseSrcPath = self.makeBrowseFromHdf(processInfo)
                    print("browse source path in make browses function: %s " % browseSrcPath)
                    os._exit(1) """

            if processInfo.srcProduct.productHdf5SrcPath is not None:  # hdf case
                browseSrcPath = self.makeBrowseFromHdf(processInfo)
            elif (
                    processInfo.srcProduct.productGeotiffSrcPath is not None
            ):  # geotif case
                browseSrcPath = self.makeBrowseFromGeoTiff(processInfo)

            # os._exit(1)

            # imageUtil.makeBrowse('PNG', browseSrcPath, browseDestPath)
            shutil.move(browseSrcPath, browseDestPath)

            # os._exit(-1)

            processInfo.destProduct.addSourceBrowse(browseDestPath, [])
            processInfo.addLog(
                "  browse image added: name=%s; path=%s"
                % (processInfo.destProduct.eoProductName, browseDestPath)
            )

            # set atime and mtime to self.generationTime
            aFileHelper = fileHelper.FileHelper()
            aFileHelper.setAMtime(
                browseDestPath, self.generationTime, self.generationTime
            )

            # create browse choice for browse metadata report
            bmet = processInfo.destProduct.browse_metadata_dict[browseDestPath]

            footprintBuilder = rep_footprint.rep_footprint()
            #
            print(
                "###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s"
                % (processInfo.destProduct.metadata.toString())
            )
            browseChoiceBlock = footprintBuilder.buildMessage(
                processInfo.destProduct.metadata,
                "rep:browseReport/rep:browse/rep:footprint",
            ).strip()
            if self.debug != 0:
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

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "Error generating browse:%s  %s\n%s" % (
                exc_type,
                exc_obj,
                traceback.format_exc(),
            )
            self.logger.error(errorMsg)
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))
            raise e

    #
    # Override
    #
    # output the Eo-Sip profuct in the destination folder
    # take the first rule and put the product in the resulting folder
    # create link for the other rules if any
    #
    def output_eoSip(self, processInfo, basePath, pathRules, overwrite=None):
        processInfo.addLog("\n - will output eoSip; basePath=%s" % (basePath))
        self.logger.info(" will output eoSip; basePath=%s" % (basePath))
        # copy eoSip in first path
        # make links in other paths
        outputProductResolvedPaths = processInfo.destProduct.getOutputFolders(
            basePath, pathRules
        )
        if len(outputProductResolvedPaths) == 0:
            processInfo.addLog("   ERROR: no product resolved path")
            self.logger.info(" ERROR: no product resolved path")
            raise Exception("no product resolved path")
        else:
            # output in first path
            firstPath = outputProductResolvedPaths[0]
            processInfo.addLog(
                "  Eo-Sip product will be writen in folder:%s" % (firstPath)
            )
            self.logger.info(
                "  Eo-Sip product will be writen in folder:%s" % (firstPath)
            )
            productPath = processInfo.destProduct.writeToFolder(firstPath, overwrite)
            processInfo.addLog("  ok, writen well\n%s" % processInfo.destProduct.info())
            self.logger.info(" ok, writen well\n%s" % processInfo.destProduct.info())
            processInfo.addIngesterLog(
                "  write done:%s" % processInfo.destProduct.path, "PROGRESS"
            )

            # output link in other path
            i = 0
            for item in outputProductResolvedPaths:
                if i > 0:
                    otherPath = "%s" % (item)
                    self.logger.info(
                        "  create also (linked?) eoSip product at tree path[%d] is:%s"
                        % (i, item)
                    )
                    processInfo.addLog(
                        "  create also (linked?) eoSip product at tree path[%d] is:%s"
                        % (i, item)
                    )
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
    # move a browse in the Destination folder
    #
    def move_browse(self, processInfo, destPath):
        processInfo.addLog("\n - will move browse")
        self.logger.info("  will move browse")
        try:
            if len(processInfo.destProduct.sourceBrowsesPath) > 0:
                tmp = os.path.split(processInfo.destProduct.sourceBrowsesPath[0])[1]
                res = shutil.copyfile(
                    processInfo.destProduct.sourceBrowsesPath[0],
                    "%s/%s" % (destPath, tmp.split("/")[-1]),
                )
                print(
                    "copy browse file into:%s/%s: res=%s"
                    % (destPath, tmp.split("/")[-1], res)
                )

        except:
            print(" browse move Error")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_exc(file=sys.stdout)
            self.logger.info(" ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("  => ERROR: %s  %s" % (exc_type, exc_obj))
            processInfo.addLog("%s" % (traceback.format_exc()))


#
#
#
if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            ingester = ingester_cosmos_skymed()
            ingester.DEBUG = 1
            exitCode = ingester.starts(sys.argv)

            #
            ingester.makeConversionReport("Cosmos-Skymed_conversion_report", ".")

            sys.exit(exitCode)
        else:
            print(
                "syntax: python ingester_xxx.py -c configuration_file.cfg [-l list_of_product_file]"
            )
            sys.exit(1)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error 1: %s; %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
