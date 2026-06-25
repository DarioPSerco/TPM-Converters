# -*- coding: cp1252 -*-
#
# this class represent a Kompsat-1 product
#
#
#
import os
import subprocess
import sys
import traceback
from subprocess import call

#
import eoSip_converter.esaProducts.verifier as verifier
import eoSip_converter.osPlatform as osPlatform
#
from eoSip_converter.esaProducts import browse_metadata
from eoSip_converter.esaProducts import formatUtils
from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product import Product
from xml_nodes import rep_footprint

#
#
REF_TYPECODES = ['RBV_PAN_1P']

# gdal commands

# GDAL_STEP_0='gdalwarp -ts 1800 0 -t_srs EPSG:4326 @SRC @DEST'
GDAL_STEP_0 = 'gdalwarp -ts 1800 0 -t_srs EPSG:4326 @SRC @DEST'
GDAL_STEP_1 = 'gdal_translate -of png @SRC @DEST'

#
BROWSE_SUFFIX = '.tif'
# metadata
METADATA_BROWSES_TYPE = 'METADATA_BROWSES_TYPE'


#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp


class Product_Kompsat1(Product):
    BROWSE_SUFFIX = '.tif'

    def __init__(self, path=None):
        Product.__init__(self, path)
        # there is only one browse
        # no metadata file to read in

        if not self.path.endswith('.tif'):
            raise Exception("product has bad extension, expected .tif:'%s'" % self.path)

        self.browseIm = None
        self.site = None
        self.browseSrcPath = None
        self.browseDestPath = None
        self.gdalInfo = None

        if self.debug != 0:
            print(" init class Product_Kompsat1")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # read matadata file
    #
    def getMetadataInfo(self):
        pass

    def use_gdal(self, command, n, processInfo):
        commandFile = "%s/command_%s.sh" % (processInfo.workFolder, n)
        fd = open(commandFile, 'w')
        fd.write(command)
        fd.close()
        command = "/bin/bash -f %s 2>&1 | tee %s/command_%s.stdout" % (commandFile, processInfo.workFolder, n)

        try:
            if self.debug != 0:
                print("COMMAND_%s=%s" % (n, command))
            retval, out = osPlatform.runCommand(command, useShell=True)
            if retval != 0:
                raise Exception("Error external-call, exit code:%s; %s" % (retval, out))
            return retval, out
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(" ERROR running external-call :%s %s" % (exc_type, exc_obj))
            traceback.print_exc(file=sys.stdout)
            raise Exception(" ERROR running external-call:%s %s" % (exc_type, exc_obj))

    #
    # get one metadata value from gdal info
    #
    def getGdalInfoMetadata(self, aPath, aMetadata, processInfo):
        if self.gdalInfo is None:
            self.gdalInfo = subprocess.check_output(['gdalinfo', aPath])
            retval, out = self.use_gdal('/bin/bash -c "gdalinfo %s"' % aPath, 0, processInfo)
            if retval == 0:
                self.gdalInfo = out

        if self.gdalInfo is not None:
            for item in self.gdalInfo.split('\n'):
                if item.find("%s=" % aMetadata) > 0:
                    return item.split("%s=" % aMetadata)[1]
        raise Exception("no gdalinfo found for '%s'" % aMetadata)

    #
    # get coords from gdal info
    #
    def getGdalInfoCoordinates(self, aPath, processInfo):
        if self.gdalInfo is None:
            # self.gdalInfo = subprocess.check_output(['gdalinfo', aPath])
            retval, out = self.use_gdal('/bin/bash -c "gdalinfo %s"' % aPath, 1, processInfo)
            if retval == 0:
                self.gdalInfo = out
        if self.gdalInfo is not None:
            ul = None
            ll = None
            ur = None
            lr = None
            for item in self.gdalInfo.split('\n'):
                if item.startswith('Upper Left'):
                    ul = item.split('(')[1].replace(')', '').replace(',', ' ').strip()
                elif item.startswith('Lower Left'):
                    ll = item.split('(')[1].replace(')', '').replace(',', ' ').strip()
                elif item.startswith('Upper Right'):
                    ur = item.split('(')[1].replace(')', '').replace(',', ' ').strip()
                elif item.startswith('Lower Right'):
                    lr = item.split('(')[1].replace(')', '').replace(',', ' ').strip()

            ul = ' '.join(ul.split())
            ll = ' '.join(ll.split())
            ur = ' '.join(ur.split())
            lr = ' '.join(lr.split())

            print(("ul: %s" % ul))
            print(("ll: %s" % ll))
            print(("ur: %s" % ur))
            print(("lr: %s" % lr))
            # os._exit(1)

            return ul, ll, ur, lr
        else:
            raise Exception("no gdalinfo")

    def makePngFromTif(self, browseSrcPath, browseDestPath, item, processInfo):
        destPathBase = browseDestPath.replace('.PNG', '_')

        command = GDAL_STEP_0.replace('@SRC', self.path)
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
        fd.write("""#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\nset\n\n""")
        fd.write(commands)
        fd.close()

        # launch the main make_browse script:
        command = "/bin/bash -f %s 2>&1 > %s/command_browse_%s.log" % (commandFile, processInfo.workFolder, item)
        #
        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        #
        if item == 0:
            return tif_piece
        else:
            return browseDestPath

    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        self.num_preview = 0

    #
    def buildTypeCode(self, processInfo):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, "EOC_PAN_1P")

    #
    #
    #
    def extractMetadata(self, met=None, processInfo=None):
        # set some evident values
        self.metadata = met
        met.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.origName)

        # src size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        #
        # In the CSV, find the date of the product via it's filename
        #
        dateString = self.processInfo.ingester.dataProviders["DATE"]
        # CSV file names do not include '_OrthoGEOSAT'. Remove this from tif so DataProvider can find the filename.
        tif_name = self.origName
        remove_substring = "_OrthoGEOSAT"
        filename = tif_name.replace(remove_substring, "")
        print(("get info from csv file at filename: %s" % filename))
        date = dateString.getRowValue(filename)

        # Format the date correctly
        month, day, year = date.split("/")
        month = month.zfill(2)
        aDate = "%s-%s-%s" % (year, month, day)
        print((" #### date for filename value: %s" % aDate))
        # os._exit(1)

        # Do the same for the Start Time
        timeString = self.processInfo.ingester.dataProviders["TIME"]
        time = timeString.getRowValue(filename)
        # Check if the time variable is a string with at least 8 characters which have the format "[0-9][0-9]:[0-9][0-9]:[0-9][0-9]"
        if isinstance(time, str) and len(time) >= 8 and time[2] == ":" and time[5] == ":" and time[
                                                                                              :2].isdigit() and time[
                                                                                                                3:5].isdigit() and time[
                                                                                                                                   6:8].isdigit():
            aTime = time[0:8]
        else:
            aTime = "00:00:00"
        print((" #### time for filename value: %s" % aTime))
        # os._exit(1)

        # Do the same for the orbit number
        orbitVal = self.processInfo.ingester.dataProviders["ORBIT"]
        orbit = orbitVal.getRowValue(filename)
        if len(orbit) >= 0:
            aOrbit = orbit
        else:
            aOrbit = 0
        print((" #### orbit number is: %s" % aOrbit))
        # os._exit(1)

        # Do the same for the country
        countryString = self.processInfo.ingester.dataProviders["COUNTRY"]
        country = countryString.getRowValue(filename)
        if isinstance(country, str) and len(country) >= 0:
            aCountry = country
        else:
            aCountry = "No country provided"
        print((" #### country is: %s" % aCountry))
        # os._exit(1)

        # Do the same for the city
        cityString = self.processInfo.ingester.dataProviders["CITY"]
        city = cityString.getRowValue(filename)
        if isinstance(city, str) and len(city) >= 0:
            aCity = city
        else:
            aCity = "No city provided"
        print((" #### city is: %s" % aCity))
        # os._exit(1)

        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, aDate)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, aTime)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%sZ" % (aDate, aTime))
        dateTime = self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%sZ" % (aDate, aTime))
        self.metadata.setMetadataPair(metadata.METADATA_ORBIT, aOrbit)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, aCountry)
        self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LONGITUDE_GRID_NORMALISED, "urn:esa:eop:country")
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, aCity)
        self.metadata.setMetadataPair(metadata.METADATA_CODESPACE_WRS_LATITUDE_GRID_NORMALISED, "urn:esa:eop:city")

        # according to Kompsat1 spec, start time same as end time and time position
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, aDate)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, aTime)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%sZ" % (aDate, aTime))
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (aDate, aTime))

        # refine
        self.refineMetadata(processInfo)

        numAdded = 0

        self.metadata = met
        self.buildTypeCode(processInfo)

        # set local attribute for the one with boundingbox
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TYPECODE)

    def makeBrowses(self, processInfo):

        anEosip = processInfo.destProduct
        browseName = anEosip.getEoProductName()

        self.browseDestPath = os.path.join(processInfo.workFolder, browseName + '.BI.PNG')
        self.makePngFromTif(self.path, self.browseDestPath, 1, processInfo)

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
    # refine the metada
    #
    def refineMetadata(self, processInfo):
        # footprint
        self.browseDestPath = os.path.join(processInfo.workFolder, 'for_footprint.tif')
        tmp_tif_path = self.makePngFromTif(self.browseSrcPath, self.browseDestPath, 0, processInfo)
        self.extractFootprint(tmp_tif_path, processInfo)

    #
    # extract quality
    #
    def extractQuality(self, helper):
        pass

    def extractFootprint(self, aPath, processInfo):

        # correct
        ul, ll, ur, lr = self.getGdalInfoCoordinates(aPath, processInfo)
        self.metadata.setMetadataPair('ul', ul)
        self.metadata.setMetadataPair('ll', ll)
        self.metadata.setMetadataPair('ur', ul)
        self.metadata.setMetadataPair('lr', lr)

        footprint = "%s %s %s %s %s %s %s %s %s %s" % \
                    (
                        ul.split(' ')[1],
                        ul.split(' ')[0],

                        ll.split(' ')[1],
                        ll.split(' ')[0],

                        lr.split(' ')[1],
                        lr.split(' ')[0],

                        ur.split(' ')[1],
                        ur.split(' ')[0],

                        ul.split(' ')[1],
                        ul.split(' ')[0],
                    )

        #
        print(("FOOTPRINT: %s" % footprint))

        #
        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(footprint)
        browseIm.calculateBoondingBox()
        self.metadata.addLocalAttribute('boundingBox', browseIm.boondingBox)
        self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        try:
            verifier.verifyFootprint(footprint, True)  # all descending
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS NOT REVERESED")
            if self.debug:
                print((" #### footprint non reversed:%s" % footprint))
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(("verifyFootprint step 0 '%s' error: %s; %s" % (footprint, exc_type, exc_obj)))
            traceback.print_exc(file=sys.stdout)
            reversed = browseIm.reverseFootprint()
            if self.debug:
                print(("verifyFootprint step 1 '%s'" % (reversed)))
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
            if self.debug:
                print((" #### footprint ok from reversed:%s" % reversed))

        # get center
        # make sure the footprint is CCW
        if self.debug != 0:
            print("browseIm:%s" % browseIm.info())
        if not browseIm.getIsCCW():
            # reverse
            if self.debug != 0:
                print("############### reverse the footprint; before:%s" % (footprint))
            browseIm.reverseFootprint()
            if self.debug != 0:
                print("###############             after;%s" % (browseIm.getFootprint()))
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, browseIm.getFootprint())
        else:
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        flat, flon = browseIm.calculateCenter()
        flat = float(flat)
        flon = float(flon)
        #
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (flat, flon))

        #
        mseclon = abs(int((flon - int(flon)) * 1000))
        mseclat = abs(int((flat - int(flat)) * 1000))
        if flat < 0:
            flat = "S%s" % formatUtils.leftPadString("%s" % abs(int(flat)), 2, '0')
        else:
            flat = "N%s" % formatUtils.leftPadString("%s" % int(flat), 2, '0')
        if flon < 0:
            flon = "W%s" % formatUtils.leftPadString("%s" % abs(int(flon)), 3, '0')
        else:
            flon = "E%s" % formatUtils.leftPadString("%s" % int(flon), 3, '0')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclat), 3, '0'))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED,
                                      formatUtils.leftPadString("%s" % int(mseclon), 3, '0'))

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
