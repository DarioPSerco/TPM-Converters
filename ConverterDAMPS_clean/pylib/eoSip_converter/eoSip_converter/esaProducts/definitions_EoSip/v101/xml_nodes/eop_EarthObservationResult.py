from .sipMessageBuilder import SipMessageBuilder


class eop_EarthObservationResult(SipMessageBuilder):
    this = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    REPRESENTATION = ["<BROWSES></BROWSES>",
                      "eop_product"]

    OPTIONAL = ["<BROWSES></BROWSES>"]
