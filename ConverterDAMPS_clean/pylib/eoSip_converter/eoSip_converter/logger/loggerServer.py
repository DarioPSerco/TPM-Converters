#
# this is a logging receiver that can filter the log messages by keyword (in message) and level
# Lavaux Gilles 2016/03
#
#


import socketserver
import logging
import logging.handlers
import pickle
import struct
import sys
import traceback
from optparse import OptionParser

minLevel = logging.NOTSET
levelMinNo = 0
sfilter = None

#
debug = 0


#
# convert logging level string to int
#
def logLevelStringToNo(sLevel):
    levelMinNo = -1
    if sLevel == 'NOTSET':
        levelMinNo = 0
    elif sLevel == 'DEBUG':
        levelMinNo = 10
    elif sLevel == 'INFO':
        levelMinNo = 20
    elif sLevel == 'WARNING':
        levelMinNo = 30
    elif sLevel == 'ERROR':
        levelMinNo = 40
    elif sLevel == 'CRITICAL':
        levelMinNo = 50
    else:
        raise Exception("Unknown loggin level:%s" % sLevel)
    return levelMinNo


#
# convert logging level string to int
#
def logLevelNoToString(no):
    slevel = None
    if no == 0:
        slevel = 'NOTSET'
    elif no == 10:
        slevel = 'DEBUG'
    elif no == 20:
        slevel = 'INFO'
    elif no == 30:
        slevel = 'WARNING'
    elif no == 40:
        slevel = 'ERROR'
    elif no == 50:
        slevel = 'CRITICAL'
    else:
        raise Exception("Unknown loggin no:%s" % no)
    return slevel


#
#
#
class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    # global minLevel, levelMinNo
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    # levelMin=logging.DEBUG
    # levelMinNo=10

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        global minLevel, levelMinNo, sfilter, debug
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        # print "%s" % dir(record)
        # print "%s %s; levelMinNo:%s" % (record.levelname, record.levelno, levelMinNo)
        if record.levelno >= levelMinNo:
            if sfilter == None:
                logger.handle(record)
            elif record.getMessage().find(sfilter) >= 0:
                logger.handle(record)
            else:
                if debug != 0:
                    print("\t[record discarted for filter '%s']" % sfilter)
        else:
            if debug != 0:
                print("\t[record discarted for level %s vs %s]" % (record.levelno, levelMinNo))

    def setLevelMin_not_used(self, m):
        global minLevel, levelMinNo
        if m == logging.NOTSET:
            levelMinNo == 0
        elif m == logging.DEBUG:
            levelMinNo == 10
        elif m == logging.INFO:
            levelMinNo == 20
        elif m == logging.WARNING:
            levelMinNo = 30
        elif m == logging.ERROR:
            levelMinNo == 40
        elif m == logging.CRITICAL:
            levelMinNo == 50
        else:
            raise Exception("Unknown loggin level:%s" % m)
        levelMin = m
        print(" set level minimum to:%s" % levelMin)

    def setFilter_not_used(self, f):
        global sfilter
        sfilter = f


#
#
#
class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """
    # global minLevel, levelMinNo

    allow_reuse_address = 1

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        self.handler = handler
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None
        # print "DIR:%s" % dir(self)
        # print "request handler:%s" % self.handler

    def serve_until_stopped(self):
        import select
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [],
                                       self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort

    def setLevelMin(self, m):
        global minLevel, levelMinNo
        if m == logging.NOTSET:
            levelMinNo = 0
        elif m == logging.DEBUG:
            levelMinNo = 10
        elif m == logging.INFO:
            levelMinNo = 20
        elif m == logging.WARNING:
            levelMinNo = 30
        elif m == logging.ERROR:
            levelMinNo = 40
        elif m == logging.CRITICAL:
            levelMinNo = 50
        else:
            raise Exception("Unknown loggin level:%s" % m)
        levelMin = m
        print(" set level minimum to:%s; %s" % (levelMin, levelMinNo))

    def setFilter(self, f):
        global sfilter
        sfilter = f


#
#
#
def main():
    try:
        parser = OptionParser()
        parser.add_option("-f", "--filter", dest="filter", help="keyword to be used as log message filter")
        parser.add_option("-l", "--level", dest="level", help="minimum log level to be displayed")

        options, args = parser.parse_args(sys.argv)
        minLevel = -1
        sfilter = None
        if options.level is not None:
            minLevel = logLevelStringToNo(options.level)

        if options.filter is not None:
            sfilter = options.filter

        logging.basicConfig(format='%(relativeCreated)5d %(name)-15s %(levelname)-8s %(message)s')
        tcpserver = LogRecordSocketReceiver()
        if minLevel != -1:
            print((' will only display logging message for level >= %s' % minLevel))
            tcpserver.setLevelMin(minLevel)
        if sfilter != None:
            print((" will filter logging message with keyword '%s'" % sfilter))
            tcpserver.setFilter(sfilter)

        print(' about to start TCP server...')
        tcpserver.serve_until_stopped()
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Error: %s  %s\n%s" % (exc_type, exc_obj, traceback.format_exc()))


if __name__ == '__main__':
    main()
