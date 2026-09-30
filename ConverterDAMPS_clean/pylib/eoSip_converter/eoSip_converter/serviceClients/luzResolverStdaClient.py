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
SERVICE_LUZRESOLVER = "luzResolver"
# 

# properties that are known in service configuration file
SETTING_URL_PATTERN = "URL_PATTERN"


class LuzResolverStdaClient(Client):
    service = None
    urlPattern = None
    layer = None
    lastCalledUrl = None

    #
    # class init
    #
    def __init__(self, propPath):
        Client.__init__(self)
        # self.debug=1
        self.clientName = SERVICE_LUZRESOLVER
        if self.debug != 0:
            print(" init class LuzResolverStdaClient")

        #
        self.service = HttpCall()
        self.service.init(propPath, None)

        if self.debug != 0:
            print(" @@ LuzResolverStdaClient: got service: %s" % self.service)
        self.urlPattern = self.service.getProperty(SETTING_URL_PATTERN)
        if self.debug != 0:
            print(" @@ LuzResolverStdaClient: got urlPattern:%s" % self.urlPattern)

    #
    # query server
    # param will be the 5 points footprint:
    #
    #
    # request is like:
    #  http://localhost:7001/luzResolver?FOOTPRINT=52.23165364%208.76142652%2052.05466425%208.76142652%2052.05466425%209.01463051%2052.23165364%209.01463051%2052.23165364%208.76142652
    # reply is like:
    # """wfsInfo[0]
    # DE017L|Bielefeld|Bielefeld|DE|Germany
    # Done in 217 mSec"""
    #
    # reply is 3 strings: luzId, town, country. Like 017, Bielefeld, Germany
    #
    def callWfsService(self, params):
        # url to be completed will be like: http://localhost:7005/

        if len(params) != 1:
            raise Exception("params has to be list with 1 values: footprint")

        footprint = urllib.parse.quote(params[0])

        dash = '%2c'
        self.lastCalledUrl = "%s?FOOTPRINT=%s" % (self.urlPattern, footprint)
        params = None
        if self.debug != 0:
            print(" ## service params: Url=%s; params=%s" % (self.lastCalledUrl, params))
        #
        self.service.setDebug(self.debug)
        # self.service.setDebug(True)
        data = None
        data = self.service.processRequest(self.lastCalledUrl, params, False, False)  # dont use post, dont decode
        if self.debug != 0:
            print("get LUZ; data=%s" % data)
        if data is None:
            raise Exception("Error resolving LUZ")

        lines = data.split('\n')
        if len(lines) > 1:
            if lines[0].find('wfsInfo[0]') >= 0:
                toks = lines[1].split('|')
                print("LUZ resolved: luzId:%s; town:%s; country:%s" % (toks[0][2:-1], toks[1], toks[4]))
                return toks[0][2:-1], toks[1], toks[4]
            else:
                raise Exception("LUZ not resolved:%s" % data)


if __name__ == '__main__':
    try:
        propPath = None
        if len(sys.argv) > 1:
            propPath = sys.argv[1]
        else:
            print("Syntax: python luzResolverStdaClient.py property_file_path")

        client = LuzResolverStdaClient(propPath)


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
