from xml_nodes.sipMessageBuilder import SipMessageBuilder


class opt_EarthObservationResult(SipMessageBuilder):
    this = ["<opt:EarthObservationResult gml:id=\"@gmlId@_$$getNextCounter()$$\">", "</opt:EarthObservationResult>"]

    REPRESENTATION = [
        "<BROWSES></BROWSES>",
        "eop_product",
        "<opt:cloudCoverPercentage uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@cloudCoverPercentage@</opt:cloudCoverPercentage>",
        "<opt:cloudCoverPercentageAssessmentConfidence uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@cloudCoverPercentageAssessmentConfidence@</opt:cloudCoverPercentageAssessmentConfidence>",
        "<opt:cloudCoverPercentageQuotationMode uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@cloudCoverPercentageQuotationMode@</opt:cloudCoverPercentageQuotationMode>",
        "<opt:snowCoverPercentage uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentage@</opt:snowCoverPercentage>",
        "<opt:snowCoverPercentageAssessmentConfidence uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentageAssessmentConfidence@</opt:snowCoverPercentageAssessmentConfidence>",
        "<opt:snowCoverPercentageQuotationMode uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentageQuotationMode@</opt:snowCoverPercentageQuotationMode>"]

    OPTIONAL = [
        "<opt:cloudCoverPercentageAssessmentConfidence uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@cloudCoverPercentageAssessmentConfidence@</opt:cloudCoverPercentageAssessmentConfidence>",
        "<opt:cloudCoverPercentageQuotationMode uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@cloudCoverPercentageQuotationMode@</opt:cloudCoverPercentageQuotationMode>",
        "<opt:snowCoverPercentage uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentage@</opt:snowCoverPercentage>",
        "<opt:snowCoverPercentageAssessmentConfidence uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentageAssessmentConfidence@</opt:snowCoverPercentageAssessmentConfidence>",
        "<opt:snowCoverPercentageQuotationMode uom=\"$$getValidValue('UNIT_PERCENTAGE')$$\">@snowCoverPercentageQuotationMode@</opt:snowCoverPercentageQuotationMode>"]
