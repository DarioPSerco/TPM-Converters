#!/usr/bin/env python
#
# 
# Lavaux Gilles 2013
#
#
import decimal
import math
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

monthDict = {1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN', 7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT',
             11: 'NOV', 12: 'DEC'}
monthDict2 = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
              'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}

DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_DATE_PATTERN_NOZ = "%Y-%m-%dT%H:%M:%S"
DEFAULT_DATE_PATTERN_MSEC = "%Y-%m-%dT%H:%M:%S.000Z"

# also in sipBuilder
VALUE_NOT_PRESENT = "CONVERTER_NOT-PRESENT"

debug = 0


#
# return a float decimal part with length == paddingLength digits with no representation error. the 0.1 problem
#
# value: like 10.23
# - with paddingLength = 3 returns 230
#
def formatFloatDecimalNoRepresentationError(value, paddingLength):
    # avoid representation error, by parsing as a string as some point, then cut decimal
    mult = math.pow(10, 3)
    sValueMult = "%d" % int(value * mult)
    if sValueMult == '0':
        return leftPadString(sValueMult, paddingLength, '0')
    res = sValueMult[-paddingLength:]
    if debug != 0:
        print((" formatFloatDecimalNoRepresentationError of value %s with %s digit: sValueMult=%s; res=%s" % (
        value, paddingLength, sValueMult, res)))
    return res

    """theMill = abs(value - int(value)) * mult
    #vv=int(value*mult)
    #theMill2 = vv


    sTheMill = "%s" % theMill
    if DEBUG !=0:
        print("formatFloatDecimalNoRepresentationError sTheMill=%s; theMill2=%s" % (sTheMill, theMill2))
    pos = sTheMill.find('.')
    if pos > 0:
        sTheMill = sTheMill[0:pos]
    if DEBUG != 0:
        print("formatFloatDecimalNoRepresentationError  sTheMill int part=%s" % sTheMill)
    sTheMillOk = rightPadString(sTheMill, paddingLength, '0')
    if DEBUG != 0:
        print("formatFloatDecimalNoRepresentationError sTheMillOk=%s" % sTheMillOk)
    return sTheMillOk"""


#
#  MPH/SPH products: convert number like : +0049648227<10-6degE>
#
#
def mphEeeToNumber(s):
    print("mphEeeToNumber:%s" % s)
    s = s.replace('<10', 'e')
    s = s.replace('degE>', '')
    s = s.replace('degN>', '')
    print(" mphEeeToNumber stipped s:%s" % s)
    return EEEtoNumber(s)


#
#  MPH/SPH products: convert like like 17-NOV-2003 07:39:19.493783 into 2003-11-17T07:39:19.49Z
#
#
def mphFormatDate(s, msecPrecision=2):
    print("mphFormatDate:%s" % s)

    pos = s.find('.')
    if pos > 0:
        s = s[0:pos + msecPrecision + 1]

    toks = s.split(' ')
    yToks = toks[0].split('-')

    s = "%s-%s-%sT%s" % (yToks[2], yToks[1], yToks[0], toks[1])

    pos = s.find('Z')
    if pos < 0:
        s = s + "Z"
    # pos = s.find('T')
    # if pos < 0:
    #    s=s.replace(' ','T')
    print(" mphFormatDate stipped s:%s" % s)
    return s


#
# return the basename of a file (remove the path)
#
def basename__NOT_USED(path):
    if debug:
        print("basename:%s" % path)
    p = path.replace('\\', '/')
    if debug:
        print("basename 1:%s" % p)
    pos = p.rfind('/')
    if pos > 0:
        return p[pos + 1:]
    else:
        return None


#
# return the dirname of a file (the path)
#
def dirname__NOT_USED(path):
    if debug:
        print(" dirname on '%s'" % path)
    p = path.replace('\\', '/')
    if debug:
        print(" dirname p='%s'" % p)
    pos = p.rfind('/')
    if pos > 0:
        return path[0:pos]
    else:
        return None


#
# get file extension: .xxx part of the basename
#
def getFileExtension(path):
    if debug:
        print(" getFileExtension on '%s'" % path)
    pos = os.path.basename(path).find('.')
    if pos > 0:
        return os.path.basename(path)[(pos + 1):]
    else:
        return None


#
#
#
def removeFileExtension(path):
    pos = os.path.basename(path).find('.')
    if pos > 0:
        return os.path.basename(path)[0:pos]
    else:
        return path


#
# wrs for longitude (L Festa suggestion): 0 --> 360 degree
#
def absoluteLongitude(lon):
    return 180 + lon


#
# wrs for latitude (L Festa suggestion): colatitude: 90 - latitude
#
def coLatitude(lat):
    return 90 - lat


#
# left pad a string to specified length
#
def leftPadString(s, size, pad):
    result = s
    while len(result) < size:
        result = pad + result
    return result


#
# right pad a string to specified length
#
def rightPadString(s, size, pad):
    result = s
    while len(result) < size:
        result = result + pad
    return result


#
# degree minute seconde to degree decimal
#
def dms2degdec(dd, mm, ss):
    return dd + mm / 60 + ss / 3600


#
# degree decimal to degree minute seconde
#
def decdeg2dms(dd):
    dd = float(dd)
    is_positive = dd >= 0
    dd = abs(dd)
    minutes, seconds = divmod(dd * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    degrees = degrees if is_positive else -degrees
    return degrees, minutes, seconds


#
# degree decimal to degree minute seconde
#
def decdeg2dmsString(dd, degChar='\'', sign=' '):
    dd = float(dd)
    if dd < 0:
        sign = "-"
    is_positive = dd >= 0
    dd = abs(dd)
    minutes, seconds = divmod(dd * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    degrees = degrees if is_positive else -degrees
    return "%s%s%s%s%s%s'" % (sign, int(degrees), degChar, int(minutes), degChar, int(seconds))


#
# convert UTL to lat lon
#
def utmToLatLon(easting, northing, zone, northernHemisphere=True):
    if northernHemisphere == 'S' or northernHemisphere == 's':
        northernHemisphere = False
    elif northernHemisphere == 'N' or northernHemisphere == 'n':
        northernHemisphere = True

    if not northernHemisphere:
        northing = 10000000 - northing

    a = 6378137
    e = 0.081819191
    e1sq = 0.006739497
    k0 = 0.9996

    arc = northing / k0
    mu = arc / (a * (1 - math.pow(e, 2) / 4.0 - 3 * math.pow(e, 4) / 64.0 - 5 * math.pow(e, 6) / 256.0))

    ei = (1 - math.pow((1 - e * e), (1 / 2.0))) / (1 + math.pow((1 - e * e), (1 / 2.0)))

    ca = 3 * ei / 2 - 27 * math.pow(ei, 3) / 32.0

    cb = 21 * math.pow(ei, 2) / 16 - 55 * math.pow(ei, 4) / 32
    cc = 151 * math.pow(ei, 3) / 96
    cd = 1097 * math.pow(ei, 4) / 512
    phi1 = mu + ca * math.sin(2 * mu) + cb * math.sin(4 * mu) + cc * math.sin(6 * mu) + cd * math.sin(8 * mu)

    n0 = a / math.pow((1 - math.pow((e * math.sin(phi1)), 2)), (1 / 2.0))

    r0 = a * (1 - e * e) / math.pow((1 - math.pow((e * math.sin(phi1)), 2)), (3 / 2.0))
    fact1 = n0 * math.tan(phi1) / r0

    _a1 = 500000 - easting
    dd0 = _a1 / (n0 * k0)
    fact2 = dd0 * dd0 / 2

    t0 = math.pow(math.tan(phi1), 2)
    Q0 = e1sq * math.pow(math.cos(phi1), 2)
    fact3 = (5 + 3 * t0 + 10 * Q0 - 4 * Q0 * Q0 - 9 * e1sq) * math.pow(dd0, 4) / 24

    fact4 = (61 + 90 * t0 + 298 * Q0 + 45 * t0 * t0 - 252 * e1sq - 3 * Q0 * Q0) * math.pow(dd0, 6) / 720

    lof1 = _a1 / (n0 * k0)
    lof2 = (1 + 2 * t0 + Q0) * math.pow(dd0, 3) / 6.0
    lof3 = (5 - 2 * Q0 + 28 * t0 - 3 * math.pow(Q0, 2) + 8 * e1sq + 24 * math.pow(t0, 2)) * math.pow(dd0, 5) / 120
    _a2 = (lof1 - lof2 + lof3) / math.cos(phi1)
    _a3 = _a2 * 180 / math.pi

    latitude = 180 * (phi1 - fact1 * (fact2 + fact3 + fact4)) / math.pi

    if not northernHemisphere:
        latitude = -latitude

    longitude = ((zone > 0) and (6 * zone - 183.0) or 3.0) - _a3

    return latitude, longitude


#
# return a dateTimeString from timestamp t(a float) : (2019: NO t is a time) + pattern
# BO... used only in reaper_cycle
#
def dateStringFromTime(t, pattern=DEFAULT_DATE_PATTERN):
    return "%s" % (t.strftime(pattern))


#
# return a dateTimeString from timestamp t(a float)
#
def dateFromSec(t, pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(t)
    return d.strftime(pattern)


#
# return a dateTime string, with msec
#
def dateFromSecMs__(t):
    d = datetime.fromtimestamp(t)
    msec = d.microsecond / 1000
    return "%s.%sZ" % (d.strftime(DEFAULT_DATE_PATTERN).replace('Z', ''), msec)


#
# return a dateTime string, with 10th of second
# BO... not used
#
# def dateFromSecDs(t):
#        d=datetime.fromtimestamp(t)
#        dsec=d.microsecond/100000
#        return "%s.%sZ" % (d.strftime(pattern).replace('Z',''), dsec)


#
# take a dateTimeString + msec delta and return a dateTime string, with msec
#
def datePlusMsec(s, deltaMsec, pattern=DEFAULT_DATE_PATTERN):
    d = datetime.strptime(s, pattern)
    d = d + timedelta(milliseconds=deltaMsec)
    # print "##%s" % d.strftime(DEFAULT_DATE_PATTERN_MSEC)
    msec = d.microsecond / 1000
    tmp = "%s" % d.strftime(DEFAULT_DATE_PATTERN_MSEC)
    return tmp.replace(".000Z", ".%sZ" % msec)


#
# return a time from a timestamp + msec_offset
# BO... not used
#
def timePlusMsec(t, deltaMsec):
    d = datetime.fromtimestamp(t)
    res = d + timedelta(milliseconds=deltaMsec)
    return res


#
# get two dateTimeString + mseconds
# return diff time in float seconds, with milliseconds precisions
#
def dateDiffmsec(s1, msec1, s2, msec2, pattern=DEFAULT_DATE_PATTERN):
    d1 = datetime.strptime(s1, pattern)
    # dms1=datetime(year=0, month=0, day=0, hour=0, minute=0, second=0, microsecond=msec1)
    d1 = d1 + timedelta(milliseconds=msec1)
    print("d1=%s; msec1=%s; type=%s" % (d1, msec1, type(d1)))
    d2 = datetime.strptime(s2, pattern)
    # dms2=datetime(year=0, month=0, day=0, hour=0, minute=0, second=0, microsecond=msec2)
    d2 = d2 + timedelta(milliseconds=msec2)
    print("d2=%s; msec2=%s; type=%s" % (d2, msec2, type(d2)))
    dt = d2 - d1
    print("dt=%s; type=%s" % (dt, type(dt)))
    return dt.days * 86400 + dt.seconds + float(dt.microseconds) / float(1000000)


#
# return time from a dateTime string
# BO... used only in reaper_cycle, no: also in worldview make_product_list
#
def timeFromDatePatterm(s, pattern=DEFAULT_DATE_PATTERN):
    if debug != 0:
        print("timeFromDatePatterm:s=%s; pattern=%s" % (s, pattern))
    return datetime.strptime(s, pattern)


#
# return the now date string
# dateNow('%Y-%m-%dT%H:%M:%SZ')=2015-10-15 14:08:45Z
#
def dateNow(pattern=DEFAULT_DATE_PATTERN):
    d = datetime.fromtimestamp(time.time())
    return d.strftime(pattern)


#
# return the now date in float seconds
# dateNowSecs('%Y-%m-%dT%H:%M:%SZ')=1444911431.0
#
def dateNowSecs():
    d = datetime.fromtimestamp(time.time())
    return time.mktime(d.timetuple())


#
# from YYYY-MM-DD to: YYYYMMDD; if max==4
#
# add test s != VALUE_NOT_PRESENT to have #### filling in case metadata not present
#
#
def normaliseDate(s=None, max=-1, pad='#'):
    if s != None and s != VALUE_NOT_PRESENT:
        s = s.replace('-', '')
        if max > 0 and len(s) > max:
            s = s[0:max]
        return s
    else:
        s = ''
        while len(s) < max:
            s = "%s%s" % (s, pad)
        if len(s) > max:
            s = s[0:max]
        return s


#
# from hh:mm:ss[.000]Z to: hhmnss; if max==6
#
# add test s != VALUE_NOT_PRESENT to have #### filling in case metadata not present
#
def normaliseTime(s=None, max=-1, pad='#'):
    if debug != 0:
        print("normaliseTime:'%s', max:%s, pad:%s" % (s, max, pad))
    if s != None and s != VALUE_NOT_PRESENT:
        s = s.replace(':', '')
        s = s.replace('Z', '')
        if max > 0 and len(s) > max:
            s = s[0:max]
        if debug != 0:
            print(" returns:'%s'" % s)
        return s
    else:
        s = ''
        while len(s) < max:
            s = "%s%s" % (s, pad)
        if debug != 0:
            print(" returns:'%s'" % s)
        return s


#
#
#
def getMonth2DigitFromMonthString(mess):
    result = None
    for monthName in list(monthDict2.keys()):
        pos = mess.find(monthName)
        if pos == 0:
            result = mess.replace(monthName, monthDict2[monthName])
            break
    return result


#
#
#
def twoDigitsYearToFourdigits(s):
    try:
        int(s)
    except:
        raise Exception("can not get 4digit year from 2 digit:%s" % s)
    year = None
    if int(s[0]) > 5:
        year = '19%s' % s
    else:
        year = '20%s' % s
    if year is None:
        raise Exception("can not get 4digit year from 2 digit:%s" % s)
    return year


#
# change JAN, FEB, etc.. into 2 digits
#
def normaliseDateString(mess=None):
    for monthName in list(monthDict2.keys()):
        pos = mess.find(monthName)
        if pos >= 0:
            mess = mess.replace(monthName, monthDict2[monthName])
    # change space into T
    mess = mess.replace(' ', 'T')

    #
    pos = mess.find('.')
    if pos >= 0:
        mess = mess[0:pos + 4]
    pos = mess.find('Z')
    if pos < 0:
        mess = mess + 'Z'

    return mess


#
#
#
def removeMsecFromdateString(s):
    pos = s.find('.')
    if pos > 0:
        return "%sZ" % s[0:pos]
    else:
        return s


#
# convert +1.3688110981e+02 to number
#
def EEEtoNumber(s=None):
    res = normaliseNumber(s)
    i = float(res)
    if debug != 0:
        print(" ### EEEtoNumber res:'%s'\n" % i)
    return "%s" % i


#
# change number text:
# - suppress leading and tailing space
# - set length
#
# add test s != VALUE_NOT_PRESENT to have #### filling in case metadata not present
#
# return: string
#
def normaliseNumber(s=None, max=-1, pad=' ', truncate=None):
    if debug != 0:
        print("normaliseNumber:'%s', max:%s, pad:%s" % (s, max, pad))
    if s == None and s != VALUE_NOT_PRESENT:
        s = "#"
        pad = '#'
    s = s.strip()

    if debug != 0:
        print(" normaliseNumber after strip; s:'%s'" % s)
    if max == -1:
        max = len(s)

    res = s
    if len(res) > max:
        # suppress space on left side
        while len(res) > max and res[0] == ' ':
            res = res[1:]

    if len(res) > max:
        # suppress space on right side, troncate if allowed
        while len(res) > max and truncate is not None:
            res = res[0:-1]

    if debug != 0:
        print(" normaliseNumber after max; res:'%s'" % res)
    while len(res) < max:
        res = "%s%s" % (pad, res)

    if debug != 0:
        print(" ### normaliseNumber res:'%s'\n" % res)
    return res


#
# reverse a footprint (CCW <-> CW)
#
def reverseFootprint(footprint):
    toks = footprint.split(" ")
    ccw = ""
    nPair = 1
    numPair = len(toks) / 2
    if debug != 0:
        print(" numPair=%s" % numPair)
    for item in range(len(toks) // 2):
        if debug != 0:
            print(" pair[%d]:%d:" % (nPair - 1, (numPair - nPair) * 2))
        if len(ccw) > 0:
            ccw = "%s " % ccw
        ccw = "%s%s %s" % (ccw, toks[(numPair - nPair) * 2], toks[(numPair - nPair) * 2 + 1])
        nPair = nPair + 1
    return ccw


#
# take a dateTimeMsecsString
# return Decimal timestamp
# dateTimeMsecsStringToDecimalSecs(2000-12-31T10:44:47.456Z)=978255887.456
#
#  carefull: float has limited precision: milliseconds can be not accurate ==> will use integer to perform sec+msec additions
# don't use float because of  fraction precision lost on big values
#
def dateTimeMsecsStringToDecimalSecs(s):
    if debug != 0:
        print("dateTimeMsecsStringToDecimalSecs s=%s; type=%s" % (s, type(s)))
    pos = s.find('.')
    msec = 0
    if pos > 0:
        msec = s[pos + 1:-1]
        s = "%sZ" % s[0:pos]
    imsec = int(msec)
    if debug != 0:
        print("dateTimeMsecsStringToDecimalSecs s=%s; msec=%s; imsec=%s" % (s, msec, imsec))
    d = datetime.strptime(s, DEFAULT_DATE_PATTERN)
    a = decimal.Decimal(time.mktime(d.timetuple()) * 1000)
    b = decimal.Decimal(imsec)
    c = decimal.Decimal(1000)
    res = (a + b) / c
    if debug != 0:
        print("dateTimeMsecsStringToDecimalSecs res=%s; type=%s" % (res, type(res)))
    return res


#
# take a Decimal second+fraction timestamp
# return dateTimeMsecsString
# secsDecimalToDateTimeMsecsString(978255887.456)=2000-12-31T10:44:47.456Z
#
#  carefull: float has limited precision: milliseconds can be not accurate ==> will use integer to perform sec+msec additions
# don't use float because of  fraction precision lost on big values
#
def secsDecimalToDateTimeMsecsString(d):
    if debug != 0:
        print("secsDecimalToDateTimeMsecsString d=%s; type=%s" % (d, type(d)))
    sec = int(d)
    msec = int((d - sec) * 1000)
    if debug != 0:
        print("secsDecimalToDateTimeMsecsString secs=%s; msec=%s" % (sec, msec))

    d = datetime.fromtimestamp(sec)
    smsec = "%s" % msec
    res = "%s.%sZ" % (d.strftime(DEFAULT_DATE_PATTERN).replace('Z', ''), leftPadString(smsec, 3, '0'))
    if debug != 0:
        print("secsDecimalToDateTimeMsecsString res=%s; type=%s" % (res, type(res)))
    return res


#
# take a dateTimeMsecsString
# return lomg millisecs timestamp
# dateTimeMsecsStringToMsecs('2000-12-31T10:44:47.456Z')=978255887.456
#
# don't use float because of  fraction precision lost on big values
#
#
def dateTimeMsecsStringToMsecs(s):
    if debug != 0:
        print("dateTimeMsecsToMsecs s=%s; type=%s" % (s, type(s)))
    pos = s.find('.')
    msec = 0
    if pos > 0:
        msec = s[pos + 1:-1]
        s = "%sZ" % s[0:pos]
    imsec = int(msec)
    if debug != 0:
        print("dateTimeMsecsToMsecs s=%s; msec=%s; imsec=%s" % (s, msec, imsec))
    d = datetime.strptime(s, DEFAULT_DATE_PATTERN)
    msecRes = int(time.mktime(d.timetuple())) * 1000

    res = msecRes + imsec
    if debug != 0:
        print("dateFromSecMs: msecRes type:%s" % (type(msecRes)))
        print("dateTimeMsecsToMsecs res=%s; type=%s" % (res, type(res)))
    return res


#
# not good: timestamp out of range
#
# take long millisecs timestamp
# return dateTimeMsecsString
# msecsTodateTimeMsecsString(78255887.456) = 1972-06-24T19:44:47.456Z
#
# don't use float because of  fraction precision lost on big values
#
def msecsTodateTimeMsecsString__(t):
    if debug != 0:
        print("msecsTodateTimeMsecsString s=%s; type=%s" % (t, type(t)))
    sec = int(t)
    msec = int((t - sec) * 1000)
    if debug != 0:
        print("msecsTodateTimeMsecsString secs=%s; msec=%s" % (sec, msec))

    d = datetime.fromtimestamp(sec)
    smsec = "%s" % msec
    res = "%s.%sZ" % (d.strftime(DEFAULT_DATE_PATTERN).replace('Z', ''), leftPadString(smsec, 3, '0'))
    if debug != 0:
        print("msecsTodateTimeMsecsString res=%s; type=%s" % (res, type(res)))
    return res


#
# return a dateTime string, with msec
#
def dateFromSecMs(t):
    d = datetime.fromtimestamp(t)
    msec = d.microsecond / 1000
    return "%s.%sZ" % (d.strftime(DEFAULT_DATE_PATTERN).replace('Z', ''), msec)


#
# remove msec from date string like: 1972-06-24T19:44:47.456Z
#  return 1972-06-24T19:44:47Z
#
def removeMsecFromDateTimeString(t):
    pos = t.find('.')
    if pos > 0:
        t = "%sZ" % t[0:pos]
    return t


#
# remove msec from time string like: 19:44:47.456
#  return 1972-06-24T19:44:47
#
def removeMsecFromTimeString(t):
    pos = t.find('.')
    if pos > 0:
        t = t[0:pos]
    return t


#
# input param:
#  - softVersion; software version is like: SPOT5_V07.07P1
#  - separator pre version number; like _V
#
#
#
def buildSip3DigitVersion(softVersion, sep):
    versionOk = softVersion
    pos = softVersion.find(sep)
    if pos > 0:
        version = softVersion[pos + len(sep):]
        if debug:
            print(("\n RUN buildVersion: _V present in software version: from:'%s', to:'%s'" % (version, softVersion)))
    else:
        if debug:
            print(("\n RUN buildVersion: _V not present in software version:'%s', keep it" % softVersion))
        version = softVersion

    if debug:
        print((" ## buildSip3DigitVersion 0; from:'%s' to:'%s'" % (softVersion, version)))
    up = ''  # remove leading 0
    foundNonZero = False
    foundDot = False
    for i in range(len(version)):
        if debug:
            print(("  test:'%s'" % version[i]))
        if version[i].isdigit():
            if version[i] != '0':
                # print("  test:'%s' is-non-zero" % version[i])
                foundNonZero = True
            if version[i] == '.':
                # print("  test:'%s' is-dot" % version[i])
                foundDot = True
            if foundNonZero and not foundDot:
                # print("  test:'%s' ok, added" % version[i])
                up += version[i]
        else:
            # print("  test:'%s' is-dot" % version[i])
            foundDot = True
    if debug:
        print((" ## buildVersion 1; from:'%s' to up:'%s'" % (softVersion, up)))

    pos2 = version.find('.')
    if pos2 > 0:
        version2 = version[0:pos2]
        reste = version[pos2 + 1:]
        low = ''
        if debug:
            print((" ## buildVersion 2; from:'%s' to:'%s'; up:%s; reste:'%s'" % (version, version2, up, reste)))
        for i in range(len(reste)):
            if reste[i].isdigit():
                low += reste[i]
            else:
                break
        if debug:
            print((" ## buildVersion 3; from:'%s' to:'%s'; up:%s; low:'%s'" % (version, version2, up, low)))

        if len(up) > 3:
            upOk = up[0:3]
            if debug:
                print((" ## buildVersion 4; cut len>3 up:%s; to:'%s'" % (up, upOk)))
            versionOk = upOk
            if debug:
                print((" #### buildVersion n-4; versionOk:'%s'" % versionOk))
        if len(up) == 3:
            upOk = up[0:3]
            if debug:
                print((" ## buildVersion 4-0; cut len==3 up:%s; to:'%s'" % (up, upOk)))
            versionOk = upOk
            if debug:
                print((" #### buildVersion n-4-0; versionOk:'%s'" % versionOk))
        elif len(up) == 2:
            if len(low) >= 1:
                lowOk = low[0]
            if debug:
                print((" ## buildVersion 4-1; len up=3; cut low>1 from:%s; to:'%s'" % (low, lowOk)))
            versionOk = "%s%s" % (up, low)
            if debug:
                print((" #### buildVersion nn-4-1; versionOk:'%s'" % versionOk))
        elif len(up) == 2:
            if len(low) > 1:
                lowOk = low[1]
                if debug:
                    print((" ## buildVersion 5; len up=2; cut low>1 from:%s; to:'%s'" % (low, lowOk)))
                versionOk = "%s%s" % (up, low)
                print((" #### buildVersion n; versionOk:'%s'" % versionOk))
            elif len(low) == 1:
                versionOk = "%s%s" % (up, low)
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
            elif len(low) == 0:
                versionOk = "0%s" % up
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
        elif len(up) == 1:
            if len(low) > 2:
                lowOk = low[:2]
                if debug:
                    print((" ## buildVersion 6; len up=1; cut low>2 from:%s; to:'%s'" % (low, lowOk)))
                versionOk = "%s%s" % (up, low)
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
            elif len(low) == 2:
                versionOk = "%s%s" % (up, low)
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
            elif len(low) == 1:
                versionOk = "%s%s0" % (up, low)
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
            elif len(low) == 0:
                versionOk = "00%s" % up
                if debug:
                    print((" #### buildVersion n; versionOk:'%s'" % versionOk))
        elif len(up) == 0:
            if len(low) > 3:
                lowOk = low[:3]
                if debug:
                    print((" ## buildVersion 7; len up=0; cut low>3 from:%s; to:'%s'" % (low, lowOk)))
                versionOk = "%s" % (up, low)
            else:
                versionOk = leftPadString(low, 3, '0')
                if debug:
                    print((" ## buildVersion 8; len up=0; leftpad low from:%s; to:'%s'" % (low, versionOk)))
        else:
            raise Exception("buildVersion unhandled version:'%s'" % version)

    else:  # no . in version
        up = ''
        for i in range(len(version)):
            if version[i].isdigit():
                up += version[i]
            else:
                break
        if len(up) > 3:
            versionOk = up[:3]
            if debug:
                print((" ## buildVersion 9; no . in version; cut from:%s; to:'%s'" % (up, versionOk)))
        elif len(up) == 3:
            versionOk = up
            if debug:
                print((" ## buildVersion 9; no . in version; unchanged from:%s; to:'%s'" % (up, versionOk)))
        else:
            versionOk = leftPadString(up, 3, '0')
            if debug:
                print((" ## buildVersion 8; no . in version; leftpad from:%s; to:'%s'" % (up, versionOk)))

    return versionOk


if __name__ == '__main__':
    try:

        version = "SPOT5_V07.07P1"
        versionOk = buildSip3DigitVersion(version, "_V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V2.01"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V2.0"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V1"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V1.3"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V200.30"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "_V40.3"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "100.30"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))

        version = "600.05"
        versionOk = buildSip3DigitVersion(version, "V")
        print((" -> version:'%s' to '%s'" % (version, versionOk)))
        os._exit(0)

        v = 43.18
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = -43.18
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = -143.1865756756875687
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = 143.1
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = 0
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = 10
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = -10
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        v = -10.0000000000044
        r = formatFloatDecimalNoRepresentationError(v, 3)
        print("formatFloatDecimalNoRepresentationError of %s=%s\n\n" % (v, r))

        aPath = './tmp_batch_1/work/0/batch_irs1c1d_prod0_workfolder_0/I1C_OPER_PAN_P___1A_19960702T082531_19960702T082531_002659_0056_0041_3R11/I1C_OPER_PAN_P___1A_19960702T082531_19960702T082531_002659_0056_0041_3R11.PNG'
        print("\n@@\n@@@dirname of %s=='%s'" % (aPath, dirname(aPath)))
        print("\nbasename of %s=='%s'" % (aPath, os.path.basename(aPath)))
        print("\nextension of %s=='%s'" % (aPath, getFileExtension(aPath)))
        aPath = './tmp_batch_1/work/0/batch_irs1c1d_prod0_workfolder_0/I1C_OPER_PAN_P___1A_19960702T082531_19960702T082531_002659_0056_0041_3R11/I1C_OPER_PAN_P___1A_19960702T082531_19960702T082531_002659_0056_0041_3R11.BI.PNG'
        print("\nextension of %s=='%s'" % (aPath, getFileExtension(aPath)))

        aPath = '/tmp/a'
        print("\n@@\n@@@dirname of %s=='%s'" % (aPath, dirname(aPath)))
        print("\nbasename of %s=='%s'" % (aPath, os.path.basename(aPath)))

        aPath = '/tmp/D/'
        print("\n@@\n@@@dirname of %s=='%s'" % (aPath, dirname(aPath)))
        print("\nbasename of %s=='%s'" % (aPath, os.path.basename(aPath)))

        t = '1972-06-24T19:44:47.456Z'
        print("removeMsecFromDateString 1972-06-24T19:44:47.456Z: %s" % removeMsecFromDateString(t))

        # timestamp=1.16767724406e+12
        timestamp = 78255887.456
        result = msecsTodateTimeMsecsString(timestamp)
        print("\n\n->msecsTodateTimeMsecsString(%s)=%s\n\n" % (timestamp, result))

        dateTime1 = '2000-12-31T10:44:40Z'
        dateTime2 = '2000-12-31T10:44:47Z'
        dateTime3 = '2000-12-31T10:44:47.039Z'
        dateTime4 = '2007-01-07T10:29:37.039Z'

        result = dateTimeMsecsStringToDecimalSecs(dateTime4)
        print("\n\n->dateTimeMsecsStringToDecimalSecs(%s)=%s\n\n" % (dateTime4, result))
        result1 = secsDecimalToDateTimeMsecsString(result)
        print("\n\n->secsDecimalToDateTimeMsecsString(%s)=%s" % (result, secsDecimalToDateTimeMsecsString(result)))


        result = dateTimeMsecsStringToMsecs(dateTime4)
        print("\n\n->dateTimeMsecsToMsecs(%s)=%s" % (dateTime4, result))
        result1 = msecsTodateTimeMsecsString(result)
        print("\n\n->msecsTodateTimeMsecsString(%s)=%s" % (result, msecsTodateTimeMsecsString(result)))

        result = dateTimeMsecsStringToMsecs(dateTime3)
        print("\n\n\n\n->dateTimeMsecsToMsecs(%s)=%s" % (dateTime3, result))
        result1 = msecsTodateTimeMsecsString(result)
        print("\n\n->msecsTodateTimeMsecsString(%s)=%s" % (result, msecsTodateTimeMsecsString(result)))

        print("dateNowSecs(%s)=%s" % (dateTime1, dateNowSecs()))
        print("dateNow(%s)=%s" % (dateTime1, dateNow(dateTime1)))
        print("dateInMsec(%s)=%s" % (dateTime3, dateInMsec(dateTime3, DEFAULT_DATE_PATTERN)))

        dt = dateDiffmsec(dateTime1, 123, dateTime2, 354, DEFAULT_DATE_PATTERN)
        print("DT=%s" % dt)

        dateTime = '2000-12-31T10:44:45Z'
        nowPlus = datePlusMsec(dateTime, 4512)
        print("\n\n\n2000-12-31T10:44:45Z + 4.512 sec=%s" % nowPlus)
        nowPlus = datePlusMsec(dateTime, -4512)
        print("\n2000-12-31T10:44:45Z - 4.512 sec=%s" % nowPlus)


        a = '+1.3688110981e+02'
        print("a=='%s' normaliseNumber(a)==>'%s'" % (a, EEEtoNumber(a)))

        # a='+0049648227<10-6degE>'
        # print "a=='%s' normaliseNumber(a)==>'%s'" % (a, EEEtoNumber(a))

        a = 0o01
        b = -0o02
        print("a=%s  colatitude a=%s" % (a, coLatitude(a)))
        print("b=%s  absoluteLongitude b=%s" % (b, absoluteLongitude(b)))

        a = -0o11
        b = 140
        print("\na=%s  colatitude a=%s" % (a, coLatitude(a)))
        print("b=%s  absoluteLongitude b=%s" % (b, absoluteLongitude(b)))

        a = "Ikonos"
        print("a=='%s' normaliseNumber(a)==>'%s'" % (a, normaliseNumber(a, 2, None, 1)))

        a = "          1"
        print("a=='%s' normaliseNumber(a)==>'%s'" % (a, normaliseNumber(a)))
        print("a=='%s' normaliseNumber(a,4)==>'%s'" % (a, normaliseNumber(a, 4)))
        print("a=='%s' normaliseNumber(a,-1)==>'%s'" % (a, normaliseNumber(a, 8)))

        a = "   +1.2345E02   "
        print("a=='%s' normaliseNumber(a,4)==>'%s'" % (a, normaliseNumber(a, 8)))
        print("a=='%s' EEEtoNumber(a)==>'%s'" % (a, EEEtoNumber(a)))

        a = "   -1.2345E02   "
        print("a=='%s' EEEtoNumber(a)==>'%s'" % (a, EEEtoNumber(a)))

        cwFootprint = "11.505158383 -1.7328153269 22.400659479 -2.9829417472 33.876066318 -3.1602073246 44.979779308 -4.903779609 55.505158383 -5.7328153269"
        ccw = reverseFootprint(cwFootprint)
        print("footprint:%s" % cwFootprint)
        print("ccw:%s" % ccw)

        print("Utm(712605, 10000, 21, True) ==> lat:0.090422 Lon:-55.089726567181266 ? :: %s %s" % utmToLatLon(712605,
                                                                                                               10000,
                                                                                                               21, True))

        sNow = dateNow()
        print("\n\n\ndateNow:%s" % sNow)

        nowPlus = datePlusMsec(sNow, 4512)
        print("now + 4.512 sec=%s" % nowPlus)

        toks = nowPlus.split('T')
        print(normaliseTime(toks[1], 6))

        dateTime = '2000-12-31T10:44:45Z'
        nowPlus = datePlusMsec(dateTime, 4512)
        print("\n\n\n2000-12-31T10:44:45Z + 4.512 sec=%s" % nowPlus)
        nowPlus = datePlusMsec(dateTime, -4512)
        print("\n2000-12-31T10:44:45Z - 4.512 sec=%s" % nowPlus)

        dateTime = '2000-10-31T10:44:45Z'
        nowPlus = datePlusMsec(dateTime, 4512)
        print("\n\n\n2000-10-31T10:44:45Z + 4.512 sec=%s" % nowPlus)
        nowPlus = datePlusMsec(dateTime, -4512)
        print("\n2000-10-31T10:44:45Z - 4.512 sec=%s" % nowPlus)

        dateTime = '2010-10-31T10:44:45Z'
        nowPlus = datePlusMsec(dateTime, 4512)
        print("\n\n\n2010-10-31T10:44:45Z + 4.512 sec=%s" % nowPlus)
        nowPlus = datePlusMsec(dateTime, -4512)
        print("\n2010-10-31T10:44:45Z - 4.512 sec=%s" % nowPlus)

        dateTime = '1986-05-16T09:22:42Z'
        nowPlus = datePlusMsec(dateTime, 4512)
        print("\n\n\n1986-05-16T09:22:42Z + 4.512 sec=%s" % nowPlus)
        nowPlus = datePlusMsec(dateTime, -4512)
        print("\n1986-05-16T09:22:42Z - 4.512 sec=%s" % nowPlus)

        print("\n\n\nnormaliseDateString:%s" % normaliseDateString("17-DEC-2013 20:26:48Z"))

        degdec = '23.711863883'
        print("degree dec:%s to deg min sec string:%s" % (degdec, decdeg2dmsString(degdec)))

        d, m, s = decdeg2dms(degdec)
        print("degree dec:%s to deg min sec:%s %s %s" % (s, d, m, s))
        print("and reverse:%s" % dms2degdec(d, m, s))


    except Exception as e:
        print(" Error")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        traceback.print_exc(file=sys.stdout)
