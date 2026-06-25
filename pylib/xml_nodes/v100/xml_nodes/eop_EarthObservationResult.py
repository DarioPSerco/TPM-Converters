from .sipMessageBuilder import SipMessageBuilder


class eop_EarthObservationResult(SipMessageBuilder):
    this = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    # this_SAR = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    # this_ALT = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    # this_OPT = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    REPRESENTATION = ["<BROWSES></BROWSES>",
                      "eop_product"]
