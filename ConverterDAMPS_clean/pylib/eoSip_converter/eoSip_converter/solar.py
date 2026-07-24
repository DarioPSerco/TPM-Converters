# pysolar mess up datetime import
from datetime import datetime, timedelta

from .geomHelper import *

#
DEFAULT_DATE_PATTERN = "%Y-%m-%dT%H:%M:%SZ"

#
debug = False


#
#
#
def getSunPosition(lat, lon, dt):
    year = dt.year
    month = dt.month
    dayOfMonth = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    if debug:
        print(("  getSunPosition at lat:%s; lon:%s; datetime:%s" % (lat, lon, dt)))
    if debug:
        print((" year:%s" % year))
        print((" month:%s" % month))
        print((" date:%s" % dayOfMonth))
        print((" hour:%s" % hour))
        print((" minute:%s" % minute))
        print((" second:%s" % second))

    h = hour + minute / 60.0 + second / 3600.0

    # fractional day, 0.0 corresponds to January 1, 2000 00:00:00 UTC

    d = h / 24.0 + (367 * year - 7 * (year + (month + 9) / 12) / 4 + 275 * month / 9 + dayOfMonth - 730530)
    if debug:
        print((" fractional day:%s" % d))
    # GL: verif because looks a little bit wrong
    dd = dt - datetime(2000, 1, 1, 0, 0, 0)
    fdd = float(dd.days) + (float(dd.seconds) / 86400.0)
    if math.floor(d - fdd) > 1.0 / 24.0:
        if debug:
            print(
                " verification of fractional day: dt - fractional (should be 2000-01-01 00:00:00) is:%s; fdd=%s" % (
                    dt - timedelta(days=d), fdd
                )
            )

            print(
                " fractional day verification warning: is more than 1 hour: %s day" % (
                    math.floor(d - fdd)
                )
            )

            print(
                " verification of my fractional calc: (should be 2000-01-01 00:00:00) is: %s; fdd=%s" % (
                    dt - timedelta(days=dd.days, seconds=dd.seconds), fdd
                )
            )
        d = fdd

    # longitude of perihelion (rad)
    w = math.radians(282.9404) + math.radians(4.70935E-5) * d
    # eccentricity (rad)
    e = 0.016709 - 1.151E-9 * d
    # mean anomaly (rad)
    M = math.radians(356.0470) + math.radians(0.9856002585) * d

    # ecliptical obliquity (rad)
    o = math.radians(23.4393) - math.radians(3.563E-7) * d

    # eccentric anomaly (rad)
    E = M + e * sin(M) * (1.0 + e * cos(M))

    # true anomaly (rad)
    v = atan2(sqrt(1.0 - e * e) * sin(E), cos(E) - e)

    # true longitude (rad)
    true_lon = v + w

    # Cartesian geocentric coordinates
    x = cos(true_lon)
    y = sin(true_lon) * cos(o)
    z = sin(true_lon) * sin(o)

    # right ascension (rad)
    alpha = atan2(y, x)
    # declination (rad)
    delta = atan2(z, sqrt(x * x + y * y))
    # local siderial time
    lst = M + w + math.pi + h * math.radians(15.0) + math.radians(lon)
    # local hour angle (rad)
    lha = lst - alpha
    # latitude (rad)
    phi = math.radians(lat)
    # altitude angle (rad)
    alt = asin(sin(phi) * sin(delta) + cos(phi) * cos(delta) * cos(lha))

    xaa = cos(lha) * cos(delta) * sin(phi) - sin(delta) * cos(phi)
    yaa = sin(lha) * cos(delta)

    # azimuth angle (rad)
    saa = atan2(yaa, xaa) + math.pi
    # zenith angle (rad)
    sza = math.pi / 2.0 - alt
    return math.degrees(sza), math.degrees(saa)


if __name__ == '__main__':
    d = datetime.strptime('2016-10-24T13:00:00Z', DEFAULT_DATE_PATTERN)
    print(("get sun azimuth for date:%s; tz=%s" % (d, d.tzinfo)))
    lat = 33.72
    lon = 35.84

    senith, azimuth = getSunPosition(lat, lon, d)
    print(" -> zenith:%s, azimut:%s" % (senith, azimuth))
