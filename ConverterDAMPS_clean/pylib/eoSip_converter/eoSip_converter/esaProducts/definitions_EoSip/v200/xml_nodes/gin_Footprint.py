from .sipMessageBuilder import SipMessageBuilder


class gin_Footprint(SipMessageBuilder):
    this = ["<gin:Footprint gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</gin:Footprint>"]

    REPRESENTATION = ["<eop:multiExtentOf/>",
                      "<gin:groundTrack>",
                      "<gml:MultiCurve gml:id=\"@gmlId@_$$getNextCounter()$$\">",
                      "<gml:curveMember>",
                      "<gml:LineString gml:id=\"@gmlId@_$$getNextCounter()$$\">",
                      "<gml:posList>@coordList@</gml:posList>",
                      "</gml:LineString>",
                      "</gml:curveMember>",
                      "</gml:MultiCurve>",
                      "</gin:groundTrack>"]
# "</eop:multiExtentOf>"]
