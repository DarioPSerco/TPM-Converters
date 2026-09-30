#
# utilities methos that verify footprint
#
#
#

from eoSip_converter.esaProducts.browseImage import BrowseImage


#
# footprint: footprint to be tested
# param: descending: boolean
#
def verifyFootprint(footprint, descending):
    # test number of coords: 5 pair (so 10)
    n = len(str(footprint).strip().split(' '))
    if n != 10:
        raise Exception("Footprint '%s' has wrong number of token, not 10 but:%s" % (footprint, n))

    # test CCW
    browseIm = BrowseImage()
    browseIm.setFootprint(footprint)
    browseIm.calculateBoondingBox()
    if not browseIm.testIsCCW():
        raise Exception("Footprint is not CCW: '%s'" % footprint)

    # test first point: top left for descending. bottom right for ascending
    if descending:
        if not browseIm.testFirstPointTopLeft():
            raise Exception("Footprint descending first point is not top-left: '%s'" % footprint)
    else:
        if not browseIm.testFirstPointBottomRight():
            raise Exception("Footprint ascending first point is not bottom-right: '%s'" % footprint)
