from xml_nodes.sipMessageBuilder import SipMessageBuilder


class gml_LinearRing(SipMessageBuilder):
    this = ["<gml:LinearRing gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</gml:LinearRing>"]

    REPRESENTATION = ["<gml:posList>@coordList@</gml:posList>"]
