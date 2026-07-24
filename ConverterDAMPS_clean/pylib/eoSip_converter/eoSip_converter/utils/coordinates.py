from __future__ import annotations

import matplotlib.pylab as plt
from dataclasses import dataclass
from math import acos, atan, atan2, cos, degrees, pi, radians, sin
from pathlib import Path
from typing import List, Optional, Tuple, Union


@dataclass
class ReferenceFrame:
    """Ellipsoid reference frame.

    Attributes
    ----------
    a : float
        Semi-major axis [m]
    inverse_f : float
        Inverse flattening (1 / f)
    epoch : float
        Reference epoch [yr]
    name : str
        Human-readable frame name
    """
    a: float
    inverse_f: float
    epoch: float
    name: str

    @classmethod
    def from_string(cls, name: str) -> ReferenceFrame:
        available_properties = {
            'WGS84': {
                'a': 6378137.0,
                'inverse_f': 298.257223563,
                'epoch': 2021.0,
            },
            'ITRF2014': {
                'a': 6378137.0,
                'inverse_f': 298.257222101,
                'epoch': 2010.0,
            },
            'ETRS89': {
                'a': 6378137.0,
                'inverse_f': 298.257222101,
                'epoch': 1989.0,
            },
            'NAD83': {
                'a': 6378137.0,
                'inverse_f': 298.257222101,
                'epoch': 2010.0,
            },

        }

        name = name.upper()

        available_frames = list(available_properties.keys())
        if name not in available_frames:
            available_frames_str = "'" + "', '".join(available_frames[:-1]) + f"', or '{available_frames[-1]}'"
            raise ValueError(f"'{name}' frame not available. Must be one of {available_frames_str}")

        properties = available_properties[name]
        properties['name'] = name

        return cls(**properties)

    @property
    def f(self) -> float:
        return 1.0 / self.inverse_f

    @property
    def b(self) -> float:
        return self.a - self.a * self.f

    @property
    def e(self) -> float:
        """Eccentricity"""
        return (1.0 - (self.b ** 2.0 / self.a ** 2.0)) ** 0.5

    def n(self, lat_deg: float) -> float:
        """Radius of curvature (m)"""
        lat_rad = radians(lat_deg)

        return self.a / (1.0 - self.e ** 2.0 * sin(lat_rad) ** 2.0) ** 0.5


class CartesianCoordinate2D:
    """Cartesian coordinate in x, and y [arbitrary]"""

    def __init__(self, x: float, y: float):
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def to_polar(self) -> PolarCoordinate:
        return PolarCoordinate(
            (self.x ** 2.0 + self.y ** 2.0) ** 0.5,
            degrees(atan2(self.y, self.x)),
        )


class PolarCoordinate:
    """Polar coordinate in r, and θ [arbitrary, deg]"""

    def __init__(self, r_m: float, theta_deg: float):
        self._r = r_m
        self._theta = theta_deg

    @property
    def r(self):
        """Distance from the origin to the coordinate [arbitrary]"""
        return self._r

    @property
    def theta(self):
        """The azimuth angle, measured CCW from the positive x-axis [deg]"""
        return self._theta

    def to_cartesian(self) -> CartesianCoordinate2D:
        return CartesianCoordinate2D(
            self.r * cos(radians(self.theta)),
            self.r * sin(radians(self.theta)),
        )


class CartesianCoordinate3D:
    """Cartesian coordinate in x, y, and z [arbitrary]"""

    def __init__(self, x: float, y: float, z: float):
        self._x = x
        self._y = y
        self._z = z

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    def to_spherical(self) -> SphericalCoordinate:
        r = (self.x ** 2.0 + self.y ** 2.0 + self.z ** 2.0) ** 0.5

        return SphericalCoordinate(
            r,
            degrees(atan2(self.y, self.x)),
            degrees(acos(self.z / r))
        )


class SphericalCoordinate:
    """Spherical coordinate in r, θ, and φ [arbitrary, deg, deg]"""

    def __init__(self, r_m: float, theta_deg: float, phi_deg: float):
        self._r = r_m
        self._theta = theta_deg
        self._phi = phi_deg

    @property
    def r(self):
        """Distance from the origin to the coordinate [arbitrary]"""
        return self._r

    @property
    def theta(self):
        """
        The azimuth angle, measured CCW from the positive x-axis
        to the projection of the point onto the xy-plane [deg]
        """
        return self._theta

    @property
    def phi(self):
        """
        The zenith angle, measured from the positive z-axis down to the line
        connecting the origin to the point [deg]
        """
        return self._phi

    def to_cartesian(self) -> CartesianCoordinate3D:
        return CartesianCoordinate3D(
            self.r * sin(radians(self.phi)) * cos(radians(self.theta)),
            self.r * sin(radians(self.phi)) * sin(radians(self.theta)),
            self.r * cos(radians(self.phi))
        )


class ECEFCoordinate(CartesianCoordinate3D):
    """Earth-centered, Earth-fixed coordinate in x, y, and z [m]"""

    def to_geodetic_coordinate(self, ref_frame: Union[str, ReferenceFrame] = 'WGS84') -> GeodeticCoordinate:
        """See https://en.wikipedia.org/wiki/Geographic_coordinate_conversion for details"""
        frame = ref_frame if isinstance(ref_frame, ReferenceFrame) else ReferenceFrame.from_string(ref_frame)

        e_prime = ((frame.a ** 2.0 - frame.b ** 2.0) / frame.b ** 2.0) ** 0.5
        p = (self.x ** 2.0 + self.y ** 2.0) ** 0.5
        F = 54.0 * frame.b ** 2.0 * self.z ** 2.0

        G = (
                p ** 2.0 +
                (1.0 - frame.e ** 2.0) * self.z ** 2.0 -
                frame.e ** 2.0 * (frame.a ** 2.0 - frame.b ** 2.0)
        )

        c = frame.e ** 4.0 * F * p ** 2.0 / G ** 3.0
        s = (1.0 + c + (c ** 2.0 + 2.0 * c) ** 0.5) ** (1.0 / 3.0)
        k = s + 1.0 + 1.0 / s

        P = F / (3.0 * k ** 2.0 * G ** 2.0)
        Q = (1.0 + 2.0 * frame.e ** 4.0 * P) ** 0.5

        r_0 = -P * frame.e ** 2.0 * p / (1.0 + Q)
        r_0 += (
                       0.5 * frame.a ** 2.0 * (1.0 + 1.0 / Q) -
                       P * (1.0 - frame.e ** 2.0) * self.z ** 2.0 / (Q * (1.0 + Q)) -
                       0.5 * P * p ** 2.0
               ) ** 0.5

        U = ((p - frame.e ** 2.0 * r_0) ** 2.0 + self.z ** 2.0) ** 0.5
        V = ((p - frame.e ** 2.0 * r_0) ** 2.0 + self.z ** 2.0 * (1.0 - frame.e ** 2.0)) ** 0.5
        z_0 = frame.b ** 2.0 * self.z / (frame.a * V)

        lat_deg = degrees(atan((self.z + e_prime ** 2.0 * z_0) / p))
        lon_deg = degrees(atan2(self.y, self.x))
        altitude = U * (1.0 - frame.b ** 2.0 / (frame.a * V))

        return GeodeticCoordinate(lat_deg, lon_deg, altitude, frame)

    def __repr__(self):
        return f"{self.__class__.__name__}(x={self.x:.1f}, y={self.y:.1f}, z={self.z:.1f})"


class GeodeticCoordinate:
    """Coordinate comprised of latitude, longitude, altitude and defined in a reference frame"""

    def __init__(self, lat_deg: float, lon_deg: float, height: float = 0.0,
                 ref_frame: Union[str, ReferenceFrame] = 'WGS84'):
        self._lat = lat_deg
        self._lon = lon_deg
        self._z = height
        self._frame = ref_frame if isinstance(ref_frame, ReferenceFrame) else ReferenceFrame.from_string(ref_frame)

    @property
    def lat(self) -> float:
        """Latitude [deg]"""
        return self._lat

    @property
    def lon(self) -> float:
        """Longitude [deg]"""
        return self._lon

    @property
    def z(self) -> float:
        """Altitude [m]"""
        return self._z

    @property
    def frame(self) -> ReferenceFrame:
        """Reference Frame coordinate is defined in"""
        return self._frame

    def bearing_to(self, coord: GeodeticCoordinate, wrapped: bool = False) -> float:
        """Return bearing (East from North) from this to another coordinate [deg]"""
        # θ = atan2( sin Δλ ⋅ cos φ2 , cos φ1 ⋅ sin φ2 − sin φ1 ⋅ cos φ2 ⋅ cos Δλ )
        dlon_deg = coord.lon - self.lon
        y = sin(radians(dlon_deg)) * cos(radians(coord.lat))
        x = cos(radians(self.lat)) * sin(radians(coord.lat))
        x -= sin(radians(self.lat)) * cos(radians(coord.lat)) * cos(radians(dlon_deg))

        bearing = degrees(atan2(y, x))

        if not wrapped:
            return bearing

        return bearing if bearing > 0 else bearing + 360.0

    def angular_separation_from(self, coord: GeodeticCoordinate) -> float:
        """Angular separation between this coordinate and another [deg]"""
        dlon_deg = coord.lon - self.lon
        dlat_deg = coord.lat - self.lat

        a = sin(radians(dlat_deg) / 2.0) ** 2.0 + cos(radians(self.lat)) * cos(radians(coord.lat)) * sin(
            radians(dlon_deg) / 2.0) ** 2.0
        c = 2.0 * atan2(a ** 0.5, (1.0 - a) ** 0.5)

        return degrees(c)

    def distance_to(self, coord: GeodeticCoordinate) -> float:
        """Distance from this coordinate to another along great circle between them [m]"""

        return radians(self.angular_separation_from(coord)) * self.frame.a

    def to_ecef(self) -> ECEFCoordinate:
        """Convert this coordinate to an ECEF coordinate"""
        N = self.frame.n(self.lat)

        return ECEFCoordinate(
            (N + self.z) * cos(radians(self.lat)) * cos(radians(self.lon)),
            (N + self.z) * cos(radians(self.lat)) * sin(radians(self.lon)),
            (N * (1.0 - self.frame.e ** 2.0) + self.z) * sin(radians(self.lat))
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(lat={self.lat:.5f}, lon={self.lon:.5f}, z={self.z:.1f}, ref_frame='{self.frame.name}')"

    @property
    def lat_dms_str(self):
        direction = 'N' if self.lon >= 0.0 else 'S'
        _, d, m, s = self._decimal_to_dms(self.lat)

        return f"{d:3}\u00B0{m:2}\u2032{s:05.2f}\u2033{direction}"

    @property
    def lon_dms_str(self):
        direction = 'E' if self.lon >= 0.0 else 'W'
        _, d, m, s = self._decimal_to_dms(self.lon)

        return f"{d:3}\u00B0{m:2}\u2032{s:05.2f}\u2033{direction}"

    def __str__(self):
        return f"{self.lat_dms_str} {self.lon_dms_str}"

    @staticmethod
    def _decimal_to_dms(decimal: float):
        direction = 1 if decimal >= 0.0 else -1
        decimal = abs(decimal)

        d = int(decimal)
        m = int((decimal - d) * 60.0)
        s = (decimal - (d + m / 60.0)) * 3600.0

        return direction, d, m, s


def bearing_to_polar_theta(bearing):
    """Convert a bearing (deg) to polar angle theta (radians) i.e. East from North to North from East (CCW from x-axis)"""
    return ((-bearing + 90.0) / 360.0) * 2.0 * pi


def wrap_angle(angle_: float) -> float:
    """Constrain an angle in degrees to the limit of 0 <= angle < 360"""
    if 0.0 <= angle_ < 360.0:
        return angle_
    elif angle_ >= 360.0:
        angle_ -= 360.0
    elif angle_ < 0.0:
        angle_ += 360.0
    return wrap_angle(angle_)


def plot_eo_outline(
    center_coord: GeodeticCoordinate,
    footprint_coords: Optional[List[GeodeticCoordinate]] = None,
    bbox_coords: Optional[List[GeodeticCoordinate]] = None,
    spacecraft_bearing: Optional[float] = None,
    image_path: Optional[Union[str, Path]] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    import logging
    import matplotlib.patheffects as path_effects
    from matplotlib.transforms import offset_copy
    from matplotlib.lines import Line2D

    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

    AZ_LINE_LENGTH = 0.4  # axes fraction

    footprint_coords = [] if footprint_coords is None else footprint_coords
    bbox_coords = [] if bbox_coords is None else bbox_coords

    plt.close('all')

    fig, ax = plt.subplots(figsize=(6, 6), dpi=300)

    ax.plot([c.lon for c in bbox_coords], [c.lat for c in bbox_coords], c='k', ls='-', marker='P', mec='k', mfc='grey', label='B-Box')
    ax.plot([c.lon for c in footprint_coords], [c.lat for c in footprint_coords], c='grey', ls='-', marker='o', mec='k', mfc='cyan', label='Footprint')
    ax.plot(center_coord.lon, center_coord.lat, mec='k', mfc='b', marker='o', label='Centre')

    for idx, coord in enumerate(footprint_coords[:-1]):
        # dist = center_coord.angular_separation_from(coord)
        # ax.plot(
        #     [center_coord.lon, center_coord.lon + dist * cos(bearing_to_polar_theta(center_coord.bearing_to(coord)))],
        #     [center_coord.lat, center_coord.lat + dist * sin(bearing_to_polar_theta(center_coord.bearing_to(coord)))],
        #     color='k', ls=':', label='_nolegend_', zorder=-2
        # )
        #
        # if idx == (len(footprint_coords) - 1) and coord == footprint_coords[0]:
        #     continue

        coord_ax_frac = ax.transAxes.inverted().transform(ax.transData.transform((coord.lon, coord.lat)))

        dxy = (12 ** 2.0 / 2.0) ** 0.5
        dx = dxy if coord_ax_frac[0] <= 0.5 else -dxy
        dy = dxy if coord_ax_frac[1] <= 0.5 else -dxy
        offset = offset_copy(ax.transData, fig=ax.figure, x=dx, y=dy, units='points')

        txt = ax.text(coord.lon, coord.lat, str(idx), transform=offset, color='cyan', va='center', ha='center', zorder=1)
        txt.set_path_effects([path_effects.Stroke(linewidth=1.5, foreground='black'), path_effects.Normal()])

    # Equalise axes (in terms of physical distances)
    current_xlims, current_ylims = ax.get_xlim(), ax.get_ylim()
    tl_coord = GeodeticCoordinate(current_ylims[1], current_xlims[0])
    tr_coord = GeodeticCoordinate(current_ylims[1], current_xlims[1])
    br_coord = GeodeticCoordinate(current_ylims[0], current_xlims[1])

    lat_ddeg = abs(tr_coord.lat - br_coord.lat)
    lon_ddeg = abs(tl_coord.lon - tr_coord.lon)
    lat_ddist = tr_coord.distance_to(br_coord)
    lon_ddist = tl_coord.distance_to(tr_coord)

    lat_m_per_deg = lat_ddist / lat_ddeg
    lon_m_per_deg = lon_ddist / lon_ddeg

    if spacecraft_bearing:
        polar_theta = ((-spacecraft_bearing + 90.0) / 360.0) * 2.0 * pi
        line_length = AZ_LINE_LENGTH * (max(lat_ddist / lat_m_per_deg, lon_ddist / lon_m_per_deg))
        ax.plot(
            [center_coord.lon, center_coord.lon + line_length * cos(polar_theta)],
            [center_coord.lat, center_coord.lat + line_length * sin(polar_theta)],
            color='r', ls='--', label='Azimuth', zorder=-1
        )

    text_proxy = Line2D(
        [0], [0], marker='$0$', ls='None', mec='black',  mfc='cyan', mew=0.5, ms=8
    )

    handles, labels = ax.get_legend_handles_labels()
    handles.append(text_proxy)
    labels.append("Order")
    ax.legend(handles=handles, labels=labels)

    if image_path:
        import rasterio
        from rasterio.plot import show
        from osgeo import gdal
        from osgeo.gdalconst import GA_ReadOnly

        ds = gdal.Open(str(image_path), GA_ReadOnly)

        with rasterio.open(image_path) as src:
            image = src.read(1)  # or read all bands with src.read() if RGB
            bounds = src.bounds

            # extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
            # latlon_coords = gdal.Info(ds, format='json')['wgs84Extent']['coordinates'][0]
            # extent = (
            #     min([c[0] for c in latlon_coords]), max([c[0] for c in latlon_coords]),
            #     min([c[1] for c in latlon_coords]), max([c[1] for c in latlon_coords])
            # )
            extent = (111.678305, 136.2696695, 71.46624, 76.9318807)
            # Flip vertically if needed depending on image orientation
            plt.imshow(image, cmap='gist_gray', extent=extent, origin='upper')
            # show(src, ax=ax, extent=extent, zorder=-10)

    if lat_ddist > lon_ddist:
        midpoint = center_coord.lon
        dx = lat_ddist / lon_m_per_deg / 2.0
        ax.set_xlim(midpoint - dx, midpoint + dx)
    elif lon_ddist > lat_ddist:
        midpoint = center_coord.lat
        dy = lon_ddist / lat_m_per_deg / 2.0
        ax.set_ylim(midpoint - dy, midpoint + dy)

    ax.set_aspect(lat_m_per_deg / lon_m_per_deg)
    ax.set_xlabel(r'Longitude [deg]')
    ax.set_ylabel(r'Latitude [deg]')
    ax.minorticks_on()
    ax.tick_params(
        axis='both', which='both', direction='in',
        top=True, bottom=True, left=True, right=True,
        labeltop=True, labelbottom=True, labelleft=True, labelright=True
    )

    return fig, ax


if __name__ == '__main__':
    tl = GeodeticCoordinate(14.2865, -1.81419)
    bl = GeodeticCoordinate(12.75599, -1.81419)
    print(tl.distance_to(bl))
    footprint_raw_data = """77.10126,117.40639
    72.85496,114.38119
    71.63476,128.28027
    75.59612,135.01199"""

    bbox_raw_data = """77.10126,114.38119
    71.63476,114.38119
    71.63476,135.01199
    77.10126,135.01199"""

    def sort_function(origin, coord, azimuth=0.0, ccw: bool = True) -> float:
        angle = wrap_angle(origin.bearing_to(coord) * (-1 if ccw else 1))
        angle = wrap_angle(angle + azimuth * (1 if ccw else -1))

        return angle


    center = GeodeticCoordinate(74.28333, 123.76667)
    print(center.bearing_to(GeodeticCoordinate(center.lat, center.lon - 0.1)))

    azimuth = None#'-10.61333  # Direction to spacecraft from center of image (West from North)

    footprint_data = [item.strip() for line in footprint_raw_data.split('\n') for item in line.split(',')]
    footprint_lats = [float(footprint_data[i * 2]) for i in range(len(footprint_data) // 2)]
    footprint_lons = [float(footprint_data[i * 2 + 1]) for i in range(len(footprint_data) // 2)]
    footprint_coords = [GeodeticCoordinate(lat, lon) for lat, lon in zip(footprint_lats, footprint_lons)]
    # footprint_coords = sorted(footprint_coords, key=lambda c: sort_function(center, c, azimuth, True))
    footprint_coords = footprint_coords + [footprint_coords[0]]

    bbox_data = [item.strip() for line in bbox_raw_data.split('\n') for item in line.split(',')]
    bbox_lats = [float(bbox_data[i * 2]) for i in range(len(bbox_data) // 2)]
    bbox_lons = [float(bbox_data[i * 2 + 1]) for i in range(len(bbox_data) // 2)]
    bbox_coords = [GeodeticCoordinate(lat, lon) for lat, lon in zip(bbox_lats, bbox_lons)]
    # bbox_coords = sorted(bbox_coords, key=lambda c: sort_function(center, c, azimuth, True))
    bbox_coords = bbox_coords + [bbox_coords[0]]

    image_path = Path('/mount/damps/hsm/PSI/TPM_EOSIP/work/RADARSAT1-PRODUCTS/DL271_RADARSAT_MDA_TPM_L1/DL271A_StartContract_Q42016/StartContract_Q42016/RSAT-1/15-00101/25Aug97_09438_01.tif')
    image_path = Path('/mount/damps/hsm/PSI/TPM_EOSIP/test_datasets/converted/radarsat1/out/unzipped/RS1_OPER_SAR_SW_SCW_19970825T224543_N74-283_E123-766_0000.BI.PNG')
    fig, ax = plot_eo_outline(center, footprint_coords, bbox_coords, spacecraft_bearing=azimuth, image_path=image_path)
    fig.show()
    fig.savefig('/home/converter/test.pdf', dpi=300, bbox_inches='tight')
