debug = True

#
# classe that send notification to system logger
#
#

import logging
import logging.handlers

from .service import Service


#
#
#
class RemoteLoggerService(Service):
    # properties that are known in service configuration file
    SETTING_HOST = "HOST"
    SETTING_PORT = "PORT"
    SETTING_NAME = "NAME"

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
    # - attach socket handler into logger
    #
    def my_init(self):
        self.host = None
        self.post = None
        self.logName = None
        self.rootLogger = None
        self.glLogger = None

        # DEBUG setting
        d = self.getProperty(self.SETTING_DEBUG)
        if d is not None:
            self.useDebugConfig(d)

        # host 
        if self.getProperty(self.SETTING_HOST) is not None:
            if self.debug != 0:
                print(" HOST setting:%s" % self.getProperty(self.SETTING_HOST))
            self.host = int(self.getProperty(self.SETTING_HOST))

        # port 
        if self.getProperty(self.SETTING_PORT) is not None:
            if self.debug != 0:
                print(" PORT setting:%s" % self.getProperty(self.SETTING_PORT))
            self.port = int(self.getProperty(self.SETTING_PORT))

        # name 
        if self.getProperty(self.SETTING_NAME) is not None:
            if self.debug != 0:
                print(" logName setting:%s" % self.getProperty(self.SETTING_NAME))
            self.logName = int(self.getProperty(self.SETTING_NAME))

        self.rootLogger = logging.getLogger('')
        # self.rootLogger.setLevel(logging.DEBUG)
        self.rootLogger.setLevel(logging.NOTSET)
        if self.debug != 0:
            print("  got rootLogger:%s" % self.rootLogger)
        # self.socketHandler = logging.handlers.SocketHandler(self.host, self.port)
        self.socketHandler = logging.handlers.SocketHandler('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        if self.debug != 0:
            print("  got socketHandler")
        # don't bother with a formatter, since a socket handler sends the event as
        # an unformatted pickle
        self.rootLogger.addHandler(self.socketHandler)
        if self.debug != 0:
            print("  ready, this logger name is:%s" % self.logName)
        # self.glLogger = logging.getLogger(self.logName)
        self.glLogger = self.rootLogger.getChild("%s" % self.logName)
        if self.debug != 0:
            print("  got glLogger:%s" % self.glLogger)

    #
    # send log messages
    #
    def processRequest(self, level, message):
        print(" RemoteLoggerService processRequest: level=%s; message=%s" % (level, message))
        if self.debug != 0:
            print(" RemoteLoggerService processRequest")
        res = None
        if level.upper() == "DEBUG":
            self.glLogger.debug(message)
            res = 'ok'
        elif level.upper() == "INFO":
            self.glLogger.info(message)
            res = 'ok'
        elif level.upper() == "WARNING":
            self.glLogger.warning(message)
            res = 'ok'
        elif level.upper() == "ERROR":
            self.glLogger.error(message)
            res = 'ok'
        elif level.upper() == "CRITICAL":
            self.glLogger.critical(message)
            res = 'ok'
        elif level.upper() == "LOG":
            self.glLogger.info("[PROGRESS]: %s" % message)
            res = 'ok'
        else:
            print("  ERROR processRequest: unknown level:'%s'; mess='%s'" % (level, message))
            res = 'ok'
        return res
