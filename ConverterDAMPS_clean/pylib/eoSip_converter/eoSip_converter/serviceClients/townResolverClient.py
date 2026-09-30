# -*- coding: cp1252 -*-
#
# this class implement access to an http service that send back browse images
#
#
import sys
import traceback
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse

from .client import Client

#
SERVICE_TOWNRESOLVER = "townResolver"
# 

# properties that are known in service configuration file
SETTING_URL_PATTERN = "URL_PATTERN"


class TownResolverClient(Client):
    service = None
    urlPattern = None
    layer = None
    lastCalledUrl = None

    #
    # class init
    #
    def __init__(self, processInfo):
        Client.__init__(self)
        # self.DEBUG=1
        self.clientName = SERVICE_TOWNRESOLVER
        if self.debug != 0:
            print(" init class TownResolverClient")

        #
        self.service = processInfo.ingester.getService(SERVICE_TOWNRESOLVER)

        if self.debug != 0:
            print(" @@ CountryResolverClient: got service: %s" % self.service)
        self.urlPattern = self.service.getProperty(SETTING_URL_PATTERN)
        if self.debug != 0:
            print(" @@ TownResolverClient: got urlPattern:%s" % self.urlPattern)

    #
    # query server
    # param will be the 5 points footprint:
    #
    def callWfsService(self, processInfo, params):
        # url to be completed will be like: http://localhost:7001/

        if len(params) != 1:
            raise Exception("params has to be list with 1 values: footprint")

        footprint = urllib.parse.quote(params[0])

        dash = '%2c'
        self.lastCalledUrl = "%s?FOOTPRINT=%s" % (self.urlPattern, footprint)
        params = None
        if self.debug != 0:
            print(" ## service params: Url=%s; params=%s" % (self.lastCalledUrl, params))
        #
        # self.service.setDebug(self.DEBUG)
        self.service.setDebug(True)
        data = None
        try:
            data = self.service.processRequest(self.lastCalledUrl, params, False, False)  # dont use post, dont decode
            if self.debug != 0:
                print(" ## service result: length=%s" % len(data))

        except urllib.error.HTTPError as e:
            print("HTTPError: %s" % e)

        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "Error:%s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc())

        return data
