from .sipMessageBuilder import SipMessageBuilder


class SIPInfo30(SipMessageBuilder):
    this = [
        """<sip:SIPInfo xmlns:sip="http://www.eo.esa.int/SIP/sipInfo/3.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="3.0" xsi:schemaLocation="http://www.eo.esa.int/SIP/sipInfo/3.0">""",
        "</sip:SIPInfo>"]

    REPRESENTATION = ["<SIPCreator>@SIPCreator@</SIPCreator>",
                      "<SIPCreationTime>@generationTime@</SIPCreationTime>",
                      "<SIPVersion>@SIPVersion@</SIPVersion>",
                      "<SIPSoftwareName>@SIPSoftwareName@</SIPSoftwareName>",
                      "<SIPSoftwareVersion>@SIPSoftwareVersion@</SIPSoftwareVersion>",
                      "<sip:SIPChangeLog>@SIPChangeLog@</sip:SIPChangeLog>",
                      "<sip:SIPSpecNameVersion>@SIPSpecNameVersion@</sip:SIPSpecNameVersion>"
                      ]

    OPTIONAL = ["SIPSoftwareName>@SIPSoftwareName@</SIPSoftwareName>",
                "SIPSoftwareVersion>@SIPSoftwareVersion@</SIPSoftwareVersion>"]
