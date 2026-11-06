import sys
import traceback

#
JSON_PATTERN = '        {"type":"Feature", "properties":{"order":"ORDER", "country":"COUNTRY", "city":"CITY", "luzId":"LUZID"}, "geometry":{"type":"Polygon", "coordinates":[[PAIR_LONG_VIRGOLA_LAT_VIRGOLA]]}}'
#
firstJson = True


def initJson(fd):
    global firstJson
    firstJson = True
    fd.write('{ "type": "FeatureCollection",\n')
    fd.write('    "features":\n')
    fd.write('    [\n')
    fd.flush()


def closeJson(fd):
    global firstJson
    fd.write('\n    ]\n')
    fd.write('}')
    fd.flush()
    fd.close()
    firstJson = False


#
# coords in lat space lon
#
def extentToJson(fd, coords, order='order', country='country', city='city', luzId='LuzId'):
    global firstJson
    #
    # 'PAIR_LONG_VIRGOLA_LAT_VIRGOLA', into: '[%s,%s],[%s,%s],[%s,%s],[%s,%s],[%s,%s]
    #
    coordPairsSring = ''
    toks = coords.split(' ')
    numPairs = len(toks)
    for n in range(numPairs // 2):
        if len(coordPairsSring) > 0:
            coordPairsSring += ', '
        coordPairsSring += "[%s,%s]" % (toks[(n * 2) + 1], toks[(n * 2)])
    print((" coordPairsSring=%s" % coordPairsSring))

    tmp = JSON_PATTERN.replace('PAIR_LONG_VIRGOLA_LAT_VIRGOLA', coordPairsSring)
    tmp = tmp.replace('ORDER', order)
    country2 = country.replace('country:', '').strip()
    city2 = city.replace('city:', '').strip()
    tmp = tmp.replace('COUNTRY', country2)
    tmp = tmp.replace('CITY', city2)
    tmp = tmp.replace('LUZID', luzId)
    print("\nJSON=%s\n" % tmp)
    if firstJson:
        fd.write(tmp)
        firstJson = False
    else:
        fd.write(',\n' + tmp)
    fd.flush()


#
#
#
def main():
    try:

        fd = open('toJson.json', 'w')
        initJson(fd)
        coords = sys.argv[1]
        coords = coords.replace('"', '').replace("'", '')
        print((" using coords:%s" % coords))
        extentToJson(fd, sys.argv[1], 'Order', 'Country', 'City', 'LuzId')
        closeJson(fd)
        print(" toJson.json done")



    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(" Error: %s %s" % (exc_type, exc_obj))
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
