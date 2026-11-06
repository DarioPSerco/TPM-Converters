#
#
# Serco 10/2015
# Lavaux Gilles 
#
#
#
#
import io
import os
import sys
import traceback

from eoSip_converter.esaProducts import formatUtils


class IpfLogger(object):
    def __init__(self, std=None, cb=None, silent=False):
        self.std = std
        self.pid = os.getpid()
        self.nodename = 'nodename'
        self.processorname = 'processorname'
        self.processorversion = 'processorversion'
        # print "IpfLogger init: std=%s; pid=%s" % (self.std, self.pid)
        # file test:
        self.fd = open('ipfLogger_mesg.txt', 'w')

    # will format a default logger message like: basicFormat='%(asctime)s - [%(levelname)s] : %(message)s' 2015-12-03
    # 17:57:57,360 - [INFO] : doing product[1/130][
    # 0/0]:/home/gilles/shared2/Datasets/Pleiade/Pleiades_Ortho_Pansharpened_jpeg2000_12bits.zip into ipf log:
    # 2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 [0000013875]: [I] Processor starting. Config file is
    # /home/IPF1/order0105.xml date nodeName processorName processorVersion pid separator level(DIIPWE) message
    def formatLoggerMsg(self, mesg):
        if mesg is None or len(mesg) == 0:
            return None

        res = ''
        try:
            # file test:
            self.fd.write("message:%s" % mesg)
            # print "formatMsg IN: %s" % mesg
            pos = mesg.find(' - [')
            pos2 = mesg.find('] : ')
            datetime = mesg[0:pos]
            level = mesg[pos + 4:pos2]
            text = mesg[pos2 + 4:].replace('\n', '\\')
            # if text starts with [PROGRESS], set level to PROGRESS
            if text.startswith('[PROGRESS]'):
                text = text[len('[PROGRESS]'):]
                level = 'P'
            elif text.startswith('[PINFO]'):
                text = text[len('[PINFO]'):]
                level = 'I'
            elif text.startswith('[PERROR]'):
                text = text[len('[PERROR]'):]
                level = 'E'

            # print "formatMsg datetime:'%s'; level:'%s'; test:'%s';" % (datetime, level, text)

            newdate = "%s000" % datetime.replace(' ', 'T').replace(',', '.')
            res = "%s %s %s %s [%s]: [%s] %s" % (newdate, self.nodename, self.processorname, self.processorversion,
                                                 formatUtils.leftPadString("%s" % self.pid, 12, '0'), level[0], text)
            # print "formatMsg out: %s" % res
            self.fd.write("\nformatted message:%s\n" % res)
            if res[-1] == '\\':
                res = res[0:-1]
            return res
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            # file test:
            self.fd.write("\n\nError: %s; %s:%s\n" % (exc_type, exc_obj, res))
            self.fd.write("%s\n\n\n\n\n" % traceback.format_exc())
            self.fd.flush()
            text = "%s; %s" % (exc_type, exc_obj)
            return "%s %s %s %s [%s]: [%s] %s" % (
                '2015-12-25T00:00:00.000000', self.nodename, self.processorname, self.processorversion,
                formatUtils.leftPadString("%s" % self.pid, 12, '0'), 'E', text
            )

    #
    # will format a message like
    # into ipf log:
    #     2004-02-24T04:02:07.458000 ipf1ws1 IPF1 01.04 [0000013875]: [I] Processor starting. Config file is /home/IPF1/order0105.xml
    #     date nodeName processorName processorVersion pid separator level(DIIPWE) message
    #
    def formatMsg(self, mesg, level='I'):
        if mesg is None or len(mesg) == 0:
            return None
        res = ''
        try:
            datetime = "%s.000000" % formatUtils.dateNow().replace('Z', '')
            text = mesg.replace('\n', '\\')
            # if text starts with [PROGRESS], set level to PROGRESS
            if text.startswith('[PROGRESS]'):
                text = text[len('[PROGRESS]'):]
                level = 'P'
            elif text.startswith('[PINFO]'):
                text = text[len('[PINFO]'):]
                level = 'I'
            elif text.startswith('[PERROR]'):
                text = text[len('[PERROR]'):]
                level = 'E'

            res = "%s %s %s %s [%s]: [%s] %s" % (datetime, self.nodename, self.processorname, self.processorversion,
                                                 formatUtils.leftPadString("%s" % self.pid, 12, '0'), level[0], text)
            if res[-1] == '\\':
                res = res[0:-1]
            return res
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            text = "%s; %s" % (exc_type, exc_obj)
            return "%s %s %s %s [%s]: [%s] %s" % (
                '2015-12-25T00:00:00.000000', self.nodename, self.processorname, self.processorversion,
                formatUtils.leftPadString("%s" % self.pid, 12, '0'), 'E', text)

    def write(self, msg):
        res = self.formatLoggerMsg(msg)
        if self.std is not None:
            self.std.write("%s\n" % res)


class Capture(io.StringIO):
    callback = None
    silent = False
    matchingString = []
    matchingLines = None
    mesg = None

    def __init__(self, stdout, cb=None, silent=False):
        self.__stdout = stdout
        self.callback = cb
        self.silent = silent
        io.StringIO.__init__(self)
        self.matchingLines = []
        self.mesg = ''

    def write(self, s):
        if not self.silent:
            self.__stdout.write(s)
        io.StringIO.write(self, s)
        #
        self.matchFilter(s)
        #
        if self.callback is not None:
            self.callback.write(self, s)

    def setFilter(self, f):
        try:
            self.matchingString.index(f)
        except:
            self.matchingString.append(f)
            self.mesg = "%sadded filter:%s\n" % (self.mesg, f)

    def matchFilter(self, mess):
        for item in self.matchingString:
            if mess.find(item) >= 0:
                self.matchingLines.append(mess)
                self.__stdout.write(mess)

    def getMatchingLines(self):
        res = ''
        for item in self.matchingLines:
            res = "%s%s\n" % (res, item)
        return res

    def read(self):
        self.seek(0)
        self.__stdout.write(io.StringIO.read(self))

    def getMesg(self):
        return self.mesg


#
#
#
if __name__ == '__main__':
    logger = IpfLogger(None)
    logger.formatMsg(
        '2015-12-03 17:57:57,360 - [INFO] : doing product[1/130][0/0]:/home/gilles/shared2/Datasets/Pleiade/Pleiades_Ortho_Pansharpened_jpeg2000_12bits.zip')
