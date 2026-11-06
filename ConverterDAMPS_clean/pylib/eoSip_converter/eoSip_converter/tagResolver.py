# -*- coding: cp1252 -*-
#
# 
#
#

import sys
import traceback

from .esaProducts import metadata


class TagResolver:
    debug = 0

    #
    # 
    #
    def __init__(self):
        pass

    #
    # resolve '@xxx@' and '$$self.getNextCounter()$$' tags
    #
    def resolve(self, segment, met=None, bmet=None):
        pos = segment.find('@')
        if pos < 0:
            tmp = self.resolveEval(segment)
            return tmp
        else:
            tmp = self.resolveVarname(segment, met, bmet)
            tmp2 = self.resolveEval(tmp)
            return tmp2

    #
    # resolve '@xxx@' and '$$self.getNextCounter()$$' tags
    #
    def resolve___(self, segment, met=None, bmet=None):
        pos = segment.find('@')
        if pos < 0:
            tmp = self.resolveMetEval(segment, met)
            tmp1 = self.resolveEval(tmp)
            return tmp1
        else:
            tmp = self.resolveVarname(segment, met)
            tmp1 = self.resolveMetEval(tmp, met)
            tmp2 = self.resolveEval(tmp1)
            return tmp2

    #
    #
    #
    def eval(self, expr):
        if self.debug != 0:
            print("%%%%%%%%%%%%%%%%%%%%%% wil eval:'%s'" % expr)
        try:
            if not expr[0:5] == 'self.':
                expr = "self.%s" % expr
            if self.debug != 0:
                print("@@@@@@@@@@@@@@@@  WIL EVAL:'%s'" % expr)
            res = eval(expr)
        except:
            xc_type, exc_obj, exc_tb = sys.exc_info()
            res = "%s%s%s" % (xc_type, exc_obj, exc_tb)
            traceback.print_exc(file=sys.stdout)
        return res

    #
    # evaluate things like: $$self.getNextCounter()$$
    # in this context
    #
    def resolveEval(self, segment):
        sep = '$$self.'
        sepLength = len(sep)
        pos = segment.find(sep)
        if pos >= 0:
            pos2 = pos
            n = 0
            result = ''
            while pos >= 0 and pos2 >= 0:
                if self.debug != 0:
                    print("### tagResolver.resolveEval: actual eval segment[%d]:'%s'" % (n, segment))
                pos2 = segment.find('$$', pos + sepLength)
                funcName = segment[pos + 2:pos2]
                if self.debug != 0:
                    print("### tagResolver.resolveEval: eval[%d]:'%s'" % (n, funcName))
                value = eval(funcName)
                if self.debug != 0:
                    print("### tagResolver.resolveEval: eval:'%s'->'%s'" % (funcName, value))
                result = "%s%s%s" % (result, segment[0:pos], value)
                segment = segment[pos2 + 2:]
                pos = segment.find('$$')
            result = "%s%s" % (result, segment)
            if self.debug != 0:
                print("### tagResolver.resolveEval: resolved eval:'%s'" % result)
            return result
        else:
            return segment

    #
    # evaluate things like: $$met.getNextCounter()$$
    # in the context of the Metadata object
    # (like in sipBuilder)
    #
    def resolveMetEval(self, segment, met=None):
        sep = '$$meta.'
        sepLength = len(sep)
        pos = segment.find(sep)
        if pos >= 0:
            pos2 = pos
            n = 0
            result = ''
            while pos >= 0 and pos2 >= 0:
                if self.debug != 0:
                    print("### tagResolver.resolveMetEval: actual eval segment[%d]:'%s'" % (n, segment))
                pos2 = segment.find('$$', pos + 2)
                varName = segment[pos + sepLength:pos2]
                if self.debug != 0:
                    print("### tagResolver.resolveMetEval: eval[%d]:'%s'" % (n, varName))
                value = met.getMetadataValue(varName)
                if self.debug != 0:
                    print("### tagResolver.resolveMetEval: eval:'%s'->'%s'" % (varName, value))
                result = "%s%s%s" % (result, segment[0:pos], value)
                segment = segment[pos2 + 2:]
                pos = segment.find(sep)
            result = "%s%s" % (result, segment)
            if self.debug != 0:
                print("### tagResolver.resolveMetEval: resolved eval:'%s'" % result)
            return result
        else:
            return segment

    #
    # resolve variable inside @varName@
    # in the context of the Metadata object
    # (like in sipBuilder)
    #
    def resolveVarname(self, segment, met=None, bmet=None):
        bpref = '@BROWSE_'
        pos = segment.find('@')
        if self.debug != 0:
            print("### tagResolver.resolveVarname: to be varName resolved:'%s'" % segment)
        pos2 = pos
        n = 0
        result = ''
        while pos >= 0 and pos2 >= 0:
            if self.debug != 0:
                print("### tagResolver.resolveVarname: actual varName segment[%d]:'%s'" % (n, segment))
            pos2 = segment.find('@', pos + 1)
            varName = segment[pos + 1:pos2]
            # print "#########'%s'<->'%s'############" % (varName[0:len(bpref)-1], bpref[1:len(bpref)])
            if varName[0:len(bpref) - 1] == bpref[1:len(bpref)]:
                if self.debug != 0:
                    print("### tagResolver.resolveVarname: resolve in browse metadata varname[%d]:'%s'" % (n, varName))
                if bmet is not None:
                    value = bmet.getMetadataValue(varName)
                else:
                    value = metadata.VALUE_NOT_PRESENT
            else:
                if self.debug != 0:
                    print("### tagResolver.resolveVarname: resolve in metadata varname[%d]:'%s'" % (n, varName))
                value = met.getMetadataValue(varName)
            if self.debug != 0:
                print("### tagResolver.resolveVarname: resolve varname:'%s'->'%s'" % (varName, value))
            result = "%s%s%s" % (result, segment[0:pos], value)
            segment = segment[pos2 + 1:]
            pos = segment.find('@')
        result = "%s%s" % (result, segment)
        if self.debug != 0:
            print("### tagResolver.resolveVarname: varName resolved:'%s'" % result)
        return result


if __name__ == '__main__':
    tr = TagResolver()
    met = metadata.Metadata()
    met.setMetadataPair(metadata.METADATA_SATELLITE, "SPOT-4")
    met.setMetadataPair(metadata.METADATA_INSTRUMENT, "HRVIR")
    res = tr.resolve("HELLO_@METADATA_SATELLITE@", met)
    print("resolved:'%s'" % res)
