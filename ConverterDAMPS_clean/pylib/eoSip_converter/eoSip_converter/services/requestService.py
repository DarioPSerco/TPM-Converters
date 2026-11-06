"""Provide access to http/https using Request

Lavaux Gilles 2018/05
"""
import sys
import time

import requests

from .service import Service

#
debug = 1


# requests service
# Provide:
class RequestService(Service):
    SETTING_URL = 'URL'
    SETTING_TIMEOUT = 'TIMEOUT'
    SETTING_PROXY = 'PROXY'
    DEFAULT_TIMEOUT = 15

    #
    # class init
    # call super class
    #
    def __init__(self, name=None):
        super(RequestService, self).__init__(name)
        self.url = None

    #
    # init
    # call super class
    #
    # param: p is usually the path of a property file
    #
    def init(self, p=None, ingester=None):
        Service.init(self, p, ingester)
        self.my_init()

    #
    # init done after the properties are loaded
    # do:
    # - check if DEBUG option set
    #
    def my_init(self):
        self.timeout = self.DEFAULT_TIMEOUT
        self.request = None
        self.proxy = None

        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        print(" RequestService DEBUG used:%s" % d)
        if d is not None:
            self.useDebugConfig(d)

            # URL setting
            self.url = self.getProperty(self.SETTING_URL)
        print(" RequestService DEBUG used:%s" % self.url)
        if self.url is None:
            raise Exception("RequestService need a %s setting" % self.SETTING_URL)

        # TIMEOUT setting
        if self.getProperty(self.SETTING_TIMEOUT) is not None:
            print(" RequestService timeout used:%s" % self.getProperty(self.SETTING_TIMEOUT))
            if self.debug != 0:
                print(" TIMEOUT setting:%s" % self.getProperty(self.SETTING_TIMEOUT))
            self.timeout = int(self.getProperty(self.SETTING_TIMEOUT))
        else:
            print(" RequestService no timeout used")

        # PROXY setting
        if self.getProperty(self.SETTING_PROXY) != None:
            print(" proxy to be implemented")

    #
    # post data
    #
    def postdata(self, data=None):
        res = None
        if self.debug != 0:
            print("  postdata; data=%s" % data)
        try:
            res = requests.post(self.url, data)

        except requests.exceptions.HTTPError as e:
            print(('  postdata http error: ' + str(e)))

        except requests.exceptions.RequestException as e:
            print(('  postdata connection error: ' + str(e)))

        return res

    def processRequest(self):
        pass


def buildGraphiteEventMessage(what='default', tags=None, data='test data'):
    if tags is None:
        tags = []

    aDict = {}
    aDict['what'] = what
    aDict['tags'] = tags
    aDict['when'] = time.time()
    aDict['data'] = data
    return aDict


if __name__ == '__main__':
    propertiePath = None
    if len(sys.argv) > 1:
        propertiePath = sys.argv[1]
        print(" will use property file at path:%s:" % propertiePath)

        aService = RequestService(name='graphite events')
        aService.init(propertiePath)

        # aDict = aService.buildGraphiteEventMessage(what, tags, data)
        payload = buildGraphiteEventMessage('New input', ['liveConversion'], 'a new file: pipo')
        print(" will send graphite event; payload=%s" % payload)
        res = aService.sendJasonPayload(payload)
        print(" res=%s; type:%s; dir:%s" % (res, type(res), dir(res)))
        print(res.status_code)

        # print res.content

    else:
        print(" need property file as argument")

    # os._exit(1)
