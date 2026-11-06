#!/usr/bin/env python
"""Make a KMZ from an EoSip product
used from command line of by the EoSip converter(s)


Gilles Lavaux

Changes:
1017-may: fix for KML over the +-180 longitude boundary. Test if is crossing using BrowseImage, if so add 360 for positive long and 720 for negative


some KML guesses:
- the GroundOverlay/gx:LatLonQuad/coordinates order is:
  3 ------- 2
  |         |
  |         |
  |         |
  0/4 ----- 1
  and they are 3 values + space: 'lon,lat,0 '
"""
import inspect
import os
import sys
import traceback
import zipfile
from optparse import OptionParser
from ..esaProducts.browseImage import BrowseImage
from ..esaProducts import metadata
from .. import xmlHelper

__templateDir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

PATH = '/home/gilles/shared/converter_workspace/outspace/image2006_new_glpkg/SPOT/SP4_OPER_HRI__X__2O_20050605T090007_N39-791_E026-958_0001.SIP.ZIP'
KML_TEMPLATE = 'TEMPLATE.KML'
#
ORBIT_DIRECTION_PATH = 'procedure/EarthObservationEquipment/acquisitionParameters/Acquisition/orbitDirection'
LINEAR_RING_PATH = 'featureOfInterest/Footprint/multiExtentOf/MultiSurface/surfaceMember/Polygon/exterior/LinearRing/posList'
SCENE_CENTER_PATH = 'featureOfInterest/Footprint/centerOf/Point/pos'
SPECIFIC_ATTRIBUTES_PATH = 'metaDataProperty/EarthObservationMetaData/vendorSpecific/SpecificInformation'

debug = True

EXT_SIP_ZIP = '.SIP.ZIP'
EXT_ZIP = '.ZIP'


def addLogToProcessInfo(processInfo, mesg):
    if processInfo is not None:
        processInfo.addLog(mesg)


#
#  2018/08: add method entry point
#
def makeKmz(srcPath, outPath='.', useBoundingBox=False, dontReverseBrowse=False):
    print("\n eosipToKmz on product at path:%s, outpath:%s; useBoundingBox:%s" % (srcPath, outPath, useBoundingBox))

    options = []
    if useBoundingBox:
        options.append('boundingbox')

    browseName, browseData = getBrowseDatafromZip(srcPath)
    if browseName is None:
        raise Exception("browse not found in EoSip")
    if browseData is None:
        raise Exception("browse data not found in EoSip")

    print("\n browseName:%s" % browseName)

    id = browseName.split('.')[0]
    print("\n use browse:%s of length:%s" % (browseName, len(browseData)))

    xmlData = getMetadataReportfromZip(srcPath)
    # if DEBUG:
    #    print xmlData

    # orbit direction
    try:
        orbitDirection = getOrbitDirection(xmlData)
    except:
        print("CAN NOT GET ORBIT DIRECTION FROM XML")
        orbitDirection = 'DESCENDING'

    # data, reverse, options
    if orbitDirection == 'DESCENDING':
        linearRing = makeLinearRing(xmlData, None, True, options, None, dontReverseBrowse)
    elif orbitDirection == 'ASCENDING':
        linearRing = makeLinearRing(xmlData, None, False, options, None, dontReverseBrowse)
    else:
        raise Exception("invalid orbit direction:%s" % orbitDirection)

    #
    sceneCenter = getSceneCenter(xmlData)

    #
    SCENE_CENTER_POINT = "%s,%s,0" % (sceneCenter.split(' ')[1], sceneCenter.split(' ')[0])

    fd = open("%s/%s" % (__templateDir, KML_TEMPLATE))
    data = fd.read()
    fd.close()

    #
    data = data.replace('PRODUCT_NAME', srcPath)
    data = data.replace('PRODUCT_CENTER_LONGITUDE', sceneCenter.split(' ')[1])
    data = data.replace('PRODUCT_CENTER_LATITUDE', sceneCenter.split(' ')[0])
    data = data.replace('PRODUCT_LINEAR_RING', linearRing)
    data = data.replace('SCENE_CENTER_POINT', SCENE_CENTER_POINT)
    data = data.replace('PRODUCT_BROWSE_HREF', browseName)

    #
    # if DEBUG:
    #    print "KML:\n%s" % data

    #
    # outPath = '.'
    kmzPath = "%s/%s.KMZ" % (outPath, id)
    zipf = zipfile.ZipFile(kmzPath, 'w')
    zipf.writestr("%s.KML" % id, data, zipfile.ZIP_DEFLATED)
    zipf.writestr(browseName, browseData, zipfile.ZIP_DEFLATED)
    zipf.close()
    print("\n\n KMZ created:%s" % kmzPath)
    return kmzPath


#
# entry point from converter
#
# call makeOneKml below
# returns a list of KMZ path ( make for worldview multiple output)
#
# used from converter: OK
# don't use the ZIP, use values from products
#
# params:
#  - useBoundingBox: boollean telling if we use the footprint or the boundingbox
#  - outPath: the path where the MKZ will be created
#  - processInfo: the processInfo instance present in the ingester
#  - dontReverseBrowse: boolean used to tell that the browse image is already oriented well
#
#
def makeKmlFromEoSip_new(useBoundingBox, outPath, aProcessInfo, dontReverseBrowse=False):
    try:
        eoSipPath = aProcessInfo.destProduct.getPath()
        result = None
        if isinstance(eoSipPath, list):
            result = []
            n = 0
            for iten in eoSipPath:
                path = makeOneKml(useBoundingBox, outPath, aProcessInfo, n, dontReverseBrowse)
                result.append(path)
                n = n + 1
        else:
            result = makeOneKml(useBoundingBox, outPath, aProcessInfo, -1, dontReverseBrowse)

        return result

    except Exception as e:
        print("Error: problem writing current kmz file in fodler:%s" % aProcessInfo.workFolder)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" problem is:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
        # return None
        raise e


#
# called when creating KMZ from converter
#
# make one KMZ, two cases:
#
# params:
#  - useBoundingBox: boollean telling if we use the footprint or the boundingbox
#  - outPath: the path where the MKZ will be created
#  - processInfo: the processInfo instance present in the ingester
#  - index: ingle EoSIp : index =-1; multiple EoSip: index >=0
#  - dontReverseBrowse: boolean used to tell that the browse image is already oriented well
#
def makeOneKml(useBoundingBox, outPath, aProcessInfo, index, dontReverseBrowse):
    try:
        options = []

        if index < 0:
            if debug:
                print("\n makeOneKml")
            product = aProcessInfo.destProduct
        else:
            if debug:
                print("\n makeOneKml (multiple case), index: %s" % index)
            product = aProcessInfo.destProduct.getEoSip(index)

        if debug:
            print(" product: %s" % product)
        eoSipPath = product.getPath()
        if debug:
            print(" eoSipPath: %s" % eoSipPath)

        #
        # new: get .BID if present
        #
        browseName = product.sourceBrowsesPath[0]
        if len(product.sourceBrowsesPath) > 1:
            for aName in product.sourceBrowsesPath:
                if aName.find('.BID.') > 0:
                    browseName = aName
                    print(" use BID browse:%s" % browseName)

        # get browse data
        with open(r'C:\Users\simon\Desktop\browseNames.txt', 'a+') as f:
            f.write(browseName + '\n')

        print(browseName)
        with open(browseName, 'rb') as fd:
            browseData = fd.read()

        # id
        browseNameInZip = browseName.split('/')[-1]
        id = browseNameInZip.split('.')[0]
        if debug:
            print(" use browse:%s ; data length:%s" % (browseName, len(browseData)))
            print(" id:%s" % id)

        # get linearRing and scene center
        ring = None
        if useBoundingBox:
            options.append('boundingbox')
            # bounding box is CCW starting at top left: UL, LL, LR, UR
            ring = product.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX)
            # print(" ring:%s" % ring)
            if ring == metadata.VALUE_NOT_PRESENT:
                raise Exception("bounding box not found in metadata!")
            # add 5th closing node
            toks = ring.split(' ')
            ring = "%s %s %s" % (ring, toks[0], toks[1])
            if debug:
                print(" bounding box:%s" % ring)
            addLogToProcessInfo(aProcessInfo, " get 5 pair of coords footprint from bounding box:%s" % ring)
        else:
            ring = product.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT)
            if debug:
                print(" footpring:%s" % ring)
            addLogToProcessInfo(aProcessInfo, " use 5 pair of coords footprint:%s" % ring)

        orbitDirection = product.metadata.getMetadataValue(metadata.METADATA_ORBIT_DIRECTION)
        addLogToProcessInfo(aProcessInfo, " orbitDirection is:%s" % orbitDirection)
        if debug:
            print(" orbitDirection:%s" % orbitDirection)

        # 
        descending = True
        if orbitDirection == 'ASCENDING':
            descending = False
        # else:
        #    raise Exception("invalid orbit direction:%s" % orbitDirection)

        sceneCenter = product.metadata.getMetadataValue(metadata.METADATA_SCENE_CENTER)
        if debug:
            print("  sceneCenter:%s" % sceneCenter)

        # build linearRing
        linearRing = makeLinearRing(None, ring, descending, options, aProcessInfo, dontReverseBrowse)

        #
        SCENE_CENTER_POINT = "%s,%s,0" % (sceneCenter.split(' ')[1], sceneCenter.split(' ')[0])

        fd = open("%s/%s" % (__templateDir, KML_TEMPLATE))
        data = fd.read()
        fd.close()

        #
        data = data.replace('PRODUCT_NAME', eoSipPath.split('/')[-1])
        data = data.replace('PRODUCT_CENTER_LONGITUDE', sceneCenter.split(' ')[1])
        data = data.replace('PRODUCT_CENTER_LATITUDE', sceneCenter.split(' ')[0])
        data = data.replace('PRODUCT_LINEAR_RING', linearRing)
        data = data.replace('SCENE_CENTER_POINT', SCENE_CENTER_POINT)
        data = data.replace('PRODUCT_BROWSE_HREF', browseNameInZip)

        description = '<html><body></body></html>'
        data = data.replace('PRODUCT_DESCRIPTION', buildHtmlDescription(product))

        #
        kmzPath = "%s/%s.KMZ" % (outPath, id)
        zipf = zipfile.ZipFile(kmzPath, 'w')
        zipf.writestr("%s.KML" % id, data, zipfile.ZIP_DEFLATED)
        zipf.writestr(browseNameInZip, browseData, zipfile.ZIP_DEFLATED)
        zipf.close()
        print(" KMZ created:%s" % kmzPath)
        return kmzPath
    except Exception as e:
        print("Error: problem writing current kmz file in fodler:%s" % aProcessInfo.workFolder)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" problem is:%s  %s\n%s\n" % (exc_type, exc_obj, traceback.format_exc()))
        # return None
        raise e


#
# build the source/source 1 html information
#
def buildHtmlDescription(product):
    original_name = product.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)

    startDate = product.metadata.getMetadataValue(metadata.METADATA_START_DATE)
    startTime = product.metadata.getMetadataValue(metadata.METADATA_START_TIME)
    stopDate = product.metadata.getMetadataValue(metadata.METADATA_STOP_DATE)
    stopTime = product.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)

    instrument = product.metadata.getMetadataValue(metadata.METADATA_INSTRUMENT)
    orbit = product.metadata.getMetadataValue(metadata.METADATA_ORBIT)
    platform = product.metadata.getMetadataValue(metadata.METADATA_PLATFORM)
    platformId = product.metadata.getMetadataValue(metadata.METADATA_PLATFORM_ID)

    typecode = product.metadata.getMetadataValue(metadata.METADATA_TYPECODE)
    size = product.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)

    size = product.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)
    size = product.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)

    sensorType = product.metadata.getMetadataValue(metadata.METADATA_SENSOR_TYPE)
    sensorMode = product.metadata.getMetadataValue(metadata.METADATA_SENSOR_OPERATIONAL_MODE)

    #
    description = '<html><body><table>'
    description = "%s<tr><td bgcolor='dedede'>Original name: </td><td bgcolor='eeeeee'>%s</td></tr>" % (
    description, original_name)
    description = "%s<tr><td bgcolor='dedede'>Size: </td><td bgcolor='eeeeee'>%s</td></tr>" % (description, size)
    description = "%s<tr><td bgcolor='dedede'>Type code: </td><td bgcolor='eeeeee'>%s</td></tr>" % (
    description, typecode)
    description = "%s<tr><td bgcolor='dedede'>Platform: </td><td bgcolor='eeeeee'>%s%s</td></tr>" % (
    description, platform, platformId)
    description = "%s<tr><td bgcolor='dedede'>Start: </td><td bgcolor='eeeeee'>%s %s</td></tr>" % (
    description, startDate, startTime)
    description = "%s<tr><td bgcolor='dedede'>Stop: </td><td bgcolor='eeeeee'>%s %s</td></tr>" % (
    description, stopDate, stopTime)

    description = "%s<tr><td bgcolor='dedede'>Sensor type: </td><td bgcolor='eeeeee'>%s</td></tr>" % (
    description, sensorType)
    description = "%s<tr><td bgcolor='dedede'>Sensor mode: </td><td bgcolor='eeeeee'>%s</td></tr>" % (
    description, sensorMode)

    description = "%s</table></body></html>" % description
    return description


#
# called when creating KMZ from EoSip file OR from converter:
# - when making from EoSip: footprintString is  None
# - when from converter: footprintString is set to footprint OR bbox( and then options contains 'boundingbox ')
#
# 2018/06 : is ok?
#
#  - xmlData: ??
#  - footprintString: the  given footprint if any
#  - descending:
#  - options:
#  - processInfo: the processInfo instance present in the ingester
#  - dontReverseBrowse: boolean used to tell that the browse image is already oriented well
#
def makeLinearRing(xmlData, footprintString, descending=True, options=None, aProcessInfo=None, dontReverseBrowse=False):
    #
    if xmlData is None:
        xmlDataInfo = 'None'
    else:
        xmlDataInfo = xmlData[0:100] + ' ...'
    addLogToProcessInfo(aProcessInfo,
                        " makeLinearRing ; start of xmlData=%s ...; footprintString=%s; descending=%s; options=%s; dontReverseBrowse=%s" % (
                        xmlDataInfo, footprintString, descending, options, dontReverseBrowse))
    #
    ringNodes = []
    boundingbox = False
    ringString = None
    # get CCW eoSip footprint
    if debug:
        # print " makeLinearRing options:%s" % options
        print(" makeLinearRing ; start of xmlData=%s ...; footprintString=%s; descending=%s; options=%s; dontReverseBrowse=%s" % (
        xmlDataInfo, footprintString, descending, options, dontReverseBrowse))
    try:
        options.index('boundingbox')
        boundingbox = True
    except:
        pass

    result2 = None
    if footprintString is None:
        if debug:
            print("  no footprintString given, get it from xml data")
        addLogToProcessInfo(aProcessInfo, " no footprintString given, get it from xml data")
        # extact metadata
        helper = xmlHelper.XmlHelper()
        # helper.setDebug(1)
        helper.setData(xmlData)
        # print "xmldata:%s" % xmlData
        helper.parseData()

        if boundingbox:
            if debug:
                print("  BOUNDINGBOX CASE:")
            addLogToProcessInfo(aProcessInfo, " BOUNDINGBOX CASE")
            helper.getNodeByPath(None, SPECIFIC_ATTRIBUTES_PATH, None, ringNodes)
            # helper.setDebug(True)
            if debug:
                print("  number of nodes found:%s" % len(ringNodes))
            found = False
            for node in ringNodes:
                aChildren = helper.getNodeChildrenByName(node, 'localAttribute')
                helper.setDebug(True)
                tmp = helper.getNodeText(aChildren[0])
                if debug:
                    print("  ##### localAttribute:%s'" % tmp)
                if tmp == 'boundingBox':
                    aChildren = helper.getNodeChildrenByName(node, 'localValue')
                    tmp = helper.getNodeText(aChildren[0])
                    # add 5th closing node
                    toks = tmp.split(' ')
                    ringString = "%s %s %s" % (tmp, toks[0], toks[1])
                    found = True
                    break

            if not found:
                raise Exception('can not get element at LINEAR_RING_PATH:%s' % LINEAR_RING_PATH)

            if debug:
                print("  found ringString (from boundingbox):%s" % ringString)

            # BBOX: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # so is like the FOOTPRINT descending case below

            # 2017 may new: test if cross 180 boundary
            browseIm = BrowseImage()
            browseIm.setFootprint(ringString)
            browseIm.testCrossing()
            crossingLongBoundary = browseIm.isCrossing
            if debug:
                print("  crossingLongBoundary:%s" % crossingLongBoundary)

            coords = ringString.split(' ')
            if debug:
                print("  USE COORDS:%s" % coords)
            resultLonLat = ''
            n = 0
            # if ascending: we have footprint CCW starting at LR: LR, UR, UL, LL, LR
            # if descending: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL

            # if we says browse is ok all time:
            if dontReverseBrowse:
                if debug:
                    print("  ## descending case, but dontReverseBrowse set -> don't reverse footprint")
                addLogToProcessInfo(aProcessInfo, " descending, but dontReverseBrowse set -> don't reverse footprint")
                raise Exception("NOT IMPLEMENTED 0")
            else:
                # descending eosip:
                if descending:
                    if debug:
                        print("  ## descending case, we want to reverse footprint")
                    addLogToProcessInfo(aProcessInfo, " descending, reverse footprint")
                    for i in range(len(coords) // 2):
                        lat = coords[(i * 2)]
                        lon = coords[(i * 2) + 1]
                        if len(resultLonLat) > 0:
                            resultLonLat += ' '
                        resultLonLat += "%s,%s,0" % (lon, lat)
                        if debug:
                            print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                        n = n + 1

                    # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                    # --> index 1,2,3,0,1
                    result2 = ''
                    toks = resultLonLat.split(' ')
                    result2 = "%s" % (toks[1])
                    result2 += " %s" % (toks[2])
                    result2 += " %s" % (toks[3])
                    result2 += " %s" % (toks[0])
                    result2 += " %s" % (toks[1])
                    if debug:
                        print("  ## descending case, we want to reverse footprint. use index 1 2 3 0 1")
                    addLogToProcessInfo(aProcessInfo, " descending, we want to reverse footprint. use index 1 2 3 0 1")
                else:
                    raise Exception("NOT IMPLEMENTED 1")

        else:
            if debug:
                print("  FOOTPRINT CASE:")
            addLogToProcessInfo(aProcessInfo, " FOOTPRINT CASE")
            helper.getNodeByPath(None, LINEAR_RING_PATH, None, ringNodes)
            ringString = helper.getNodeText(ringNodes[0])

            if len(ringNodes) == 0:
                raise Exception('can not get element at LINEAR_RING_PATH:%s' % LINEAR_RING_PATH)
            if debug:
                print("  found ringString (from footprint):%s" % ringString)

            # 2017 may new: test if cross 180 boundary
            browseIm = BrowseImage()
            browseIm.setFootprint(ringString)
            browseIm.testCrossing()
            crossingLongBoundary = browseIm.isCrossing
            if debug:
                print("  crossingLongBoundary:%s" % crossingLongBoundary)

            coords = ringString.split(' ')
            if debug:
                print("  USE COORDS:%s" % coords)
            resultLonLat = ''
            n = 0
            # if ascending: we have footprint CCW starting at LR: LR, UR, UL, LL, LR
            # if descending: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # descending eosip:

            if descending == True:
                if debug:
                    print("  ## descending case, we want to reverse footprint")
                addLogToProcessInfo(aProcessInfo,
                                    " descending case, dontReverseBrowse is:" + dontReverseBrowse + "; test reverse footprint")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                if debug:
                    print("  lon,lat,elev ring:'%s'" % resultLonLat)

                # if we says browse is ok all time:
                toks = resultLonLat.split(' ')
                if dontReverseBrowse:
                    if debug:
                        print("  ## descending case, but dontReverseBrowse set -> don't reverse footprint. use index 3 0 1 2 3")
                    addLogToProcessInfo(aProcessInfo,
                                        " descending, but dontReverseBrowse set -> don't reverse footprint. use index 3 0 1 2 3")
                    # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                    # --> index 1,2,3,0,1
                    result2 = ''
                    result2 = "%s" % (toks[3])
                    result2 += " %s" % (toks[0])
                    result2 += " %s" % (toks[1])
                    result2 += " %s" % (toks[2])
                    result2 += " %s" % (toks[3])
                else:
                    if debug:
                        print("  ## descending case, but dontReverseBrowsenot set -> reverse footprint?. use index 1 2 3 0 1")
                    addLogToProcessInfo(aProcessInfo,
                                        " descending, but dontReverseBrowse not set -> reverse footprint?. use index 1 2 3 0 1")
                    # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                    # --> index 1,2,3,0,1
                    result2 = ''
                    result2 = "%s" % (toks[1])
                    result2 += " %s" % (toks[2])
                    result2 += " %s" % (toks[3])
                    result2 += " %s" % (toks[0])
                    result2 += " %s" % (toks[1])

            else:
                if debug:
                    print("  ## ascending case, we dont want to reverse footprint")
                addLogToProcessInfo(aProcessInfo, " ascending, we dont want to reverse footprint")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                if debug:
                    print("  lon,lat,elev ring:'%s'" % resultLonLat)

                if debug:
                    print("  ## ascending case, ascending, we dont want to reverse footprint. use index 3 0 1 2 3")
                addLogToProcessInfo(aProcessInfo,
                                    " ascending case, we dont want to reverse footprint. use index 3 0 1 2 3")

                # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                # --> index 3,0,1,2,3
                result2 = ''
                toks = resultLonLat.split(' ')
                result2 = "%s" % (toks[3])
                result2 += " %s" % (toks[0])
                result2 += " %s" % (toks[1])
                result2 += " %s" % (toks[2])
                result2 += " %s" % (toks[3])

    else:  # footprint is not None
        ringString = footprintString
        if debug:
            print("  footprintString given:%s" % ringString)
        addLogToProcessInfo(aProcessInfo, " footprintString given:%s" % ringString)
        if boundingbox:
            if debug:
                print("  BOUNDINGBOX CASE:")
            addLogToProcessInfo(aProcessInfo, " BOUNDINGBOX CASE")
            # BBOX: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # so is like the FOOTPRINT descending case below

            # 2017 may new: test if cross 180 boundary
            browseIm = BrowseImage()
            browseIm.setFootprint(ringString)
            browseIm.testCrossing()
            crossingLongBoundary = browseIm.isCrossing
            if debug:
                print("  crossingLongBoundary:%s" % crossingLongBoundary)

            coords = ringString.split(' ')
            if debug:
                print("  USE COORDS:%s" % coords)
            resultLonLat = ''
            n = 0
            # if ascending: we have footprint CCW starting at LR: LR, UR, UL, LL, LR
            # if descending: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # descending eosip:
            if descending == True:
                if debug:
                    print("  ## descending case, we want to reverse footprint")
                addLogToProcessInfo(aProcessInfo, " descending, reverse footprint")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                # --> index 1,2,3,0,1
                result2 = ''
                toks = resultLonLat.split(' ')
                if dontReverseBrowse:
                    if debug:
                        print("  ## descending case, but dontReverseBrowse set -> don't reverse footprint, use index 1 2 3 0 1")
                    addLogToProcessInfo(aProcessInfo,
                                        " descending, but dontReverseBrowse set -> don't reverse footprint, use index 1 2 3 0 1")
                    result2 = "%s" % (toks[1])
                    result2 += " %s" % (toks[2])
                    result2 += " %s" % (toks[3])
                    result2 += " %s" % (toks[0])
                    result2 += " %s" % (toks[1])
                else:
                    if debug:
                        print("  ## descending case, dontReverseBrowse not set -> reverse footprint, use index 0 1 2 3 0")
                    addLogToProcessInfo(aProcessInfo,
                                        " descending, dontReverseBrowse not set -> reverse footprint, use index 0 1 2 3 0")
                    result2 += " %s" % (toks[0])
                    result2 += " %s" % (toks[1])
                    result2 += " %s" % (toks[2])
                    result2 += " %s" % (toks[3])
                    result2 += " %s" % (toks[0])
            else:
                if debug:
                    print("  ## ascending case,  don't reverse footprint")
                addLogToProcessInfo(aProcessInfo, " ascending,  don't reverse footprint")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                if debug:
                    print("  top left CW: lon,lat,elev ring:'%s'" % resultLonLat)

                # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                # --> index 3,0,1,2,3
                result2 = ''
                toks = resultLonLat.split(' ')
                # result2 = "%s" % (toks[3])
                # result2 += " %s" % (toks[0])
                # result2 += " %s" % (toks[1])
                # result2 += " %s" % (toks[2])
                # result2 += " %s" % (toks[3])
                result2 = "%s" % (toks[1])
                result2 += " %s" % (toks[2])
                result2 += " %s" % (toks[3])
                result2 += " %s" % (toks[0])
                result2 += " %s" % (toks[1])
                if debug:
                    print("  ## ascending case, dontReverseBrowse not set -> don't reverse footprint, use index 1 2 3 0 1")
                addLogToProcessInfo(aProcessInfo,
                                    " ascending, dontReverseBrowse not set -> don't reverse footprint, use index 0 1 2 3 0")

        else:
            if debug:
                print("  FOOTPRINT CASE:")
            addLogToProcessInfo(aProcessInfo, " FOOTPRINT CASE")
            # 2017 may new: test if cross 180 boundary
            browseIm = BrowseImage()
            browseIm.setFootprint(ringString)
            browseIm.testCrossing()
            crossingLongBoundary = browseIm.isCrossing
            if debug:
                print("  crossingLongBoundary:%s" % crossingLongBoundary)

            coords = ringString.split(' ')
            if debug:
                print("  USE COORDS:%s" % coords)
            resultLonLat = ''
            n = 0
            # if ascending: we have footprint CCW starting at LR: LR, UR, UL, LL, LR
            # if descending: we have footprint CCW starting at UL: UL, LL, LR, UR, UL
            # we want to create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
            # descending eosip:
            if descending == True:
                if debug:
                    print("  ## descending case, we want to reverse footprint")
                addLogToProcessInfo(aProcessInfo, " descending, reverse footprint")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                if debug:
                    print("  top left CW: lon,lat,elev ring:'%s'" % resultLonLat)
                    addLogToProcessInfo(aProcessInfo, " top left CW: lon,lat,elev ring:'%s'" % resultLonLat)

                # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                # --> index 1,2,3,0,1
                result2 = ''
                toks = resultLonLat.split(' ')
                result2 = "%s" % (toks[1])
                result2 += " %s" % (toks[2])
                result2 += " %s" % (toks[3])
                result2 += " %s" % (toks[0])
                result2 += " %s" % (toks[1])
                if debug:
                    print("  ## descending case, ? reverse footprint, use index 1 2 3 0 1")
                addLogToProcessInfo(aProcessInfo, " descending, ? reverse footprint, use index 1 2 3 0 1")

            else:
                if debug:
                    print("  ## ascending case")
                addLogToProcessInfo(aProcessInfo, " ascending")
                for i in range(len(coords) // 2):
                    lat = coords[(i * 2)]
                    lon = coords[(i * 2) + 1]
                    if len(resultLonLat) > 0:
                        resultLonLat += ' '
                    resultLonLat += "%s,%s,0" % (lon, lat)
                    if debug:
                        print("  ## n=%s; resultLonLat=%s" % (n, resultLonLat))
                    n = n + 1

                if debug:
                    print("  bottom right CW: lon,lat,elev ring:'%s'" % resultLonLat)
                    addLogToProcessInfo(aProcessInfo, " bottom right CW: lon,lat,elev ring:'%s'" % resultLonLat)

                # we create the KML ring CCW starting at LL: LL, LR, UR, UL, LL
                # --> index 3,0,1,2,3
                result2 = ''
                toks = resultLonLat.split(' ')
                result2 = "%s" % (toks[3])
                result2 += " %s" % (toks[0])
                result2 += " %s" % (toks[1])
                result2 += " %s" % (toks[2])
                result2 += " %s" % (toks[3])
                if debug:
                    print("  ## ascending case, ? reverse footprint, use index 3 0 1 2 3")
                addLogToProcessInfo(aProcessInfo, " ascending, ? reverse footprint, use index 3 0 1 2 3")

    # get a lat space lon representation for test purpose
    toks = result2.split(',0 ')
    latLon = ''
    for tok in toks:
        if len(latLon) > 0:
            latLon += " "
        latLon += "%s %s" % (tok.split(",")[1], tok.split(",")[0])
    print(("  makeLinearRing FINAL footprint like 'lat space lon space' string:%s" % latLon))
    addLogToProcessInfo(aProcessInfo, "  makeLinearRing FINAL footprint like 'lat space lon space' string:%s" % latLon)

    print(("  makeLinearRing FINAL KML 'lon,lat space' string:%s" % result2.replace(',0 ', ' ')[0:-2]))
    addLogToProcessInfo(aProcessInfo,
                        "  makeLinearRing FINAL KML 'lon,lat space' string:%s" % result2.replace(',0 ', ' ')[0:-2])

    return result2


#
# return scene center 'lat lon'
#
def getSceneCenter(xmlData):
    # extact metadata
    helper = xmlHelper.XmlHelper()
    # helper.setDebug(1)
    helper.setData(xmlData)
    helper.parseData()

    # 
    tmpNodes = []
    helper.getNodeByPath(None, SCENE_CENTER_PATH, None, tmpNodes)
    if len(tmpNodes) == 0:
        raise Exception('can not get element at SCENE_CENTER_PATH:%s' % SCENE_CENTER_PATH)
    tmp = helper.getNodeText(tmpNodes[0])
    if debug:
        print("\n scene center:%s" % tmp)
    return tmp


#
# return orbit direction ASCENDING/DESCENDING
#
def getOrbitDirection(xmlData):
    # extact metadata
    helper = xmlHelper.XmlHelper()
    # helper.setDebug(1)
    helper.setData(xmlData)
    helper.parseData()

    # 
    tmpNodes = []
    helper.getNodeByPath(None, ORBIT_DIRECTION_PATH, None, tmpNodes)
    if len(tmpNodes) == 0:
        raise Exception('can not get element at ORBIT_DIRECTION_PATH:%s' % ORBIT_DIRECTION_PATH)
    tmp = helper.getNodeText(tmpNodes[0])
    if debug:
        print("\n orbit direction:%s" % tmp)
    return tmp


#
# retrieve metadata report from zip archive
#
def getMetadataReportfromZip(path):
    shortName = os.path.split(path)[-1]
    if shortName.upper().endswith(EXT_SIP_ZIP):
        shortName = shortName[0:-len(EXT_SIP_ZIP)]
        if debug:
            print("  shortName:%s" % shortName)

    elif shortName.upper().endswith(EXT_ZIP):
        shortName = shortName[0:-len(EXT_ZIP)]
        if debug:
            print("  shortName:%s" % shortName)

    reportName = None
    reportData = None
    fh = open(path, 'rb')
    z = zipfile.ZipFile(fh)
    n = 0
    d = 0
    for name in z.namelist():
        firstLevel = True
        if name.find('/') >= 0:
            firstLevel = False

        if firstLevel:
            # print "  first level:"
            if name.upper().endswith('%s.XML' % shortName):
                reportName = name
                reportData = z.read(name)
                if debug:
                    print("  found metadata report:%s" % reportName)
                break

            elif name.upper().endswith('%s.MD.XML' % shortName):
                reportName = name
                reportData = z.read(name)
                if debug:
                    print("  found metadata report:%s" % reportName)
                break

        n = n + 1
        # if DEBUG:
        #    print "  zip content[%d]:%s" % (n, name)
        if name.endswith('/'):
            d = d + 1
            firstLevel = False

    z.close()
    fh.close()
    return reportData


#
# retrieve browse data and name from zip archive
#
def getBrowseDatafromZip(path):
    browseData = None
    browseName = None
    fh = open(path, 'rb')
    z = zipfile.ZipFile(fh)
    n = 0
    d = 0
    for name in z.namelist():
        firstLevel = True
        if name.find('/') >= 0:
            firstLevel = False

        if firstLevel:
            # print "  first level:"
            if name.upper().endswith('.BID.PNG'):
                browseName = name
                browseData = z.read(browseName)
            elif name.upper().endswith('.PNG'):
                browseName = name
                browseData = z.read(browseName)
            elif name.upper().endswith('.JPG'):
                browseName = name
                browseData = z.read(browseName)

        n = n + 1
        # if DEBUG:
        #    print "  zip content[%d]:%s" % (n, name)
        if name.endswith('/'):
            d = d + 1
            firstLevel = False

        if browseName is not None:
            break

    z.close()
    fh.close()
    return browseName, browseData


#
# use from command line
#
def main():
    """Main funcion"""

    print("sys.argv:%s" % sys.argv)

    path = PATH
    options = []
    parser = OptionParser()
    parser.add_option("-p", "--path", dest="path", help="eoSip path")
    parser.add_option("-b", "--boundingbox", dest="boundingBox", default=False,
                      help="use boundingBox instead of footprint")
    pOptions, args = parser.parse_args(sys.argv)

    if pOptions.path != None:
        path = pOptions.path
    else:
        # raise Exception('need a path, try -h for syntax')
        pass
    useBoundingBox = False
    if pOptions.boundingBox != None:
        print(" pOptions.boundingBox=%s" % pOptions.boundingBox)
        if pOptions.boundingBox == 'True':
            options.append('boundingbox')
            useBoundingBox = True

    print("\n eosipToKmz on product at path:%s, useBoundingBox=%s" % (path, useBoundingBox))

    browseName, browseData = getBrowseDatafromZip(path)
    if browseName is None:
        raise Exception("browse not found in EoSip")
    if browseData is None:
        raise Exception("browse data not found in EoSip")

    print("\n browseName:%s" % browseName)

    id = browseName.split('.')[0]
    print("\n use browse:%s of length:%s" % (browseName, len(browseData)))

    xmlData = getMetadataReportfromZip(path)
    # if DEBUG:
    #    print xmlData

    # orbit direction
    try:
        orbitDirection = getOrbitDirection(xmlData)
    except:
        print("CAN NOT GET ORBIT DIRECTION FROM XML")
        orbitDirection = 'DESCENDING'

    # data, reverse, options
    if orbitDirection == 'DESCENDING':
        linearRing = makeLinearRing(xmlData, None, True, options, None)
    elif orbitDirection == 'ASCENDING':
        linearRing = makeLinearRing(xmlData, None, False, options, None)
    else:
        raise Exception("invalid orbit direction:%s" % orbitDirection)

    #
    sceneCenter = getSceneCenter(xmlData)

    #
    SCENE_CENTER_POINT = "%s,%s,0" % (sceneCenter.split(' ')[1], sceneCenter.split(' ')[0])

    fd = open("%s/%s" % (__templateDir, KML_TEMPLATE))
    data = fd.read()
    fd.close()

    #
    data = data.replace('PRODUCT_NAME', path)
    data = data.replace('PRODUCT_CENTER_LONGITUDE', sceneCenter.split(' ')[1])
    data = data.replace('PRODUCT_CENTER_LATITUDE', sceneCenter.split(' ')[0])
    data = data.replace('PRODUCT_LINEAR_RING', linearRing)
    data = data.replace('SCENE_CENTER_POINT', SCENE_CENTER_POINT)
    data = data.replace('PRODUCT_BROWSE_HREF', browseName)

    #
    # if DEBUG:
    #    print "KML:\n%s" % data

    #
    outPath = '.'
    kmzPath = "%s/%s.KMZ" % (outPath, id)
    zipf = zipfile.ZipFile(kmzPath, 'w')
    zipf.writestr("%s.KML" % id, data, zipfile.ZIP_DEFLATED)
    zipf.writestr(browseName, browseData, zipfile.ZIP_DEFLATED)
    zipf.close()
    print("\n\n KMZ created:%s" % kmzPath)


#
#
#
if __name__ == "__main__":
    main()
