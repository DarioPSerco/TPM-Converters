import sys

debug = True

#
# classe that can perform http GET and POST calls 
#
#
#

from .service import Service


class NoopService(Service):

    #
    # class init
    # call super class
    #
    def __init__(self, name=None):
        Service.__init__(self, name)

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
        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            self.useDebugConfig(d)

    #
    #
    def processRequest(self, **kvarg):
        if self.debug != 0:
            print(" processRequest")


if __name__ == '__main__':
    propertiePath = None
    if len(sys.argv) > 1:
        propertiePath = sys.argv[1]
        print(" will use property file at path:%s:" % propertiePath)

    noopp = NoopService(name='test noop')
    noopp.setDebug(True)
    noopp.init(propertiePath)
