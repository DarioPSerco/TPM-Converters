#!/usr/bin/env python
"""Lavaux Gilles 2014

This class is used to store resources info
"""
import sys
import traceback

debug = 0


class RessourceProvider(object):
    def __init__(self):
        self.resseourcesPath = {}
        self.debug = debug
        if self.debug != 0:
            print(" init RessourceProvider")

    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        self.debug = d

    def getDebug(self):
        return self.debug

    # add ressource entry like: icon=C:/Users/glavaux/Shared/LITE/testData/Aeolus/logo.png
    def addRessourcePath(self, n, v):
        if self.debug != 0:
            print("add ressource path for '%s':'%s'" % (n, v))
        self.resseourcesPath[n] = v

    # get ressource entry
    def getRessourcePath(self, n):
        if self.debug != 0:
            print("get ressource path for '%s'" % n)
        if n not in self.resseourcesPath:
            raise Exception("ressource not found:" + n)
        return self.resseourcesPath[n]

    # return info
    def toString(self):
        from io import StringIO

        out = StringIO()
        print(("Resources:\n"), file=out)
        n = 0
        for key in list(self.resseourcesPath.keys()):
            print(("  %s=%s" % (key, self.resseourcesPath[n])), file=out)
        return out.getvalue()


if __name__ == '__main__':
    try:
        provider = RessourceProvider()
        provider.addRessourcePath('icon', ':/Users/glavaux/Shared/LITE/testData/Aeolus/logo.png')

    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
