from xml_nodes.sipMessageBuilder import SipMessageBuilder


class alt_EarthObservationResult(SipMessageBuilder):
    this = ["<eop:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</eop:EarthObservationResult>"]

    REPRESENTATION = [
        "<BROWSES></BROWSES>",
        "eop_product"]

    OPTIONAL = []
