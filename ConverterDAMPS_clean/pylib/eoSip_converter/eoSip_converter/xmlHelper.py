#!/usr/bin/env python
#
# xml helper
# Lavaux Gilles 2013
#
#
import sys
import xml.dom.minidom
from xml.dom.minidom import getDOMImplementation

import lxml.etree as etree

debug = 0


class XmlHelper:
    # dom object
    domDoc = None
    # path
    path = None
    # data
    data = None
    #
    # lxml part:
    #
    lxmlRoot = None

    def __init__(self):
        self.debug = debug
        if self.debug != 0:
            print("xmlHelper created")

    #
    # set DEBUG
    #
    def setDebug(self, d):
        if not isinstance(d, int):
            print("ERROR setDebug: parameter is not an integer")
        print(" XmlHelper setDebug:%s" % d)
        self.debug = d

    #
    # get DEBUG
    #
    def getDebug(self):
        return self.debug

    #
    #
    #
    def createDoc(self, top=None, tag=None):
        impl = getDOMImplementation()
        self.domDoc = impl.createDocument(None, top, None)
        return self.domDoc.documentElement

    #
    # set domDoc
    #
    def setDomDoc(self, d=None):
        self.domDoc = d

    #
    # get domDoc
    #
    def getDomDoc(self):
        return self.domDoc

    #
    # set content
    #
    def setData(self, d=None):
        self.data = d

    #
    # get rootNode
    #
    def getRootNode(self):
        return self.domDoc.documentElement

    #
    # load a file, don't parse the content
    #
    def loadFile(self, p=None):
        self.path = p
        if self.debug != 0:
            print(" will load file:%s" % self.path)
        fd = open(self.path, 'r')
        self.rawLines = fd.readlines()
        fd.close()
        self.data = ''
        for item in self.rawLines:
            self.data = "%s%s" % (self.data, item)
        if self.debug != 0:
            print("  %s loaded" % self.path)

    #
    # parse content
    #
    def parseData(self, d=None):
        if d is not None:
            self.data = d
        if self.data is None or len(self.data) == 0:
            raise Exception("nothing to be parsed")
        self.domDoc = xml.dom.minidom.parseString(self.data)
        if self.debug != 0:
            print("  data parsed")

    #
    # get list of nodes by name
    #
    def getNodeChildrenByName(self, node=None, name=None):
        if node is None:
            raise Exception("node can not be None")
        result = []
        nodeList = node.childNodes
        for node in nodeList:
            if node.localName == name:
                result.append(node)
        if self.debug != 0:
            print("  getNodeChildrenByName() return: %s items" % len(result))
        return result

    #
    # get first node by path 
    #
    def getFirstNodeByPath(self, node=None, path=None, attr=None):
        result = []
        self.getNodeByPath(node, path, attr, result)
        if len(result) > 0:
            return result[0]
        else:
            return None

    #
    # get list of nodes by path
    #
    # def getNodeByPath(self, node=None, path=None, result=[]):
    #    print " getNodeByPath: result=%s" % result
    #    self.getNodeByPath(node, path, None, result)

    #
    # get list of all childrens
    #
    def getNodeDescendant(self, node=None, attr=None, result=None):
        if result == None:
            raise Exception("result list can not be None")
        if self.debug == 1:
            print("")
        if self.domDoc == None:
            raise Exception("dom document is None, is data parsed?")

        # get root node by default
        if node is None:
            node = self.getRootNode()

        if self.debug != 0:
            print("  getNodeDescendant: current node:%s" % node.localName)

        nodeList = node.childNodes
        for node in nodeList:
            result.append(node)
            self.getNodeDescendant(node, attr, result)

    #
    # get list of nodes by path (TODO: and filter by attribute if given)
    #
    # params:
    #    node: look from this node and below, root node if None
    #    path: path to look at: don't use leading or triling '/'
    #    attr: look for matching attribute: syntax: key==value
    #    result: list where to put the found nodes
    #
    def getNodeByPath(self, entryNode=None, path=None, attr=None, result=None):
        if self.debug != 0:
            if entryNode is None:
                print(" enter getNodeByPath: entryNode=%s; path=%s; attr=%s; result=%s" % (
                entryNode, path, attr, result))
            else:
                print(" enter getNodeByPath: entryNode=%s; path=%s; attr=%s; result=%s" % (
                entryNode.localName, path, attr, result))
        if result == None:
            raise Exception("result list can not be None")

        if self.debug == 1:
            print("")
        if self.domDoc == None:
            raise Exception("dom document is None, is data parsed?")
        # need that path starts with /
        if len(path) > 0 and path[0] != "/":
            path = "/" + path
        if self.debug != 0:
            print("  getNodeByPath: current path:%s" % path)

        # get root node by default
        if entryNode is None:
            entryNode = self.getRootNode()
            # already good?
            if self.debug != 0:
                print("  getNodeByPath() test root node.localName:%s VS %s" % (entryNode.localName, path))
            if "/" + entryNode.localName == path:
                # test attribute
                if attr is None:
                    result.append(entryNode)
                else:  # format key=value
                    if entryNode.getAttribute(attr.split('==')[0]) == attr.split('==')[1]:
                        result.append(entryNode)
                return

        # get current level name, build next iteration path
        toks = path.split("/")
        if self.debug != 0:
            print("  getNodeByPath: toks:%s" % toks)
        current_target = toks[1]
        nextPath = ""
        if len(toks) > 2:
            for seg in range(2, len(toks)):
                nextPath = "%s/%s" % (nextPath, toks[seg])
        if self.debug != 0:
            print("  getNodeByPath: current_target:%s;  nextPath;%s" % (current_target, nextPath))

        if nextPath != '':  # not deepest level
            # look for non leaf node
            nodeList = entryNode.childNodes
            n = 0
            for node in nodeList:
                if self.debug != 0:
                    print("  getNodeByPath: non-deep-ok node[%d]; name:%s; current_target:%s" % (
                    n, node.localName, current_target))
                if node.localName == current_target:
                    if self.debug != 0:
                        print("  getNodeByPath: --> name:%s match" % node.localName)
                    self.getNodeByPath(node, nextPath, attr, result)
                n = n + 1

        else:  # deepest ok level reached
            # look for the node
            nodeList = entryNode.childNodes
            n = 0
            for node in nodeList:
                if self.debug != 0:
                    print("  getNodeByPath: deep-ok node[%d]; name:%s; current_target:%s" % (
                    n, node.localName, current_target))
                if node.localName == current_target:
                    if self.debug != 0:
                        print("  getNodeByPath: -->  name:%s match" % node.localName)
                    # test attribute
                    if attr is None:
                        if self.debug != 0:
                            print("  getNodeByPath: -->  name:%s match and no attribute used, is OK" % node.localName)
                        result.append(node)
                    else:  # format key=value
                        if node.getAttribute(attr.split('==')[0]) == attr.split('==')[1]:
                            result.append(node)
                            if self.debug != 0:
                                print("  getNodeByPath: -->  name:%s match and attribute match, is OK" % node.localName)
                        else:
                            if self.debug != 0:
                                print("  getNodeByPath: -->  name:%s match and attribute don't match:'%s' vs '%s', is NOT OK" % (
                                node.localName, node.getAttribute(attr.split('=')[0]), attr))
                n = n + 1

    #
    # info
    #
    def info(self):
        print("xmlHelper.info:")
        print(" path:%s" % self.path)
        if self.data != None:
            print(" data length: %d" % len(self.data))
        else:
            print(" data: None")

    #
    # get a node text content
    #
    def getNodeText(self, node):
        # if node==None:
        #    return None
        res = None
        n = 0
        for anode in node.childNodes:
            n = n + 1
            # print " child %d: type:%s  %s" % (n, anode.nodeType, anode)
            if anode.nodeType == anode.TEXT_NODE:
                res = anode.data
        return res

    #
    # get a node attribute text content
    #
    def getNodeAttributeText(self, node, attr):
        # print " getNodeAttributeText; attr=%s" % attr
        res = None
        res = node.getAttribute(attr)
        return res

    #
    #
    #
    def setNodeAttributeText(self, node, attr, value):
        node.setAttribute(attr, value)

    #
    #
    #
    def createCdataNode(self, name, data):
        cdata = self.domDoc.createCDATASection(data)
        cdv = self.domDoc.createElement("cdatanode")
        cdv.setAttribute("Sev", "1")
        cdv.appendChild(cdata)
        return cdv

    #
    # set a node cdata content
    #
    def setNodeCdata(self, node, data):
        cdata = self.domDoc.createCDATASection(data)
        node.setAttribute("Sev", "1")
        node.appendChild(cdata)

    #
    # set a node text content
    #
    def setNodeText(self, node, text):
        res = None
        for anode in node.childNodes:
            if anode.nodeType == anode.TEXT_NODE:
                anode.data = text
                res = anode.data
        if res == None:
            textnode = self.domDoc.createTextNode(text)
            node.appendChild(textnode)
        return res

    #
    # append a node
    #
    def appendChild(self, node, name):
        child = self.domDoc.createElement(name)
        node.appendChild(child)
        return child

    #
    #
    #
    def createNode(self, text, attrName=None, attrValue=None):
        aNode = self.domDoc.createElement(text)
        if attrName is not None and attrValue is not None:
            self.setNodeAttributeText(aNode, attrName, attrValue)
        return aNode

    #
    # pretty print using minidom
    #
    def prettyPrint(self, node=None):
        if node == None:
            return self.domDoc.documentElement.toxml()
        else:
            return node.toxml()

    #
    # pretty print using lxml
    #
    # TODO: don't re-parse the data
    #
    def prettyPrintAll(self):
        # global LXML_READY
        # if not LXML_READY:
        #    if self.DEBUG!=0:
        #        print "  prettyPrintAll use minidom"
        #    return self.domDoc.documentElement.toprettyxml()
        # else:
        # if self.DEBUG!=0:
        #   print "  prettyPrintAll use LXML"
        parser = etree.XMLParser(resolve_entities=False, strip_cdata=False, remove_blank_text=True)
        root = etree.fromstring(self.data, parser)
        return etree.tostring(root, encoding='utf-8', pretty_print=True)

    #
    # lxml parts
    #

    #
    #
    #
    def _createLxmlRoot(self):
        if self.debug != 0:
            print("  __createLxmlRoot")
        self.lxmlRoot = etree.fromstring(self.data)

    #
    #
    #
    def lxmlGetElemenentsByAttribute(self, key, attrName, attrValue):
        if self.lxmlRoot is None:
            self._createLxmlRoot()
        filter = "//%s[@%s='%s']" % (key, attrName, attrValue)
        # print " xpath filter:%s" % filter
        return self.lxmlRoot.xpath(filter)

    #
    # return nodes bases on path and attribute name+value filtering
    #
    def getNodeContentPathAttrFiltered(self, path, attrName, attrValue):
        if self.debug:
            print("  starting getNodeContentPathAttrFiltered")
        aList = []
        aRes = []
        self.getNodeByPath(None, path, None, aList)
        if self.debug:
            print("  getNodeContentPathAttrFiltered found %s node(s)" % len(aList))
        n = 0
        for aNode in aList:
            if self.debug:
                print("  getNodeContentPathAttrFiltered a node[%s]=%s; content=%s" % (n, aNode, self.getNodeText(aNode)))
            v = self.getNodeAttributeText(aNode, attrName)
            if v is not None:
                if v == attrValue:
                    if self.debug:
                        print("  getNodeContentPathAttrFiltered a node[%s] attr match" % n)
                    aRes.append(aNode)
                else:
                    if self.debug:
                        print("  getNodeContentPathAttrFiltered a node[%s] don't match" % n)
            n += 1
        return aRes


def main():
    """Main funcion"""

    helper = XmlHelper()
    if len(sys.argv) > 1:
        print("use xmlHelper on file:%s" % sys.argv[1])
        helper.loadFile(sys.argv[1])
        helper.parseData()
        print("info:%s" % helper.info())

        doc = helper.getDomDoc()
        print("doc:%s" % doc)
        earthObservationResultNodes = doc.getElementsByTagName('eop:EarthObservationResult')
        print(" earthObservationResultNodes:%s" % earthObservationResultNodes)
        productNode = earthObservationResultNodes[0].getElementsByTagName('eop:product')
        print(" productNode:%s" % productNode)
        print("\nbefore:%s" % helper.prettyPrint(earthObservationResultNodes[0]))

        entry = doc.createElement('eop:browse')
        earthObservationResultNodes[0].insertBefore(entry, productNode[0])

        print(dir(earthObservationResultNodes[0]))

        print("\nafter:%s" % helper.prettyPrint(earthObservationResultNodes[0]))
        # helper.getNodeByName(None, "List_of_Ipf_Procs")
        # resultList=[]
        # helper.getNodeByPath(None, "Quality_Assesment/Quality_Parameter", None, resultList)
        # print "result 1:%s" % resultList
        # print "result 1 text :%s" % helper.getNodeText(resultList[0])

    else:
        # path="C:/Users/glavaux/data/Development/python/xmls/KO2_OPER_EOC_PAN_1G_20110504T015124_20110504T015124_0001.XML"
        # path="/home/gilles/shared2/MDPs/EN1_OESR_ASA_IM__0P_20100204T002606_20100204T002748_041467_0331_0001.SSM.XML"
        path = "/home/gilles/shared2/Datasets/spot5-take5/new/stripped/SPOT5_HRG2_XS_20150716_N2A_LombardyItaliaD0000B0000/SPOT5_HRG2_XS_20150716_N2A_LombardyItaliaD0000B0000.xml"
        helper.loadFile(path)
        helper.parseData()
        # print helper.info()

        # test for spot5-take5
        results = []
        helper.getNodeByPath(None, 'CTN_HISTORY/TASKS/TASK', None, results)
        # print "number of resulsts:%s" % len(results)
        n = 0
        inputFilename = None
        for item in results:
            plugin = helper.getFirstNodeByPath(item, 'PLUGIN_ASKED', None)
            name = None
            if plugin != None:
                pname = helper.getNodeText(plugin)
            else:
                raise Exception('can not find PLUGIN_ASKED in task[%s]' % n)
            plugInName = helper.getNodeText(plugin)
            print(" found PLUGIN_ASKED: %s: %s" % (n, plugInName))

            if plugInName == 'ORTHO':
                inputFile = helper.getFirstNodeByPath(item, 'INPUT_PRODUCTS/FILE', None)
                if inputFile != None:
                    inputFilename = helper.getNodeText(inputFile)
                # print " found INPUT_PRODUCTS: %s" % (helper.getNodeText(inputFile))
                break
            n += 1

        if inputFilename != None:
            print(" found INPUT_PRODUCTS: %s" % inputFilename)
        else:
            raise Exception('can not find INPUT_PRODUCTS')

        print("\n\nPretty print:\n%s" % helper.prettyPrintAll())
        result = []
        helper.getNodeDescendant(None, None, result)
        print("\n\ngetNodeDescendant: length:%s" % len(result))

        n = 0
        for node in result:
            if node.nodeType == node.TEXT_NODE:
                print(" node[%s] type=%s (text); localname=%s" % (n, node.nodeType, node.localName))
            else:
                print(" node[%s] type=%s; localname=%s" % (n, node.nodeType, node.localName))
            n = n + 1


if __name__ == "__main__":
    main()
