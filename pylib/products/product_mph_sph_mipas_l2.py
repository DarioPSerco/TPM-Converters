# -*- coding: cp1252 -*-

from . import formatUtils
from . import metadata
from . import product_mph_sph
from .product_mph_sph import Product_Mph_Sph


class Product_Mph_Sph_Mipas_L2(Product_Mph_Sph):
    #
    # syntax is: sectionName|[key][+nLine,+nLine...]
    #
    xmlMapping2 = {'X_POSITION': 'MPH|X_POSITION',
                   'Y_POSITION': 'MPH|Y_POSITION',
                   'Z_POSITION': 'MPH|Z_POSITION',
                   'X_VELOCITY': 'MPH|X_VELOCITY',
                   'Y_VELOCITY': 'MPH|Y_VELOCITY',
                   'Z_VELOCITY': 'MPH|Z_VELOCITY'
                   }

    #
    #
    #
    def __init__(self, p=None):
        Product_Mph_Sph.__init__(self, p)

        self.productAux = {}

        print(" init class Product_Mph_Sph_Mipas_L2, path=%s" % p)

    #
    #
    #
    def extractMetadata(self, met=None):
        print(" extractMetadata")
        # from parent
        num_added = Product_Mph_Sph.extractMetadata(self, met)
        print("  extracted from parent: %s" % num_added)

        # from this
        num_added = 0

        for field in self.xmlMapping2:
            rule = self.xmlMapping2[field]
            aValue = None
            if self.debug != 0:
                print(" handle metadata 2:%s; rule=%s" % (field, rule))

            section = rule.split('|')[0]
            key = rule.split('|')[1]
            if section == "MPH":
                for line in self.mphData.split('\n'):
                    # print "test MPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:]  # .replace('"','')
                        if self.debug != 0:
                            print(" found 2:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break

            elif section == "SPH":
                for line in self.sphData.split('\n'):
                    # print "test SPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:]  # .replace('"','')
                        if self.debug != 0:
                            print(" found 2:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break
            else:
                raise Exception("bad field rule 2:%s" % rule)

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        # set typecode
        met.setMetadataPair(metadata.METADATA_TYPECODE, met.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)[0:10])

        # copy metadata that will be overwriten
        met.setMetadataPair('ProductName', met.getMetadataValue(metadata.METADATA_PRODUCTNAME))

        print(" this metadata extracted:%s" % num_added)
        return num_added

    #
    #
    #
    def formatDateString(self, s):
        # print " formatDateString:%s" % s
        tmp = product_mph_sph.mphFormatDate(s)
        # print " formatDateString after mphFormatDate:%s" % tmp
        toks = tmp.split('T')
        toks2 = toks[0].split('-')
        month = toks2[1]
        monthNum = formatUtils.getMonth2DigitFromMonthString(month)
        tmp = "%s-%s-%s %s" % (toks2[0], monthNum, toks2[2], toks[1])
        if tmp.find('T') >= 0:
            tmp = tmp.replace('T', '')
        if tmp.find('Z') >= 0:
            tmp = tmp.replace('Z', '')
        pos = tmp.find('.')
        if pos > 0:
            tmp = tmp[0:pos]
        return tmp

    #
    # refine the metada, should perform in order:
    # 
    #
    def refineMetadata(self):
        self.metadata.setMetadataPair('ProductName',
                                      product_mph_sph.mphStripString(self.metadata.getMetadataValue('ProductName')))
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)))
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)))

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME))
        tmp = self.formatDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        #
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, product_mph_sph.mphStripString(
            self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_NAME)))

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_GENERATION_TIME))
        tmp = tmp.replace('T', '').replace('Z', '')
        self.metadata.setMetadataPair(metadata.METADATA_GENERATION_TIME, tmp)

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        tmp = self.formatDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_START_DATE, tmp)

        #
        tmp = product_mph_sph.mphStripString(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE))
        tmp = self.formatDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, tmp)

        #
        tmp = product_mph_sph.mphStripByteUnit(self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE))
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, int(tmp))

        #
        v1 = product_mph_sph.mphStripMpersecUnit(self.metadata.getMetadataValue('X_VELOCITY'))
        v2 = product_mph_sph.mphStripMpersecUnit(self.metadata.getMetadataValue('Y_VELOCITY'))
        v3 = product_mph_sph.mphStripMpersecUnit(self.metadata.getMetadataValue('Z_VELOCITY'))
        if v3[0] == '+':
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'A')
        elif v3[0] == '-':
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, 'D')
        else:
            self.metadata.setMetadataPair(metadata.METADATA_ORBIT_DIRECTION, v3)

        self.metadata.setMetadataPair('StateVectorVelocity', "%s %s %s" % (v1, v2, v3))

        #
        v1 = product_mph_sph.mphStripMeterUnit(self.metadata.getMetadataValue('X_POSITION'))
        v2 = product_mph_sph.mphStripMeterUnit(self.metadata.getMetadataValue('Y_POSITION'))
        v3 = product_mph_sph.mphStripMeterUnit(self.metadata.getMetadataValue('Z_POSITION'))
        self.metadata.setMetadataPair('StateVectorPosition', "%s %s %s" % (v1, v2, v3))

        #
        geo = ''
        lines = self.sphHeaderData.split('\n')
        for line in lines:
            if line.find('FIRST_TANGENT_LAT') >= 0:
                geo = "%s%s " % (geo, product_mph_sph.mphDegreeEeeToNumber(line[len('FIRST_TANGENT_LAT') + 1:]))
            elif line.find('FIRST_TANGENT_LONG') >= 0:
                geo = "%s%s " % (geo, product_mph_sph.mphDegreeEeeToNumber(line[len('FIRST_TANGENT_LONG') + 1:]))
            elif line.find('LAST_TANGENT_LAT') >= 0:
                geo = "%s%s " % (geo, product_mph_sph.mphDegreeEeeToNumber(line[len('LAST_TANGENT_LAT') + 1:]))
            elif line.find('LAST_TANGENT_LONG') >= 0:
                geo = "%s%s " % (geo, product_mph_sph.mphDegreeEeeToNumber(line[len('LAST_TANGENT_LONG') + 1:]))
        self.metadata.setMetadataPair('GeographicalCoverage', geo[0:-1])

        #
        for i in range(self.NUM_DSD):
            dsd = self.getDsdContent(i)
            # print "%s" % dsd
            lines = dsd.split('\n')
            n = 0
            for line in lines:
                if line.find('FILENAME') >= 0:
                    filename = line[len('FILENAME') + 1:].replace('"', '').strip()
                    # print " @@@@@ productAux[%s]:'%s'" % (n,filename)
                    if len(filename) > 0:
                        self.productAux[filename] = filename
                        print(" added productAux[%s]:'%s'" % (n, filename))
                        n = n + 1

    #
    #
    #
    def extractFootprint(self):
        pass

# if __name__ == '__main__':
#     print "start"
#     logging.basicConfig(level=logging.WARNING)
#     log = logging.getLogger('example')
#     try:
#         p=Mph_Sph_Mipas_L2_Product("/home/gilles/shared2/Datasets/IDEAS/ifremer/MIP_NL__2PWDSI20100211_190437_000060442086_00443_41579_1000.N1")
#         p.getMetadataInfo()
#         met=metadata.Metadata()
#         p.extractMetadata(met)
#
#         print "\n\nmetadata:%s" % met.dump()
#     except Exception, err:
#         log.exception('Error from throws():')
