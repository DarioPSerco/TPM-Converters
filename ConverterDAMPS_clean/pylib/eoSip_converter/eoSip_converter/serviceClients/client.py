"""this class is a base class for Client
"""

debug = 0


class Client:
    """base class for Client"""

    def __init__(self):
        self.debug = debug
        if self.debug != 0:
            print(" init class Client")

    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        print(" Client %s setDebug:%s" % (self.clientName, d))
        self.debug = d

    def getDebug(self):
        return self.debug

    def findDataLine(self, lines, pattern):
        res = None
        n = 0
        for line in lines:
            if line.find(pattern) >= 0:
                if self.debug != 0:
                    print("  !!!!!!!!!!!!!!! findDataLine: pattern '%s' found in line:%s" % (pattern, line))
                res = line
                break
            n += 1
        return res, n
