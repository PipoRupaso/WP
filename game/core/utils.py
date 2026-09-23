# -*- coding: utf-8 -*-
"""Мелкие утилиты: хэш-шум, clamp, интерполяция, выпуклая оболочка."""


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def hash01(a, b, c=0):
    h = (int(a * 73856093) ^ int(b * 19349663) ^ int(c * 83492791)) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return (h % 10000) / 10000.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_pt(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def quad_pt(q, u, t):
    top = lerp_pt(q[0], q[1], u)
    bot = lerp_pt(q[3], q[2], u)
    return lerp_pt(top, bot, t)


def convex_hull(points):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def unrot_vec(a, b, rot):
    if rot == 0:
        return (a, b)
    if rot == 1:
        return (b, -a)
    if rot == 2:
        return (-a, -b)
    return (-b, a)
