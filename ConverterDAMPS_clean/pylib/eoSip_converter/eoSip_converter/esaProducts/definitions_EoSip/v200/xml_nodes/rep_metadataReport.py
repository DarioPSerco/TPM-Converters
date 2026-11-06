import logging

from eoSip_converter.esaProducts import metadata
from eoSip_converter.esaProducts.metadata import Metadata
from .sipMessageBuilder import SipMessageBuilder


class rep_metadataReport(SipMessageBuilder):
    this = [
        "<rep:metadataReport version=\"1.2\" xsi:schemaLocation=\"http://ngeo.eo.esa.int/schema/metadataReport IF-ngEO-MetadataReport.xsd\" xmlns:rep=\"http://ngeo.eo.esa.int/schema/metadataReport\" xmlns:opt=\"http://www.opengis.net/opt/2.0\" xmlns:ssp=\"http://www.opengis.net/eop/2.0\" xmlns:lmb=\"http://www.opengis.net/eop/2.0\" xmlns:atm=\"http://www.opengis.net/eop/2.0\" xmlns:alt=\"http://www.opengis.net/eop/2.0\" xmlns:eop=\"http://www.opengis.net/eop/2.0\" xmlns:sar=\"http://www.opengis.net/eop/2.0\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</rep:metadataReport>"]

    this_SAR = [
        "<rep:metadataReport version=\"1.2\" xsi:schemaLocation=\"http://ngeo.eo.esa.int/schema/metadataReport IF-ngEO-MetadataReport.xsd\" xmlns:rep=\"http://ngeo.eo.esa.int/schema/metadataReport\" xmlns:opt=\"http://www.opengis.net/opt/2.0\" xmlns:ssp=\"http://www.opengis.net/eop/2.0\" xmlns:lmb=\"http://www.opengis.net/eop/2.0\" xmlns:atm=\"http://www.opengis.net/eop/2.0\" xmlns:alt=\"http://www.opengis.net/eop/2.0\" xmlns:eop=\"http://www.opengis.net/eop/2.0\" xmlns:sar=\"http://www.opengis.net/eop/2.0\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</rep:metadataReport>"]

    this_ALT = [
        "<rep:metadataReport version=\"1.2\" xsi:schemaLocation=\"http://ngeo.eo.esa.int/schema/metadataReport IF-ngEO-MetadataReport.xsd\" xmlns:rep=\"http://ngeo.eo.esa.int/schema/metadataReport\" xmlns:opt=\"http://www.opengis.net/opt/2.0\" xmlns:ssp=\"http://www.opengis.net/eop/2.0\" xmlns:lmb=\"http://www.opengis.net/eop/2.0\" xmlns:atm=\"http://www.opengis.net/eop/2.0\" xmlns:alt=\"http://www.opengis.net/eop/2.0\" xmlns:eop=\"http://www.opengis.net/eop/2.0\" xmlns:sar=\"http://www.opengis.net/eop/2.0\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</rep:metadataReport>"]

    this_OPT = [
        "<rep:metadataReport version=\"1.2\" xsi:schemaLocation=\"http://ngeo.eo.esa.int/schema/metadataReport IF-ngEO-MetadataReport.xsd\" xmlns:rep=\"http://ngeo.eo.esa.int/schema/metadataReport\" xmlns:opt=\"http://www.opengis.net/opt/2.0\" xmlns:ssp=\"http://www.opengis.net/eop/2.0\" xmlns:lmb=\"http://www.opengis.net/eop/2.0\" xmlns:atm=\"http://www.opengis.net/eop/2.0\" xmlns:alt=\"http://www.opengis.net/eop/2.0\" xmlns:eop=\"http://www.opengis.net/eop/2.0\" xmlns:sar=\"http://www.opengis.net/eop/2.0\" xmlns:gml=\"http://www.opengis.net/gml/3.2\" xmlns:om=\"http://www.opengis.net/om/2.0\" xmlns:ows=\"http://www.opengis.net/ows/2.0\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">",
        "</rep:metadataReport>"]

    REPRESENTATION = ["<rep:responsibleOrgName>@responsible@</rep:responsibleOrgName>",
                      "<rep:reportType>@reportType@</rep:reportType>",
                      "<rep:dateTime>@generationTime@</rep:dateTime>",
                      "eop_EarthObservation"]

    REPRESENTATION_SAR = ["<rep:responsibleOrgName>@responsible@</rep:responsibleOrgName>",
                          "<rep:reportType>@reportType@</rep:reportType>",
                          "<rep:dateTime>@generationTime@</rep:dateTime>",
                          "sar_EarthObservation"]

    REPRESENTATION_ALT = ["<rep:responsibleOrgName>@responsible@</rep:responsibleOrgName>",
                          "<rep:reportType>@reportType@</rep:reportType>",
                          "<rep:dateTime>@generationTime@</rep:dateTime>",
                          "alt_EarthObservation"]

    REPRESENTATION_OPT = ["<rep:responsibleOrgName>@responsible@</rep:responsibleOrgName>",
                          "<rep:reportType>@reportType@</rep:reportType>",
                          "<rep:dateTime>@generationTime@</rep:dateTime>",
                          "opt_EarthObservation"]

    FIELDS = ['responsible', 'reportType', 'generationTime']

    MANDATORY = ['responsible', 'reportType', 'generationTime']

    def test(self):
        # set minumum metadata classe
        meta = Metadata()
        meta.setOtherInfo("TYPOLOGY_SUFFIX", "EOP")
        meta.setMetadataPair(metadata.METADATA_PRODUCTNAME, 'product_name')
        meta.setMetadataPair(metadata.METADATA_PACKAGENAME, 'package_name')
        #
        # print "metadata dir:" % (dir(meta))
        meta.setMetadataPair(metadata.METADATA_START_DATE, '20021023')
        # meta.alterMetadataMaping('href', metadata.METADATA_PACKAGENAME)
        # meta.alterMetadataMaping('111', metadata.METADATA_ORBIT)
        mess = self.buildMessage(meta, "rep.metadataReport")
        print("message:%s" % mess)

        print("metadata mapping altered?:%s" % (meta.isMetadataMapingAltered()))

        return mess


if __name__ == '__main__':
    print("start")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('example')
    try:
        c = rep_metadataReport()
        mess = c.test()

        fd = open("./sipProductReport.xml", "w")
        fd.write(mess)
        fd.close()
        print("message written in file:%s" % fd)
    except Exception as err:
        log.exception('Error from throws():')
