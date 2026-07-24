from xml_nodes.sipMessageBuilder import SipMessageBuilder


class gml_curveMember(SipMessageBuilder):
    this = ["<gml:curveMember>", "</gml:curveMember>"]

    REPRESENTATION = ["<gml:LineString gml:id=\"@gmlId@_$$getNextCounter()$$\">",
                      "<gml:posList>@coordList@</gml:posList>",
                      "</gml:LineString>"]
