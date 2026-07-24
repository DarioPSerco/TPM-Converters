"""This class implements access to a remote TCP python logger
"""

SERVICE_RLOGGER = "remoteLogger"

# properties that are known in service configuration file
SETTING_HOST = "HOST"
SETTING_PORT = "PORT"
SETTING_NAME = "NAME"


class RemoteLoggerServiceClient:
    debug = 0
    service = None
    host = None
    port = None
    logName = None

    # class init
    def __init__(self, processInfo):
        # Client.__init__(self)
        self.clientName = SERVICE_RLOGGER
        if self.debug != 0:
            print(" init class RemoteLoggerServiceClient")
        self.service = processInfo.ingester.getService(SERVICE_RLOGGER)
        if self.debug != 0:
            print(" RemoteLoggerServiceClient: got service: %s" % self.service)

    def processRequest(self, level, message):
        if self.debug != 0:
            print(" client processRequest; level=%s; message=%s" % (level, message))
        self.service.processRequest(level, message)
