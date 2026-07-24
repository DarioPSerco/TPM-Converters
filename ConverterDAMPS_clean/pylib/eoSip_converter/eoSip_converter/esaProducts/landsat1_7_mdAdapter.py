# -*- coding: cp1252 -*-
#
# this class adapt some src metadata into the MD.XML format that can be parsed by Product_EOSIP
#
#
import eoSip_converter.xmlHelper as xmlHelper

SCHEMA = """ xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:opt="http://www.opengis.net/opt/2.1" xmlns:eop="http://www.opengis.net/eop/2.1" xmlns:om="http://www.opengis.net/om/2.0" xmlns:ows="http://www.opengis.net/ows/2.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  """
DELIMITER = '<eop:EarthObservation'


#
#
#
class Landsat1_7_mdAdapter:

    #
    #
    #
    def __init__(self):
        self.formattedXml = None
        print(" init class Landsat1_7_mdAdapter")

    #
    #
    #
    def generateMdXml(self, data):
        print(" generateMdXml from data:\n%s" % data)
        # pos = data.replace(DELIMITER, DELIMITER )

        helper = xmlHelper.XmlHelper()
        helper.setData(data)
        helper.parseData()
        print(" generateMdXml data parsed")

        aNode = helper.getFirstNodeByPath(None, 'EarthObservation', None)
        if aNode is None:
            raise Exception("can not find node metadataReport/EarthObservation")

        self.formattedXml = helper.prettyPrint(aNode)

        # add schemas
        pos = self.formattedXml.find(DELIMITER)
        if pos < 0:
            raise Exception("incorrect formattedXml")
        self.formattedXml = self.formattedXml[0: pos + len(DELIMITER)] + SCHEMA + self.formattedXml[
                                                                                  pos + len(DELIMITER):]
        print(" generateMdXml resulting xml:\n%s" % self.formattedXml)

        fd = open('/home/gilles/shared/a.xml', 'w')
        fd.write(self.formattedXml)
        fd.flush()
        fd.close()

        return self.formattedXml

    #
    #
    #
    def getMetadataXml(self):
        return self.formattedXml
