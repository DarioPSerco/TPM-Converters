# -*- coding: cp1252 -*-
#
# this class represent a cartosat1 IMAGE product
#
#  - 
#  - 
#
#
import os
import platform
import sys
import traceback
import zipfile
from datetime import datetime
from subprocess import call

import eoSip_converter.esaProducts.verifier as verifier
import eoSip_converter.osPlatform as osPlatform
import eoSip_converter.xmlHelper as xmlHelper
from eoSip_converter.esaProducts import browse_metadata, formatUtils, metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product import Product
from xml_nodes import rep_footprint

OP_SYS = platform.system()
REF_TYPECODES = ['PAN_PAM_3O']

# browses from .zip
QUICKLOOK_SUFFIX = '_ql.tif'
# metadata
METADATA_SUFFIX = '_metadata.xml'

#
GDAL_STEP_0 = 'gdalwarp -overwrite -ts 1800 0 -t_srs EPSG:4326 -ot Int16 @SRC @DEST'
GDAL_STEP_1 = 'gdal_translate -of png -ot byte @SRC @DEST'


#
#
#
def writeShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif [ $? -ne 0 ]; then\n  exit %s\nfi\n" % (tmp, badExitCode)
    return tmp

def writePowerShellCommand(command, testExit=False, badExitCode=-1):
    tmp = "%s\n" % command
    if testExit:
        tmp = "%sif ($LASTEXITCODE -ne 0) {\n    exit %s\n}\n" % (tmp, badExitCode)

    return tmp


#
#
#
class Product_Cartosat_Image(Product):
    #
    xmlMapping = {
        # metadata.METADATA_START_DATE: 'Production/DATASET_PRODUCTION_DATE',
        'DATASET_NAME': 'Production/DATASET_NAME',
        metadata.METADATA_PROCESSING_LEVEL: 'Production/DATASET_PRODUCT_LEVEL',
        metadata.METADATA_PROCESSING_TYPE: 'Production/DATASET_PRODUCT_TYPE',
        metadata.METADATA_SENSOR_NAME: 'Production/DATASET_SENSOR',
    }

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        #
        if not self.path.endswith('.zip'):
            raise Exception("product has bad extension, expected .zip:'%s'" % self.path)

        self.site = None
        self.metadataFile = None
        self.metadataPath = None
        self.metadataContent = None

        #
        self.TifMap = {}  # name, path

        #
        self.browseIm = None

        #
        self.browseSrcPath = None
        self.browseDestPath = None

        #
        self.gdalInfo = None

        if self.debug != 0:
            print(" init class Product_Cartosat_Image")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    #
    #
    def use_gdal(self, command, n, processInfo):
        commandFile = "%s/command_%s.%s" % (processInfo.workFolder, n, 'ps1' if OP_SYS == "Windows" else 'sh')
        with open(commandFile, 'wt') as fd:
            fd.write(command)

        if OP_SYS == "Windows":
            command = "powershell -File \"%s\" 2>&1 | Tee-Object -FilePath \"%s/command_%s.stdout\"" % (commandFile, processInfo.workFolder, n)
        else:
            command = "/bin/bash -f %s 2>&1 | tee %s/command_%s.stdout" % (commandFile, processInfo.workFolder, n)

        try:
            if self.debug != 0:
                print("COMMAND_%s=%s" % (n, command))
            retval, out = osPlatform.runCommand(command, useShell=False if OP_SYS == 'Windows' else True)
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
            # self.gdalInfo = subprocess.check_output(['gdalinfo', aPath])
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
            if OP_SYS == 'Windows':
                retval, out = self.use_gdal('gdalinfo "%s"' % aPath, 1, processInfo)
            else:
                retval, out = self.use_gdal('/bin/bash -c "gdalinfo %s"' % aPath, 1, processInfo)

            if isinstance(out, bytes):
                out = out.decode()

            if retval == 0:
                self.gdalInfo = out
        if self.gdalInfo is not None:
            print(("gdalInfo: %s" % self.gdalInfo))
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

            # ul = " ".join(ul.split(' '))
            # ll = " ".join(ll.split(' '))
            # ur = " ".join(ur.split(' '))
            # lr = " ".join(lr.split(' '))
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

    #
    #
    #
    def makePngFromTif(self, browseSrcPath, browseDestPath, item, processInfo):
        destPathBase = browseDestPath.replace('.PNG', '_')

        # convert to png
        command = GDAL_STEP_0.replace('@SRC', browseSrcPath)
        piece = "%s_warped.tif" % destPathBase
        command1 = command.replace('@DEST', piece)

        write_command_func = writePowerShellCommand if OP_SYS == 'Windows' else writeShellCommand
        if item > 0:
            command = GDAL_STEP_1.replace('@SRC', piece)
            command2 = command.replace('@DEST', browseDestPath)
            commands = "%s%s" % (
                write_command_func(command1, True),
                write_command_func(command2, True)
            )

        else:
            commands = write_command_func(command1, True)

        if OP_SYS == 'Windows':
            commands = '%s\nWrite-Host\nWrite-Host\nWrite-Host "browse done"' % commands
        else:
            commands = "%s\necho\necho\necho 'browse done'" % commands

        commandFile = "%s/command_browse_%s.%s" % (processInfo.workFolder, item, 'ps1' if OP_SYS == 'Windows' else 'sh')
        with open(commandFile, 'wt') as fd:
            if OP_SYS == "Windows":
                fd.write('Write-Host "starting..."\n\nWrite-Host "PATH is:$env:PATH"\nGet-ChildItem Env:\n\n')
            else:
                fd.write("""#!/bin/bash\necho starting...\n\necho "PATH is:$PATH"\nset\n\n""")
            fd.write(commands)

        # launch the main make_browse script:
        if OP_SYS == 'Windows':
            command = "powershell -file %s  > %s/command_browse_%s.log 2>&1" % (commandFile, processInfo.workFolder, item)
        else:
            command = "/bin/bash -f %s 2>&1 > %s/command_browse_%s.log" % (commandFile, processInfo.workFolder, item)

        retval = call(command, shell=True)
        if self.debug:
            print("  external make browse exit code:%s" % retval)
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)
        print(" external make browse exit code:%s" % retval)

        #
        if item == 0:
            return piece
        else:
            return browseDestPath

    #
    # use _ql.tif to make a PNG
    # reproject it
    #
    def makeBrowses(self, processInfo):
        anEosip = processInfo.destProduct
        browseName = anEosip.getEoProductName()
        self.browseDestPath = os.path.join(processInfo.workFolder, browseName + '.BI.PNG')

        # imageUtil.makeBrowse('PNG', self.browseSrcPath, self.browseDestPath)
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

        processInfo.addLog(" browse image choice created:browseChoiceBlock=\n%s" % browseChoiceBlock)

    #
    # extract the product
    #
    def extractToPath(self, folder=None, dont_extract=False):
        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print((" Will extract directory product '%s' to path:%s" % (self.path, folder)))

        if not os.path.exists(folder):
            raise Exception("destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print((" will extract product to path:%s" % folder))

        self.EXTRACTED_PATH = "%s/EO_product" % folder
        if not os.path.exists(self.EXTRACTED_PATH):
            os.makedirs(self.EXTRACTED_PATH)
        #
        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)
        #
        n = 0
        numQl = 0
        for name in z.namelist():
            n += 1
            if name.endswith(QUICKLOOK_SUFFIX):
                self.browseSrcPath = self.EXTRACTED_PATH + '/' + os.path.basename(name)
                if not dont_extract:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(self.browseSrcPath, 'wb')
                    outfile.write(z.read(name))
                    outfile.close()
                numQl += 1

            elif name.endswith(METADATA_SUFFIX):
                self.metadata_content = z.read(name)
                self.metadata_path = self.EXTRACTED_PATH + '/' + os.path.basename(name)
                if not dont_extract:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(self.metadata_path, 'wb')
                    outfile.write(self.metadata_content)
                    outfile.close()

            # self.contentList.append(name)
        z.close()
        fh.close()

        if numQl == 0:
            raise Exception("no quicklook found")
        elif numQl > 1:
            raise Exception("too many quicklook found: %s" % numQl)

        # print(" #### extract done; TifMap:%s" % self.TifMap)
        print((" extract done; metadata file:%s; quicklook file: %s" % (self.metadataPath, self.browseSrcPath)))

        """print("gdalInfo: %s" % gdalInfo)
        ul = None
        ll = None
        ur = None
        lr = None
        for item in gdalInfo.split('\n'):
            if item.startswith('Upper Left'):
                ul = item.split('(')[1].replace(')', '').replace(',', '').strip()
            elif item.startswith('Lower Left'):
                ll = item.split('(')[1].replace(')', '').replace(',', '').strip()
            elif item.startswith('Upper Right'):
                ur = item.split('(')[1].replace(')', '').replace(',', '').strip()
            elif item.startswith('Lower Right'):
                lr = item.split('(')[1].replace(')', '').replace(',', '').strip()
        print("ul: %s" % ul)
        print("ll: %s" % ll)
        print("ur: %s" % ur)
        print("lr: %s" % lr)"""

    #
    #   Extracts the first set of metadata.
    #   The extraction is performed on the 'workreport' file, a plain-text (similar to properties) file.
    #
    def extractMetadata(self, met=None, processInfo=None):
        # get site from product parent folder
        self.site = os.path.basename(os.path.dirname(self.path))
        print((" site: %s" % self.site))
        met.addLocalAttribute('site', self.site)

        if len(self.metadata_content) == 0:
            raise Exception("no metadata to be parsed")

        # extact metadata
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

        self.metadata = met

        #
        aData = None
        nodes = []
        helper.getNodeByPath(None, 'Acquisition/Acquisition_Parameter', None, nodes)
        if len(nodes) == 0:
            raise Exception("no Acquisition/Acquisition_Parameter node found")
        for item in nodes:
            aData = helper.getFirstNodeByPath(item, 'ACQUISITION_PARAMETER_CODE', None)
            if aData is not None:
                aValue = helper.getNodeText(aData)
                print((" #### ACQUISITION_PARAMETER_CODE %s value: %s" % (aData, aValue)))
                if aValue == 'Orbit_no':
                    aData2 = helper.getFirstNodeByPath(item, 'ACQUISITION_PARAMETER_VALUE', None)
                    if aData2 is not None:
                        aValue2 = helper.getNodeText(aData2)
                        met.setMetadataPair(metadata.METADATA_ORBIT, aValue2)
                        print((" ## metadata.METADATA_ORBIT: %s" % aValue2))

                elif aValue == 'Sun_azimuth':
                    aData2 = helper.getFirstNodeByPath(item, 'ACQUISITION_PARAMETER_VALUE', None)
                    if aData2 is not None:
                        aValue2 = helper.getNodeText(aData2)
                    met.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, aValue2)
                    print((" ## metadata.METADATA_SUN_AZIMUTH: %s" % aValue2))

                elif aValue == 'Sun_elevation':
                    aData2 = helper.getFirstNodeByPath(item, 'ACQUISITION_PARAMETER_VALUE', None)
                    if aData2 is not None:
                        aValue2 = helper.getNodeText(aData2)
                    met.setMetadataPair(metadata.METADATA_SUN_ELEVATION, aValue2)
                    print((" ## metadata.METADATA_SUN_ELEVATION: %s" % aValue2))
            else:
                raise Exception("no ACQUISITION_PARAMETER_CODE node found")
        # os._exit(1)

        # size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        # get date from tiff info: format: 2020:02:03 12:34:57
        # tif_date = self.getGdalInfoMetadata(self.browseSrcPath, 'TIFFTAG_DATETIME', processInfo)
        # print("tif_date: %s" % tif_date)
        # met.setMetadataPair('tif_date', tif_date)
        # met.setMetadataPair(metadata.METADATA_START_DATE, tif_date.split(' ')[0].replace(':', '-'))
        # met.setMetadataPair(metadata.METADATA_STOP_DATE, tif_date.split(' ')[0].replace(':', '-'))

        met.setMetadataPair(metadata.METADATA_STOP_DATE, met.getMetadataValue(metadata.METADATA_START_DATE))

        # os._exit(0)

        #
        self.refineMetadata(processInfo)

        #
        self.buildTypeCode(processInfo)

        return met

    #
    # extract the footprint
    #
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
        # footprint = '-24.560 294.045 -24.828 293.982 -24.888 294.275 -24.619 294.338 -24.560 294.045'
        print(("FOOTPRINT: %s" % footprint))
        # os._exit(1)

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
                print(("verifyFootprint step 1 '%s'" % reversed))
            verifier.verifyFootprint(reversed, True)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, reversed)
            self.metadata.setMetadataPair("FOOTPRINT", "FOOTPRINT IS REVERESED")
            if self.debug:
                print((" #### footprint ok from reversed:%s" % reversed))

        clat, clon = browseIm.calculateCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))
        flon = float(clon)
        flat = float(clat)
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

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo):
        # start and stop
        if 1 == 2:
            aTime = "00:00:00"
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, aTime)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, aTime)

            aDate = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%sZ" % (aDate, aTime))

            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, aDate)
            self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (aDate, aTime))
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%s" % (aDate, aTime))

        tmp = self.metadata.getMetadataValue(
            'DATASET_NAME')  # like: IR05_PAN_PA__3O_20100801T084046_20100801T084050_NSG_28364_3181.TIF
        startDate = tmp[len("IR05_PAN_PA__3O_"):len("IR05_PAN_PA__3O_") + 8]
        startTime = tmp[len("IR05_PAN_PA__3O_") + 9:len("IR05_PAN_PA__3O_") + 15]
        stopDate = tmp[len("IR05_PAN_PA__3O_20100801T084046_"):len("IR05_PAN_PA__3O_20100801T084046_") + 8]
        stopTime = tmp[len("IR05_PAN_PA__3O_20100801T084046_") + 9:len("IR05_PAN_PA__3O_20100801T084046_") + 15]
        print(("startDate=%s; startTime=%s; stopDate=%s; stopTime=%s" % (startDate, startTime, stopDate, stopTime)))
        # os._exit(1)
        startDate = "%s-%s-%s" % (startDate[0:4], startDate[4:6], startDate[6:8])
        startTime = "%s:%s:%s" % (startTime[0:2], startTime[2:4], startTime[4:6])
        stopDate = "%s-%s-%s" % (stopDate[0:4], stopDate[4:6], stopDate[6:8])
        stopTime = "%s:%s:%s" % (stopTime[0:2], stopTime[2:4], stopTime[4:6])
        print(("startDate=%s; startTime=%s; stopDate=%s; stopTime=%s" % (startDate, startTime, stopDate, stopTime)))

        # os._exit(1)

        # Validate the date format
        DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE_TIME, "%sT%sZ" % (startDate, startTime))
        try:
            datetime.strptime("%sT%sZ" % (startDate, startTime), DEFAULT_DATE_PATTERN)
            print("Date format is valid.")
        except ValueError:
            raise Exception("Start date format is invalid: ", "%sT%sZ" % (startDate, startTime))

        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE_TIME, "%sT%sZ" % (stopDate, stopTime))
        try:
            datetime.strptime("%sT%sZ" % (stopDate, stopTime), DEFAULT_DATE_PATTERN)
            print("Date format is valid.")
        except ValueError:
            raise Exception("Stop date format is invalid: ", "%sT%sZ" % (stopDate, stopTime))

        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (stopDate, stopTime))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, startDate)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stopDate)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, startTime)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stopTime)

        # make a reprojected tif, to get the footprint info
        self.browseDestPath = os.path.join(processInfo.workFolder, 'for_footprint.tif')
        tmp_tif_path = self.makePngFromTif(self.browseSrcPath, self.browseDestPath, 0, processInfo)
        self.extractFootprint(tmp_tif_path, processInfo)

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
