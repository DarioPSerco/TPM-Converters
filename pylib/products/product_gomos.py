# -*- coding: cp1252 -*-
import logging

from . import formatUtils
from . import metadata
from .product import Product
from .product_mph_sph import Product_Mph_Sph


class Product_Gomos(Product_Mph_Sph):
    #
    # syntax is: sectionName|[key][+nLine,+nLine...]
    #
    xmlMapping = {metadata.METADATA_ORIGINAL_NAME: 'MPH|PRODUCT',
                  metadata.METADATA_ACQUISITION_CENTER: 'MPH|ACQUISITION_STATION',
                  metadata.METADATA_PROCESSING_CENTER: 'MPH|PROC_CENTER',
                  metadata.METADATA_PROCESSING_TIME: 'MPH|PROC_TIME',
                  metadata.METADATA_SOFTWARE_NAME: 'MPH|SOFTWARE_VER',
                  metadata.METADATA_START_DATE: 'MPH|SENSING_START',
                  metadata.METADATA_STOP_DATE: 'MPH|SENSING_STOP',
                  metadata.METADATA_PHASE: 'MPH|PHASE',
                  metadata.METADATA_CYCLE: 'MPH|CYCLE',
                  metadata.METADATA_TRACK: 'MPH|REL_ORBIT',
                  metadata.METADATA_ORBIT: 'MPH|ABS_ORBIT',
                  metadata.METADATA_PRODUCT_SIZE: 'MPH|TOT_SIZE'
                  }

    #
    #
    #
    def __init__(self, p=None):
        Product_Mph_Sph.__init__(self, p)
        print(" init class Product_Gomos, path=%s" % p)
        self.type = Product.TYPE_MPH_SPH
        # block size
        self.MPH_SIZE = 1247
        self.SPH_SIZE = 1059
        self.mphData = None
        self.sphData = None

    #
    #
    #
    def getMetadataInfo(self):
        self.mphData = data = self.read(self.MPH_SIZE)
        self.sphData = data = self.read(self.SPH_SIZE, self.MPH_SIZE)
        print(" extract metadata info:\nMPH:\n%s\nSPH:\n%s" % (self.mphData, self.sphData))
        return None

    #
    #
    #
    def extractMetadata(self, met=None):
        if met == None:
            raise Exception("metadate is None")

        # set some evident values
        met.setMetadataPair(metadata.METADATA_PRODUCTNAME, self.origName)

        # use what contains the metadata file
        metContent = self.getMetadataInfo()

        # get fields
        num_added = 0

        for field in self.xmlMapping:
            rule = self.xmlMapping[field]
            aValue = None
            if self.debug == 0:
                print(" ##### handle metadata:%s; rule=%s" % (field, rule))

            section = rule.split('|')[0]
            key = rule.split('|')[1]
            if section == "MPH":
                for line in self.mphData.split('\n'):
                    # print "test MPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:].replace('"', '')
                        print(" found:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break

            elif section == "SPH":
                for line in self.sphData.split('\n'):
                    # print "test SPH line:%s" % line
                    if line.find(key) == 0:
                        aValue = line[len(key) + 1:].replace('"', '')
                        print(" found:%s" % aValue)
                        met.setMetadataPair(field, aValue)
                        break
            else:
                raise Exception("bad field rule:%s" % rule)

            met.setMetadataPair(field, aValue)
            num_added = num_added + 1

        self.metadata = met

        self.refineMetadata()

        self.getTypeCode()

        self.extractFootprint()

    #
    # refine the metada, should perform in order:
    # - normalise date and time
    # - normalise numbers
    # get footprint coords
    #
    def refineMetadata(self):

        # processing time
        tmp = formatUtils.mphFormatDate(self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_TIME))
        tmp = formatUtils.normaliseDateString(tmp)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_TIME, tmp)

        # processing center
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PROCESSING_CENTER)
        self.metadata.setMetadataPair(metadata.METADATA_PROCESSING_CENTER, tmp.strip())

        # start
        tmp = formatUtils.mphFormatDate(self.metadata.getMetadataValue(metadata.METADATA_START_DATE))
        tmp = formatUtils.normaliseDateString(tmp)
        pos = tmp.find('T')
        date = None
        time = None
        if pos > 0:
            date = tmp[0:pos]
            time = tmp[pos + 1:].replace('Z', '')
            # just 2 decimal after second
            # pos2 = time.find('.')
            # if pos2>0:
            #    time = time[0:(pos2+3)]
            self.metadata.setMetadataPair(metadata.METADATA_START_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_START_TIME, time)

        else:
            raise Exception("invalid start date:" + tmp)
        # stop
        tmp = formatUtils.mphFormatDate(self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE))
        tmp = formatUtils.normaliseDateString(tmp)
        pos = tmp.find('T')
        date = None
        time = None
        if pos > 0:
            date = tmp[0:pos]
            time = tmp[pos + 1:].replace('Z', '')
            # just 2 decimal after second
            # pos2 = time.find('.')
            # if pos2>0:
            #    time = time[0:(pos2+3)]
            self.metadata.setMetadataPair(metadata.METADATA_STOP_DATE, date)
            self.metadata.setMetadataPair(metadata.METADATA_STOP_TIME, time)

        else:
            raise Exception("invalid start date:" + tmp)

        # time position == stop date + time
        self.metadata.setMetadataPair(metadata.METADATA_TIME_POSITION, "%sT%sZ" % (
        self.metadata.getMetadataValue(metadata.METADATA_STOP_DATE),
        self.metadata.getMetadataValue(metadata.METADATA_STOP_TIME)))

        # size
        tmp = self.metadata.getMetadataValue(metadata.METADATA_PRODUCT_SIZE)
        tmp = int(tmp.replace('<bytes>', ''))
        self.metadata.setMetadataPair(metadata.METADATA_PRODUCT_SIZE, tmp)

        # cycle
        tmp = self.metadata.getMetadataValue(metadata.METADATA_CYCLE)
        self.metadata.setMetadataPair(metadata.METADATA_CYCLE, "%s" % int(tmp))

        # track
        tmp = self.metadata.getMetadataValue(metadata.METADATA_TRACK)
        self.metadata.setMetadataPair(metadata.METADATA_TRACK, "%s" % int(tmp))
        self.metadata.setMetadataPair(metadata.METADATA_WRS_LONGITUDE_GRID_NORMALISED,
                                      formatUtils.normaliseNumber("%s" % int(tmp), 3, '0'))

        # acq station
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ACQUISITION_CENTER)
        self.metadata.setMetadataPair(metadata.METADATA_ACQUISITION_CENTER, tmp.strip())

        # software name
        tmp = self.metadata.getMetadataValue(metadata.METADATA_SOFTWARE_NAME)
        self.metadata.setMetadataPair(metadata.METADATA_SOFTWARE_NAME, tmp.strip())

    #
    #
    #
    def getTypeCode(self):
        tmp = self.metadata.getMetadataValue(metadata.METADATA_ORIGINAL_NAME)
        self.metadata.setMetadataPair(metadata.METADATA_TYPECODE, tmp[0:10])

    #
    #
    #
    def extractFootprint(self):
        pass


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        p = Product_Gomos(
            "C:/Users/glavaux/Shared/LITE/testData/Gomos/GOM_LIM_1P/GOM_LIM_1P_20020415_00644/GOM_LIM_1PRFIN20020415_013513_000000642005_00089_00644_0587.N1")
        p.getMetadataInfo()
        met = metadata.Metadata()
        p.extractMetadata(met)

        print("\n\nmetadata:%s" % met.dump())
    except Exception as err:
        log.exception('Error from throws():')
