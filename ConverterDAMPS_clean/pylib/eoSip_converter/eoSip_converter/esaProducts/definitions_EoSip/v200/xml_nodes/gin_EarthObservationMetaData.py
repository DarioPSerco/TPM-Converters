# from esaProducts.definitions_EoSip.sipMessageBuilder import SipMessageBuilder
from .sipMessageBuilder import SipMessageBuilder


class gin_EarthObservationMetaData(SipMessageBuilder):
    this = ["<gin:EarthObservationMetaData>", "</gin:EarthObservationMetaData>"]

    REPRESENTATION = ["<eop:identifier>@identifier@</eop:identifier>",
                      "<eop:doi>@doi@</eop:doi>",
                      "<eop:parentIdentifier>@parentIdentifier@</eop:parentIdentifier>",
                      "<eop:acquisitionType>@acquisitionType@</eop:acquisitionType>",
                      "<eop:productType>@productType@</eop:productType>",
                      "<eop:status>@status@</eop:status>",
                      "eop_downlinkedTo",
                      "<eop:productQualityDegradationQuotationMode>@productQualityDegradationQuotationMode@</eop:productQualityDegradationQuotationMode>",
                      "<eop:productQualityStatus>@productQualityStatus@</eop:productQualityStatus>",
                      "<eop:productQualityDegradationTag>@productQualityDegradationTag@</eop:productQualityDegradationTag>",
                      "<eop:productQualityReportURL>@productQualityReportURL@</eop:productQualityReportURL>",
                      "eop_processing",
                      "<gin:missionPhase>@missionphase@</gin:missionPhase>",
                      "<LOCAL_ATTR></LOCAL_ATTR>"]

    OPTIONAL = ["<eop:doi>@doi@</eop:doi>",
                "<eop:productQualityStatus>@productQualityStatus@</eop:productQualityStatus>",
                "<eop:productQualityDegradationTag>@productQualityDegradationTag@</eop:productQualityDegradationTag>",
                "<eop:productQualityReportURL>@productQualityReportURL@</eop:productQualityReportURL>",
                "eop_downlinkedTo", ]
