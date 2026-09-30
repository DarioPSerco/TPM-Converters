from .sipMessageBuilder import SipMessageBuilder


class eop_metaDataProperty(SipMessageBuilder):
    this = ["<eop:metaDataProperty>", "</eop:metaDataProperty>"]

    REPRESENTATION = ["gin_EarthObservationMetaData"]
