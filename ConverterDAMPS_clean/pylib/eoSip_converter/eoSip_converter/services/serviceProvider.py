"""This class is a service provider

Lavaux Gilles 2014
"""
import sys
import traceback

# the defaults service
SERVICE_REMOTE_LOGGER = 'remoteLogger'
SERVICE_XML_VALIDATE = 'xmlValidate'
SERVICE_GRAPHITE_EVENTS = 'graphiteEvents'

debug = 1


class ServiceProvider:
    initString = None
    services = None

    #
    # initString is like: xmlValidate=class@module@properties|parameterString
    # - xmlValidate: name of the service
    # - class@module@properties needed to instanciate the service class
    # - parameterString
    #
    def __init__(self, init):
        self.debug = debug
        self.initString = init
        self.services = {}

        if self.debug != 0:
            print(" init ServiceProvider with init string:'%s'" % init)

    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    #
    def getDebug(self):
        return self.debug

    #
    # add a service
    #
    def addService(self, name, settings, ingester):
        if self.debug != 0:
            print(" add Service with settings string:'%s'" % settings)

        toks = settings.split("|")
        if len(toks[0].split("@")) != 3:
            raise Exception("token 1 of service source has not 3 '@' separated fields:'%s'" % toks[1])

        aClass, aPackage, setting = toks[0].split("@")
        if self.debug != 0:
            print("  will instantiate class:'%s' in package:'%s' with init:'%s'" % (aClass, aPackage, setting))

        parameters = toks[1]
        if self.debug != 0:
            print("  parameters:'%s'" % parameters)

        # load the module:
        full_module_path = '.'.join(__name__.split('.')[:-1] + [aPackage])

        # create it:
        module = __import__(full_module_path, fromlist=[aPackage])
        if self.debug != 0:
            print("  module loaded:%s" % module)
        class_ = getattr(module, aClass)
        aclass = class_(name)
        if self.debug != 0:
            print("  got class:%s" % aclass)
        aclass.init(parameters, ingester)
        self.services[name] = aclass
        if self.debug != 0:
            print("  service ready:")
            print(aclass.dumpProperty())

    #
    # list the known service
    #
    def listServices(self):
        return list(self.services.keys())

    #
    # get a service
    #
    def getService(self, name):
        if name not in self.services:
            raise Exception("unknown service name:%s" % name)
        return self.services[name]

    #
    # has a service?
    #
    def hasService(self, name):
        return name in self.services


if __name__ == '__main__':
    try:
        serviceprovider = ServiceProvider("")
        serviceprovider.addService(
            "httpCall",
            "HttpCall@httpService@None|http://127.0.0.1:7000/validate?XML_PATH=@XML_PATH@&XSD_PATH=@XSD_PATH@")

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
