# -*- coding: cp1252 -*-
#
# this class represent a Landsat RBV product
#
#  - 
#  - 
import os
import platform
import shutil
from subprocess import call

import eoSip_converter.xmlHelper as xmlHelper
import eoSip_converter.geomHelper as geomHelper
from eoSip_converter.esaProducts.product import Product
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts import browse_metadata, metadata

from xml_nodes import rep_footprint

OP_SYS = platform.system()

REF_TYPECODES = ['RBV_PAN_1P']

# browses from .zip
BROWSE_SUFFIX = '_001.tif'
# metadata
METADATA_SUFFIX = '.xml'
identifier = 'identifier'
format = 'format'
acquiring_station = 'Acquiring_station'
QUADRANT = 'quadrant'
CHANNEL = 'channel'
PROGRESSIVE_NUMBER = "Progressive_number"

# gdal commands
# GDAL_STEP_0='gdal_translate @DEST1 -scale 0 2048 -ot Byte @DEST2'
#GDAL_STEP_0 = 'gdal_translate -scale 0 2048 -ot Byte @SRC @DEST'
#GDAL_STEP_0='gdalwarp -ts 1800 0 -t_srs EPSG:4326 @SRC @DEST'
GDAL_STEP_1='gdal_translate -of png @SRC @DEST'


def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


def writePowershellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif ($LASTEXITCODE -ne 0) {\n    exit %s\n}\n" % (tmp, badExitCode)

    return tmp


class Product_Landsat_RBV(Product):
    #
    xmlMapping = {
        # metadata.METADATA_START_DATE: 'title/"Acquisition date: "',
        metadata.METADATA_CREATOR: 'creator',
        identifier: 'identifier',
        acquiring_station: 'station',
        format: 'format',
        acquiring_station: 'Acquiring station'
        # metadata.METADATA_PROCESSING_LEVEL: 'Production/DATASET_PRODUCT_LEVEL',

    }

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)
        self.metadata_path = path
        fd = open(path, 'r')
        self.metadata_content = fd.read()
        fd.close()

        #
        self.browseIm = None

        #
        self.browseSrcPath = None
        self.browseDestPath = None

        # self.EO_FOLDER = os.path.dirname(path)

        if self.debug != 0:
            print(" init class Product_Landsat_RBV")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    """ def makePngFromTif(self, browseSrcPath, browseDestPath, item, processInfo):
            destPathBase = browseDestPath.replace('.PNG', '_')

            print("***********src: %s" % self.browseSrcPath)
            print("***********dest: %s" % browseDestPath)
            #os._exit(1)

            command = GDAL_STEP_0.replace('@SRC', self.browseSrcPath)
            tif_piece = "%s_warped.tif" % (destPathBase)
            command1 = command.replace('@DEST', tif_piece)

            if item > 0:
                command = GDAL_STEP_1.replace('@SRC', tif_piece)
                command2 = command.replace('@DEST', browseDestPath)
                commands = "%s%s" % (writeShellCommand(command1, True), writeShellCommand(command2, True))
            else:
                commands = writeShellCommand(command1, True)
            commands = "%s\necho\necho\necho 'browse done'" % (commands)


            commandFile = "%s/command_browse_%s.sh" % (processInfo.workFolder, item)
            fd = open(commandFile, 'w')
            fd.write(#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\nset\n\n)
            fd.write(commands)
            fd.close() 

            # launch the main make_browse script:
            command = "/bin/bash -f %s 2>&1 > %s/command_browse_%s.log" % (commandFile, processInfo.workFolder, item)
            #
            retval = call(command, shell=True)
            if self.debug:
                print "  external make browse exit code:%s" % retval
            if retval != 0:
                raise Exception("Error generating browse, exit coded:%s" % retval)
            print " external make browse exit code:%s" % retval

            #
            if item ==0:
                return tif_piece
            else:
                return browseDestPath  """

    def makePngFromTif(self, browseSrcPath, browseDestPath, item, processInfo):
        #destPathBase = browseDestPath.replace('.PNG', '_')

        print(("***********src: %s" % self.browseSrcPath))
        print(("***********dest: %s" % browseDestPath))
        #os._exit(1)

        command = GDAL_STEP_1.replace('@SRC', self.browseSrcPath)
        #tif_piece = "%s_warped.tif" % (destPathBase)
        command1 = command.replace('@DEST', browseDestPath)

        write_cmd = writePowershellCommand if OP_SYS == 'Windows' else writeShellCommand

        if item > 0:
            commands = "%s" % (write_cmd(command1, True))
        else:
            commands = write_cmd(command1, True)

        if OP_SYS == 'Windows':
            commands = '%s\nWrite-Host " "\nWrite-Host " "\nWrite-Host "browse done"' % (commands)
        else:
            commands = "%s\necho\necho\necho 'browse done'" % commands

        commandFile = "%s/command_browse_%s.%s" % (processInfo.workFolder, item, 'ps1' if OP_SYS == 'Windows' else 'sh')
        with open(commandFile, 'w') as fd:
            if OP_SYS == 'Windows':
                fd.write('Write-Host "starting..."\n\nWrite-Host "PATH is: $env:PATH"\nGet-ChildItem Env:\n\n')
            else:
                fd.write("""#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\nset\n\n""")

            fd.write(commands)

        # launch the main make_browse script:
        if OP_SYS == 'Windows':
            command = 'powershell -File \"%s\" 2>&1 > %s/command_browse_%s.log' % (commandFile, processInfo.workFolder, item)
        else:
            command = "/bin/bash -f %s 2>&1 > %s/command_browse_%s.log" % (commandFile, processInfo.workFolder, item)
        #
        retval = call(command, shell=False if OP_SYS == 'Windows' else True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        #
        return browseDestPath

    #
    #
    def makeBrowses(self, processInfo):

        anEosip = processInfo.destProduct
        browseName = anEosip.getEoProductName()

        self.browseDestPath = os.path.join(processInfo.workFolder, browseName + '.BI.PNG')

        self.makePngFromTif(self.browseSrcPath, self.browseDestPath, 1, processInfo)

        aBrowsePath = self.browseDestPath
        # set AM time if needed
        anEosip.setFileAMtime(aBrowsePath)
        processInfo.destProduct.addSourceBrowse(aBrowsePath, [])
        processInfo.addLog(" main browse image added: name=%s; path=%s" % (browseName, aBrowsePath))

        # create browse choice for browse metadata report
        bmet = anEosip.browse_metadata_dict[aBrowsePath]
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM BROWSE METADATA:%s" % (bmet.toString()))

        reportBuilder = rep_footprint.rep_footprint()
        #
        if self.debug != 0:
            print("###\n###\n### BUILD BROWSE CHOICE FROM METADATA:%s" % (anEosip.metadata.toString()))
        browseChoiceBlock = reportBuilder.buildMessage(anEosip.metadata,
                                                       "rep:browseReport/rep:browse/rep:footprint").strip()
        if self.debug != 0:
            print("browseChoiceBlock:%s" % (browseChoiceBlock))
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

        processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % (browseChoiceBlock))

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination fodler does not exists:%s" % folder)

        # GL: where the EO product will be extracted:  in the working folder
        # self.EXTRACTED_PATH = "%s/EO_product" % folder
        self.EXTRACTED_PATH = folder

        # keep list of content
        self.contentList = []
        #
        # basename = os.path.basename(self.path) # GL removed: use self.origName
        dirname = os.path.dirname(self.path)
        toks = os.path.splitext(self.origName)
        base = toks[0]


        # GL: there is just one file in the native product: the .tif that is in a subdir named as the .xml
        # so we get it directly, no folder walk needed
        """for root, dirs, files in os.walk(self.EO_FOLDER, topdown=False):
            for name in files:
                print(" ## extractToPath; file[%s]: %s" % (n, name))
                nameCheck = "%s%s" % (check, BROWSE_SUFFIX)
                #print("name with browse suffix: %s" % nameCheck)
                if name.lower().endswith(nameCheck):
 
                    n = n + 1
                    eoFile = "%s/%s" % (root, name)
                    print " ## product content[%d]:'%s' in:%s" % (n, name, eoFile)

                    self.browseSrcPath = eoFile
                    #self.browseSrcPath = self.EXTRACTED_PATH + '/' +  os.path.basename(name)

                    print(" ## eoFile=%s" % name)
                    shutil.copyfile(self.browseSrcPath, "%s/%s" % (self.EXTRACTED_PATH, name))
                    print(" ## FOUND self.browseSrcPath=%s" % self.browseSrcPath)
                    self.contentList.append(name)
                    #print("## content list size: %s" % len(self.processInfo.srcProduct.contentList))
                    #os._exit(1)
            n+=1
        """
        # GL: copy the .xml file (that is used as entry point) in the working folder for debugging ease
        # there is another more optimized possibility thta don't do the copy, to be used later
        shutil.copyfile(self.path, "%s/%s" % (self.EXTRACTED_PATH, self.origName))
        self.contentList.append(self.origName)

        # also the .tif file for the time being, not needed at all, just for testing phase
        # there is another more optimized possibility thta don't do the copy, to be used later
        tifNames = os.listdir("%s/%s" % (dirname, base))
        print((" ## tifNames: %s" % tifNames))
        # assert len(tifNames)>0
        if len(tifNames) == 0:
            raise Exception("No preview image found in product")
        self.browseSrcPath = "%s/%s/%s" % (dirname, base, tifNames[0])
        print((" ## self.browseSrcPath: %s" % self.browseSrcPath))

        if not os.path.exists("%s/%s" % (self.EXTRACTED_PATH, base)):
            os.makedirs("%s/%s" % (self.EXTRACTED_PATH, base))
            print((" ## %s folder created" % "%s/%s" % (self.EXTRACTED_PATH, base)))
        else:
            print((" ## folder %s already exists: " % "%s/%s" % (self.EXTRACTED_PATH, base)))
        shutil.copyfile(self.browseSrcPath, "%s/%s/%s" % (self.EXTRACTED_PATH, base, tifNames[0]))
        self.contentList.append("%s/%s" % (base, tifNames[0]))
    # os._exit(0)


    # os._exit(1)

    #
    #   Extracts the first set of metadata.
    #   The extraction is performed on the 'workreport' file, a plain-text (similar to properties) file.
    #
    def extractMetadata(self, met=None, processInfo=None):
        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        self.metadata = met

        # print("metadata content %s" % self.metadata_content)
        # print("metadata content type %s" % type(self.metadata_content))

        # save metadata to workfolder for test purpose:
        destPath = "%s/%s" % (processInfo.workFolder, os.path.basename(self.path))
        shutil.copyfile(self.path, destPath)

        # extract metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metadata_content)
        helper.parseData()
        num_added = 0
        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData == None:
                aValue = None
            else:
                if attr == None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

            if self.debug != 0:
                print("  -->%s=%s" % (field, aValue))
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        print(("metadata extracted: %s" % num_added))

        # traverse the 'title' node in the metadata .xml that contains information for the product
        aData = None
        nodes = []
        helper.getNodeByPath(None, 'title', None, nodes)
        if len(nodes) == 0:
            raise Exception("no title nodes found --> not enough metadata to complete conversion")
        count = 0
        for item in nodes:
            count += 1
            text = helper.getNodeText(item)
            print((" ## ITEM text %s: %s" % (count, text)))
            if text is not None:
                aData = text.split(': ')[0]
                aValue = text.split(': ')[1]
                print((" #### aData %s aValue: %s" % (aData, aValue)))

                if aData == 'Media format':
                    met.setMetadataPair(metadata.METADATA_PRODUCT_TYPE, aValue)
                    print((" ## metadata.METADATA_PRODUCT_TYPE: %s" % aValue))
                elif aData == 'Acquisition date':
                    met.setMetadataPair(metadata.METADATA_ACQUISITION_DATE, aValue)
                    print((" ## metadata.METADATA_ACQUISITION_DATE: %s" % aValue))
                elif aData == 'Satellite name':
                    met.setMetadataPair(metadata.METADATA_SATELLITE, aValue)
                    print((" ## metadata.METADATA_SATELLITE: %s" % aValue))
                elif aData == 'Satellite instrument':
                    met.setMetadataPair(metadata.METADATA_SATELLITE_ID, aValue)
                    print((" ## metadata.METADATA_SATELLITE_ID: %s" % aValue))
                elif aData == 'Path number':
                    met.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, aValue)
                    print((" ## metadata.METADATA_TRACK (Path): %s" % aValue))
                elif aData == 'Row number':
                    met.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, aValue)
                    print((" ## metadata.METADATA_FRAME (Row): %s" % aValue))
                elif aData == 'Quadrant':
                    met.setMetadataPair(QUADRANT, aValue)
                    print((" ## Quadrant: %s" % aValue))
                elif aData == 'Channel':
                    met.setMetadataPair(CHANNEL, aValue)
                    print((" ## Channel: %s" % aValue))
                elif aData == 'Acquiring station':
                    met.setMetadataPair("Acquiring station", aValue)
                    print((" ## Acquiring station: %s" % aValue))
                elif aData == 'Progressive number':
                    met.setMetadataPair(PROGRESSIVE_NUMBER, aValue)
                    print((" ## Progressive number: %s" % aValue))

            else:
                raise Exception("no metadata nodes found")

        if (self.metadata.getMetadataValue(QUADRANT))=='CONVERTER_NOT-PRESENT':
            raise Exception("Quadrant not found")
        if (self.metadata.getMetadataValue(PROGRESSIVE_NUMBER))=='CONVERTER_NOT-PRESENT':
            raise Exception("Progressive number not found")
        if (self.metadata.getMetadataValue(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED))=='CONVERTER_NOT-PRESENT':
            raise Exception("Latitude value not found")
        if (self.metadata.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED))=='CONVERTER_NOT-PRESENT':
            raise Exception("Longitude value not found")
        if (self.metadata.getMetadataValue(acquiring_station))=='CONVERTER_NOT-PRESENT':
            raise Exception("Acquiring station not found")
        if (self.metadata.getMetadataValue(format))=='CONVERTER_NOT-PRESENT':
            raise Exception("Format not found")
        if (self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_DATE))=='CONVERTER_NOT-PRESENT':
            raise Exception("Acquisition date information not found")
        if (self.metadata.getMetadataValue(metadata.METADATA_SATELLITE))=='CONVERTER_NOT-PRESENT':
            raise Exception("Satellite data not found")
        #os._exit(1)

        # size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        #
        self.extractFootprint(processInfo)

        #
        self.refineMetadata(processInfo)

        #
        self.metadata.addLocalAttribute("quadrantNumber", self.metadata.getMetadataValue('quadrant'))

        #
        self.buildTypeCode(processInfo)

        return met

    #
    #
    #
    def extractFootprint(self, processInfo):
        print(" #### extractFootprint")
        adataProvider = self.processInfo.ingester.dataProviders["FOOTPRINT_CORNERS"]
        print((" #### extractFootprint adataProvider: %s" % adataProvider))

        ## GL: TODO: use real row/path
        #testPathRow = "8_10"
        rowPath = "%s_%s" % (self.metadata.getMetadataValue(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED), self.metadata.getMetadataValue(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED))
        print(("get info from csv file at rowPath: %s" % rowPath))
        processInfo.addLog("get info from csv file at rowPath: %s" % rowPath)
        corners = adataProvider.getRowValue(rowPath)
        print((" #### extractFootprint corner: %s" % corners))  # shall be -46.9134|-40.063|69.4249|71.6274. WEST|EAST|SOUTH|NORTH
        #os._exit(1)

        ## GL: TODO: taken from product_cartosat_image.py, not optimized, shall use corners and not intermediate ul, ur etc values
        toks = corners.split("|")
        ul = toks[3] + " " + toks[0]
        ur = toks[3] + " " + toks[1]
        ll = toks[2] + " " + toks[0]
        lr = toks[2] + " " + toks[1]
        self.metadata.setMetadataPair('ul', ul)
        self.metadata.setMetadataPair('ll', ll)
        self.metadata.setMetadataPair('ur', ur)
        self.metadata.setMetadataPair('lr', lr)

        full_footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                         (
                             ul.split(' ')[0],
                             ul.split(' ')[1],

                             ll.split(' ')[0],
                             ll.split(' ')[1],

                             lr.split(' ')[0],
                             lr.split(' ')[1],

                             ur.split(' ')[0],
                             ur.split(' ')[1],

                             ul.split(' ')[0],
                             ul.split(' ')[1],
                         )

        #self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
        self.metadata.setMetadataPair('all_frame_footprint', full_footprint)
        print((" ## all_frame_footprint: %s" % full_footprint))

        #os._exit(1)

        # quarter scene footprint


        quadrant = int(self.metadata.getMetadataValue(QUADRANT))
        #quadrant=2
        mllat, mllon = geomHelper.getIntermediatePoint(float(ul.split(' ')[0]), #ul split at first index (west) for ul middle lat
                                                       float(ul.split(' ')[1]), #and at second index (north) for ul mid longitude
                                                       float(ll.split(' ')[0]), #ll split first index (west)
                                                       float(ll.split(' ')[1]), 0.5) #ll split second index (south)

        mrlat, mrlon = geomHelper.getIntermediatePoint(float(ur.split(' ')[0]),
                                                       float(ur.split(' ')[1]),
                                                       float(lr.split(' ')[0]),
                                                       float(lr.split(' ')[1]), 0.5)

        mtlat, mtlon = geomHelper.getIntermediatePoint(float(ul.split(' ')[0]),
                                                       float(ul.split(' ')[1]),
                                                       float(ur.split(' ')[0]),
                                                       float(ur.split(' ')[1]), 0.5)

        mblat, mblon = geomHelper.getIntermediatePoint(float(ll.split(' ')[0]),
                                                       float(ll.split(' ')[1]),
                                                       float(lr.split(' ')[0]),
                                                       float(lr.split(' ')[1]), 0.5)

        c1lat, c1lon = geomHelper.getIntermediatePoint(float(ll.split(' ')[0]),
                                                       float(ll.split(' ')[1]),
                                                       float(ur.split(' ')[0]),
                                                       float(ur.split(' ')[1]), 0.5)

        c2lat, c2lon = geomHelper.getIntermediatePoint(float(ul.split(' ')[0]),
                                                       float(ul.split(' ')[1]),
                                                       float(lr.split(' ')[0]),
                                                       float(lr.split(' ')[1]), 0.5)

        clat, clon = geomHelper.getIntermediatePoint(c1lat,
                                                     c1lon,
                                                     c2lat,
                                                     c2lon, 0.5)

        print(("# clat, clon: %s %s" % (clat, clon)))

        if quadrant==1: # upper left
            footprintQ1 = "%s %s %s %s %s %s %s %s %s %s" % \
                          (
                              ul.split(' ')[0],
                              ul.split(' ')[1],

                              mllat,
                              mllon,

                              clat,
                              clon,

                              mtlat,
                              mtlon,

                              ul.split(' ')[0],
                              ul.split(' ')[1],
                          )
            self.metadata.setMetadataPair('footprintQ1', footprintQ1)
            print((" ## footprintQ1: %s" % footprintQ1))
            footprint = footprintQ1
        elif quadrant==2: # upper right
            footprintQ2 = "%s %s %s %s %s %s %s %s %s %s" % \
                          (
                              mtlat,
                              mtlon,

                              clat,
                              clon,

                              mrlat,
                              mrlon,

                              ur.split(' ')[0],
                              ur.split(' ')[1],

                              mtlat,
                              mtlon,
                          )
            self.metadata.setMetadataPair('footprintQ2', footprintQ2)
            print((" ## footprintQ2: %s" % footprintQ2))
            footprint = footprintQ2
        elif quadrant == 3:  # lower left
            footprintQ3 = "%s %s %s %s %s %s %s %s %s %s" % \
                          (
                              mllat,
                              mllon,

                              ll.split(' ')[0],
                              ll.split(' ')[1],

                              mblat,
                              mblon,

                              clat,
                              clon,

                              mllat,
                              mllon,
                          )

            self.metadata.setMetadataPair('footprintQ3', footprintQ3) #typo changed Q4 to Q3 in string
            print((" ## footprintQ3: %s" % footprintQ3))
            footprint = footprintQ3
        elif quadrant == 4:  # lower right
            footprintQ4 = "%s %s %s %s %s %s %s %s %s %s" % \
                          (
                              clat,
                              clon,

                              mblat,
                              mblon,

                              lr.split(' ')[0],
                              lr.split(' ')[1],

                              mrlat,
                              mrlon,

                              clat,
                              clon,
                          )

            self.metadata.setMetadataPair('footprintQ4', footprintQ4)
            print((" ## footprintQ4: %s" % footprintQ4))
            footprint = footprintQ4
        else:
            raise Exception("invalid quadrant: %s" % quadrant)

        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
        #quadrant = int(self.metadata.getMetadataValue(QUADRANT))
        #exception catcher
        #pnumbers = int(self.metadata.getMetadataValue(PROGRESSIVE_NUMBER))
        #if self.metadata.getMetadataValue(PROGRESSIVE_NUMBER) is None:
        #	raise Exception("no progressive number found")

        """ 		if prognum == "CONVERTER_NOT-PRESENT":
            raise Exception("invalid progressive number: ", prognum ) """

        #
        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(full_footprint)
        browseIm.calculateBoondingBox()
        #self.metadata.addLocalAttribute('boundingBox', browseIm.boondingBox)
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)

        clat, clon = browseIm.calculateCenter()
        #self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))

        print(("Full frame footprint is: ", full_footprint))
    #os._exit(1)

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo):
        # start and stop
        aTime = "00:00:00"
        toks = self.metadata.getMetadataValue(identifier)
        toks = toks.split('_')
        start = toks[0]
        path = toks[1]
        row = toks[2]
        quadrant = toks[3]
        print(("## START:%s" % start))
        print(("## path:%s" % path))
        print(("## row:%s" % row))
        print(("## quadrant:%s" % quadrant))
        year = start[0:4]
        month = start[4:6]
        day = start[6:8]
        aDate = "%s-%s-%s" % (year, month, day)
        print(("Date is %s" % aDate))
        # os._exit(1)

        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, aDate)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, aTime)
        dateTime = self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%sZ" % (aDate, "00:00:00"))
        print(("## Start DateTime:%s" % dateTime))

        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, aDate)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, aTime)
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (aDate, "00:00:00"))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%sZ" % (aDate, "00:00:00"))

        self.metadata.setMetadataPair(metadata.METADATA_TRACK, path)
        self.metadata.setMetadataPair(metadata.METADATA_FRAME, row)

        quadrant = self.metadata.getMetadataValue(QUADRANT)
        channel = self.metadata.getMetadataValue(CHANNEL)
        pnumber = self.metadata.getMetadataValue(PROGRESSIVE_NUMBER)

        print((" ## CHANNEL: %s" % channel))
        print((" ## QUADRANT: %s" % quadrant))
        print((" ## PROGRESSIVE_NUMBER: %s" % pnumber))
        #os._exit(1)

        # if channel == "CONVERTER_NOT-PRESENT":
        #	print("############################")
        #	channel = 0

        print((type(channel)))
        print(channel)

        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, "%s%s" % (quadrant, pnumber.zfill(2)))

    #
    # os._exit(1)

    #
    #
    #
    def buildTypeCode(self, processInfo):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, REF_TYPECODES[0])

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass

    #
    #
    #
    def toString(self):
        res = "path:%s" % self.path
        return res

    #
    #
    #
    def dump(self):
        res = "path:%s" % self.path
        print(res)