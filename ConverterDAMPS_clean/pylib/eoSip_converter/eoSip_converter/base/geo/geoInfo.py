from io import StringIO


class GeoInfo:
    name = None
    footprint = None
    boundingBox = None
    properties = None

    def __init__(self, n):
        self.name = n
        self.properties = {}

    def setFootprint(self, f):
        self.footprint = f

    def setBoundingBox(self, b):
        self.boundingBox = b

    def setProperties(self, p):
        self.properties = p

    def getProperties(self):
        return self.properties

    def getFootprint(self):
        return self.footprint

    def getBoundingBox(self):
        return self.boundingBox

    def getFootprintCoordAsFloat(self):
        # "coordinates":[[[5.94165872,63.02838231],[6.3254340,63.02838231],[6.3254340,61.98175800],[5.94165872,61.98175800],[5.94165872,63.02838231]]]
        toks = self.footprint.split(' ')
        res = []
        for n in range(len(toks) // 2):
            lon = float(toks[(n * 2) + 1])
            lat = float(toks[n * 2])
            pair = []
            pair.append(lon)
            pair.append(lat)
            res.append(pair)
        res2 = []
        res2.append(res)
        return res2

    def getFootprintAsJson(self):
        # "coordinates":[[[5.94165872,63.02838231],[6.3254340,63.02838231],[6.3254340,61.98175800],[5.94165872,61.98175800],[5.94165872,63.02838231]]]
        out = StringIO()
        out.write('[[')
        toks = self.footprint.split(' ')
        for n in range(len(toks) // 2):
            out.write('[')
            out.write(toks[(n * 2) + 1])
            out.write(',')
            out.write(toks[n * 2])
            out.write(']')
        out.write(']]')
        return out.getvalue()
