# -*- coding: cp1252 -*-
#
# this class implement access to an http service that send back browse images
#
#
import sys
import traceback
import urllib.request, urllib.parse, urllib.error

from .client import Client
from eoSip_converter.services.httpService import HttpCall

#
SERVICE_TOWNRESOLVER = "townResolver"
# 

# properties that are known in service configuration file
SETTING_URL_PATTERN = "URL_PATTERN"


class TownResolverStdaClient(Client):
    service = None
    urlPattern = None
    layer = None
    lastCalledUrl = None

    #
    # class init
    #
    def __init__(self, propPath):
        Client.__init__(self)
        self.debug = 1
        self.clientName = SERVICE_TOWNRESOLVER
        if self.debug != 0:
            print(" init class TownResolverClient")

        #
        self.service = HttpCall()
        self.service.init(propPath, None)

        if self.debug != 0:
            print(" @@ TownResolverClient: got service: %s" % self.service)
        self.urlPattern = self.service.getProperty(SETTING_URL_PATTERN)
        if self.debug != 0:
            print(" @@ TownResolverClient: got urlPattern:%s" % self.urlPattern)

    #
    # query server
    # param will be the 5 points footprint:
    #
    # returns: country ISO and town name
    #
    def callWfsService(self, params):
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
        data = self.service.processRequest(self.lastCalledUrl, params, False, False)  # dont use post, dont decode
        if self.debug != 0:
            print(" getTownInfo; data=%s; type:%s" % (data, type(data)))
        if data is None:
            raise Exception("Error resolving country info")

        lines = data.split('\n')
        # get town name
        res, n = self.findDataLine(lines, "# wfsInfo[0]")
        tokens = lines[n + 1].split(":")
        townName = tokens[1]
        # get country ISO
        res, n = self.findDataLine(lines, "WmsInfo-country_code:")
        tokens = lines[n].split(":")
        countryIso = tokens[1]
        print(" getTownInfo; country ISO=%s; townName=%s" % (countryIso, townName))
        return countryIso, townName


if __name__ == '__main__':
    try:
        propPath = None
        if len(sys.argv) > 1:
            propPath = sys.argv[1]
        else:
            print("Syntax: python townResolverStdaClient.py property_file_path")

        client = TownResolverStdaClient(propPath)


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
