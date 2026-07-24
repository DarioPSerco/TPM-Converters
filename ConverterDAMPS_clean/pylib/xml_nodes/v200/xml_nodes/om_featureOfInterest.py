from .sipMessageBuilder import SipMessageBuilder


class om_featureOfInterest(SipMessageBuilder):
    this = ["<om:featureOfInterest>"]

    REPRESENTATION = ["gin_Footprint"]

    OPTIONAL = ["gin_Footprint"]
