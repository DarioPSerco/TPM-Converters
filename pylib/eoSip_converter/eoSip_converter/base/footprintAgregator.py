import json
import re
import sys
import traceback

import eoSip_converter.esaProducts.metadata as metadata
from eoSip_converter.fileHelper import FileHelper
from .geo.geoInfo import GeoInfo

debug = False


class FootprintAgregator:
    #
    debug = True
    # productName/GeoInfo
    productGeoInfoMap = None
    # wanted metadata fields
    wantedMetadata = []

    #
    #
    #
    def __init__(self):
        self.productGeoInfoMap = {}

    #
    #
    #
    def setWantedMetadata(self, l):
        self.wantedMetadata = l

    #
    #
    #
    def getWantedMetadata(self):
        return self.wantedMetadata

    #
    #
    #
    def getNumProducts(self):
        return len(self.productGeoInfoMap)

    #
    # look for geoJson files below a given path, and concatenate the files features
    #
    def concatenateGeoJson(self, srcPath, geoJsonFilePath):
        fileHelper = FileHelper()
        re1Prog = re.compile("^.*$")
        re2Prog = re.compile("^.json$")
        list = fileHelper.list_files(srcPath, re1Prog, re2Prog)
        if debug:
            print((" > concatenateGeoJson; found %s json files" % len(list)))
        #
        # out = StringIO()
        geojson = {'type': 'FeatureCollection', 'features': []}
        n = 0
        total = 0
        for item in list:
            if debug:
                print(("\n  doing file[%s]:'%s'" % (n, item)))
            fd = open(item, 'r')
            data = json.load(fd)
            if debug:
                print(("\n\n>>\n%s\n\n" % data))
            # out.write(data['type'])
            # out.write('\n')
            i = 0
            for feature in data['features']:
                if debug:
                    print(("  feature[%s]:%s" % (i, feature)))
                # out.write(feature)
                # out.write('\n')
                geojson['features'].append(feature)
                total += 1
                i += 1
            fd.close()
            if debug:
                print(("   contains: %s features" % i))
            n += 1
        # res=out.getvalue()
        geo_str = json.dumps(geojson)
        if debug:
            print(("## geo_str=%s" % geo_str))
        fd = open(geoJsonFilePath, 'w')
        fd.write(geo_str)
        fd.flush()
        fd.close()
        print(("\n > concatenateGeoJson geoJson file generated: '%s'\n    contains %s features" % (
        geoJsonFilePath, total)))

    #
    # add a product
    #
    # get the foorprint info from:
    # - srcProduct OR destProduct ???
    # -
    #
    def addProduct(self, pInfo):
        if debug:
            print((" SRC METADATA dump:%s" % pInfo.srcProduct.metadata.dump()))
            print((" DEST METADATA dump:%s" % pInfo.destProduct.metadata.dump()))

        pInfo.destProduct.agregateGeoInfo(pInfo)
        # print(" STOP AT GEOINGO AGREGATION")
        # os._exit(1)

        if pInfo.srcProduct.origName in list(self.productGeoInfoMap.keys()):
            print((" #### Product %s is already present in productGeoInfoMap" % pInfo.srcProduct.origName))
            return
        geoInfo = GeoInfo(pInfo.srcProduct.origName)
        geoInfo.setFootprint(pInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_FOOTPRINT))
        geoInfo.setBoundingBox(pInfo.srcProduct.metadata.getMetadataValue(metadata.METADATA_BOUNDING_BOX))
        props = {}
        # default
        props['BatchId'] = pInfo.ingester.fixed_batch_name
        props['ItemId'] = pInfo.num
        # wanted metadata
        n = 0
        if debug:
            print((" adding %s metadata" % len(self.wantedMetadata)))
        for mName in self.wantedMetadata:
            v = pInfo.srcProduct.metadata.getMetadataValue(mName)
            props[mName] = v
            if debug:
                print((" adding metadata[%s]:%s=%s" % (n, mName, v)))
            n += 1
        geoInfo.setProperties(props)
        self.productGeoInfoMap[pInfo.srcProduct.origName] = geoInfo

    #
    #
    #
    def makeJsonShape(self):
        if debug:
            print(" ## makeJsonShape")

        n = 0

        geojson = {'type': 'FeatureCollection', 'features': []}
        for key in list(self.productGeoInfoMap.keys()):
            if debug:
                print((" doing geoitem[%s]:%s" % (n, key)))
            geoInfo = self.productGeoInfoMap[key]
            feature = {'type': 'Feature',
                       'properties': geoInfo.getProperties(),
                       'geometry': {'type': 'Polygon',
                                    'coordinates': geoInfo.getFootprintCoordAsFloat()}}
            geojson['features'].append(feature)
            n += 1

        geo_str = json.dumps(geojson)
        if debug:
            print(("## geo_str=%s" % geo_str))
        return geo_str

    #
    # return geoJson for a single footprint
    #
    def makeSingleJsonShape(self, name, footprint, props=None):
        if debug:
            print((" ## makeSingleJsonShape with:%s" % footprint))

        geojson = {'type': 'FeatureCollection', 'features': []}
        geoInfo = GeoInfo(name)
        geoInfo.setFootprint(footprint)
        if props is not None:
            geoInfo.setProperties(props)
        feature = {'type': 'Feature',
                   'properties': geoInfo.getProperties(),
                   'geometry': {'type': 'Polygon',
                                'coordinates': geoInfo.getFootprintCoordAsFloat()}}
        geojson['features'].append(feature)

        geo_str = json.dumps(geojson)
        if debug:
            print(("## geo_str=%s" % geo_str))
        return geo_str


#
#
#
if __name__ == '__main__':
    exitCode = -1

    try:
        aPath = '/home/gilles/shared/CONVERTERS_REFERENCE/glpkg_launchdir/geojson'
        agreg = FootprintAgregator()
        agreg.concatenateGeoJson(aPath, "concatenatedGeoJson.json")

        exitCode = 0
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print((" Error: %s; %s" % (exc_type, exc_obj)))
        traceback.print_exc(file=sys.stdout)
        exitCode = -2

    sys.exit(exitCode)
