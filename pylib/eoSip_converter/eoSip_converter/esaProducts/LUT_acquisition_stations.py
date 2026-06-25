import sys
import traceback

__ACQ_STATION_NAMES = ['Budapest (Hungary)', 'Bremerhaven (Germany)', 'Berlin (Germany)', 'Berne (Switzerland)',
                       'Brest (France)', 'Copenhagen (Denmark)', 'CETP Facility (France)', 'De Bilt (Holland)',
                       'University of Dundee (United Kingdom)', 'ESRIN, Frascati (Italy)',
                       'Farnborough (United Kingdom)', 'Fucino (Italy)', 'Grimstadt (Norway)', 'Hamburg (Germany)',
                       'Helsinki (Finland)', 'KARI (Norway)', 'Kiruna ESRANGE (Sweden)', 'Kiruna Salmijarvi (Sweden)',
                       'Krakow (Poland)', 'Centre Meteo Lannion (France)', 'Lasham (United Kingdom)',
                       'La Spezia (Italy)', 'Matera (Italy)', 'Matera direct downlink for Telespazio', 'Madrid (Spain)',
                       'Moscow (Russia)', 'Norrkoping (Sweden)', 'DLR, Neustrelitz (Germany)', 'Offenbach (Germany)',
                       'DLR, Oberpfaffenhofen (Germany)', 'Oslo (Norway)', 'Prague (Czech Republic)',
                       'RAL, Rutherford Appleton Laboratory (United Kingdom)', 'Redu (Belgium)',
                       'Meteo Office Rome (Italy)', 'Santa Maria Island, Azores (Portugal)',
                       'Spitzbergen (Norway) (DLR Portable Station)', 'Svalbard (Norway)', 'Scanzano (Italy)',
                       'Tiksi (Russia, Siberia)', 'Tromsoe Satellite Station (Norway)', 'Toulouse (France)',
                       'Traben-Trarbach (Germany)', 'Toulouse Test Site (France)', 'Istanbul (Turkey)',
                       'West Freugh (United Kingdom)', 'Villafranca (Spain)', 'Cairo (Egypt)',
                       'Hartebeesthoek South Africa)', 'Johannesburg (South Africa)', 'Libreville (Gabon)',
                       'La Reunion (France)', 'Malindi', 'Maspalomas (Spain)', 'Marzuq (Lybya)',
                       'Agrhymet, Niamey (Nigeria)', 'Nairobi (Kenya)', 'Pretoria (South Africa)', 'Tunis (Tunisia)',
                       'Tripoli (Lybia)', 'Casey (Australia)', 'McMurdo (USA)', "O'Higgins (Germany)", 'Palmer (USA)',
                       'Syowa (Japan)', 'Terranova Bay (Italy)', 'Troll (Norway)', 'Bangkok (Thailand)',
                       'Beijing (China)', 'Bishkek, Kyrgystan', 'Chung-Li (Taiwan)', 'Da-Xing-An-Ling',
                       'Dhaka (Bangladesh)', 'Dharan (Saudi Arabia)', 'Hanoi (Vietnam)', 'Hatoyama (Japan)',
                       'Hiroshima (Japan)', 'Hong Kong (China)', 'Hyderabad (India) - former Shadnadar',
                       'Islamabad (Pakistan)', 'Jeddah (Saudi Arabia)', 'Khanty-Mansiysk (Russia)', 'Keelung (Taiwan)',
                       'Kitab (Russia)', 'Kiyose (Japan)', 'Kumamoto (Japan)', 'Lapan, Jakarta (Indonesia)',
                       'MACRES, Malaysian RS Centre, Kuala Lumpur (Malaysia)', 'Magadan (Russia)',
                       'Malaysian Met Department, Selangor (Malaysia)', 'Manila (Philippines)', 'New Dheli (India)',
                       'Novosibirsk (Russia)', 'Pari Pari (Indonesia)', 'Riyadh (Saudi Arabia)', 'Sendai (Japan)',
                       'Seoul: National University (Korea)', 'Seoul:KMS (Korea)', 'Singapore', 'Taipei (Taiwan)',
                       'Tel Aviv (Israel)', 'Tokyo:Tokyo University (Japan)', 'Tsukaba (Japan)', 'Ulan Bator, Mongolia',
                       'Adelaide (Australia)', 'Alice Spring (Australia)', 'Aspendale (Australia) ',
                       'Darwin (Australia)', 'Hobart (Australia)', 'Hobart (Australia) NOAA', 'Honolulu (USA)',
                       'Perth (Australia)', 'Sydney (Australia)', 'Townsville (Australia)', 'Wellington (New Zealand)',
                       'Poker Plats, Alaska', 'Atlanta Test Site (USA)',
                       'Bedford Institute of Oceanography Nova Scotia (Canada)', 'Chetumal (Mexico)',
                       'Downsview (Canada)', 'Edmonton (Canada)', 'NOAA Gilmore Creek Alaska Station',
                       'Fairbanks Alaska SAR Facility', 'University of Alaska, (USA)', 'Goddard (USA)',
                       'Gatineau (Canada)', 'Gatineau (Canada) - high rate', 'Gatineau (Canada) - low rate',
                       'Baton Rouge, Louisiana State University, Louisiana (USA)', 'University of Miami, Florida (USA)',
                       'NOAA/NESDIS - (USA)', 'Norman, Oklahoma (USA)', 'NOAA Wallops Island Virginia Station',
                       'Prince Albert (Canada)', 'Prince Albert (Canada)ERS high rate',
                       'Prince Albert (Canada)ERS low rate', 'Poker Flat Research Range (Canada)', 'Redwood City (USA)',
                       'UCSD, SCR Scripps Institute of Oceanography, San Diego, California',
                       'EROS Data Center Sioux Falls, South Dakota (USA)', 'Stennis Space Centre (USA)',
                       'Spot USA Mobile Station', 'Greenbelt MD (USA)', 'Toronto (Canada)',
                       'University of Texas, Austin, Texas (USA)', 'University of Rhode Island (USA)',
                       'Buenos Aires (Argentina) ', 'Cordoba (Argentina)', 'Cotopaxi (Equador)', 'Cuiaba (Brazil)',
                       'FUNCEME, Fortaleza (Brazil)', 'INPE, Cachoeira Paulista (Brazil)', 'Kourou (French Guyana)',
                       'Mar Chiquita (Argentina)', 'Santiago (Chile)', 'Kerguelen (France, Indian Ocean)',
                       'Unknown TBD', 'Unknown code', 'Station Not Relevant', 'Special value for Empty']
__ACQ_STATION_2CODE = ['BU', 'BH', 'BL', 'BN', 'BR', 'CH', 'CT', 'DB', 'DD', 'FR', 'FB', 'FS', 'GR', 'HM', 'HS', 'KA',
                       'KS', 'KS', 'KK', 'LN', 'LH', 'LZ', 'MA', 'MT', 'MD', 'MW', 'NK', 'NZ', 'OF', 'OB', 'OS', 'PR',
                       'RA', 'RD', 'RM', 'SM', 'SP', 'SV', 'SZ', 'TI', 'TS', 'TO', 'TC', 'TE', 'TU', 'WF', 'VF', 'CR',
                       'HB', 'JO', 'LI', 'LR', 'ML', 'MS', 'MZ', 'NM', 'NB', 'PO', 'TN', 'TL', 'CS', 'MM', 'TF', 'PL',
                       'SY', 'TB', 'TA', 'TH', 'BJ or BE', 'BK', 'TW', 'DX', 'DK', 'DS', 'HN', 'HA', 'HI', 'HG', 'SE',
                       'IS', 'JS', 'KM', 'KG', 'KB', 'KY', 'KU', 'JK', 'KL', 'MG', 'SL', 'MN', 'ND', 'NV', 'IN', 'SA',
                       'SN', 'S2', 'S1', 'SG', 'TP', 'IR', 'TK', 'TJ', 'UB', 'AD', 'AS', 'AP', 'DA', 'HO', 'HT', 'HW',
                       'PT', 'SD', 'TV', 'WL', 'AG ', 'AT ', 'BI', 'CM', 'DV', 'EM', 'NG', 'AF', 'UA', 'GD', 'GT', 'GH',
                       'GS', 'LS', 'MI', 'NE', 'NO', 'NW', 'PA', 'PH', 'PS', 'AG', 'RW', 'SR', 'SF', 'SS', 'SU', 'TG',
                       'TT', 'UT', 'UR', 'BA', 'CA', 'CO', 'CU', 'FT', 'CP', 'KO', 'MC', 'ST', 'KE', 'GE', 'XX', 'YY',
                       'ZZ']
__ACQ_STATION_3CODE = ['BUD', 'BRH', 'BRL', 'BRN', 'BRS', 'CPH', 'CTP', 'DBH', 'DDE', 'ESR', 'FRB', 'FUI', 'GRS', 'HAM',
                       'HLS', 'KAR', 'KSE', 'KSS', 'KRK', 'LNN', 'LHM', 'LSZ', 'MTI', 'MTN', 'MAD', 'MSW', 'NRK', 'NSG',
                       'OFB', 'OPF', 'OSL', 'PRG', 'RAL', 'RDU', 'ROM', 'SMR', 'SPB', 'SGS', 'SZ', 'TKS', 'TRS', 'TOU',
                       'TTC', 'TTE', 'IST', 'WFR', 'VFR', 'CRO', 'HBK', 'JOS', 'LBG', 'REP', 'MLD', 'MPS', 'MZQ', 'NMY',
                       'NRB', 'PTO', 'TNS', 'TRI', 'CSY', 'MMR', 'OHG', 'PLM', 'SYW', 'TNB', 'TRA', 'BKT', 'BJG',
                       'BSK or BSH', 'TWN', 'DAX', 'DHK', 'DSA', 'HNO', 'HAJ', 'HIS', 'HKG', 'HYD', 'ISp', 'JSA', 'KMY',
                       'KLG', 'KTB', 'KYS', 'KUJ', 'JKL', 'KLM', 'MGD', 'SLG', 'MNL', 'NWD', 'NVB', 'DKI', 'RSA', 'SND',
                       'SNU', 'KMS', 'SGP', 'TPE', 'ISR', 'TK1', 'TSJ', 'ULB', 'ADL', 'ASA', 'APD', 'DAR', 'HOA', 'HBT',
                       'HWH', 'PTH', 'SYD', 'TSV', 'WLT', 'AGP', 'ATL', 'BDF', 'MEX', 'DWV', 'EDM', 'NGC', 'ASF', 'FAU',
                       'GOD', 'GAT', 'GAT', 'GAT', 'LSU', 'MIM', 'NOA', 'NOM', 'NOW', 'PAS', 'PAS', 'PAS', 'AGS', 'RWC',
                       'SCR', 'SFL', 'SSC', 'SUM', 'TGM', 'TRT', 'UTA', 'URI', 'BAA', 'COA', 'CPE', 'CUB', 'FTB', 'CPA',
                       'KOU', 'MCH', 'STG', 'KEG', 'GEP', 'XXX', 'YYY', 'ZZZ']
__ACQ_STATION_ZONE = ['EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE',
                      'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE',
                      'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE',
                      'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE',
                      'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE', 'EUROPE',
                      'EUROPE', 'EUROPE', 'Africa', 'Africa', 'Africa', 'Africa', 'Africa', 'Africa', 'Africa',
                      'Africa', 'Africa', 'Africa', 'Africa', 'Africa', 'Africa', 'Antartica', 'Antartica', 'Antartica',
                      'Antartica', 'Antartica', 'Antartica', 'Antartica', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia',
                      'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia',
                      'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia',
                      'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Asia', 'Australia', 'Australia',
                      'Australia', 'Australia', 'Australia', 'Australia', 'Australia', 'Australia', 'Australia',
                      'Australia', 'Australia', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'North America', 'North America', 'North America',
                      'North America', 'North America', 'South America', 'South America', 'South America',
                      'South America', 'South America', 'South America', 'South America', 'South America',
                      'South America', 'Others', 'Others', 'Others', 'Others', 'Others']

#
SOURCE = 'ACQUISITION_STATIONS_SRC.txt'

#
debug = 0


#
#
#
def getNameFromCode2(code2):
    name = None
    n = 0
    for item in __ACQ_STATION_2CODE:
        if item == code2:
            name = __ACQ_STATION_NAMES[n]
            break
        n += 1
    if name is None:
        raise Exception("2 digit acquisition station code unknown:%s" % code2)
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
        raise Exception("acquisition station name unknown:%s" % name)
    return code


#
#
#
def getCode3FromCode2(code2):
    code3 = None
    n = 0
    for item in __ACQ_STATION_2CODE:
        if item == code2:
            code3 = __ACQ_STATION_3CODE[n]
            break
        n += 1
    if code3 is None:
        raise Exception("2 digit acquisition station code unknown:%s" % code2)
    return code3


#
#
#
def test():
    code3 = 'BH'
    name = getNameFromCode2(code3)  # Bremerhaven (Germany)
    print("%s name is:%s" % (code3, name))


#
# read the data.txt file which contains the doc content. Build the 4 list used later in source code above
#
def readSource():
    fd = open(SOURCE, 'r')
    lines = fd.readlines()
    fd.close()

    zone = ''
    n = 0
    for line in lines:
        line = line.strip()
        cursor = len(line)
        if debug != 0:
            print("line=%s" % line)
        if line[0] == '#':
            zone = line[1:]
            if debug != 0:
                print(" zone:%s" % zone)
        else:
            toks = line.split('\t')
            if len(toks) == 3:
                print("  station[%d] name=%s; 2dg:%s; 3dg:%s" % (n, toks[0], toks[1], toks[2]))
                __ACQ_STATION_NAMES.append(toks[0])
                __ACQ_STATION_2CODE.append(toks[1])
                __ACQ_STATION_3CODE.append(toks[2])
                __ACQ_STATION_ZONE.append(zone)
            else:
                print("  line dont has 3 tokens but:%s; line=%s" % (len(toks), line))

            if len(__ACQ_STATION_ZONE) != len(__ACQ_STATION_NAMES) or len(__ACQ_STATION_NAMES) != len(
                    __ACQ_STATION_2CODE) or len(__ACQ_STATION_2CODE) != len(__ACQ_STATION_3CODE):
                raise Exception("length mismatch")

            n += 1

    print("\n\n\nzones:%s" % __ACQ_STATION_ZONE)
    print("names:%s" % __ACQ_STATION_NAMES)
    print("2digits:%s" % __ACQ_STATION_2CODE)
    print("3digits:%s" % __ACQ_STATION_3CODE)

    print("length zone:%s" % len(__ACQ_STATION_ZONE))
    print("length names:%s" % len(__ACQ_STATION_NAMES))
    print("length 2digits:%s" % len(__ACQ_STATION_2CODE))
    print("length 3digits:%s" % len(__ACQ_STATION_3CODE))


if __name__ == '__main__':
    try:
        # readSource()

        test()


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
