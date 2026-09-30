# from esaProducts.definitions_EoSip.sipMessageBuilder import SipMessageBuilder
from .sipMessageBuilder import SipMessageBuilder


class eop_EarthObservationMetaData(SipMessageBuilder):
    this = ["<eop:EarthObservationMetaData>", "</eop:EarthObservationMetaData>"]

    REPRESENTATION = ["<eop:identifier>@identifier@</eop:identifier>",
                      "<eop:doi>@doi@</eop:doi>",
                      "<eop:parentIdentifier>@parentIdentifier@</eop:parentIdentifier>",
                      "<eop:acquisitionType>@acquisitionType@</eop:acquisitionType>",
                      "<eop:productType>@productType@</eop:productType>",
                      "<eop:status>@status@</eop:status>",
                      "eop_downlinkedTo",
                      "<eop:productQualityStatus>@productQualityStatus@</eop:productQualityStatus>",
                      "<eop:productQualityDegradation uom=\"%\">@productQualityDegradation@</eop:productQualityDegradation>",
                      "<eop:productQualityDegradationTag>@productQualityDegradationTag@</eop:productQualityDegradationTag>",
                      "<eop:productQualityReportURL>@productQualityReportURL@</eop:productQualityReportURL>",
                      "eop_processing",
                      "<LOCAL_ATTR></LOCAL_ATTR>"]

    OPTIONAL = ["<eop:doi>@doi@</eop:doi>",
                "<eop:productQualityStatus>@productQualityStatus@</eop:productQualityStatus>",
                "<eop:productQualityDegradation uom=\"%\">@productQualityDegradation@</eop:productQualityDegradation>",
                "<eop:productQualityDegradationTag>@productQualityDegradationTag@</eop:productQualityDegradationTag>",
                "<eop:productQualityReportURL>@productQualityReportURL@</eop:productQualityReportURL>"
                ]
