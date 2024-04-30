import math
import random
import numpy as np
from scipy.optimize import minimize
#from math import pi, cos, sin

def get_ellipse(center, major, ratio, rotation, n_points):
    rotation_radians = rotation / 360 * 2 * math.pi
    rsin, rcos = math.sin(rotation_radians), math.cos(rotation_radians)

    xy = [(math.cos(th)  * major, math.sin(th) * major * ratio )
        for th in [i * (2 * math.pi) / n_points for i in range(n_points)] ]
    xy = [(x * rcos - y * rsin, x * rsin + y * rcos) for x, y in xy]
    xy = [(x + center[0], y + center[1]) for x, y in xy]
    return xy


def get_random_ellipse(center, n_points):

    major = random.uniform(40, 300)
    ratio = random.uniform(.1, 1)
    rotation = random.uniform(0, 360)

    xy = get_ellipse(center, major, ratio, rotation, n_points)
    return xy


def get_best_ellipse(points):

    # we need to reweight the points because they may have different concentrations
    # a point will have a weight related to the average distance to the previous and
    # the next point in the path

    d0 = points.diff().fillna(0) ** 2
    d1 = points.diff(-1).fillna(0) ** 2

    d0 = np.sqrt(d0.x + d0.y)
    d1 = np.sqrt(d1.x + d1.y)
    d = ((d0 + d1) / 2)

    my_points = points.to_numpy()
    my_center = ((my_points[:, 0] * d).sum() / sum(d),
                 (my_points[:, 1] * d).sum() / sum(d))

    def error(parms):
        major, ratio, rotation = parms
        xy = get_ellipse(my_center, major, ratio, rotation, len(points))
        xy = np.array(xy)

        dists_x = np.subtract.outer(my_points[:, 0], xy[:, 0])
        dists_y = np.subtract.outer(my_points[:, 1], xy[:, 1])
        dists = dists_x**2 + dists_y**2
        out = dists.min(axis=0).sum()
        return out

    out = minimize(error, np.array([300, .5, 45]), method='Nelder-Mead', tol=1e-6)

    out = {
        'center': my_center,
        'major': out['x'][0],
        'ratio': out['x'][1],
        'rotation': out['x'][2]
    }
    return out


# taken from https://scipython.com/blog/direct-linear-least-squares-fitting-of-an-ellipse/

def fit_ellipse(x, y):
    """

    Fit the coefficients a,b,c,d,e,f, representing an ellipse described by
    the formula F(x,y) = ax^2 + bxy + cy^2 + dx + ey + f = 0 to the provided
    arrays of data points x=[x1, x2, ..., xn] and y=[y1, y2, ..., yn].

    Based on the algorithm of Halir and Flusser, "Numerically stable direct
    least squares fitting of ellipses'.


    """

    D1 = np.vstack([x**2, x*y, y**2]).T
    D2 = np.vstack([x, y, np.ones(len(x))]).T
    S1 = D1.T @ D1
    S2 = D1.T @ D2
    S3 = D2.T @ D2
    T = -np.linalg.inv(S3) @ S2.T
    M = S1 + S2 @ T
    C = np.array(((0, 0, 2), (0, -1, 0), (2, 0, 0)), dtype=float)
    M = np.linalg.inv(C) @ M
    eigval, eigvec = np.linalg.eig(M)
    con = 4 * eigvec[0]* eigvec[2] - eigvec[1]**2
    ak = eigvec[:, np.nonzero(con > 0)[0]]
    return np.concatenate((ak, T @ ak)).ravel()


def cart_to_pol(coeffs):
    """

    Convert the cartesian conic coefficients, (a, b, c, d, e, f), to the
    ellipse parameters, where F(x, y) = ax^2 + bxy + cy^2 + dx + ey + f = 0.
    The returned parameters are x0, y0, ap, bp, e, phi, where (x0, y0) is the
    ellipse centre; (ap, bp) are the semi-major and semi-minor axes,
    respectively; e is the eccentricity; and phi is the rotation of the semi-
    major axis from the x-axis.

    """

    # We use the formulas from https://mathworld.wolfram.com/Ellipse.html
    # which assumes a cartesian form ax^2 + 2bxy + cy^2 + 2dx + 2fy + g = 0.
    # Therefore, rename and scale b, d and f appropriately.
    a = coeffs[0]
    b = coeffs[1] / 2
    c = coeffs[2]
    d = coeffs[3] / 2
    f = coeffs[4] / 2
    g = coeffs[5]

    den = b**2 - a*c
    if den > 0:
        raise ValueError('coeffs do not represent an ellipse: b^2 - 4ac must'
                         ' be negative!')

    # The location of the ellipse centre.
    x0, y0 = (c*d - b*f) / den, (a*f - b*d) / den

    num = 2 * (a*f**2 + c*d**2 + g*b**2 - 2*b*d*f - a*c*g)
    fac = np.sqrt((a - c)**2 + 4*b**2)
    # The semi-major and semi-minor axis lengths (these are not sorted).
    ap = np.sqrt(num / den / (fac - a - c))
    bp = np.sqrt(num / den / (-fac - a - c))

    # Sort the semi-major and semi-minor axis lengths but keep track of
    # the original relative magnitudes of width and height.
    width_gt_height = True
    if ap < bp:
        width_gt_height = False
        ap, bp = bp, ap

    # The eccentricity.
    r = (bp/ap)**2
    if r > 1:
        r = 1/r
    e = np.sqrt(1 - r)

    # The angle of anticlockwise rotation of the major-axis from x-axis.
    if b == 0:
        phi = 0 if a < c else np.pi/2
    else:
        phi = np.arctan((2.*b) / (a - c)) / 2
        if a > c:
            phi += np.pi/2
    if not width_gt_height:
        # Ensure that phi is the angle to rotate to the semi-major axis.
        phi += np.pi/2
    phi = phi % np.pi

    return x0, y0, ap, bp, e, phi


def get_best_ellipse_alt(points):

    tmp = fit_ellipse(points[0], points[1])
    x0, y0, ap, bp, e, phi = cart_to_pol(tmp)

    out = {
        'center': [x0, y0],
        'major': ap,
        'ratio': bp / ap,
        'rotation': phi * 180 / np.pi
    }

    return out