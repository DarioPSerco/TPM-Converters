import sys
import traceback

__ACQ_STATION_NAMES = ['ALICE SPRING', 'ATLANTA TEST SITE', 'AUSSAGUEL', 'AUSTRALIA HOBART', 'Adelaide (Australia)',
                       'Agrhymet, Niamey (Nigeria)', 'Aspendale (Australia)', 'BANGKOK', 'BEIJING', 'BEIJING - ERS',
                       'BISHKEK', 'Bedford', 'Berlin', 'Berne (Switzerland)', 'Bolzano (Italy)', 'Brest (France)',
                       'Budapest', 'Buenos Aires, Argentina', 'CORDOBA, ARGENTINA', 'COTOPAXI, ECUADOR',
                       'CUIABA, BRAZIL', 'Cairo (Egypt)', 'Casey, Antartica', 'Centre Meteo Lannion (France)',
                       'Chetumal (Mexico)', 'Copenhagen', 'DLR, Oberpfaffenhofen (Germany)', 'Da-Xing',
                       'Darwin, Australia', 'De Bilt (Holland)', 'Dhaka (Bangladesh)', 'Dharan, Saudi Arabia',
                       'Downsview (Canada)', 'Dummy Station', 'EROs Data Centre Sioux Falls (USA)', 'Edmonton (Canada)',
                       'FAIRBANKS, ALASKA', 'FUCINO STATION', 'Fairbanks Alaska Univ.', 'Farnborough (United Kingdom)',
                       'Funceme, Fortaleza (Brazil)', 'GATINEAU HIGH RATE STATION', 'GATINEAU LOW RATE STATION',
                       'Gatineau', 'Gilmore Creek, Akaska', 'Goddard (USA)', 'Greenbelt MD (USA)', 'Grimstadt (Norway)',
                       'HATOYAMA, JAPAN', 'HONOLULU', 'HYDERABAD', 'Hamburg', 'Hanoi', 'Hartebeestoek, South Africa',
                       'Helsinki', 'Hiroshima (Japan)', 'Hobart, Australia', 'Hong Kong (China)',
                       'INPE, Cashoiera Paulista (Brazil)', 'ISLAMABAD,PAKISTAN', 'ISRAEL', 'ISTAMBUL',
                       'JOHANNESBURG STATION', 'Jeddah, Saudi Arabia', 'KARI (Norway)', 'KHANTY MANSYISK',
                       'KIRUNA STATION', 'KITAB', 'KUALA LUMPUR (Malaysia)', 'KUMAMOTO JAPAN', 'Keelung (Taiwan)',
                       'Kenyan Met Office, Nairobi (Kenya)', 'Kergu (Estonia)', 'Kiyose (Japan)',
                       'Kourou (French Guiana)', 'Krakow (Poland)', 'LIBREVILLE', 'La Reunion', 'La Reunion (France)',
                       'La Spezia (Italy)', 'Lapan, Jakarta (Indonesia)', 'Lasham (United Kingdom)',
                       'Lousiana University. Louisiana USA', 'MALINDI,KENIA', 'MASPALOMAS STATION', 'MATERA', 'MCMURDO',
                       'MIAMI', 'MOSCOW', 'Madrid', 'Magadan', 'Malaysian Met Department, Selangor (Malaysia)',
                       'Manila (Phillipines)', 'Mar Chiquita (Argentina)', 'Marzuq, Libia', 'Matera Telespazio',
                       'NEUSTRELITZ', 'NOAA Wallops Island \xbf Virgina Station', 'NOAA/NESDIS - (USA)',
                       'NORMAN STATION', 'New Dheli', 'Norrkoping (Sweden)', 'Novosibirsk (Russia)', "O'HIGGINS",
                       'Offenbach (Germany)', 'Oslo', 'PARI-PARI', 'PDHS-E', 'PRINCE ALBERT HIGH RATE STATION',
                       'PRINCE ALBERT LOW RATE STATION', 'Palmer Station, Antarctica', 'Paris', 'Perth, Australia',
                       'Poker Plats, Alaska', 'Prague', 'Pretoria', 'Price Albert, Canada',
                       'RAL, Rutherford Appleton Lab. (United Kingdom)', 'RHYAD, SAUDI ARABIA', 'RRSC Nairobi (Kenya)',
                       'Redu (Belgium)', 'Redwood City (USA)', 'Rome', 'SINGAPORE', 'SVALBARD', 'SYOWA, JAPAN',
                       'San Diego, SCR', 'Santa Maria Island', 'Santiago', 'Scanzano', 'Sendai (Japan)', 'Seoul',
                       'Seoul Univ.', 'Spitzbergen (Norway)', 'Spot USA Mobile Station', 'Stennis Space Centre (USA)',
                       'Sydney', 'TAIWAN', 'TROMSOE', 'Taipei (Taiwan)', 'Terranova Bay, Antartica',
                       'Tiksi (Russia, Siberia)', 'Tokay University (Japan)', 'Tokyo University (Japan)', 'Toronto',
                       'Toulouse Test Site (France)', 'Townsville, Australia', 'Traben-Trarbach (Germany)', 'Tripoli',
                       'Troll', 'Tsukaba', 'Tunis', 'ULAN BATOR', 'UNKNOWN', 'University of Dundee (UK)',
                       'University of Rhode Island (USA)', 'University of Texas, Austin, Texas (USA)',
                       'Villafranca (Spain)', 'WEST FREUGH, UK', 'Wellington (New Zealand)']
__ACQ_STATION_2CODE = ['AS', 'AT', 'TO', 'HO', 'AD', 'NM', 'AP', 'TH', 'BJ', 'BE', 'BK', 'BI', 'BL', 'BN', 'BZ', 'BR',
                       'BU', 'BA', 'CA', 'CO', 'CU', 'CR', 'CS', 'LN', 'CM', 'CH', 'OB', 'DX', 'DA', 'DB', 'DK', 'DS',
                       'DV', '__', 'SF', 'EM', 'AF', 'FS', 'UA', 'FB', 'FT', 'GH', 'GS', 'GT', 'NG', 'GD', 'TG', 'GR',
                       'HA', 'HW', 'SE', 'HM', 'HN', 'HB', 'HS', 'HI', 'HT', 'HG', 'CP', 'IS', 'IR', 'TU', 'JO', 'JS',
                       'KA', 'KM', 'KS', 'KB', 'KL', 'KU', 'KG', 'NB', 'KE', 'KY', 'KO', 'KK', 'LI', 'RE', 'LR', 'LZ',
                       'JK', 'LH', 'LS', 'ML', 'MS', 'MA', 'MM', 'MI', 'MW', 'MD', 'MG', 'SL', 'MN', 'MC', 'MZ', 'MT',
                       'NZ', 'NW', 'NE', 'NO', 'ND', 'NK', 'NV', 'TF', 'OF', 'OS', 'IN', 'FR', 'PH', 'PS', 'PL', 'CT',
                       'PT', 'AG', 'PR', 'PO', 'PA', 'RA', 'SA', 'NI', 'RD', 'RW', 'RM', 'SG', 'SV', 'SY', 'SR', 'SM',
                       'ST', 'SZ', 'SN', 'S1', 'S2', 'SP', 'SU', 'SS', 'SD', 'TW', 'TS', 'TP', 'TB', 'TI', 'TY', 'TK',
                       'TT', 'TE', 'TV', 'TC', 'TL', 'TA', 'TJ', 'TN', 'UB', 'XX', 'DD', 'UR', 'UT', 'VF', 'WF', 'WL']

#
SOURCE = 'ACQUISITION_STATIONS_MMMC_SRC.txt'

#
debug = 0


#
#
#
def getNameFromCode2(code):
    name = None
    n = 0
    for item in __ACQ_STATION_2CODE:
        if item == code:
            name = __ACQ_STATION_NAMES[n]
            break
        n += 1
    if name is None:
        raise Exception("2 digit mmmc acquisition station code unknown:%s" % code)
    return name


#
#
#
def getCode2FromName(name):
    code = None
    n = 0
    for item in __ACQ_STATION_NAMES:
        if item == name:
            code = __ACQ_STATION_2CODE[n]
            break
        n += 1
    if code is None:
        raise Exception("mmmc acquisition station name unknown:%s" % name)
    return code


#
#
#
def test():
    code2 = 'FR'
    name = getNameFromCode2(code2)  # esrin?
    print("%s name is:%s" % (code2, name))


#
# read the data.txt file which contains the doc content. Build the 2 list used later in source code above
#
def readSource():
    fd = open(SOURCE, 'r')
    lines = fd.readlines()
    fd.close()

    n = 0
    for line in lines:
        line = line.strip()
        cursor = len(line)
        if debug != 0:
            print("line=%s" % line)

        toks = line.split('\t')
        if len(toks) == 2:
            print("  station[%d] 2code=%s; name:%s" % (n, toks[0], toks[1]))
            __ACQ_STATION_NAMES.append(toks[1])
            __ACQ_STATION_2CODE.append(toks[0])
        else:
            print("  line dont has 2 tokens but:%s; line=%s" % (len(toks), line))

        if len(__ACQ_STATION_NAMES) != len(__ACQ_STATION_2CODE):
            raise Exception("length mismatch")

        n += 1

    print("names:%s" % __ACQ_STATION_NAMES)
    print("2digits:%s" % __ACQ_STATION_2CODE)

    print("length names:%s" % len(__ACQ_STATION_NAMES))
    print("length 2digits:%s" % len(__ACQ_STATION_2CODE))


if __name__ == '__main__':
    try:
        # readSource()

        test()


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
