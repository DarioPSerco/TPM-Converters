from . import formatUtils
from .browseImage import BrowseImage


class SpotBrowseImage(BrowseImage):
    def __init__(self):
        super(SpotBrowseImage, self).__init__()

    def SimplifiedLocationModel_to_latLon(self, i, j, a, b, c, d, e, f, aa, bb, cc, dd, ee, ff):
        lamb = a + b * i + c * j + d * i * j + e * (i * i) + f * (j * j)
        phi = aa + bb * i + cc * j + dd * i * j + ee * (i * i) + ff * (j * j)
        return lamb, phi


if __name__ == '__main__':
    browse = SpotBrowseImage()
    # razvan MD
    # browse.setFootprint('50.536655 0.184164 51.295147 -0.438592 50.869156 -1.717447 50.116280 -1.076581 50.536655 0.184164')
    # f130:
    # browse.setFootprint('50.706326 -1.422633 51.509552 -2.083871 51.082394 -3.366864 50.284790 -2.687338 50.706326 -1.422633')
    # d79f:
    browse.setFootprint(
        '57.548565 -6.235787 58.214821 -7.003214 57.726082 -8.463278 57.067547 -7.676068 57.548565 -6.235787')
    browse.calculateCenter()
    print(browse.info())
    browse.reverse()
    print("\nreversed:")
    print(browse.info())
    print("\n\n\n\n")
    # razvan BI
    # browse.setFootprint('50.875046 -1.722543 51.310780 -0.413662 50.546196 0.213645 50.116253 -1.076558 50.875046 -1.722543')
    # f130:
    # browse.setFootprint('51.107277 -3.388437 51.544346 -2.074867 50.715931 -1.393089 50.284798 -2.687346 51.107277 -3.388437')
    # d79f:
    # browse.setFootprint('57.555702 -6.213644 57.067524 -7.676043 57.731705 -8.470135 58.227787 -6.987471 57.555702 -6.213644')
    browse.setFootprint(
        '38.152265593 23.711863883 37.627042014 23.544841355 37.522555637 24.208814974 38.047013384 24.380444704 38.152265593 23.711863883')
    print(browse.info())
    # browse.reverse()
    # print "\nreversed:"
    # print browse.info()

    a = +2.3714294305e+01
    b = -5.6014734187e-05
    c = +2.2243454617e-04
    d = -5.1178050636e-10
    e = +1.0500627652e-10
    f = +1.1379650366e-10

    aa = +3.8151240357e+01
    bb = -1.7511127855e-04
    cc = -3.4455233470e-05
    dd = +8.5313922377e-11
    ee = -1.1468841765e-11
    ff = -2.4005047122e-10

    # a=+2.2585357635e+05
    # b=-5.6744087413e+03
    # c=-3.2267980576e+02
    # d=+1.4028012460e+01
    # e=-1.3018328340e+00
    # f=-2.2249585805e+01

    # aa=-1.0117665338e+05
    # bb=-4.4076471186e+02
    # cc=+7.1627498376e+03
    # dd=-4.5751211986e+01
    # ee=+2.0391433814e+00
    # ff=-2.3903772041e+01

    w = 3604
    h = 3426

    centerLat = +3.7837853182e+01
    centerLon = +2.3960911569e+01

    ULXMAP = +7.2456000000e+05
    ULYMAP = +4.2262070000e+06

    # lon, lat
    lamb0, phy0 = browse.SimplifiedLocationModel_to_latLon(1, 1, a, b, c, d, e, f, aa, bb, cc, dd, ee, ff)
    print("0: %s %s" % (lamb0, phy0))
    lamb1, phy1 = browse.SimplifiedLocationModel_to_latLon(1, h, a, b, c, d, e, f, aa, bb, cc, dd, ee, ff)
    print("1: %s %s" % (lamb1, phy1))
    lamb2, phy2 = browse.SimplifiedLocationModel_to_latLon(w, h, a, b, c, d, e, f, aa, bb, cc, dd, ee, ff)
    print("2: %s %s" % (lamb2, phy2))
    lamb3, phy3 = browse.SimplifiedLocationModel_to_latLon(w, 1, a, b, c, d, e, f, aa, bb, cc, dd, ee, ff)
    print("3: %s %s" % (lamb3, phy3))

    print("%s %s %s %s %s %s %s %s %s %s " % (phy0, lamb0, phy1, lamb1, phy2, lamb2, phy3, lamb3, phy0, lamb0))

    parrent = "SCENE 1 092-274 86/05/16 09:22:42 2 X"

    fd = open('coords.txt', 'w')
    fd.write("footprint + center:\n")
    fd.write(browse.getFootprint())
    fd.write("\n%s %s" % (centerLat, centerLon))

    fd.write("\nsimple model:\n")
    fd.write("%s %s %s %s %s %s %s %s %s %s " % (phy0, lamb0, phy1, lamb1, phy2, lamb2, phy3, lamb3, phy0, lamb0))
    fd.write("\ninsert\n")
    lat, lon = formatUtils.utmToLatLon(ULXMAP, ULYMAP, 34, "N")
    fd.write("\n%s %s" % (lat, lon))

    fd.write(
        "\n\npage web:38.152265593 23.711863883 38.047013384 24.380444704 37.522555637 24.208814974 37.627042014 23.544841355 38.152265593 23.711863883")

    fd.close()
