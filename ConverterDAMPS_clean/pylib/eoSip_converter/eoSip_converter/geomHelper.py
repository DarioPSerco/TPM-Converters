# -*- coding: cp1252 -*-
#
# 
#
#
import math
import sys
from math import radians, cos, sin, asin, sqrt, atan2, degrees

import numpy as np

from .geom import vector2D

debug = 0


#
#
#
def degToRad__(d):
    print((" degToRad on :%s; type:%s" % (d, type(d))))
    return list(map(radians, d))


#
#
#
def radToDeg__(r):
    print((" radToDeg on :%s; type:%s" % (r, type(r))))
    return list(map(degrees, r))


#
#
#
def deg2rad(d):
    # print(" degToRad on :%s; type:%s" % (d, type(d)))
    return radians(d)


#
#
#
def rad2deg(r):
    # print(" radToDeg on :%s; type:%s" % (r, type(r)))
    return degrees(r)


#
#
#
def coordinateBetween(lat1, lon1, lat2, lon2):
    if debug != 0:
        print("\n\n\n coordinateBetween deg %s %s %s %s" % (lat1, lon1, lat2, lon2))
    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = list(map(radians, [lat1, lon1, lat2, lon2]))

    bx = cos(lat2) * cos(lon2 - lon1)
    by = cos(lat2) * sin(lon2 - lon1)
    lat3 = atan2(sin(lat1) + sin(lat2), sqrt((cos(lat1) + bx) * (cos(lat1) + bx) + by ** 2))
    lon3 = lon1 + atan2(by, cos(lat1) + bx)

    if debug != 0:
        print("\n\n\n coordinateBetween res deg: %s %s" % (degrees(lat3), degrees(lon3)))
    return degrees(lat3), degrees(lon3)


#
# Calculate the great circle distance between two points 
# on the earth (specified in decimal degrees)
#
# returns the distance in meters
#
def metersDistanceBetween(lat1, lon1, lat2, lon2):
    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = list(map(radians, [lat1, lon1, lat2, lon2]))

    # haversine formula 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    if debug != 0:
        print("angle=%s" % c)

    # if we want the distance in meter
    # 6378137f meters is the radius of the Earth
    meters = 6378137 * c
    return meters


# from java, == arcDistanceBetween. OK
#
# returns radians ?: yes
#
def sphericalDistance(lat1, lon1, lat2, lon2):
    phi0, lambda0, phi, alambda = list(map(radians, [lat1, lon1, lat2, lon2]))
    pdiff = sin(((phi - phi0) / 2))
    ldiff = sin((alambda - lambda0) / 2)
    rval = sqrt((pdiff * pdiff) + cos(phi0) * cos(phi) * (ldiff * ldiff))

    return 2 * asin(rval)


#
#
#
def getCorners(footprint, angleLimit):  # , minPair, stepMult):
    # print " # footprint: %s" % footprint

    if 1 == 2:
        fd = open("/home/gilles/shared/test/footprint.txt", "w")
        fd.write(footprint)
        fd.flush()
        fd.close()
        # os._exit(0)
    toks = footprint.split(' ')

    withDelta = []
    ox = None
    oy = None
    for n in range(len(toks) // 2):
        if debug != 0:
            print(" # doing n: %s on %s" % (n, (len(toks) / 2)))
        added = False
        if ox is None:
            if debug != 0:
                print(" %s first added to withDelta" % n)
            withDelta.append(toks[n * 2])
            withDelta.append(toks[n * 2 + 1])
            added = True
        else:
            if debug != 0:
                print(" diff[%s] from lat/y %s and %s" % (n, float(toks[n * 2]), float(oy)))
            if abs(float(toks[n * 2]) - float(oy)) != 0:
                if debug != 0:
                    print(" old lat: %s; new lat: %s. lat/y diff: %s" % (
                    oy, toks[n * 2], float(toks[n * 2]) - float(oy)))
                    print(" diff[%s] from lon/x %s and %s" % (n, float(toks[n * 2 + 1]), float(ox)))
                if abs(float(toks[n * 2 + 1]) - float(ox)) != 0:
                    if debug != 0:
                        print("  old lon: %s; new lon: %s.lon/x diff: %s" % (
                        ox, toks[n * 2 + 1], float(toks[n * 2 + 1]) - float(ox)))
                    added = True
        if added:
            withDelta.append(toks[n * 2])
            withDelta.append(toks[n * 2 + 1])
            if debug != 0:
                print(" %s added to withDelta: %s; %s\n" % (n, toks[n * 2], toks[n * 2 + 1]))
            oy = toks[n * 2]
            ox = toks[n * 2 + 1]
        else:
            if debug != 0:
                print(" %s not added to withDelta\n" % n)

        # oy=toks[n*2]
        # ox=toks[n*2+1]

    #
    if debug != 0:
        print(" num coords from: %s to: %s" % (len(toks), len(withDelta)))
    # os._exit(1)
    fstr = ""
    toks = []
    for item in withDelta:
        if len(fstr) > 1:
            fstr += " "
        fstr = "%s%s" % (fstr, item)
        toks.append(item)
    if debug != 0:
        print(" withDelta footprint: %s" % fstr)

    if 1 == 2:
        fd = open("/home/gilles/shared/test/footprint_1.txt", "w")
        fd.write(fstr)
        fd.flush()
        fd.close()
    # os._exit(1)

    #
    f = []
    for item in toks:
        f.append(float(item))

    #
    # wantedPair=5
    total = len(f) / 2
    step = 2

    """print " total: %s; minPair: %s; stepMult: %s" % (total, minPair, stepMult)
    if total > minPair*2:
        step = step * stepMult
        print " too many pair, make step from: 2 to: %s" % (step)"""

    # if total > (wantedPair/2):
    #    print " adjust step from: %s to: %s" % (step, total/(wantedPair))
    #    step = total/(wantedPair)

    """if total >20: && total <= 40>:
        step = 4
    elif total >40 && total <= 80>:
        step = 8"""

    #
    # iter = range((len(f) // step)+1)
    iter = list(range(len(f) // step))
    if debug != 0:
        print(" ## num iter: %s; step: %s" % (len(iter), step))
    # os._exit(1)

    corners = []
    pair = None
    for i in iter:
        n = i * step
        if debug != 0:
            print("\n ##\n ## at cursor: %s/%s; step: %s\n ##" % (n, len(f), step))
        y1 = f[n]
        x1 = f[n + 1]
        nn = n + (2 * step)
        if debug != 0:
            print(" nn 0 is now: %s" % nn)
            print(" test: nn+1 >= len(iter*step): %s >= %s" % (nn + 1, len(iter * step)))
        if nn + 1 >= len(
                iter * step):  # we come back to the first point, so use the next one to build the second angle?? normally should never be the case because it's the next test the good one
            if debug != 0:
                print("0 nn+1=%s>%s so set to:%s" % (nn, len(iter * step), nn - len(iter)))
            nn = nn - len(iter * step) + (2 * step)
            if debug != 0:
                print(" nn 0-1 is now: %s" % nn)
        y2 = f[nn]
        x2 = f[nn + 1]
        nn = nn + (2 * step)
        if debug != 0:
            print(" nn 1 is now: %s" % nn)
            print(" test: nn >= len(iter*step): %s >= %s" % (nn, len(iter * step)))
        if nn + 1 >= len(
                iter * step):  # this should be the good test: we come back to the first point, so use the next one to build the second angle
            if debug != 0:
                print("1 nn+1=%s>%s so set to:%s" % (nn + 1, len(iter * step), nn - len(iter) + 2))
            nn = nn - len(iter * step) + (2 * step) + 2
            if debug != 0:
                print(" nn 1-1 is now: %s" % nn)
        y3 = f[nn]
        x3 = f[nn + 1]
        if debug != 0:
            print("do point[%s]: x=%s y=%s vs x=%s y=%s vs x=%s y=%s " % (n, x1, y1, x2, y2, x3, y3))
        v1 = vector2D.Vec2d(x2 - x1, y2 - y1)
        v2 = vector2D.Vec2d(x3 - x2, y3 - y2)
        if debug != 0:
            print("\nv1=%s" % v1)
            print("v2=%s" % v2)
        angle = v2.get_angle_between(v1)
        if debug != 0:
            print(">>>>>>>>>>>angle[%s]: %f" % (i, v2.get_angle_between(v1)))
        pair = "%s %s" % (y1, x1)
        if angle > angleLimit:
            corners.append(pair)

    # add first point
    # corners.append("%s %s" % (f[0], f[1]))
    # add last one if needed
    if corners[len(corners) - 1] != pair:
        if debug != 0:
            print(" # first pair (%s) != last pair (%s): close polygon by adding last pair" % (corners[0], pair))
        corners.append(corners[0])

    if debug != 0:
        print("\nnum corners: %s" % len(corners))
    n = 0
    for item in corners:
        if debug != 0:
            print(" corner %s: %s" % (n, item))
        n += 1

    footprint2 = ""
    for item in corners:
        if len(footprint2) > 0:
            footprint2 += " "
        footprint2 = "%s%s" % (footprint2, item)
    if debug != 0:
        print("\n footprint2: %s" % footprint2)
    return footprint2


# from java. OK
#
# returns lat lon in degrees
#
def getIntermediatePoint(lat1, lon1, lat2, lon2, f):
    if debug != 0:
        print(" @@@@@@@@@@@@@@@@ getIntermediatePoint deg %s %s %s %s" % (lat1, lon1, lat2, lon2))
    lon = 999999
    lat = 999999

    # get distance a-b
    d = sphericalDistance(lat1, lon1, lat2, lon2)
    if debug != 0:
        print(" @@@@@@@@@@@@@@@@ d0:%s    %s" % (d, degrees(d)))

    # a==b case
    if d == 0:
        return lat1, lon1
    # d = arcDistanceBetween(lat1, lon1, lat2, lon2)
    # print " @@@@@@@@@@@@@@@@ d1:%s    %s" % (d, degrees(d))

    lat1, lon1, lat2, lon2 = list(map(radians, [lat1, lon1, lat2, lon2]))
    # apply formula
    A = sin((1.0 - f) * d) / sin(d)
    B = sin(f * d) / sin(d)

    x = A * cos(lat1) * cos(lon1) + B * cos(lat2) * cos(lon2)
    y = A * cos(lat1) * sin(lon1) + B * cos(lat2) * sin(lon2)
    z = A * sin(lat1) + B * sin(lat2)

    lat = atan2(z, sqrt(pow(x, 2) + pow(y, 2)))
    lon = atan2(y, x)

    # return lat, lon
    return degrees(lat), degrees(lon)


#
# Calculate the great circle distance between two points 
# on the earth (specified in decimal degrees)
#
# returns the arc distance in radian
#
def arcDistanceBetween(lat1, lon1, lat2, lon2):
    if debug != 0:
        print("\n\n\n arcDistanceBetween deg %s %s %s %s" % (lat1, lon1, lat2, lon2))
    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = list(map(radians, [lat1, lon1, lat2, lon2]))
    # print " arcDistanceBetween rad %s %s %s %s" % (lat1, lon1, lat2, lon2)

    # haversine formula 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    if debug == 0:
        print("angle=%s rad or %s deg" % (c, degrees(c)))

    # if we want the distance in meter
    # 6378137f meters is the radius of the Earth
    # meters = 6378137f * c
    return c


#
# return the lat and lon of several lat and lon coordinates
#
# latInDegr and lonInDegr are list of lat and lon
#
def getLatLngCenter(latInDegr, lonInDegr):
    sumX = 0
    sumY = 0
    sumZ = 0

    for i in range(len(latInDegr)):
        lat = deg2rad(latInDegr[i])
        lng = deg2rad(lonInDegr[i])
        # sum of cartesian coordinates
        sumX = sumX + cos(lat) * cos(lng)
        sumY = sumY + cos(lat) * sin(lng)
        sumZ = sumZ + sin(lat)

    avgX = sumX / len(latInDegr)
    avgY = sumY / len(latInDegr)
    avgZ = sumZ / len(latInDegr)

    # convert average x, y, z coordinate to latitude and longtitude
    lng = atan2(avgY, avgX)
    hyp = sqrt(avgX * avgX + avgY * avgY)
    lat = atan2(avgZ, hyp)

    return rad2deg(lat), rad2deg(lng)


#
# input: x(lon), y(lat) angle in radians
# returns: polar-angle (theta, rho) , azimuth-angle (phi) in radian
#
def cart2polNp(x, y):
    rho = np.sqrt(x ** 2 + y ** 2)
    phi = np.arctan2(y, x)
    # return(float(rho), float(phi))
    return rho, phi


#
# input: polar-angle (theta) , azimuth-angle (phi) in radian
# returns: x(lon), y(lat) angle in radians
#
def pol2cartNp(rho, phi):
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    # return(float(x), float(y))
    return x, y


#
#
#
def rad2degNp(r):
    return np.degrees(r)


#
#
#
def deg2radNp(r):
    return np.radians(r)


def myRad2Deg(r):
    aDegree = r * (180 / math.pi)
    return aDegree


def myDeg2Rad(d):
    aRadian = d * (math.pi / 180)
    return aRadian


def pol2cart2(r, theta):
    """
    Parameters:
    - r: float, vector amplitude
    - theta: float, vector angle
    Returns:
    - x: float, x coord. of vector end
    - y: float, y coord. of vector end
    """

    z = r * np.exp(1j * theta)
    x, y = z.real, z.imag

    return x, y


def cart2pol2(x, y):
    """
    Parameters:
    - x: float, x coord. of vector end
    - y: float, y coord. of vector end
    Returns:
    - r: float, vector amplitude
    - theta: float, vector angle
    """

    z = x + y * 1j
    r, theta = np.abs(z), np.angle(z)

    return r, theta


#
"""
Note that "Lat/Lon/Alt" is just another name for spherical coordinates,
 and phi/theta/rho are just another name for latitude, longitude, and altitude. 
 (A minor difference: altitude is usually measured from the surface of the sphere; rho is measured from the center -- to convert, just add/subtract the radius of the sphere.)
"""


#
# params: theta (lon) rad, phi (lat) rad, radius
# returns x, y , z
# 2021 OK
def spericalToCartesian(theta, phi, r):
    x = r * sin(theta) * cos(phi)
    y = r * sin(theta) * sin(phi)
    z = r * cos(theta)
    return x, y, z


#
# params: x , y , z
# returns: theta, phi, r (lon, lat, r)
# 2021 OK
def cartesianToSperical(x, y, z):
    r = math.sqrt(x ** 2 + y ** 2 + z ** 2)
    theta = math.acos(z / r)
    phi = math.atan2(y, x)
    return theta, phi, r


if __name__ == '__main__':

    lat = 30.98
    lon = 13.34
    z = 12345
    # print("myDeg2Rad %s=%s" % (90, myDeg2Rad(90)))
    # print("myDeg2Rad %s=%s" % (lat, myDeg2Rad(lat)))

    theta, phi, r = cartesianToSperical(deg2rad(lon), deg2rad(lat), z)
    print("cartesianToSperical: theta (lon): %s; phi (lat): %s; z: %s" % (phi, theta, r))

    x, y, z = spericalToCartesian(theta, phi, r)
    print("spericalToCartesian: x (lon)=%s; y (lat)=%s; z=%s" % (rad2deg(x), rad2deg(y), z))

    rho, phi = cart2pol2(deg2rad(lon), deg2rad(lat))
    lon1, lat1 = pol2cart2(rho, phi)
    print("cart2pol lat=%s lon=%s -> rho:%s; phi:%s" % (lat, lon, rho, phi))
    print("pol2cart reverse it       -> lat:%s; lon:%s" % (lat, lon))


    print("sphericalDistance (90,0) vs (0,0):%s" % sphericalDistance(90, 0, 0, 0))
    print("metersDistanceBetween (90,0) vs (0,0):%s" % metersDistanceBetween(90, 0, 0, 0))

    p1 = array([0.0, 0.0])
    p2 = array([1.0, 0.0])

    p3 = array([4.0, -5.0])
    p4 = array([4.0, 2.0])

    print("intersect test 1:%s" % seg_intersect(p1, p2, p3, p4))

    p1 = array([2.0, 2.0])
    p2 = array([4.0, 3.0])

    p3 = array([6.0, 0.0])
    p4 = array([6.0, 3.0])

    print(seg_intersect(p1, p2, p3, p4))
    print("intersect test 2:%s" % seg_intersect(p1, p2, p3, p4))

    p1 = array([0.0, 0.0])
    p2 = array([4.0, 0.0])

    p3 = array([0.0, 5.0])
    p4 = array([1.0, 4.0])

    print(seg_intersect(p1, p2, p3, p4))
    print("intersect test 3:%s" % seg_intersect(p1, p2, p3, p4))

    # CW:
    # poly='43.505158383 -9.7328153269 43.400659479 -8.9829417472 42.876066318 -9.1602073246 42.979779308 -9.903779609 43.505158383 -9.7328153269'
    # poly='43.5 -9.73 43.4 -8.98 42.88 -9.16 42.98 -9.9 43.5 -9.73'
    # CCW
    poly = '0.43 112.969 -0.421 112.969 -0.421 113.443 0.43 113.443 0.43 112.969'

    toks = poly.split(' ')
    f = []
    totAngle = 0
    for item in toks:
        f.append(float(item))
    for i in range((len(f) // 2) - 1):
        n = i * 2
        # print "\n\nn:%s  len(f):%d" % (n, len(f))
        y1 = f[n]
        x1 = f[n + 1]
        nn = n + 2

        # We come back to the first point, so use the next one to build the
        # second angle?? normally should never be the case because it's the next
        # test the good one
        if nn >= len(f):
            print("0 nn=%s>%s so set to:%s" % (nn, len(f), nn - len(f)))
            nn = nn - len(f) + 2

        y2 = f[nn]
        x2 = f[nn + 1]
        nn = nn + 2

        # This should be the good test: we come back to the first point, so use
        # the next one to build the second angle
        if nn >= len(f):
            print("1 nn=%s>%s so set to:%s" % (nn, len(f), nn - len(f) + 2))
            nn = nn - len(f) + 2
        y3 = f[nn]
        x3 = f[nn + 1]
        print("do point[%s]:%s %s vs %s %s vs %s %s " % (n, x1, y1, x2, y2, x3, y3))
        v1 = vector2D.Vec2d(x2 - x1, y2 - y1)
        v2 = vector2D.Vec2d(x3 - x2, y3 - y2)
        # print "\nv1=%s" % v1
        # print "v2=%s" % v2
        angle = v2.get_angle_between(v1)
        print(">>>>>>>>>>>angle:%f" % v2.get_angle_between(v1))
        totAngle = totAngle + angle
    print("\n\n\ntotal angle=%s\n\n" % totAngle)

    print("distance:%s" % metersDistanceBetween(0.43, 112.969, -0.421, 142.969))
    print("middle:lat=%s; lon=%s" % coordinateBetween(0.43, 112.969, -40.421, 142.969))

    # v = Vec2d(3,4)
    # v1=makeVector(0,30)
    # print "length:%s" % get_length(v1)
