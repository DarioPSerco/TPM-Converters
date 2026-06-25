# -*- coding: cp1252 -*-
#
# this class represent a cosmos-skymed product
#
#
import os
import tarfile
from io import StringIO

import h5py

#
import eoSip_converter.xmlHelper as xmlHelper
from . import formatUtils
from . import metadata
#
from .product import Product

# for verification
REF_TYPECODE = {'SAR_HIM_AU', 'SAR_HIM_AB', 'SAR_HIM_1B', 'SAR_HIM_1C', 'SAR_HIM_1D', 'SAR_SPP_AU', 'SAR_SPP_AB',
                'SAR_SPP_1B', 'SAR_SPP_1C', 'SAR_SPP_1D', 'SAR_SCW_AU', 'SAR_SCW_AB', 'SAR_SCW_1B', 'SAR_SCW_1C',
                'SAR_SCW_1D', 'SAR_SCH_AU', 'SAR_SCH_AB', 'SAR_SCH_1B', 'SAR_SCH_1C', 'SAR_SCH_1D'}


#
# the gdal command we will execute to build the browse
#
class GdalGroup(object):

    def __init__(self, name):
        self.name = name
        self.commands = []

    def addCommand(self, s):
        print(" @@@ GdalGroup.addCommand:%s" % s)
        self.commands.append(s)

    def getCommands(self):
        return self.commands

    def toString(self):
        out = StringIO()
        print("GdalGroup:", file=out)
        print(self.name, file=out)
        print("\n Total commands: %s" % len(self.commands), file=out)
        n = 0
        for command in self.commands:
            print("\n command[%s]: %s" % (n, command), file=out)
        return out.getvalue()


#
# cosmos-skymed product class
#
class Product_Cosmos_Skymed(Product):
    METADATA_HDF5_SUFIX = 'h5.xml'
    PRODUCT_HDF5_SUFFIX = '.h5'
    TGZ_SUFFIX = '.tgz'
    PRODUCT_GEOTIFF_SUFFIX = '.tif'
    BROWSE_GEOTIFF_SUFFIX = 'QLK.tif'

    # metadata from geotiff attribs xml file
    geotiffAttribsMapping = {metadata.METADATA_ORBIT_DIRECTION: 'Attribute@Name=Orbit Direction',
                             metadata.METADATA_ORBIT: 'Attribute@Name=Orbit Number'
                             }

    # metadata from geotiff aux xml file
    geotiffAuxMapping = {metadata.METADATA_ORBIT_DIRECTION: 'MDI@key=Orbit_Direction',
                         metadata.METADATA_ORBIT: 'MDI@key=Orbit_Number'
                         }

    # metadata from hdf file
    hdf5Mapping = {metadata.METADATA_ORBIT_DIRECTION: 'Orbit Direction',
                   metadata.METADATA_ORBIT: 'Orbit Number'
                   }

    # metadata from xml file
    xmlMapping = {
        metadata.METADATA_START_DATE: 'ProductDefinitionData/SceneSensingStartUTC',
        metadata.METADATA_STOP_DATE: 'ProductDefinitionData/SceneSensingStopUTC',

        # corners
        'BL': 'ProductDefinitionData/GeoCoordBottomLeft',
        'BR': 'ProductDefinitionData/GeoCoordBottomRight',
        'TL': 'ProductDefinitionData/GeoCoordTopLeft',
        'TR': 'ProductDefinitionData/GeoCoordTopRight',
        'PROJECTION': 'ProductDefinitionData/ProjectionId',
        metadata.METADATA_SCENE_CENTER: 'ProductDefinitionData/GeoCoordSceneCentre',

        metadata.METADATA_PROCESSING_TIME: 'ProductInfo/ProductGenerationDate',
        metadata.METADATA_PROCESSING_MODE: 'ProductDefinitionData/ProductType',

        metadata.METADATA_SATELLITE: 'ProductDefinitionData/SatelliteId',

        metadata.METADATA_SENSOR_OPERATIONAL_MODE: 'ProductDefinitionData/AcquisitionMode',

        metadata.METADATA_ACQUISITION_CENTER: 'ProductDefinitionData/AcquisitionStationId',
        metadata.METADATA_PROCESSING_CENTER: 'OtherInfo/ProcessingCentre',
    }

    #
    #
    #
    def __init__(self, path=None):
        Product.__init__(self, path)

        self.metSrcName = None
        self.metSrcPath = None
        self.metadataSrcContent = None

        # browse block only for level 1c 1d
        self.browseBlockDisabled = False

        # hdf product
        self.productHdf5SrcPath = None

        # geotiff product
        self.productGeotiffSrcPath = None
        self.browseGeotiffSrcPath = None

        #
        self.hdfGeotifFlag = None

        #
        self.topBottomFlipped = False

        #
        self.LeftRightFlipped = False

        # hold gdal commands
        self.gdalGroups = {}

        if self.debug != 0:
            print(" init class Product_Cosmos_Skymed")

    #
    #
    #
    def addGdalGroup(self, n, g):
        print(" @@@ addGdalGroup %s:%s" % (n, g))
        self.gdalGroups[n] = g
        print("     GdalGroup is now:%s" % self.gdalGroups)

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

    #
    #
    #
    def makeBrowses(self, processInfo):
        pass

    #
    # handle the input product files:
    #
    #
    def extractToPath(self, folder=None, dont_extract=False):
        self.debug = 1
        self.workFolder = folder
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % self.workFolder)
        if self.debug != 0:
            print(" Will extract directory product '%s' to path:%s" % (self.path, self.workFolder))

        # extract into workfolder/EO_product folder. Later will be compressed into the EO ZIP part
        self.contentList = []
        self.EXTRACTED_PATH = "%s/EO_product" % self.workFolder

        self.tmpSize = os.stat(self.path).st_size

        if not os.path.exists(self.EXTRACTED_PATH):
            # raise Exception("Destination folder does not exists:%s" % self.EXTRACTED_PATH)
            os.makedirs(self.EXTRACTED_PATH)
        if self.debug != 0:
            print(" exttacting product to path:%s" % self.EXTRACTED_PATH)
        tar = tarfile.open(self.path, 'r')

        if not dont_extract:
            tar.extractall(self.EXTRACTED_PATH)
            print((" extracted inside:%s" % self.EXTRACTED_PATH))
        else:
            print(" dont_extract flag is set!!")
        tar.close()

        n = 0
        for root, dirs, files in os.walk(self.EXTRACTED_PATH, topdown=False):
            for name in files:
                print((" check extracted file:%s" % os.path.join(root, name)))

                if name.endswith(self.METADATA_HDF5_SUFIX):  # metadata
                    if self.debug != 0:
                        print("   metName:%s" % name)
                    self.metSrcName = name
                    fd = open(os.path.join(root, name), 'r')
                    data = fd.read()
                    fd.close()
                    self.metadataSrcContent = data
                    print("   metContent length:%s" % len(data))

                elif name.endswith(self.PRODUCT_HDF5_SUFFIX):  # product
                    self.productHdf5SrcPath = os.path.join(root, name)
                    self.productName = name
                    if self.debug != 0:
                        print("   productName:%s" % name)

                elif name.endswith(self.TGZ_SUFFIX):  # product as tgz
                    tgzPath = os.path.join(root, name)
                    if self.debug != 0:
                        print("   extracingt EO tgzPath:%s" % tgzPath)
                    tar2 = tarfile.open(tgzPath, 'r')
                    self.tgzFolder = "%s/TGZ" % self.workFolder
                    if not os.path.exists(self.tgzFolder):
                        os.makedirs(self.tgzFolder)
                    if not dont_extract:
                        tar2.extractall(self.tgzFolder)
                        if self.debug != 0:
                            print("   EO tgz extracted at path:%s" % self.tgzFolder)
                    else:
                        print(" dont_extract flag is set!!")
                    tar2.close()

                    # look for geotiff + quicklook
                    for root2, dirs2, files2 in os.walk(self.tgzFolder, topdown=False):
                        for name2 in files2:
                            print("   EO tgz name:%s" % name2)
                            if name2.endswith(self.BROWSE_GEOTIFF_SUFFIX):  # there is a browse image like xxxx.QLK.tif

                                self.browseGeotiffSrcPath = os.path.join(root2, name2)
                                # self.productName = name2
                                if self.debug != 0:
                                    print("   geotiff browse name (in tgz):%s" % name2)
                            elif name2.endswith(
                                    self.PRODUCT_GEOTIFF_SUFFIX):  # there is NO browse image, will make it from xxxxxx.tif file
                                self.productGeotiffSrcPath = os.path.join(root2, name2)
                                # self.productName = name2
                                if self.debug != 0:
                                    print("   geotiff name (in tgz):%s" % name2)

                relPath = os.path.join(root, name)[len(self.EXTRACTED_PATH) + 1:]
                print("   content[%s] workfolder relative path:%s" % (n, relPath))
                self.contentList.append(relPath)

            # os._exit(1)

    #
    #
    #
    def buildTypeCode(self):
        om = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        pm = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_MODE)

        typecode = None
        if om == 'HIM':
            if pm == 'SCS_B':
                typecode = 'SAR_HIM_AB'
                self.browseBlockDisabled = True
            elif pm == 'SCS_U':
                typecode = 'SAR_HIM_AU'
                self.browseBlockDisabled = True
            elif pm == 'DGM_B':
                typecode = 'SAR_HIM_1B'
                self.browseBlockDisabled = True
            elif pm == 'GEC_B':
                typecode = 'SAR_HIM_1C'
            elif pm == 'GTC_B':
                typecode = 'SAR_HIM_1D'
            else:
                raise Exception("strange METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)


        elif om == 'SPP':
            if pm == 'SCS_B':
                typecode = 'SAR_SPP_AB'
            elif pm == 'SCS_U':
                typecode = 'SAR_SPP_AU'
            elif pm == 'DGM_B':
                typecode = 'SAR_SPP_1B'
            elif pm == 'GEC_B':
                typecode = 'SAR_SPP_1C'
            elif pm == 'GTC_B':
                typecode = 'SAR_SPP_1D'
            else:
                raise Exception("strange METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)


        elif om == 'SCW':
            if pm == 'SCS_B':
                typecode = 'SAR_SCW_AB'
            elif pm == 'SCS_U':
                typecode = 'SAR_SCW_AU'
            elif pm == 'DGM_B':
                typecode = 'SAR_SCW_1B'
            elif pm == 'GEC_B':
                typecode = 'SAR_SCW_1C'
            elif pm == 'GTC_B':
                typecode = 'SAR_SCW_1D'
            else:
                raise Exception("strange METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)




        elif om == 'SCH':
            if pm == 'SCS_B':
                typecode = 'SAR_SCH_AB'
            elif pm == 'SCS_U':
                typecode = 'SAR_SCH_AU'
            elif pm == 'DGM_B':
                typecode = 'SAR_SCH_1B'
            elif pm == 'GEC_B':
                typecode = 'SAR_SCH_1C'
            elif pm == 'GTC_B':
                typecode = 'SAR_SCH_1D'
            else:
                raise Exception("strange METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)

        print((" @@##@@ typecode:%s" % typecode))
        if not typecode in REF_TYPECODE:
            raise Exception("buildTypeCode; unknown typecode:%s" % typecode)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, typecode)

    #
    #
    #
    def extractMetadata(self, met=None):
        # self.DEBUG=1
        if met is None:
            raise Exception("metadate is None")

        # use what contains the metadata file
        if self.metadataSrcContent is None:
            raise Exception("no metadata to be parsed")

        # set size
        met.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, self.tmpSize)

        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(self.metadataSrcContent)
        helper.parseData()

        # get fields
        resultList = []
        op_element = helper.getRootNode()
        num_added = 0

        # get from xml file
        for field in self.xmlMapping:
            if self.xmlMapping[field].find("@") >= 0:
                attr = self.xmlMapping[field].split('@')[1]
                path = self.xmlMapping[field].split('@')[0]
            else:
                attr = None
                path = self.xmlMapping[field]

            aData = helper.getFirstNodeByPath(None, path, None)
            if aData is None:
                aValue = None
            else:
                if attr is None:
                    aValue = helper.getNodeText(aData)
                else:
                    aValue = helper.getNodeAttributeText(aData, attr)

                    # if self.DEBUG!=0:
            print("  num_added[%s] -->%s=%s" % (num_added, field, aValue))

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # local attributes
        # remove extension from original name
        # pos =  self.origName.find('.')
        # if pos > 0:
        #    self.origName=self.origName[0:pos]
        # met.addLocalAttribute("originalName", self.origName)

        self.metadata = met

        return num_added

    #
    # refine the metada
    #
    def refineMetadata(self, processInfo):

        # get satellite id from: CSKS2
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SATELLITE)
        if not tmp[-1].isnumeric():
            raise Exception("cannot get platformId from:'%s'" % tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PLATFORM_ID, tmp[-1])

        # set the start stop date and time
        # is like: 2018-02-22 03:19:19.632447422
        tmp = self.metadata.getMetadataValue(metadata.METADATA_START_DATE)
        start_tokens = tmp.split(' ')

        print((" ############# start_tokens:%s" % start_tokens))
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, start_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME,
                                      "%s.%s" % (start_tokens[1].split('.')[0], start_tokens[1].split('.')[1][:3]))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
        stop_tokens = tmp.split(' ')

        print((" ############# stop_tokens:%s" % stop_tokens))
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, stop_tokens[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME,
                                      "%s.%s" % (stop_tokens[1].split('.')[0], stop_tokens[1].split('.')[1][:3]))

        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
            self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
            self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set WRS grid
        # is like: 38.160336 34.316416 0.000000
        center = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        clat = float(center.split(' ')[0])
        clon = float(center.split(' ')[1])
        self.metadata.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, clon)
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

        # adjust METADATA_PROCESSING_TIME.has no msec
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME)
        # may be like 2017-08-31 19:59:39.000000000
        pos = tmp.find('.')
        if pos > 0:
            # self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp[0:pos+4].replace(' ','T')+'Z')
            self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp[0:pos].replace(' ', 'T') + 'Z')
        else:
            pass

        # adjust METADATA_ACQUISITION_CENTER
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        # may be like 1301/EACQ02/Kiruna
        pos = tmp.find('/')
        if pos > 0:
            self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, tmp.split('/')[-1])
        else:
            pass

        #
        # hdf5 case attributes
        #
        if self.productHdf5SrcPath is not None:
            # raise Exception("no hdf product found")
            print(" get info from HDF5 file:%s" % self.productHdf5SrcPath)
            self.h5file = h5py.File(self.productHdf5SrcPath, 'r')
            if 1 == 1 and self.debug != 0:
                n = 0
                for key in list(self.h5file.attrs.keys()):
                    print(" all HDF5 attribute[%s] %s=%s" % (n, key, self.h5file.attrs[key]))
                    n += 1
            n = 0
            for key in self.hdf5Mapping:
                mapping = self.hdf5Mapping[key]
                print(" look for HDF5 attribute[%s]:%s" % (n, mapping))
                if mapping in self.h5file.attrs:
                    self.metadata.setMetadataPair(key, self.h5file.attrs[mapping])
                    print("  HDF5 attribute found %s=%s" % (key, self.h5file.attrs[mapping]))
                else:
                    print("  HDF5 attribute not found:%s" % key)
                n += 1

            #
            # test hdf items for single scene, look for quicklook item; name like QLK or /S01/QLK
            #
            print("\n\n\n check HDF5 content start")
            # name of the browse file we will create. Is also key of the gdalGroups map holdiing the gdal command to be executed to produce the browse
            gdalSceneName = None
            # HDF5 dataset name: like S01 S02 etc...
            gdalQlId = None
            #
            self.allQlkMap = {}
            num = len(list(self.h5file.items()))
            print(" @@###@@ self.h5file; number of items:%s" % num)
            for n in range(num):
                name = list(self.h5file.items())[n][0]
                print(" @@###@@ self.h5file; item[%s] name:%s" % (n, name))
                if name == 'QLK':
                    gdalSceneName = name
                    gdalQlId = name
                    self.allQlkMap[gdalSceneName] = gdalQlId
                    print(" @@###@@ self.h5file; found quicklook name: QLK")
                    """
                    elif name== 'S01':
                        print " @@###@@ self.h5file; found:S01"
                        dataset = self.h5file.items()[n][1]
                        print " @@###@@ self.h5file; S01 dataset:%s" % dataset
                        for name2 in dataset:
                            print " @@###@@ self.h5file; %s item.name:%s" % (name , name2)
                            if name2 == 'QLK':
                                gdalSceneName = '_S01_QLK'
                                gdalQlId = 'S01/QLK'
                                print " @@###@@ self.h5file; found first item quicklook name:%s" % gdalSceneName
                    """
                elif name.startswith('S'):
                    print(" @@###@@ self.h5file; found:%s" % name)
                    dataset = list(self.h5file.items())[n][1]
                    print(" @@###@@ self.h5file; %s dataset:%s" % (name, dataset))
                    for name2 in dataset:
                        print(" @@###@@ self.h5file; %s item.name:%s" % (name, name2))
                        if name2 == 'QLK':
                            gdalSceneName = '_%s_%s' % (name, name2)
                            gdalQlId = '%s/%s' % (name, name2)
                            self.allQlkMap[gdalSceneName] = gdalQlId
                            print(" @@###@@ self.h5file; found first item quicklook name:%s" % gdalSceneName)
                else:
                    print(" @@###@@ self.h5file; found:%s" % name)

            print(" check HDF5 content end; gdalSceneName=%s; gdalQlId=%s\n self.allQlkMap=%s\n\n" % (
            gdalSceneName, gdalQlId, self.allQlkMap))


        #
        # geotiff case attributes
        #
        elif self.productGeotiffSrcPath is not None:
            # can be named like TIF + '.aux.xml'
            # or like tif without extension + 'attribs.xml'
            useAux = False
            useAttrib = False
            auxXml = "%s.aux.xml" % self.productGeotiffSrcPath
            if os.path.exists(auxXml):
                useAux = True
            else:
                print(" no geoTiff aux file:%s" % auxXml)
                basename = os.path.basename(self.productGeotiffSrcPath)
                dirname = os.path.dirname(self.productGeotiffSrcPath)
                base = basename.split('.')[0]
                base = "%s.attribs.xml" % base
                auxXml = "%s/%s" % (dirname, base)
                print(" so look for geoTiff attribs file:%s" % auxXml)
                if not os.path.exists(auxXml):
                    raise Exception("geoTiff aux file:%s doesn't exists" % auxXml)
                useAttrib = True

            if useAux:
                print(" get info from geoTiff aux file:%s" % auxXml)

                # extact metadata
                fd = open(auxXml, 'r')
                dataXml = fd.read()
                fd.close()
                helper = xmlHelper.XmlHelper()
                helper.setDebug(1)
                helper.setData(dataXml)
                helper.parseData()

                # MDI@key=Orbit_Direction
                num_added = 0
                for field in self.geotiffAuxMapping:
                    value = self.geotiffAuxMapping[field]
                    print("@@@@ do field:%s; value:%s" % (field, value))
                    if self.geotiffAuxMapping[field].find("@") >= 0:
                        attr = self.geotiffAuxMapping[field].split('@')[1]
                        path = self.geotiffAuxMapping[field].split('@')[0]
                    else:
                        attr = None
                        path = self.geotiffAuxMapping[field]
                    print("  field:%s; path:%s; attr:%s" % (field, path, attr))

                    if attr is not None:
                        toks = attr.split('=')
                        if len(toks) == 2:
                            elems = helper.lxmlGetElemenentsByAttribute(path, toks[0], toks[1])
                            if len(elems) == 1:
                                res = elems[0].text
                                print("  res:%s; type:%s" % (res, type(res)))
                                if res.strip().endswith('d'):
                                    if res.strip()[0:-1].isdigit():
                                        res = int(res.strip()[0:-1])
                                        print("  field is numeric:%s; value:%s" % (field, res))
                                    else:
                                        print("  field is not numeric:%s; value:%s" % (field, res))
                                print("  field found:%s; value:%s" % (field, res))
                                self.metadata.setMetadataPair(field, res)
                                num_added = num_added + 1
                            else:
                                print("  field not found:%s" % field)
                                self.metadata.setMetadataPair(field, None)
                        else:
                            raise Exception("attr type not supported:%s" % attr)

            elif useAttrib:
                print(" get info from geoTiff attrib file:%s" % auxXml)

                # extact metadata
                fd = open(auxXml, 'r')
                dataXml = fd.read()
                fd.close()
                helper = xmlHelper.XmlHelper()
                helper.setDebug(1)
                helper.setData(dataXml)
                helper.parseData()

                # MDI@key=Orbit_Direction
                num_added = 0
                for field in self.geotiffAttribsMapping:
                    value = self.geotiffAttribsMapping[field]
                    print("@@@@ do field:%s; value:%s" % (field, value))
                    if self.geotiffAttribsMapping[field].find("@") >= 0:
                        attr = self.geotiffAttribsMapping[field].split('@')[1]
                        path = self.geotiffAttribsMapping[field].split('@')[0]
                    else:
                        attr = None
                        path = self.geotiffAttribsMapping[field]
                    print("  field:%s; path:%s; attr:%s" % (field, path, attr))

                    if attr is not None:
                        toks = attr.split('=')
                        if len(toks) == 2:
                            elems = helper.lxmlGetElemenentsByAttribute(path, toks[0], toks[1])
                            if len(elems) == 1:
                                res = elems[0].text
                                print("  res:%s; type:%s" % (res, type(res)))
                                if res.strip().endswith('d'):
                                    if res.strip()[0:-1].isdigit():
                                        res = int(res.strip()[0:-1])
                                        print("  field is numeric:%s; value:%s" % (field, res))
                                    else:
                                        print("  field is not numeric:%s; value:%s" % (field, res))
                                print("  field found:%s; value:%s" % (field, res))
                                self.metadata.setMetadataPair(field, res)
                                num_added = num_added + 1
                            else:
                                print("  field not found:%s" % field)
                                self.metadata.setMetadataPair(field, None)
                        else:
                            raise Exception("attr type not supported:%s" % attr)

        #
        od = self.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)

        #
        # we start the mess about finding the footprint. We can have
        # - multiple strip forming one browse  (HDF5 case)
        # - geotiff present in the EO product, inside a tgz
        #
        #
        #
        toksTL = self.metadata.getMetadataValue('TL').strip().split(';+;')
        toksBL = self.metadata.getMetadataValue('BL').strip().split(';+;')
        print(("toksTL:%s; toksBL:%s" % (toksTL, toksBL)))
        # os._exit(1)

        # is the top/bottom flipped?
        top = toksTL[0].strip().split(' ')[0]
        bottom = toksBL[0].strip().split(' ')[0]
        if float(bottom) > float(top):
            print(" @@##@@ look like Top BOTTOM coords are flipped! top=%s; bottom=%s" % (top, bottom))
            self.topBottomFlipped = True
        else:
            print(" @@##@@ look like Top BOTTOM coords are NOT flipped! top=%s; bottom=%s" % (top, bottom))
        self.metadata.setMetadataPair("topBottomFlipped", self.topBottomFlipped)

        self.numberOfScene = len(toksTL)
        print(" @@##@@ number of scene(s) (from corners coordinates string) :%s" % self.numberOfScene)

        # operationnalMode
        om = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if om == 'HIMAGE':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'HIM')
        elif om == 'PINGPONG':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SPP')
        elif om == 'WIDEREGION':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SCW')
        elif om == 'HUGEREGION':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SCH')
        else:
            raise Exception("unknown METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)

        #
        self.buildTypeCode()

        # moved to methods because too big
        if len(toksTL) > 1:
            self.multiSceneFootprint(od, processInfo)
            return


        else:  # only one scene in footprint string
            self.singleSceneFootprint(od, processInfo)
            return

        # operationnalMode
        om = self.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)
        if om == 'HIMAGE':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'HIM')
        elif om == 'PINGPONG':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SPP')
        elif om == 'WIDEREGION':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SCW')
        elif om == 'HUGEREGION':
            self.metadata.setMetadataPair(metadata.METADATA_SENSOR_OPERATIONAL_MODE, 'SCH')
        else:
            raise Exception("unknown METADATA_SENSOR_OPERATIONAL_MODE:%s" % om)

        #
        self.buildTypeCode()

    #
    #
    #
    def multiSceneFootprint(self, od, processInfo):
        print(" @@##@@ footprint: multiple scene case !!")

        toksTL = self.metadata.getMetadataValue('TL').strip().split(';+;')
        toksBL = self.metadata.getMetadataValue('BL').strip().split(';+;')
        toksBR = self.metadata.getMetadataValue('BR').strip().split(';+;')
        toksTR = self.metadata.getMetadataValue('TR').strip().split(';+;')
        print(("### toksTR[:%s" % toksTR))
        print(("### toksTL[:%s" % toksTL))
        print(("### toksBR[:%s" % toksBR))
        print(("### toksBL[:%s" % toksBL))
        # os._exit(1)

        # extremes of corners:
        cornerTL = toksTR[-1].strip().split(' ')[0:-1]
        cornerTR = toksTL[0].strip().split(' ')[0:-1]
        cornerBL = toksBR[-1].strip().split(' ')[0:-1]
        cornerBR = toksBL[0].strip().split(' ')[0:-1]

        # hdf5 case
        if self.productHdf5SrcPath is not None:
            warpedTif = []
            gdalSceneNum = None
            #
            # when there is several pieces for the full scene it look like:
            # - when descending , pieces 0 is on the right, and piece n on the left  ( on the view)
            # -
            for n in range(len(toksTL)):
                print(" @@##@@  doing multiple scene; scene[%s];  TR=%s; TL=%s; BL=%s; BR=%s" % (
                    n, toksTR[n], toksTL[n], toksBR[n], toksBL[n]))

                if od == 'DESCENDING':
                    # get gdal reference points for pixel 0:0 0:w 0:h
                    gdalCoordlon_0 = toksTL[n].strip().split(' ')[1]
                    gdalCoordlat_0 = toksTL[n].strip().split(' ')[0]

                    gdalCoordlon_1 = toksTR[n].strip().split(' ')[1]
                    gdalCoordlat_1 = toksTR[n].strip().split(' ')[0]

                    gdalCoordlon_2 = toksBL[n].strip().split(' ')[1]
                    gdalCoordlat_2 = toksBL[n].strip().split(' ')[0]

                    # gdalSceneNum= 'S%02d' % (len(toksTL)-n)
                    gdalSceneNum = 'S%02d' % (n + 1)

                    footprintPiece = '%s %s %s %s %s' % (
                        ' '.join(toksTR[n].strip().split(' ')[0:-1]),
                        ' '.join(toksBR[n].strip().split(' ')[0:-1]),
                        ' '.join(toksBL[n].strip().split(' ')[0:-1]),
                        ' '.join(toksTL[n].strip().split(' ')[0:-1]),
                        ' '.join(toksTR[n].strip().split(' ')[0:-1]),
                    )
                else:
                    # raise Exception("NEED TO CONFIRM ASCENDING MULTIPLE SCENE !!")
                    # get gdal reference points for pixel 0:0 0:w 0:h
                    gdalCoordlon_0 = toksBR[n].strip().split(' ')[1]
                    gdalCoordlat_0 = toksBR[n].strip().split(' ')[0]

                    gdalCoordlon_1 = toksBL[n].strip().split(' ')[1]
                    gdalCoordlat_1 = toksBL[n].strip().split(' ')[0]

                    gdalCoordlon_2 = toksTR[n].strip().split(' ')[1]
                    gdalCoordlat_2 = toksTR[n].strip().split(' ')[0]

                    # gdalSceneNum = 'S%02d' % n
                    gdalSceneNum = 'S%02d' % (len(toksTL) - n)

                    footprintPiece = '%s %s %s %s %s' % (
                        ' '.join(toksBL[n].strip().split(' ')[0:-1]),
                        ' '.join(toksTL[n].strip().split(' ')[0:-1]),
                        ' '.join(toksTR[n].strip().split(' ')[0:-1]),
                        ' '.join(toksBR[n].strip().split(' ')[0:-1]),
                        ' '.join(toksBL[n].strip().split(' ')[0:-1]),
                    )

                print("footprint[%s]:'%s'" % (n, footprintPiece))
                self.metadata.setMetadataPair("%s__%s" % (metadata.METADATA_FOOTPRINT, n), footprintPiece)

                # build gdal command that will create the browses
                gdalSceneName = "_%s_QLK" % gdalSceneNum
                # exists in self.allQlkMap
                if not gdalSceneName in self.allQlkMap:
                    raise Exception("gdalSceneName %s not present im allQlkMap" % gdalSceneName)
                hdf5name = self.allQlkMap[gdalSceneName]

                gdalGroup = GdalGroup(gdalSceneName)
                gdalCommand = """gdal_translate -of GTiff -a_srs EPSG:4326 -gcp 0 0 %s %s -gcp {WIDTH} 0 %s %s -gcp 0 {HEIGHT} %s %s HDF5:"%s"://%s %s/%s.tif""" % (
                    gdalCoordlon_0, gdalCoordlat_0, gdalCoordlon_1, gdalCoordlat_1, gdalCoordlon_2, gdalCoordlat_2,
                    self.productHdf5SrcPath, hdf5name, self.workFolder, gdalSceneName)
                gdalGroup.addCommand(gdalCommand)
                gdalCommand = """gdalwarp -t_srs EPSG:4326 -dstalpha %s/%s.tif %s/warped_%s.tif""" % (
                    self.workFolder, gdalSceneName, self.workFolder, gdalSceneNum)
                gdalGroup.addCommand(gdalCommand)
                self.gdalGroups[gdalSceneName] = gdalGroup
                warpedTif.append("%s/warped_%s.tif" % (self.workFolder, gdalSceneNum))
                processInfo.addLog(
                    "## prepare gdalGroup command; HDF5 case; doing multiple scene; scene[%s]; gdalSceneName=%s" % (
                    n, gdalSceneName))

            # full footprint
            print(" @@##@@ footprint: multi scene case; doing browse for hdf5 name:%s" % hdf5name)
            test = '%s %s %s %s %s %s %s %s %s %s' % (
                cornerTL[0], cornerTL[1],
                cornerTR[0], cornerTR[1],
                cornerBR[0], cornerBR[1],
                cornerBL[0], cornerBL[1],
                cornerTL[0], cornerTL[1]
            )
            self.metadata.setMetadataPair("MULTI_HDF5_FOOTPRINT_TL_TR_BR_BL_TL", test)

            if od == 'DESCENDING':
                if self.topBottomFlipped:
                    footprintFull = '%s %s %s %s %s %s %s %s %s %s' % (
                        cornerTL[0], cornerTL[1],
                        cornerBL[0], cornerBL[1],
                        cornerBR[0], cornerBR[1],
                        cornerTR[0], cornerTR[1],
                        cornerTL[0], cornerTL[1]
                    )
                    self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprintFull)
                    self.metadata.setMetadataPair('footprintFullDesc', footprintFull)
                    print(" @@##@@ footprint FLIPPED MULTI DESCENDING HDF5 TL_TR_BR_BL_TL test:%s" % test)
                    print(" @@##@@ footprint FLIPPED MULTI DESCENDING HDF5:%s" % footprintFull)
                    raise Exception("DESCENDING HDF5 multiple not in TDS, TO BE CHECKED, inform Gilles")
                else:
                    footprintFull = '%s %s %s %s %s %s %s %s %s %s' % (
                        cornerTL[0], cornerTL[1],
                        cornerBL[0], cornerBL[1],
                        cornerBR[0], cornerBR[1],
                        cornerTR[0], cornerTR[1],
                        cornerTL[0], cornerTL[1]
                    )
                    self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprintFull)
                    self.metadata.setMetadataPair('footprintFullDesc', footprintFull)
                    print(" @@##@@ footprint NOT FLIPPED MULTI DESCENDING HDF5 TL_TR_BR_BL_TL test:%s" % test)
                    print(" @@##@@ footprint NOT FLIPPED MULTI DESCENDING HDF5:%s" % footprintFull)

            else:  # ASCENDING
                # SAR_SCH_AU:
                #  Ascending: look flipped vertically
                #  footprint TL_TR_BR_BL_TL test: 42.069886 11.637935 41.817337 9.345321 43.590239 8.985554 43.838691 11.346315 42.069886 11.637935
                #  is like:
                #  2 - --- 3
                #  |       |
                #  |       |
                #  1 ----  0 + 4
                #
                #  ==> Need: TL BL BR TR TL

                if self.topBottomFlipped:
                    footprintFull = '%s %s %s %s %s %s %s %s %s %s' % (
                        cornerTL[0], cornerTL[1],
                        cornerBL[0], cornerBL[1],
                        cornerBR[0], cornerBR[1],
                        cornerTR[0], cornerTR[1],
                        cornerTL[0], cornerTL[1]
                    )
                    print(" @@##@@ footprint FLIPPED MULTI ASCENDING HDF5 TL_TR_BR_BL_TL test:%s" % test)
                    print(" @@##@@ footprint FLIPPED MULTI ASCENDING HDF5:%s" % footprintFull)
                    # processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_KMZ_DONT_REVERSE_BROWSE, True)
                    # os._exit(1)
                else:
                    footprintFull = '%s %s %s %s %s %s %s %s %s %s' % (
                        cornerBL[0], cornerBL[1],
                        cornerTL[0], cornerTL[1],
                        cornerTR[0], cornerTR[1],
                        cornerBR[0], cornerBR[1],
                        cornerBL[0], cornerBL[1],
                    )
                    print(" @@##@@ footprint NOT FLIPPED MULTI ASCENDING HDF5 TL_TR_BR_BL_TL test:%s" % test)
                    print(" @@##@@ footprint NOT FLIPPED MULTI ASCENDING HDF5:%s" % footprintFull)
                    # processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_KMZ_DONT_REVERSE_BROWSE, True)
                    # os._exit(1)

                self.metadata.setMetadataPair('footprintFullAsc', footprintFull)
                self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprintFull)

        # geoTiff case
        elif self.productGeotiffSrcPath is not None:
            # multiple scene case with geotiff, is this possible?
            raise Exception("GEOTIFF multiple not in TDS, TO BE CHECKED, inform Gilles")

        # hdf5 case
        if self.productHdf5SrcPath is not None:
            self.hdfGeotifFlag = 'HDF5'
            # gdal merge all pieces
            gdalCommand = "gdal_merge.py -of Gtiff -n 0 "
            for aTif in warpedTif:
                gdalCommand += aTif + " "
            gdalCommand += "-o %s/merged.tif" % self.workFolder
            gdalGroup = GdalGroup('final')
            gdalGroup.addCommand(gdalCommand)
            # and make a png to not have problem with PIL + tiff
            gdalCommand = 'gdal_translate -of PNG %s/merged.tif %s/merged.png' % (self.workFolder, self.workFolder)
            gdalGroup.addCommand(gdalCommand)

            self.addGdalGroup('final', gdalGroup)

            mergedPath = '%s/merged.png' % self.workFolder
            self.browseOK = mergedPath

        # geoTiff case
        elif self.productGeotiffSrcPath is not None:
            self.hdfGeotifFlag = 'GEOTIFF'
            gdalGroup = GdalGroup('geotiff')
            gdalCommand = "gdal_translate -of PNG -a_nodata 1 %s %s/merged.png" % (
                self.browseGeotiffSrcPath, self.workFolder)
            gdalGroup.addCommand(gdalCommand)

            self.addGdalGroup('final', gdalGroup)

            mergedPath = "%s/merged.png" % self.workFolder
            self.browseOK = mergedPath

    #
    #
    #
    def singleSceneFootprint(self, od, processInfo):
        # only one scene in footprint string
        print(" @@##@@ footprint: single scene case !!")

        # use first browse
        firstName = None

        # hdf5 case
        if self.productHdf5SrcPath is not None:
            self.hdfGeotifFlag = 'HDF5'
            processInfo.addLog("## hdfGeotifFlag = 'HDF5'")
            self.metadata.setMetadataPair("hdfGeotifFlag", self.hdfGeotifFlag)
            processInfo.addLog("## allQlkMap=%s" % self.allQlkMap)
            for gdalSceneName in self.allQlkMap:
                hdf5name = self.allQlkMap[gdalSceneName]
                if firstName is None:
                    firstName = gdalSceneName
                print(" @@##@@ footprint: single scene case; doing browse:%s for hdf5 name:%s" % (
                gdalSceneName, hdf5name))
                test = '%s %s %s %s %s' % (
                    ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1])
                )
                self.metadata.setMetadataPair("HDF5_FOOTPRINT_TL_TR_BR_BL_TL", test)

                # OBSOLETE:
                # these corner coords looks to be image oriented and not world oriented
                #
                # so for ascending we have like:
                # TL=43.745815 9.896750 0.000000
                # TR=43.813585 10.395173 0.000000
                # BL=44.165637 9.783919 0.000000
                # BR=44.233516 10.286041 0.000000
                # -> from top-left clockwise: TL TR BR BL: 43.745815 9.896750 43.813585 10.395173 44.233516 10.286041 44.165637 9.783919
                # -> 3 --- 2
                #
                #    0 --- 1
                #
                # and descending:
                # TL=55.814264 12.965201 0.000000
                # TR=55.893045 12.328686 0.000000
                # BL=55.412238 12.802971 0.000000
                # BR=55.490557 12.173162 0.000000
                # -> from top-left clockwise: TL TR BR BL: 55.814264 12.965201 55.893045 12.328686 55.490557 12.173162 55.412238 12.802971
                # -> 1 --- 0
                #
                #    2 --- 3
                #

                processInfo.addLog("## orbitDirection=%s" % od)
                if od == 'DESCENDING':
                    print(" @@##@@ footprint: single scene case: DESCENDING")
                    if not self.topBottomFlipped:
                        # SAR_HIM_AB:
                        #  Ascending: look NOT flipped vertically
                        #  footprint TL_TR_BR_BL_TL test: 31.505962 48.213331 31.516566 48.751997 31.078507 48.762376 31.068083 48.226191 31.505962 48.213331
                        #  is like:
                        #  1 --- 0 +4
                        #  |       |
                        #  |       |
                        #  2 ----  3
                        #
                        #  ==> Need: TR BR BL TL TR
                        footprint = '%s %s %s %s %s' % (
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1])
                        )
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped:%s;  TL_TR_BR_BL_TL test:%s" % (
                        self.topBottomFlipped, test))
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped:%s;  footprint:%s" % (
                        self.topBottomFlipped, footprint))
                        # os._exit(1)
                        # raise Exception("need to verify single scene descending case; inform gilles")

                        # build gdal command that will create the browses
                        gdalGroup = GdalGroup(gdalSceneName)
                        gdalCommand = """gdal_translate -of GTiff -a_srs EPSG:4326 HDF5:"%s"://%s %s/%s.tif""" % (
                        self.productHdf5SrcPath, hdf5name, self.workFolder, gdalSceneName)
                        gdalGroup.addCommand(gdalCommand)
                        self.addGdalGroup(gdalSceneName, gdalGroup)
                    else:
                        footprint = '%s %s %s %s %s' % (
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1])
                        )
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped?:%s;  TL_TR_BR_BL_TL test:%s" % (
                        self.topBottomFlipped, test))
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped?:%s;  footprint:%s" % (
                        self.topBottomFlipped, footprint))
                        os._exit(1)
                        # raise Exception("need to verify single scene descending case; inform gilles")

                        # build gdal command that will create the browses
                        gdalGroup = GdalGroup(gdalSceneName)
                        gdalCommand = """gdal_translate -of GTiff -a_srs EPSG:4326 HDF5:"%s"://%s %s/%s.tif""" % (
                        self.productHdf5SrcPath, hdf5name, self.workFolder, gdalSceneName)
                        gdalGroup.addCommand(gdalCommand)
                        self.addGdalGroup(gdalSceneName, gdalGroup)

                    self.LeftRightFlipped = True
                    self.metadata.setMetadataPair("LeftRightFlipped", self.LeftRightFlipped)

                else:  # ascending
                    print(" @@##@@ footprint: single scene case: ASCENDING")
                    if not self.topBottomFlipped:
                        # SAR_HIM_1D:
                        #  Ascending: look NOT flipped vertically
                        #  footprint TL_TR_BR_BL_TL test: 31.505962 48.213331 31.516566 48.751997 31.078507 48.762376 31.068083 48.226191 31.505962 48.213331
                        #  is like:
                        #  0+4 --- 1
                        #  |       |
                        #  |       |
                        #  3 ----  2
                        #
                        #  ==> Need: BR BL TL TR BR

                        footprint = '%s %s %s %s %s' % (
                            ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1])
                        )
                        print(" @@##@@ footprint single scene HDF5; ASCENDING; flipped?:%s;  TL_TR_BR_BL_TL test:%s" % (
                        self.topBottomFlipped, test))
                        print(" @@##@@ footprint single scene HDF5; ASCENDING; flipped?:%s;  footprint:%s" % (
                        self.topBottomFlipped, footprint))
                        # os._exit(1)

                    else:
                        # HIM_AB:
                        #  Ascending: look flipped vertically
                        #  footprint TL_TR_BR_BL_TL test: 19.155642 -99.214828 19.226327 -98.833775 19.657382 -98.922395 19.586743 -99.304527 19.155642 -99.214828
                        #  is like:
                        #  3 ---- 2
                        #  |      |
                        #  |      |
                        #  0+4 -- 1
                        #
                        #  ==> Need: TR BR BL TL TR

                        footprint = '%s %s %s %s %s' % (
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                            ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1])
                        )
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped?:%s;  TL_TR_BR_BL_TL test:%s" % (
                        self.topBottomFlipped, test))
                        print(" @@##@@ footprint single scene HDF5; DESCENDING; flipped?:%s;  footprint :%s" % (
                        self.topBottomFlipped, footprint))
                        # os._exit(1)

                    # processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_KMZ_DONT_REVERSE_BROWSE, True)
                    # self.metadata.setMetadataPair('footprintAsc', footprint)

                    # build gdal command that will create the browse
                    gdalGroup = GdalGroup(gdalSceneName)
                    gdalCommand = """gdal_translate -of GTiff -a_srs EPSG:4326 HDF5:"%s"://%s %s/%s.tif""" % (
                    self.productHdf5SrcPath, hdf5name, self.workFolder, gdalSceneName)
                    gdalGroup.addCommand(gdalCommand)
                    self.addGdalGroup(gdalSceneName, gdalGroup)
                    processInfo.addLog(
                        "## prepare gdalGroup command; HDF5 case; doing single scene; gdalSceneName=%s" % gdalSceneName)

            print(" @@##@@ footprint TL_TR_BR_BL_TL test:%s" % test)
            print(" @@##@@ footprint: single scene case HDF5:%s" % footprint)
            # os._exit(1)

            # and make a png to not have problem with PIL + tiff
            print(" @@##@@ footprint: single scene case; will use browse %s, create merged.png" % firstName)
            mergedPath = "%s/merged.png" % self.workFolder
            self.browseOK = mergedPath
            gdalGroup = GdalGroup('final')
            gdalCommand = "gdal_translate -of PNG %s/%s.tif %s" % (self.workFolder, firstName, mergedPath)
            gdalGroup.addCommand(gdalCommand)
            self.addGdalGroup('final', gdalGroup)

            print("footprint:'%s'" % footprint)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

        # geoTiff case: coords are already view oriented?
        elif self.productGeotiffSrcPath is not None:
            self.hdfGeotifFlag = 'GEOTIFF'
            processInfo.addLog("## hdfGeotifFlag = 'GEOTIFF'")
            self.metadata.setMetadataPair("hdfGeotifFlag", self.hdfGeotifFlag)

            print(" @@##@@ footprint: single scene case; doing for GEOTIFF name:%s" % self.productGeotiffSrcPath)
            test = '%s %s %s %s %s' % (
                ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1])
            )
            self.metadata.setMetadataPair("GEOTIFF_FOOTPRINT_TL_TR_BR_BL_TL", test)

            # coords look world oriented, also image?. So no flip to be done.
            # ascending case:
            # TL=25.989036 -80.563607 0.000000
            # TR=25.986737 -80.075097 0.000000
            # BL=25.502978 -80.565379 0.000000
            # BR=25.500729 -80.078852 0.00000
            # -> from top-left clockwise: TL TR BR BL: 25.989036 -80.563607 25.986737 -80.075097 25.500729 -80.078852 25.502978 -80.565379
            # -> 0 --- 1
            #
            #    3 --- 2
            #
            #
            # TL=12.886089 -8.226844 0.000000
            # TR=12.884364 -7.774941 0.000000
            # BL=12.397158 -8.228313 0.000000
            # BR=12.395501 -7.777268 0.000000
            # -> from top-left clockwise: TL TR BR BL: 12.886089 -8.226844 12.884364 -7.774941 12.395501 -7.777268 12.397158 -8.228313
            # -> 0 --- 1
            #
            #    3 --- 2

            test = '%s %s %s %s %s' % (
                ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1])
            )
            self.metadata.setMetadataPair("GEOTIFF_FOOTPRINT_TL_TR_BR_BL_TL", test)

            if od == 'DESCENDING':
                footprint = '%s %s %s %s %s' % (
                    ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1])
                )

                print(" @@##@@ footprint GEOTIFF DESCENDING single scene case; TL_TR_BR_BL_TL test:%s" % test)
                print(" @@##@@ footprint GEOTIFF DESCENDING single scene case; footprint:%s" % footprint)
                # os._exit(1)
            else:
                footprint = '%s %s %s %s %s' % (
                    ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TR').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('TL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BL').strip().split(' ')[0:-1]),
                    ' '.join(self.metadata.getMetadataValue('BR').strip().split(' ')[0:-1])
                )

                print(" @@##@@ footprint GEOTIFF ASCENDING single scene case; TL_TR_BR_BL_TL test:%s" % test)
                print(" @@##@@ footprint GEOTIFF ASCENDING single scene case; footprint:%s" % footprint)
                # processInfo.srcProduct.metadata.setMetadataPair(metadata.METADATA_KMZ_DONT_REVERSE_BROWSE, True)
                # os._exit(1)

            gdalGroup = GdalGroup('geotiff')
            gdalCommand = "gdal_translate -of PNG -a_nodata 1 %s %s/merged.png" % (
            self.browseGeotiffSrcPath, self.workFolder)
            gdalGroup.addCommand(gdalCommand)

            self.addGdalGroup('final', gdalGroup)

            mergedPath = "%s/merged.png" % self.workFolder
            self.browseOK = mergedPath

            print("footprint:'%s'" % footprint)
            self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, footprint)

    #
    # extract quality
    #
    def extractQuality(self, helper, met):
        pass

    #
    # extract the footprint posList point, ccw, lat lon
    #
    def extractFootprint(self, helper, met):
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
