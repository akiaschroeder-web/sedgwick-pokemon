"""NLCD rasters (Albers Equal Area, 30 m) sampled onto the county tile grid.
Pure Python Albers forward projection (WGS84 ellipsoid), no pyproj."""
import math
import numpy as np
from PIL import Image

A, F = 6378137.0, 1 / 298.257223563
E2 = 2 * F - F * F
E = math.sqrt(E2)


def _q(phi):
    s = math.sin(phi)
    return (1 - E2) * (s / (1 - E2 * s * s) - (1 / (2 * E)) * math.log((1 - E * s) / (1 + E * s)))


def _m(phi):
    s = math.sin(phi)
    return math.cos(phi) / math.sqrt(1 - E2 * s * s)


class Albers:
    def __init__(self, lat1, lat2, lat0, lon0):
        p1, p2, p0 = map(math.radians, (lat1, lat2, lat0))
        m1, m2 = _m(p1), _m(p2)
        q1, q2, q0 = _q(p1), _q(p2), _q(p0)
        self.n = (m1 * m1 - m2 * m2) / (q2 - q1)
        self.C = m1 * m1 + self.n * q1
        self.r0 = A * math.sqrt(self.C - self.n * q0) / self.n
        self.lon0 = math.radians(lon0)

    def fwd(self, lon, lat):
        """Vectorised: numpy arrays of degrees -> (x, y) metres."""
        phi = np.radians(lat)
        s = np.sin(phi)
        q = (1 - E2) * (s / (1 - E2 * s * s) - (1 / (2 * E)) * np.log((1 - E * s) / (1 + E * s)))
        r = A * np.sqrt(self.C - self.n * q) / self.n
        th = self.n * (np.radians(lon) - self.lon0)
        return r * np.sin(th), self.r0 - r * np.cos(th)


class Raster:
    def __init__(self, path):
        im = Image.open(path)
        t = im.tag_v2
        self.sx, self.sy = t[33550][0], t[33550][1]
        tp = t[33922]
        self.x0, self.y0 = tp[3] - tp[0] * self.sx, tp[4] + tp[1] * self.sy
        d = t[34736]       # lat1, lat2, lat0, lon0, fe, fn, invf, a
        self.proj = Albers(d[0], d[1], d[2], d[3])
        self.fe, self.fn = d[4], d[5]
        self.a = np.array(im)
        self.nodata = int(t.get(42113, 255))

    def sample(self, lon, lat):
        x, y = self.proj.fwd(lon, lat)
        c = np.floor((x + self.fe - self.x0) / self.sx).astype(int)
        r = np.floor((self.y0 - (y + self.fn)) / self.sy).astype(int)
        ok = (c >= 0) & (r >= 0) & (c < self.a.shape[1]) & (r < self.a.shape[0])
        out = np.full(lon.shape, self.nodata, self.a.dtype)
        out[ok] = self.a[r[ok], c[ok]]
        return out

    def bounds_lonlat(self):
        """Rough lon/lat extent (by searching corners)."""
        import itertools
        return None
