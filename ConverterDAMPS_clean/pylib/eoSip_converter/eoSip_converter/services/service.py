# -*- coding: cp1252 -*-
#
# this class is a base class for Service
#
#
import configparser
import logging
import os
from abc import abstractmethod
from io import StringIO

debug = 0


class Service(object):
    #
    SETTING_DEBUG = 'DEBUG'
    #
    name = None
    propertieFile = None
    properties = None
    ingester = None
    ready = True

    #
    # init simple
    # param: p is a string
    #
    def __init__(self, name=None):
        self.name = name
        self.debug = debug
        self.ingester = None
        if self.debug != 0:
            print(" create class Service; name=%s" % self.name)

            #

    def useDebugConfig(self, s):
        # print " service %s use DEBUG setting (should be True/False):'%s'; type:%s" % (self.name, s, type(s))
        if s.lower() == "true":
            self.debug = 1
        elif s.lower() == "false":
            self.debug = 0
        else:
            raise Exception("invalid DEBUG setting (should be True/False):'%s'" % s)

    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        print(" Service %s setDebug:%s" % (self.name, d))
        self.debug = d

    #
    def getDebug(self):
        return self.debug

    #
    def setIngester(self, i):
        if self.debug != 0:
            print(" Service setIngester:%s" % i)
        self.ingester = i

    #
    # init with ingester + property file
    #
    # param: p is usually the path of a property file, can be local to ingester './xxx.props' or absolute '/...path.../xxx.props'. Can be None
    #        ingester is the ingester instance, is used to get the property file path
    #
    # TODO: leave the ingester load the ressources 
    #
    def init(self, p=None, ingester=None):
        self.ingester = ingester
        if p is not None:
            if self.debug != 0:
                print(" # init class Service with parameter:%s" % p)
            if p[0:2] == "./":
                p = "%s/%s" % (self.ingester.getConverterHomeDir(), p[2:])
            if self.debug != 0:
                print(" using service property file at path:'%s'" % p)
            if not os.path.exists(p):
                raise Exception("property path does not exists:%s" % p)
            self.propertieFile = p
            self.loadProperties()
        else:
            if self.debug != 0:
                print(" # init class Service with no property file given !!")

    #
    # load the properties setting file
    #
    def loadProperties(self):
        if self.debug != 0:
            print(" load properties in Service '%s' from file:%s" % (self.name, self.propertieFile))
        __config = configparser.RawConfigParser()
        __config.optionxform = str
        __config.read(self.propertieFile)
        self.properties = dict(__config.items("GLOBAL"))

    #
    #
    def getProperties(self):
        return self.properties

    #
    # test 2019/01/28
    def setProperties(self, aDict):
        self.properties = aDict

    #
    # return a property value
    #
    def getProperty(self, propName=None):
        try:
            return self.properties[propName]
        except:
            return None

    #
    #
    #
    def dumpProperty(self):
        out = StringIO()
        print('service properties dump:', file=out)
        for key in list(self.properties.keys()):
            print(" key:'%s'; value:'%s'" % (key, self.properties[key]), file=out)
        return out.getvalue()

    #
    # process a request
    #
    @abstractmethod
    def processRequest(self):
        pass


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        s = Service("a=1")
        s.processRequest()
    except Exception as err:
        log.exception('Error from throws():')
