# -*- coding: cp1252 -*-
#
# this class represent a Ikonos product (ZIP directory product)
#  it contains:
#
#
#
import os
import zipfile

from . import browse_metadata
from . import formatUtils
from . import metadata
from .browseImage import BrowseImage
from .product_directory import Product_Directory
from .sectionIndentedDocument import SectionDocument


#


#
#
#
class Product_Ikonos(Product_Directory):
    PREVIEW_SUFFIX = 'ovr.jpg'
    METADATA_SUFFIX = 'metadata.txt'
    EXTRACTED_PATH = None
    preview_data = None
    metadata_data = None
    preview_path = None
    metadata_path = None

    #
    # syntax is: sectionName|[key][+nLine,+nLine...]
    #
    xmlMapping = {metadata.METADATA_PROCESSING_TIME: 'Creation Date:*|0',
                  metadata.METADATA_START_DATE: 'Acquisition Date/Time:*|0',
                  metadata.METADATA_SUN_ELEVATION: 'Sun Angle Elevation:*|0',
                  metadata.METADATA_SUN_AZIMUTH: 'Sun Angle Azimuth:*|0',
                  metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE: 'Nominal Collection Azimuth:*|0',
                  metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE: 'Nominal Collection Elevation:*|0',
                  metadata.METADATA_IMAGE_NUM_COLUMNS: 'Columns:*|0',
                  metadata.METADATA_IMAGE_NUM_ROWS: 'Rows:*|0',
                  metadata.METADATA_COUNTRY: 'Country Code:*|0',
                  metadata.METADATA_ACQUISITION_CENTER: 'Ground Station ID:*|0',
                  metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER: 'Map Projection:*|0,2,3',
                  metadata.METADATA_CLOUD_COVERAGE: 'Percent Cloud Cover:*|0',
                  # point 0 1 2 3
                  # metadata.METADATA_FOOTPRINT:'Component Geographic Corner Coordinates*|3,4,6,7,9,10,12,13,3,4',
                  # should get point 1 2 3 0
                  metadata.METADATA_FOOTPRINT: 'Component Geographic Corner Coordinates*|6,7,9,10,12,13,3,4,6,7',
                  browse_metadata.BROWSE_METADATA_RECT_COORDLIST: 'Component Map Coordinates (in Map Units)*|1,2',
                  }

    #
    #
    #
    def __init__(self, path):
        Product_Directory.__init__(self, path)
        self.wfsCountryResolver = None
        print(" init class Product_Ikonos")

    #
    #
    #
    def getMetadataInfo(self):
        return self.metadata_data

    #
    #
    #
    def extractToPath(self, folder=None, dont_extract=False):
        global METADATA_NAME, PREVIEW_NAME
        if not os.path.exists(folder):
            raise Exception("Destination folder does not exists:%s" % folder)
        if self.debug != 0:
            print(" will exttact product to path:%s" % folder)
        fh = open(self.path, 'rb')
        z = zipfile.ZipFile(fh)

        # keep list of content
        self.contentList = []
        n = 0
        d = 0
        totalSize = 0
        # optimization: only extract 2 files we need
        zipEntryPreviewName = None
        zipEntryMetadataName = None

        for name in z.namelist():
            n = n + 1

            info = z.getinfo(name)
            totalSize = totalSize + info.file_size

            if self.debug != 0:
                print("  zip content[%d]:%s; siz4:%s" % (n, name, info.file_size))
            if name.find(self.PREVIEW_SUFFIX) >= 0:
                self.preview_path = "%s/%s" % (folder, name)
                zipEntryPreviewName = name
            elif name.find(self.METADATA_SUFFIX) >= 0:
                self.metadata_path = "%s/%s" % (folder, name)
                zipEntryMetadataName = name
            if self.debug != 0:
                print("   %s extracted at path:%s" % (name, folder + '/' + name))
            if name.endswith('/'):
                d = d + 1
            self.contentList.append(name)

        # IKONOS products only have one scene in one folder
        # optimization: only extract 2 files we need
        #
        extractList = []
        if zipEntryPreviewName is not None:
            extractList.append(zipEntryPreviewName)
        else:
            raise Exception("no browse image found")
        if zipEntryMetadataName is not None:
            extractList.append(zipEntryMetadataName)

        if len(extractList) == 0:
            print("nothing to be extracted found in zip! Content is:")
            n = 0
            for item in self.contentList:
                print("  zip entry[%d]:%s" % (n, item))
                n += 1
            raise Exception("nothing to be extracted found in zip!")

        if d == 1:
            if dont_extract != True:
                z.extractall(folder, extractList)
            if self.metadata_path != None:
                fd = open(self.metadata_path, 'r')
                self.metadata_data = fd.read()
                fd.close()

            if self.preview_path != None:
                fd = open(self.preview_path, 'r')
                self.preview_data = fd.read()
                fd.close()
            self.EXTRACTED_PATH = folder
            print(" ################### self.preview_path:%s" % self.preview_path)
            if self.debug != 0:
                print(" ################### self.preview_path:%s" % self.preview_path)
        else:
            raise Exception("More than 1 directory in product:%d" % d)
        z.close()
        fh.close()

        self.size = totalSize

    #
    #
    #
    def buildTypeCode(self):
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, '###_###_##')

    #
    #
    #
    def extractMetadata(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        # set some evident values
        met.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.origName)

        # use what contains the metadata file
        metContent = self.getMetadataInfo()

        # extact metadata, not xml data but 'text section indented'
        sectionDoc = SectionDocument()
        sectionDoc.loadDocument(self.metadata_path)

        # get fields
        num_added = 0

        for field in self.xmlMapping:
            rule = self.xmlMapping[field]
            aValue = None
            if self.debug == 0:
                print(" ##### handle metadata:%s" % field)

            toks = rule.split('|')
            if len(toks) != 2:
                raise Exception("malformed metadata rule:%s" % field)
            # wildcard used?
            if toks[0][-1] == '*':
                line = sectionDoc.getSectionLine(toks[0])
                # line offset(s) list are in second token
                offsets = toks[1].split(',')
                aValue = ''
                for offset in offsets:
                    nLine = line + int(offset)
                    if len(aValue) > 0:
                        aValue = "%s|" % aValue
                    aValue = "%s%s" % (aValue, sectionDoc.getLineValue(nLine))
                if self.debug == 0:
                    print("  metadata:%s='%s'" % (field, aValue))
            else:
                aValue = sectionDoc.getValue(toks[0], toks[1])
            # supress initial space is any
            if aValue[0] == ' ':
                aValue = aValue[1:]
            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        self.metadata = met

        # METADATA_PARENT_IDENTIFIER: source product name 'NNAA,20090721222747_po_2627437_0000000.zip' without NNAA and zip
        # local attribute originalName: 20090721222747_po_2627437_0000000.zip 
        tmp = self.origName.replace('NNAA,', '')
        self.metadata.addLocalAttribute('originalName', tmp)
        tmp = tmp.replace('.zip', '')
        self.metadata.setMetadataPair(metadata.METADATA_PARENT_IDENTIFIER, tmp)
        num_added = num_added + 1

        return num_added

    #
    # refine the metada, should perform in order:
    # - normalise date and time
    # - set platform info
    # - build type code
    #
    def refineMetadata(self):
        # set or verify per mission info
        self.metadata.setMetadataPair('METADATA_SENSOR_TYPE', 'OPTICAL')

        # '2008-08-06 10:51 GMT' into: date + time
        toks = self.metadata.getMetadataValue(metadata.METADATA_START_DATE).strip().split(" ")
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_START_TIME, "%s:00" % toks[1])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, toks[0])
        self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, "%s:00" % toks[1])

        #
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # set processing time: is '07/21/09' in metadata file
        # self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, "%sT%s:00Z" % (toks[0],toks[1]))
        toks = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME).strip().split("/")
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME,
                                      "20%s-%s-%sT00:00:00Z" % (toks[0], toks[2], toks[1]))

        # supress the degrees
        tmp = self.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT).replace(" degrees", "").replace("|",
                                                                                                          "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_FOOTPRINT, formatUtils.reverseFootprint(tmp))

        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_ELEVATION).replace(" degrees", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_SUN_ELEVATION, tmp)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_SUN_AZIMUTH).replace(" degrees", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_SUN_AZIMUTH, tmp)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE).replace(
            " degrees", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ACROSS_TRACK_INCIDENCE_ANGLE, tmp)

        tmp = self.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE).replace(
            " degrees", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_INSTRUMENT_ALONG_TRACK_INCIDENCE_ANGLE, tmp)

        # supress the meters, rect coordlist for ikonos is ULX |ULY
        tmp = self.metadata.getMetadataValue(browse_metadata.BROWSE_METADATA_RECT_COORDLIST).replace(" meters",
                                                                                                     "").strip()
        self.metadata.setMetadataPair(browse_metadata.BROWSE_METADATA_RECT_COORDLIST, tmp)

        # supress the pixels
        tmp = self.metadata.getMetadataValue(metadata.METADATA_IMAGE_NUM_ROWS).replace(" pixels", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_IMAGE_NUM_ROWS, tmp)
        tmp = self.metadata.getMetadataValue(metadata.METADATA_IMAGE_NUM_COLUMNS).replace(" pixels", "").strip()
        self.metadata.setMetadataPair(metadata.METADATA_IMAGE_NUM_COLUMNS, tmp)

        # format UTM code
        tmp = self.metadata.getMetadataValue(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER).strip()
        if tmp.find("Universal Transverse Mercator") >= 0:
            toks = tmp.split("|")
            tmp = "UTM_%s%s" % (toks[2].strip(), toks[1].strip())
            self.metadata.setMetadataPair(metadata.METADATA_REFERENCE_SYSTEM_IDENTIFIER, tmp)

        # strip cloud coverage value
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CLOUD_COVERAGE).strip()
        self.metadata.setMetadataPair(metadata.METADATA_CLOUD_COVERAGE, tmp)

        self.extractQuality(None, self.metadata)
        self.extractFootprint(None, self.metadata)

        #
        # self.wfsCountryResolver = WfsServiceClient.WfsServiceClient(self.processInfo)
        # reply = self.getCountry()
        # print " got cuntry code:%s" % reply
        # self.processInfo.addLog(" got cuntry code:%s" % reply)
        self.metadata.addLocalAttribute('countryCode', self.metadata.getMetadataValue(metadata.METADATA_COUNTRY))

        #
        # reorder the localattributes: boundingbox, countrycode, originalname
        #
        a = self.metadata.getLocalAttributeValue('boundingBox')
        b = self.metadata.getLocalAttributeValue('countryCode')
        c = self.metadata.getLocalAttributeValue('originalName')
        if a == None or b == None or c == None:
            raise Exception("error when reordering local attributes")
        print("got local attributes: a=%s; b=%s; c=%s" % (a, b, c))
        self.metadata.removeLocalAttribute('boundingBox')
        self.metadata.removeLocalAttribute('countryCode')
        self.metadata.removeLocalAttribute('originalName')
        self.metadata.addLocalAttribute('boundingBox', a)
        self.metadata.addLocalAttribute('countryCode', b)
        self.metadata.addLocalAttribute('originalName', c)

        return 1

    #
    #
    #
    def getCountry(self):
        self.processInfo.addLog(" will get cuntry code")
        clon = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LON)
        clat = self.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER_LAT)
        params = []
        lon = float(clon)
        lat = float(clat)
        params.append(lon)
        params.append(lat)
        params.append(lon + 0.001)
        params.append(lat + 0.001)
        reply = self.wfsCountryResolver.callWfsService(self.processInfo, params)
        lines = reply.split('\n')
        print("COUNTRY REPLY:\n%s" % reply)
        return lines[1].split(':')[1][0:-1]

    #
    #
    #
    def extractQuality(self, helper, met):
        return

    #
    # extract the footprint
    # - footprint is already extracted directly from metadata, Is already CCW . NEW: BUT IS NOT CORRECT FOR DESCENDING)
    # is:
    #   3          2
    #
    #
    #   0/4        1
    #
    # - there are 5 footprint node
    # - need to build the rowCol
    #
    #
    def extractFootprint(self, helper, met):
        # there are 5 coords
        met.setMetadataPair(browse_metadata.BROWSE_METADATA_FOOTPRINT_NUMBER_NODES, "5")

        nrows = self.metadata.getMetadataValue(metadata.METADATA_IMAGE_NUM_ROWS)
        ncols = self.metadata.getMetadataValue(metadata.METADATA_IMAGE_NUM_COLUMNS)

        tmp = "1 %s %s %s %s 1 1 1 1 %s" % (ncols, nrows, ncols, nrows, ncols)
        met.setMetadataPair(metadata.METADATA_FOOTPRINT_IMAGE_ROWCOL, tmp)

        # the footprint in Ikonos are not starting all on the same corner. Get top left footprint
        # calculate boundingbox and scene center
        browseIm = BrowseImage()
        browseIm.setFootprint(met.getMetadataValue(metadata.METADATA_FOOTPRINT))
        lat, lon = browseIm.calculateCenter()
        browseIm.calculateBoondingBox()
        ok = browseIm.testFirstPointTopLeft()
        if ok:
            self.processInfo.addLog(" footprint is already starting at top left")
        else:
            self.processInfo.addLog(
                " footprint is NOT starting at top left:%s" % met.getMetadataValue(metadata.METADATA_FOOTPRINT))
            topLeftPointIndex = browseIm.findPointTopLeft()
            self.processInfo.addLog(" footprint topLeftPointIndex:%s" % topLeftPointIndex)
            topLeftFootprint = browseIm.getTopLeftFootprint()
            met.setMetadataPair(metadata.METADATA_FOOTPRINT, topLeftFootprint)

        browseIm.setFootprint(met.getMetadataValue(metadata.METADATA_FOOTPRINT))

        met.setMetadataPair(metadata.METADATA_SCENE_CENTER, "%s %s" % (lat, lon))
        met.setMetadataPair(metadata.METADATA_SCENE_CENTER_LAT, lat)
        met.setMetadataPair(metadata.METADATA_SCENE_CENTER_LON, lon)

        # boundingBox is needed in the localAttributes
        met.setMetadataPair(metadata.METADATA_BOUNDING_BOX, browseIm.boondingBox)
        met.addLocalAttribute("boundingBox", met.getMetadataValue(metadata.METADATA_BOUNDING_BOX))

        # get scene center lat long in degree + milidegree for filename
        lat = float(lat)
        ilat = int(lat)
        imlat = abs(int((lat - ilat) * 1000))
        simlat = "%s" % formatUtils.normaliseNumber("%s" % imlat, 3, '0')
        print(" refineMetadata ilat=%s; imlat=%s; simlat=%s" % (ilat, imlat, simlat))
        if ilat < 0:
            silat = "%s" % abs(ilat)
            slat = "S%s" % formatUtils.normaliseNumber(silat, 2, '0')
        else:
            silat = "%s" % abs(ilat)
            slat = "N%s" % formatUtils.normaliseNumber(silat, 2, '0')

        lon = float(lon)
        ilon = int(lon)
        imlon = abs(int((lon - ilon) * 1000))
        simlon = "%s" % formatUtils.normaliseNumber("%s" % imlon, 3, '0')
        print(" refineMetadata ilon=%s; imlon=%s; simlon=%s" % (ilon, imlon, simlon))
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

        return

    def toString(self):
        res = "preview file:%s" % self.preview_path
        res = "%s\nmetadata file:%s" % (res, self.metadata_path)
        return res

    def dump(self):
        print(self.toString())
