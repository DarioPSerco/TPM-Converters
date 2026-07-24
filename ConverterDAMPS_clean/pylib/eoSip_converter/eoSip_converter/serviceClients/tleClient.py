# -*- coding: cp1252 -*-
#
# this class implement access to a tle service
#
#
from .client import Client

#
SERVICE_TLE = "tle"


#

# properties that are known in service configuration file
# SETTING_NAME="NAME"

class TleServiceClient(Client):
    service = None
    logName = None

    #
    # class init
    #
    def __init__(self, processInfo):
        Client.__init__(self)
        self.clientName = SERVICE_TLE
        if self.debug != 0:
            print(" init class RemoteLoggerServiceClient")
        self.service = processInfo.ingester.getService(SERVICE_TLE)
        if self.debug != 0:
            print(" @@@@@@@@@@@@@@@@ TleServiceClient: got service: %s" % self.service)

    #
    #
    def processRequest(self, kvarg):
        if self.debug != 0:
            print(" @@@@@@@@@@@@@@@@ TleServiceClient processRequest; message=%s" % kvarg)
        return self.service.processRequest(kvarg)
