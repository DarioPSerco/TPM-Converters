#
# utilities to convert json to shapefile and reverse
# Lavaux Gilles 2020-02
#
#
# support:
# - POINT
# - POLYGON
# - MULTYPOLYGON
#
#

import inspect
import json
import os
import sys
import traceback
from json import dumps

from eoSip_converter.data.shapefile import shapefile

debug = False


#
# convert a shapefile to json
#
def shapeToJson(shapePath, jsonPath):
    # read the shapefile
    reader = shapefile.Reader(shapePath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    buffer = []
    n = 0
    for sr in reader.shapeRecords():
        if debug:
            print((" doing record %s" % n))
        atr = dict(list(zip(field_names, sr.record)))
        geom = sr.shape.__geo_interface__
        buffer.append(dict(type="Feature", geometry=geom, properties=atr))
        n += 1

    # write the GeoJSON file

    geojson = open(jsonPath, "w")
    geojson.write(dumps({"type": "FeatureCollection", "features": buffer}, indent=2) + "\n")
    geojson.close()


#
# convert a json to shapefile with POINT
#
def jsonToShapePoint(jsonPath, shapePath):
    fd = open(jsonPath, 'r')
    geojson_data = json.load(fd)
    fd.close()
    if debug:
        print((" readed %s bytes" % len(geojson_data)))
    #
    shape_file_writer = shapefile.Writer(shapePath, shapefile.POINT)
    #
    n = 0
    skipped = 0
    fieldNames = []
    for feature in geojson_data["features"]:
        if debug:
            print((" doing record %s" % n))
        if feature["geometry"]["type"] != "Point":
            print((" ! WARNING: feature at index %s is not 'Point' but '%s', skipped" % (n, feature["geometry"]["type"])))
            skipped += 1
        else:
            coords = feature["geometry"]["coordinates"]
            keys = list(feature["properties"].keys())
            if n == 0:  # first record, create the shape fields
                j = 0
                for aName in keys:
                    print(("   create shape field[%s]:%s" % (j, aName)))
                    shape_file_writer.field(aName)
                    fieldNames.append(aName)
                    j += 1

            values = list(feature["properties"].values())
            if debug:
                print(("  coords[%s]:%s" % (n, coords)))
                print(("  values[%s]:%s" % (n, values)))

            if 1 == 2:  # test
                j = 0
                valuesList = []
                for item in values:
                    if debug:
                        print(("   v[%s]:%s" % (j, item)))
                    valuesList.append(item)
                    j += 1
                if len(fieldNames) != len(valuesList):
                    raise Exception("fieldNames length != values length: %s VS %s" % (fieldNames, valuesList))
            shape_file_writer.point(coords[0], coords[1])
            # shape_file_writer.record(*valuesList)
            shape_file_writer.record(*tuple(values))
        n += 1

    makeProjectionFile(shapePath)

    if skipped > 0:
        print((" ! WARNING: %s feature were skipped" % skipped))


#
# convert a json to shapefile with POLYGON
#
def jsonToShapePolygon(jsonPath, shapePath):
    fd = open(jsonPath, 'r')
    geojson_data = json.load(fd)
    fd.close()
    print((" readed %s bytes" % len(geojson_data)))
    #
    shape_file_writer = shapefile.Writer(shapePath, shapefile.POLYGON)
    #
    n = 0
    skipped = 0
    fieldNames = []
    for feature in geojson_data["features"]:
        if debug:
            print((" doing record %s" % n))
        if feature["geometry"]["type"] != "Polygon":
            print((" ! WARNING: feature at index %s is not 'Polygon' but '%s', skipped" % (
            n, feature["geometry"]["type"])))
            skipped += 1
        else:
            coords = feature["geometry"]["coordinates"]
            keys = list(feature["properties"].keys())
            if n == 0:  # first record, create the shape fields
                j = 0
                for aName in keys:
                    print(("   create shape field[%s]:%s" % (j, aName)))
                    shape_file_writer.field(aName)
                    fieldNames.append(aName)
                    j += 1

            values = list(feature["properties"].values())
            if debug:
                print(("  coords[%s]:%s" % (n, coords)))
                print(("  values[%s]:%s" % (n, values)))

            if 1 == 2:  # tests
                j = 0
                valuesList = []
                for item in values:
                    if debug:
                        print(("   v[%s]:%s" % (j, item)))
                    valuesList.append(item)
                    j += 1
                if len(fieldNames) != len(valuesList):
                    raise Exception("fieldNames length != values length: %s VS %s" % (fieldNames, valuesList))

            shape_file_writer.poly(tuple(coords))
            # shape_file_writer.record(*valuesList)
            shape_file_writer.record(*tuple(values))
        n += 1

    makeProjectionFile(shapePath)

    if skipped > 0:
        print((" ! WARNING: %s feature were skipped" % skipped))


#
# convert a json to shapefile with MULTYPOLYGON
#
def jsonToShapeMultiPolygon(jsonPath, shapePath):
    fd = open(jsonPath, 'r')
    geojson_data = json.load(fd)
    fd.close()
    print((" readed %s bytes" % len(geojson_data)))
    #
    shape_file_writer = shapefile.Writer(shapePath, shapefile.POLYGON)

    #
    n = 0
    skipped = 0
    fieldNames = []
    for feature in geojson_data["features"]:
        if debug:
            print((" doing record %s" % n))
        if feature["geometry"]["type"] != "MultiPolygon":
            print((" ! WARNING: feature at index %s is not 'MultiPolygon' but '%s', skipped" % (
            n, feature["geometry"]["type"])))
            skipped += 1
        else:
            coords = feature["geometry"]["coordinates"]
            keys = list(feature["properties"].keys())
            if n == 0:  # first record, create the shape fields
                j = 0
                for aName in keys:
                    print(("   create shape field[%s]:%s" % (j, aName)))
                    shape_file_writer.field(aName)
                    fieldNames.append(aName)
                    j += 1

            values = list(feature["properties"].values())
            allPoly = []
            allPolyTuple = ()
            lastPoly = None
            if debug:
                print(("  all coords[%s]:%s" % (n, coords)))

            j = 0
            for items in coords:
                if debug:
                    print(("    coords[%s][%s]:%s\n    type:%s; length:%s" % (n, j, items, type(items), len(items))))
                k = 0
                for items2 in items:
                    if debug:
                        print(("    coords[%s][%s][%s]:%s\n    type:%s; length:%s" % (
                        n, j, k, items2, type(items2), len(items2))))
                    allPoly.append(items2)
                    k += 1
                # allPoly.append(items)
                lastPoly = items
                # allPolyTuple=allPolyTuple+(items,)
                j += 1
            if debug:
                print(("  values[%s]:%s" % (n, values)))
                # print("  lastPoly[%s]:%s" % (n, lastPoly))

            if 1 == 2:  # tests
                j = 0
                valuesList = []
                for item in values:
                    if debug:
                        print(("   v[%s]:%s" % (j, item)))
                    valuesList.append(item)
                    j += 1
                if len(fieldNames) != len(valuesList):
                    raise Exception("fieldNames length != values length: %s VS %s" % (fieldNames, valuesList))

            if debug:
                print((" allPolyTuple=%s" % (allPolyTuple,)))
                print((" allPoly=%s" % allPoly))
            shape_file_writer.poly(allPoly)
            shape_file_writer.record(*tuple(values))
        n += 1

    makeProjectionFile(shapePath)

    if skipped > 0:
        print((" ! WARNING: %s feature were skipped" % skipped))


#
# make a default projection file
#
def makeProjectionFile(shapePath, overwrite=False):
    aPath = os.path.splitext(shapePath)[0] + '.prj'
    if overwrite or not os.path.exists(aPath):
        prj = open(aPath, "w")
        epsg = 'GEOGCS["WGS 84",'
        epsg += 'DATUM["WGS_1984",'
        epsg += 'SPHEROID["WGS 84",6378137,298.257223563]]'
        epsg += ',PRIMEM["Greenwich",0],'
        epsg += 'UNIT["degree",0.0174532925199433]]'
        prj.write(epsg)
        prj.close()
    else:
        print(" don't create .prj file because it exists and NO overwrite")


#
#
#
if __name__ == '__main__':
    exitCode = -1

    try:

        #
        # do some conversion on POINT
        #
        src = 'POINT_green-p-parking-2019.shp'
        dest = 'POINT_green-p-parking-2019__to-shape.json'
        destBack = 'POINT_green-p-parking-2019__json-and-back.shp'

        shapeFilePath = '../gl_examples/shape'
        jsonFilePath = '../gl_examples/json'

        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

        srcFull = '%s/%s/%s' % (currentdir, shapeFilePath, src)
        destFull = '%s/%s/%s' % (currentdir, jsonFilePath, dest)
        if 1 == 1:
            print("\n\n")
            # shape to json
            print((" converting shapefile with POINTs %s into json:%s" % (srcFull, destFull)))
            shapeToJson(srcFull, destFull)
            print("  shape POINTs to json done")

        if 1 == 1:
            print("\n\n")
            # json to shape
            srcFull = destFull
            destFull = '%s/%s/%s' % (currentdir, shapeFilePath, destBack)
            print((" converting json:%s into shape with POINTs:%s" % (srcFull, destFull)))
            jsonToShapePoint(srcFull, destFull)
            print("  json to shape POINTs done")

        #
        # do some conversion on POLYGON
        #
        src = 'POLYGON_worldview2_strips_info_vobject_low.json'
        dest = 'POLYGON_worldview2_strips_info_vobject_low.shp'
        destBack = 'POLYGON_worldview2_strips_info_vobject_low__shape-and-back.json'

        shapeFilePath = '../gl_examples/shape'
        jsonFilePath = '../gl_examples/json'

        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

        srcFull = '%s/%s/%s' % (currentdir, jsonFilePath, src)
        destFull = '%s/%s/%s' % (currentdir, shapeFilePath, dest)
        if 1 == 1:
            print("\n\n")
            # json to shape
            print((" converting json with POLYGON %s into shape:%s" % (srcFull, destFull)))
            jsonToShapePolygon(srcFull, destFull)
            print("  json POLYGON to shape done")

        if 1 == 1:
            print("\n\n")
            # shape to json
            srcFull = destFull
            destFull = '%s/%s/%s' % (currentdir, jsonFilePath, destBack)
            print((" converting shape with POLYGONs:%s into json:%s" % (srcFull, destFull)))
            shapeToJson(srcFull, destFull)
            print("  shape POLYGONs to json done")

        #
        # do some conversion on MULTI_POLYGON
        #
        src = 'MULTI-POLYGON_urban_saved_json.json'
        dest = 'MULTI-POLYGON_urban_saved_json.shp'
        destBack = 'MULTI-POLYGON_urban_saved_json__shape-and-back.json'

        shapeFilePath = '../gl_examples/shape'
        jsonFilePath = '../gl_examples/json'

        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

        srcFull = '%s/%s/%s' % (currentdir, jsonFilePath, src)
        destFull = '%s/%s/%s' % (currentdir, shapeFilePath, dest)
        if 1 == 1:
            print("\n\n")
            # json to shape
            print((" converting json with POLYGON %s into shape:%s" % (srcFull, destFull)))
            jsonToShapeMultiPolygon(srcFull, destFull)
            print("  json MULTI-POLYGON to shape done")

        if 1 == 1:
            print("\n\n")
            # shape to json
            srcFull = destFull
            destFull = '%s/%s/%s' % (currentdir, jsonFilePath, destBack)
            print((" converting shape with POLYGONs:%s into json:%s" % (srcFull, destFull)))
            shapeToJson(srcFull, destFull)
            print("  shape POLYGONs to json done")

        exitCode = 0
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print((" Error: %s; %s" % (exc_type, exc_obj)))
        traceback.print_exc(file=sys.stdout)
        exitCode = -2

    sys.exit(exitCode)
