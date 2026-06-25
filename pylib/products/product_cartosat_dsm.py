# -*- coding: cp1252 -*-
#
# this class represent a Cartosat1 DSM product
#
#  - 
#  - 
#
#
import json
import os
import platform
import sys
import traceback
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from subprocess import call

import eoSip_converter.geomHelper as geomHelper
import eoSip_converter.utils.shellUtils as shutils
from eoSip_converter import osPlatform
from eoSip_converter.esaProducts import browse_metadata, metadata
from eoSip_converter.esaProducts.browseImage import BrowseImage
from eoSip_converter.esaProducts.product import Product
from eoSip_converter.data.shapefile.utils.shapeJson import shapeToJson
from xml_nodes import rep_footprint

REF_TYPECODES = ['DSM_DEM_3D']

# browses from .zip
QUICKLOOK_SUFFIX = '_dsm.tif'
ACV_SUFFIX = '_acv.tif'

# for .png generation
GDAL_STEP_0 = 'gdalwarp -ts 1800 0 -t_srs EPSG:4326 @SRC @DEST'
GDAL_STEP_1 = 'gdal_translate -of png @SRC @DEST'
# for footprint generation
GDAL_FOOTPRINT_STEP_0 = 'gdalwarp -srcnodata 255 -dstnodata 0 -t_srs EPSG:4326 -dstalpha -of GTiff @SRC @TMP_TIF'
GDAL_FOOTPRINT_STEP_1 = 'gdal_polygonize.py @TMP_TIF -b 2 -8 -f "ESRI Shapefile"  @TMP_SHP'


OP_SYS = platform.system()

#
#
#
class Product_Cartosat_Dsm(Product):

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        #
        if not self.path.endswith('.zip'):
            raise Exception("product has bad extension, expected .zip:'%s'" % self.path)

        #
        self.site = None
        self.browseSrcPath = None
        self.browseDestPath = None
        self.acvSrcPath = None

        if self.debug != 0:
            print(" init class Product_Cartosat_Image")

    #
    # called at the end of the doOneProduct, before the index/shopcart creation
    #
    def afterProductDone(self):
        pass

    #
    # read metadata file
    #
    def getMetadataInfo(self):
        pass

    #
    #
    #
    def makePngFromTif(self, browseDestPath, processInfo):
        if OP_SYS == 'Windows':
            write_cmd = shutils.writePowershellCommand
            run_cmds = shutils.run_powershell_commands
        else:
            write_cmd = shutils.writeShellCommand
            run_cmds = shutils.run_shell_commands

        destPathBase = browseDestPath.replace('.PNG', '_')
        # convert to png
        command = GDAL_STEP_0.replace('@SRC', self.browseSrcPath)
        warpedTif = "%s_warped.tif" % destPathBase
        warpedPng = "%s_warped.png" % destPathBase
        if os.path.exists(warpedTif):
            os.remove(warpedTif)
        command1 = command.replace('@DEST', warpedTif)

        command2 = GDAL_STEP_1.replace('@SRC', warpedTif).replace('@DEST', warpedPng)

        command3 = "%s -stretch %s %s 0.02" % (self.stretcherAppExe, warpedPng, browseDestPath)

        commands = "%s%s%s" % (
            write_cmd(command1, True, -1, "warp"),
            write_cmd(command2, True, -1, "translate"),
            write_cmd(command3, True, -1, "translate")
        )

        if OP_SYS == 'Windows':
            commands += '\nWrite-Host " "\nWrite-Host " "\nWrite-Host "browse done"'
        else:
            commands += "\necho\necho\necho 'browse done'"

        retval = run_cmds(commands, processInfo.workFolder, "make browse")
        if self.debug:
            print(("  external make browse exit code:%s" % retval))
        if retval != 0:
            raise Exception("Error generating browse, exit coded:%s" % retval)

        return browseDestPath

    #
    # read metadata file
    #
    # def getMetadataInfo(self):
    #     pass

    # def use_gdal(self, command, n, processInfo):
    #     commandFile = "%s/command_%s.sh" % (processInfo.workFolder, n)
    #     fd = open(commandFile, 'w')
    #     fd.write(command)
    #     fd.close()
    #     command = "/bin/bash -f %s 2>&1 | tee %s/command_%s.stdout" % (commandFile, processInfo.workFolder, n)
    #
    #     try:
    #         if self.debug != 0:
    #             print("COMMAND_%s=%s" % (n, command))
    #         retval, out = osPlatform.runCommand(command, useShell=True)
    #         if retval != 0:
    #             raise Exception("Error running use_gdal external-call, exit code:%s; %s" % (retval, out))
    #         return retval, out
    #     except:
    #         exc_type, exc_obj, exc_tb = sys.exc_info()
    #         print(" ERROR running use_gdal external-call :%s %s" % (exc_type, exc_obj))
    #         traceback.print_exc(file=sys.stdout)
    #         raise Exception(" ERROR running use_gdal external-call:%s %s" % (exc_type, exc_obj))

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
    def getGdalInfoMetadata_NOT_USED(self, aPath, aMetadata, processInfo):
        if self.gdalInfo is None:
            import subprocess
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
        # retval, gdalInfo = self.use_gdal('/bin/bash -c "gdalinfo %s"' % aPath, 1, processInfo)

        if OP_SYS == 'Windows':
            retval, gdalInfo = self.use_gdal('gdalinfo "%s"' % aPath, 1, processInfo)
        else:
            retval, gdalInfo = self.use_gdal('/bin/bash -c "gdalinfo %s"' % aPath, 1, processInfo)

        if retval != 0:
            raise Exception("gdalinfo error: " % retval)
        if gdalInfo is not None:
            gdalInfo = gdalInfo if isinstance(gdalInfo, str) else gdalInfo.decode()
            print(("gdalInfo: %s" % gdalInfo))
            ul = None
            ll = None
            ur = None
            lr = None
            for item in gdalInfo.split('\n'):
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

    #
    # use _ql.tif to make a PNG
    #
    def makeBrowses(self, processInfo):

        anEosip = processInfo.destProduct
        browseName = anEosip.getEoProductName()
        self.browseDestPath = os.path.join(processInfo.workFolder, browseName + '.BI.PNG')
        self.makePngFromTif(self.browseDestPath, processInfo)

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
            print((" Will extract product to path:%s" % folder))

        self.EXTRACTED_PATH = "%s/EO_product" % folder
        if not os.path.exists(self.EXTRACTED_PATH):
            os.makedirs(self.EXTRACTED_PATH)

        #
        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)
        #
        n = 0
        numQl = 0
        numAcv = 0
        for name in z.namelist():
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

            elif name.endswith(ACV_SUFFIX):
                self.acvSrcPath = self.EXTRACTED_PATH + '/' + os.path.basename(name)
                if not dont_extract:
                    parent = os.path.dirname(self.EXTRACTED_PATH + '/' + name)
                    if not os.path.exists(parent):
                        os.makedirs(parent)
                    outfile = open(self.acvSrcPath, 'wb')
                    outfile.write(z.read(name))
                    outfile.close()
                    numAcv += 1

            n += 1
            self.contentList.append(name)
        z.close()
        fh.close()

        if numAcv == 0:
            raise Exception("no xx_acv.tif found")

        if numQl == 0:
            raise Exception("no quicklook found")
        elif numQl > 1:
            raise Exception("too many quicklook found: %s" % numQl)

        print((" extract done; num of files: %s" % len(self.contentList)))
        print((" extract done; files: %s" % self.contentList))

    #
    # <Internal-ID><Mission><Area>___<Format><Version>.<Extension>
    # E.g. 094638P5020E045NPC___G4.zip
    #
    def getMetadaFromZipPackage(self):
        basename = os.path.basename(self.path)
        print(("getMetadaFromZipPackage from: %s" % basename))
        toks = basename.split('___')
        p_id = toks[0][0:6]
        p_mission = toks[0][6:8]
        p_area = toks[0][8:18]  # like: 020E045N
        p_format = toks[1][0]
        p_version = toks[1][1]

        if self.debug != 0:
            print((" ##### getMetadaFromZipPackage; p_id: %s, p_mission:%s, p_area: %s; p_format: %s; p_version=%s" % (
                p_id, p_mission, p_area, p_format, p_version)))

        self.metadata.setMetadataPair('p_id', p_id)
        self.metadata.setMetadataPair('area', p_area)
        self.metadata.setMetadataPair('p_mission', p_mission)
        self.metadata.setMetadataPair('p_format', p_format)
        self.metadata.setMetadataPair('p_version', p_version)

        flon = "%s%s" % (p_area[3], p_area[0:3])
        flat = "%s%s" % (p_area[7], p_area[5:7])

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_DEG_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_DEG_NORMALISED, flon)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_MDEG_NORMALISED, '000')
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_MDEG_NORMALISED, '000')

        self.metadata.setMetadataPair(metadata.METADATA_WRS_LATITUDE_GRID_NORMALISED, flat)
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED, flon)

        # os._exit(1)

    #
    # <Product-family>_<Internal-ID>_<QC-date>_<Area>_<Layer-name>.<Extension>
    # E.g. em3d_094638_20191213_020E045NPC_dsm.tif
    #
    def getMetadaFromFilename(self, filename):
        print(("getMetadaFromFilename from: %s" % filename))
        toks = filename.split('_')
        p_family = toks[0]
        p_id = toks[1]
        p_date = toks[2]
        p_area = toks[3][0:10]
        p_layer = toks[4]
        if self.debug:
            print((" ##### getMetadaFromFilename; p_family: %s; p_id: %s, p_date: %s, p_area: %s; p_layer: %s" % (
                p_family, p_id, p_date, p_area, p_layer)))

        self.metadata.setMetadataPair('p_date', p_date)
        self.metadata.setMetadataPair('quadrant', p_area[-1])

    def search_for_xml(self, start_dir):
        dataset_names = []
        for root, dirs, files in os.walk(start_dir):
            for file in files:
                if file.endswith('.zip'):
                    with zipfile.ZipFile(os.path.join(root, file), 'r') as zip_ref:
                        for zip_info in zip_ref.infolist():
                            if zip_info.filename.endswith('/'):
                                continue
                            if zip_info.filename.endswith('.xml'):
                                with zip_ref.open(zip_info.filename) as xml_file:
                                    xml_tree = ET.parse(xml_file)
                                    xml_root = xml_tree.getroot()
                                    dataset_name = xml_root.find('.//DATASET_NAME').text
                                    dataset_names.append(dataset_name)
                elif file.endswith('.xml'):
                    xml_tree = ET.parse(os.path.join(root, file))
                    xml_root = xml_tree.getroot()
                    dataset_name = xml_root.find('.//DATASET_NAME').text
                    dataset_names.append(dataset_name)
        return dataset_names

    #
    #   Extracts the first set of metadata.
    #   The extraction is performed on the 'workreport' file, a plain-text (similar to properties) file.
    #
    def extractMetadata(self, met=None, processInfo=None):
        # get site from product parent folder
        self.site = os.path.basename(os.path.dirname(self.path))
        print((" site: %s" % self.site))
        met.addLocalAttribute('site', self.site)

        self.metadata = met

        # size
        self.size = os.stat(self.path).st_size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.size)

        self.getMetadaFromZipPackage()
        self.getMetadaFromFilename(os.path.basename(self.contentList[-1]))
        # set 2 digit version
        quadrant = self.metadata.getMetadataValue('quadrant')
        version = self.metadata.getMetadataValue('p_version')
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_VERSION, "%s%s" % (version, quadrant))

        self.refineMetadata(processInfo)
        #
        self.buildTypeCode(processInfo)

        return met

    #
    # extract the footprint:
    # - use nodata from tif to create an alpha mask
    # - polygonize into a shapefile
    # - simplify the shapefile
    # - transform to json, then read the coordinates
    #
    def extractFootprint(self, processInfo):
        if OP_SYS == 'Windows':
            write_cmd = shutils.writePowershellCommand
            run_cmds = shutils.run_powershell_commands
        else:
            write_cmd = shutils.writeShellCommand
            run_cmds = shutils.run_shell_commands

        tmp_tif = os.sep.join([
            processInfo.workFolder,
            os.path.basename(self.acvSrcPath)
                   .replace(ACV_SUFFIX, '_acv_nodata.tif')
        ])

        if os.path.exists(tmp_tif):
            os.remove(tmp_tif)

        command = GDAL_FOOTPRINT_STEP_0.replace('@SRC', self.acvSrcPath)\
                                       .replace('@TMP_TIF', tmp_tif)
        commands = write_cmd(command, True, -1, "make alpha nodata tif")

        final_shp = os.sep.join([
            processInfo.workFolder,
            os.path.basename(self.acvSrcPath)
                   .replace(ACV_SUFFIX, '_acv_nodata_final.shp')
        ])

        tmp_shp = os.sep.join([
            processInfo.workFolder,
            os.path.basename(self.acvSrcPath)
                   .replace(ACV_SUFFIX, '_acv_nodata.shp')
        ])

        command = GDAL_FOOTPRINT_STEP_1.replace('@TMP_TIF', tmp_tif)\
                                       .replace("@TMP_SHP", final_shp)
        commands = "%s%s" % (
            commands,
            write_cmd(command, True, -1, "polygonize to .shp")
        )

        if OP_SYS == 'Windows':
            commands += "\n\nWrite-Host \"done\""
        else:
            commands += "\n\necho 'done'"

        retval = run_cmds(commands, processInfo.workFolder, "get footprint")

        if self.debug:
            print(("  external get footprint exit code:%s" % retval))

        if retval != 0:
            # raise Exception("Error external get footprint, exit coded:%s" % retval)
            print(("  external get footprint exit code:%s" % retval))

        # make a json out of the shapefile
        final_geojson = os.sep.join([
            processInfo.workFolder,
            os.path.basename(self.acvSrcPath)
                   .replace(ACV_SUFFIX, '_acv_nodata_final.geojson')
        ])
        shapeToJson(final_shp, final_geojson)

        # get coordinates from geojson
        with open(final_geojson, 'rt') as fd:
            data = json.load(fd)

        print((" JSON: %s" % data))

        # build boundingbox from source product gdalinfo
        # correct
        ul, ll, ur, lr = self.getGdalInfoCoordinates(tmp_tif, processInfo)
        self.metadata.setMetadataPair('ul', ul)
        self.metadata.setMetadataPair('ll', ll)
        self.metadata.setMetadataPair('ur', ul)
        self.metadata.setMetadataPair('lr', lr)

        # with last point repeated for closed polygon (var used as footprint for certain products)
        #
        bboxForFootprint = "%s %s %s %s %s %s %s %s %s %s" % \
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

        # bbox with 4 coord pairs
        #
        bbox = "%s %s %s %s %s %s %s %s" % \
               (
                   ul.split(' ')[1],
                   ul.split(' ')[0],

                   ll.split(' ')[1],
                   ll.split(' ')[0],

                   lr.split(' ')[1],
                   lr.split(' ')[0],

                   ur.split(' ')[1],
                   ur.split(' ')[0],

               )

        # self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, bbox)
        # self.metadata.addLocalAttribute('boundingBox', bbox)

        # some products contain additional feature geometries which are very small. 
        # filter feature geometries in data['features'] so that only those with more than 40 individual coordinate counts remain
        #
        try:
            if len(data['features']) > 1:
                data['features'] = [feature for feature in data['features'] if
                                    len([coord for sublist in feature['geometry']['coordinates'] for coord in
                                         sublist]) >= 40]
            else:
                pass

        except KeyError:
            print("Invalid GeoJSON format. Unable to access required keys.")

        # coordinates = data['features'][0]
        # print(" coordinates 0 : %s" % coordinates)
        # print(" JSON: %s" % data)

        # Some products contain appending polygons which are very small. These are expressed as nested coordinates in the geojson.
        # Similar to the last solution, we want to remove smaller appending polygons from the main shape. 
        # We do this by filtering out any smaller sets of nested coordinates from the geojson
        #
        coordinates1 = data['features'][0]['geometry']['coordinates']
        try:
            if len(coordinates1) > 1:
                reduced_coordinates = []
                for list in coordinates1:
                    for coords in list:
                        if len(coords) > 40:
                            reduced_coordinates.extend(coords)
                data['features'][0]['geometry']['coordinates'] = [reduced_coordinates]
                coordinates1 = [reduced_coordinates]


        except KeyError:
            print("Invalid GeoJSON format. Unable to access required keys.")

        # Since these touch off the main polygon, we can subsume their coordinates into the larger footprint
        #
        # if len(coordinates1) > 1:
        #    combined_coordinates = []
        #    for coords in coordinates1:
        #        combined_coordinates.extend(coords)
        #    data['features'][0]['geometry']['coordinates'] = combined_coordinates
        #    coordinates1 = combined_coordinates

        # If no features remain, raise an error
        #
        if len(data['features']) == 0:
            raise ValueError("No features detected in footprint geojson")

        # If more than one set of coords exists for a feature at this stage, raise an error
        #
        elif len(data['features'][0]['geometry']['coordinates']) == 0:
            raise ValueError("No polygon detected in footprint geojson")

        # some products contain multiple large feature geometries, so we should not filter out significantly large shapes
        # If there is still more than one feature in the list, expand the footprint to be the bounding box, so that they are all encompased within the one enlarged footprint
        #
        if len(data['features']) != 1:

            footprint = bboxForFootprint
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)


        # else the product just has a single shapefile, in which case we build its footprint as is
        #
        else:
            # build footprint
            footprint = ""
            n = 0
            np = 0
            for poly in coordinates1:
                for pair in poly:
                    print((" pair[%s]: %s" % (n, pair)))
                    if len(footprint) > 0:
                        footprint += " "
                    footprint += "%s %s" % (pair[1], pair[0])
                    n += 1
                np += 1
            print((" number of poly: %s" % np))
            print((" number of pair: %s" % n))
            print((" footprint: %s" % footprint))
            self.metadata.setMetadataPair("not_reduced_footprint", footprint)

            numPoints = len(footprint.split(" ")) / 2
            n = 0
            while numPoints > 40:
                print(" #### getCorners for num coords: %s" % (len(footprint.split(" ")) / 2))
                footprint = geomHelper.getCorners(footprint, 5)
                numPoints = len(footprint.split(" ")) / 2
                n += 1

            # footprint = self.filter_consecutive_pairs(footprint)

            if '123954P5001E049NPD___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # Belgrade
            elif '094638P5020E045NPC___G4' in self.path:
                footprint = "44.9968594633 20.3798333415 44.9967082821 20.239990762 44.9966578884 20.2395876122 44.9967082821 20.2395372185 44.9966578884 20.2391340687 45.0186799451 20.2466427333 45.01888152 20.2467435207 45.0190830949 20.2467939145 45.0193350635 20.2468947019 44.9968594633 20.3798333415"
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            else:
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

            # Donetsk
            if '086591P5037E047NPB___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # Kaunas
            if '102408P5024E055NPC___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # Napoli
            if '112784P5014E040NPB___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # Tiraspol
            if '088698P5029E047NPD___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # Ankara
            if '129266P5032E040NPD___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)
            # London
            if '133517P5001W051NPC___G4' in self.path:
                footprint = bboxForFootprint
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        #
        browseIm = BrowseImage()
        self.browseIm = browseIm
        browseIm.setFootprint(bboxForFootprint)
        # browseIm.setFootprint(bbox)
        # browseIm.calculateBoondingBox()
        # self.metadata.addLocalAttribute('boundingBox', browseIm.boondingBox)

        clat, clon = browseIm.calculateCenter()
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (clat, clon))

        # bounding box should only be included if it's not the same as the footprint
        #
        if footprint != bboxForFootprint:
            self.metadata.setMetadataPair(metadata.METADATA_BOUNDING_BOX, bbox)
            self.metadata.addLocalAttribute('boundingBox', bbox)

    def filter_consecutive_pairs(self, footprint):
        filtered_list = []
        prev_pair = None

        for i in range(0, len(footprint), 14):
            pair = footprint[i:i + 13]
            if pair != prev_pair:
                filtered_list.append(pair)
            prev_pair = pair

        return [filtered_list]

    #
    # Refine the metadata.
    #
    def refineMetadata(self, processInfo):

        print(("Full path: %s" % self.path))
        start_dir = os.path.dirname(self.path)
        print(("start dir: %s" % start_dir))
        dataset_names = self.search_for_xml(start_dir)
        print(("*************************dataset name: %s" % dataset_names))

        if dataset_names:
            print(("**************Dataset_names for the xmls found: %s" % dataset_names))
        else:
            raise Exception("Cannot extract date from metadata file. No metadata found at dir: %s" % start_dir)

        # os._exit(1)

        # The searchForXml function finds all xmls in the source data and adds their dataset_name dates to a list. We want to use the most recent date.
        latest_date = None
        latest_xml = None

        for name in dataset_names:
            datetime_string = name.split('_')[5][:15]
            datetime_object = datetime.strptime(datetime_string, '%Y%m%dT%H%M%S')
            if latest_date is None or datetime_object > latest_date:
                latest_date = datetime_object
                latest_file = name
        print(("********************latest file: %s" % latest_file))
        print(("********************latest date: %s" % latest_date))
        # os._exit(1)

        # start and stop
        tmp = latest_file  # like: IR05_PAN_PA__3O_20100801T084046_20100801T084050_NSG_28364_3181.TIF
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

        """ self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (stopDate, stopTime))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, startDate)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stopDate)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, startTime)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, stopTime) """

        # For DSM product, the begin position and then end postion use the same datetime values: the begin position. So set the stop dates to the start dates.
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (startDate, startTime))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, startDate)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, startDate)
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, startTime)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, startTime)

        self.extractFootprint(processInfo)

        # print("-->%sT%sZ" % (aDate, aTime))
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
