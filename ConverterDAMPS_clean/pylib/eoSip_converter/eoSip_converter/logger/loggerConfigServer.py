import logging
import logging.config
import time

SETTING_PORT = 'SETTING_PORT'
debug = 1


class LogServer(object):
    """The infoKeeper proxy class"""
    debug = debug
    configFile = 'logging.conf'
    defaultLogger = 'simpleExample'
    port = None

    def __init__(self, p):
        self.debug = debug
        self.port = p
        print(" logServer starting on port:%s" % self.port)

    def start(self):
        # read initial config file
        print(" use config file:%s" % self.configFile)
        logging.config.fileConfig(self.configFile)

        print(" will listen on port:%s" % self.port)
        # create and start listener on port xxxx
        t = logging.config.listen(self.port)
        t.start()

        print(" will use logger:%s" % self.defaultLogger)
        logger = logging.getLogger(self.defaultLogger)

        try:
            # loop through logging calls to see the difference
            # new configurations make, until Ctrl+C is pressed
            while True:
                logger.debug('DEBUG message')
                logger.info('info message')
                logger.warn('warn message')
                logger.error('error message')
                logger.critical('critical message')
                time.sleep(5)
        except KeyboardInterrupt:
            # cleanup
            logging.config.stopListening()
            t.join()
