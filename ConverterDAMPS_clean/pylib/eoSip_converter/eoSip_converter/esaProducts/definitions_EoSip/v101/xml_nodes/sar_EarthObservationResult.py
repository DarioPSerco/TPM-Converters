from .sipMessageBuilder import SipMessageBuilder


class sar_EarthObservationResult(SipMessageBuilder):
    this = ["<sar:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</sar:EarthObservationResult>"]

    REPRESENTATION = ["<BROWSES></BROWSES>",
                      "eop_product"]

    OPTIONAL = []
