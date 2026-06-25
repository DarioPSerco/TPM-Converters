# -*- coding: cp1252 -*-
#
# this class implement access to an http service that send back browse images
#
#
import sys
import traceback
import urllib.request, urllib.error, urllib.parse

from .client import Client

#
SERVICE_M2BS = "m2bs"
# 

# properties that are known in service configuration file
SETTING_URL_PATTERN = "URL_PATTERN"
SETTING_TYPECODES_LUT = "TYPECODES_LUT"
SETTING_PLATFORMS_LUT = "PLATFORMS_LUT"


class M2bsClient(Client):
    debug = 0
    service = None
    urlPattern = None
    layer = None
    lastCalledUrl = None

    #
    # class init
    #
    def __init__(self, processInfo):
        Client.__init__(self)
        self.clientName = SERVICE_M2BS
        if self.debug != 0:
            print(" init class M2bsClient")

        #
        self.service = processInfo.ingester.getService(SERVICE_M2BS)

        if self.debug != 0:
            print("@@@@@@@@@@@@@@@@ M2bsClient: got service m2bs:%s" % self.service)
        self.urlPattern = self.service.getProperty(SETTING_URL_PATTERN)
        if self.debug != 0:
            print("@@@@@@@@@@@@@@@@ M2bsClient: got urlPattern:%s" % self.urlPattern)
        typeCodesLut = self.service.getProperty(SETTING_TYPECODES_LUT)
        if self.debug != 0:
            print("@@@@@@@@@@@@@@@@ M2bsClient: typeCodesLut:%s" % typeCodesLut)
        platformsLut = self.service.getProperty(SETTING_PLATFORMS_LUT)
        if self.debug != 0:
            print("@@@@@@@@@@@@@@@@ M2bsClient: platformsLut:%s" % platformsLut)
        self.lutDict = {}
        # pairs like: ASA_IM__0P|ASARz0IM;
        n = 0
        for pair in typeCodesLut.split(';'):
            pos = pair.index('|')
            if pos > 0:
                name = pair[0:pos]
                value = pair[pos + 1:]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@ M2bsClient: typecode pair[%s]: %s=%s" % (n, name, value))
                self.lutDict[name] = value
            n = n + 1
        self.platformsLut = {}
        # pairs like: Envisat|ENVISAT_1;
        n = 0
        for pair in platformsLut.split(';'):
            pos = pair.index('|')
            if pos > 0:
                name = pair[0:pos]
                value = pair[pos + 1:]
                if self.debug != 0:
                    print("@@@@@@@@@@@@@@@@ M2bsClient: platform pair[%s]: %s=%s" % (n, name, value))
                self.platformsLut[name] = value
            n = n + 1

    #
    # query server
    # param will be frame properties:
    # - platform
    # - platformId
    # - collection typecode
    # - start datetime
    # - stop datetime
    # - ascending
    #
    def callWfsService(self, processInfo, params):
        # url to be completed will be like: http://eoliserv.eo.esa.int/browse/ASARz0IM/ASA_IM__0P/ENVISAT_1/20100901T021901050-20100901T021948090_D_B-XI0B.jpg
        # urlPattern is: http://eoliserv.eo.esa.int/browse/

        if len(params) != 6:
            raise Exception(
                "params has to be list with 5 values: platform, typecode, startdataTime, stopdateTime, ascending")

        platform = params[0]
        platformId = params[1]
        typecode = params[2]
        start = params[3]
        stop = params[4]
        ascending = params[5][0]

        if typecode not in self.lutDict:
            raise Exception("unknown type code:'%s'" % typecode)

        platform = "%s%s" % (platform, platformId)
        if platform not in self.platformsLut:
            raise Exception("unknown platform:'%s'" % platform)

        path0 = self.lutDict[typecode]
        plat = self.platformsLut[platform]
        startOK = start.replace(':', '').replace('-', '').replace('.', '')
        stopOK = stop.replace(':', '').replace('-', '').replace('.', '')

        dash = '%2c'
        self.lastCalledUrl = "%s%s/%s/%s/%s-%s_%s_B-XI0B.jpg" % (
        self.urlPattern, path0, typecode, plat, startOK, stopOK, ascending)
        params = None
        if self.debug != 0:
            print("############## service params: Url=%s; params=%s" % (self.lastCalledUrl, params))
        #
        # self.service.setDebug(self.DEBUG)
        imageData = None
        try:
            imageData = self.service.processRequest(self.lastCalledUrl, params, False,
                                                    False)  # dont use post, dont decode
            if self.debug != 0:
                print("############## service result: length=%s" % len(imageData))

        except urllib.error.HTTPError as e:
            print("HTTPError: %s" % e)

        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "Error:%s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc())

        return imageData
