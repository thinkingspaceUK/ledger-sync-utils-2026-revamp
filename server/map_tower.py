"""
The Penthouse: three floors of a luxury apartment at the top of a skyscraper.

Levels 67, 68 and 69 of a glass tower, joined by a lift and a switchback stair
in the core. 67 is the living floor: an open-plan great room, kitchen and
dining room, a study, a games room, and the terrace with the pool. 68 is the
bedrooms: the master suite with its bath and dressing room, a cinema room,
two guest rooms. 69 is the sky lounge: the bar, a library, a gym and a spa.
Every outside wall is glass from floor to ceiling, and every pane breaks: shoot
it or jump at it and it is gone, and so are you if you keep going, because
outside there is nothing but the city two hundred and fifty metres down.

The city round it is drawn by the client from a seed ('skyline' deco); only
the tower itself is solid. The street is the map's ground, far below, and a
player who falls past the 'void' height is dead before they land.
"""

import math

from mapgen import Town, rot, STEP_D

FLOOR = 3.6                     # storey height
SLAB = 0.3                      # a floor slab, structure and finish
CEIL = FLOOR - SLAB             # clear height, floor to the slab above
HW, HD = 20.0, 13.0             # half size of the indoor floors
IN_X, IN_Z = HW - 0.12, HD - 0.12   # the inside face of the glass line
TER_D = 12.0                    # the terrace runs this far south of the glass
STREET = -250.0                 # the city's ground, under the tower
VOID = -90.0                    # a fall past this is the end
ROOF = 3 * FLOOR
LEVELS = (0.0, FLOOR, 2 * FLOOR)
NAMES = ('67', '68', '69')
WT = 0.2                        # an inside wall
BAY = 2.5                       # glass panes this wide between the mullions
RISE = FLOOR / 14               # a stair step
LIFT_X0, LIFT_X1 = -1.2, 1.2    # the lift car, inside
LIFT_Z0, LIFT_Z1 = -12.7, -10.3
LIFT_W, LIFT_H = 1.3, 2.2       # its doors
ST_X0, ST_X1 = 1.55, 5.75       # the stairwell, inside
ST_Z0, ST_Z1 = -12.7, -8.3
ST_MID = (ST_X0 + ST_X1) / 2
TOWER_Z = (-HD + HD + TER_D) / 2    # the lower body's centre: it carries the terrace too
TOWER_HD = (2 * HD + TER_D) / 2


class Tower(Town):
    kind = 'tower'
    name = 'The Penthouse'
    theme = 'city'
    trim_buildings = False

    def __init__(self, seed):
        Town.__init__(self, seed)
        self.bx, self.bz = 60.0, 60.0
        self.spots = []            # (x, y, z) places someone can stand, for spawns
        self.lights = []

    # -- primitives ---------------------------------------------------------------

    def lb(self, x0, x1, y0, y1, z0, z1, mat='paint', tint=0, yaw=0.0):
        """A box by its extents (world x and z, absolute y)."""
        if x1 - x0 > 0.01 and y1 - y0 > 0.01 and z1 - z0 > 0.01:
            self.box((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2, yaw, mat, tint)

    def dd(self, k, x, y, z, **kw):
        d = {'k': k, 'x': round(x, 2), 'y': round(y, 2), 'z': round(z, 2)}
        d.update(kw)
        self.deco.append(d)

    def wall(self, axis, at, lo, hi, y0, y1, doors=(), mat='paint', tint=0, t=WT, dh=2.2):
        """An inside wall: along x at z = at ('z') or along z at x = at ('x'), from lo to hi,
        with a hinged door in each (u, w) gap and the wall carried on over the door."""
        cur = lo
        for (u, w) in sorted(doors):
            if axis == 'z':
                self.lb(cur, u - w / 2, y0, y1, at - t / 2, at + t / 2, mat, tint)
                self.lb(u - w / 2, u + w / 2, y0 + dh, y1, at - t / 2, at + t / 2, mat, tint)
                self.door_leaf(u, y0, at, 0.0, w, dh)
            else:
                self.lb(at - t / 2, at + t / 2, y0, y1, cur, u - w / 2, mat, tint)
                self.lb(at - t / 2, at + t / 2, y0 + dh, y1, u - w / 2, u + w / 2, mat, tint)
                self.door_leaf(at, y0, u, math.pi / 2, w, dh)
            cur = u + w / 2
        if axis == 'z':
            self.lb(cur, hi, y0, y1, at - t / 2, at + t / 2, mat, tint)
        else:
            self.lb(at - t / 2, at + t / 2, y0, y1, cur, hi, mat, tint)

    def opening(self, axis, at, lo, hi, y0, y1, u, w, mat='paint', tint=0, t=WT, dh=2.3):
        """A wall with a doorless opening: a wide way through, the wall over it."""
        if axis == 'z':
            self.lb(lo, u - w / 2, y0, y1, at - t / 2, at + t / 2, mat, tint)
            self.lb(u + w / 2, hi, y0, y1, at - t / 2, at + t / 2, mat, tint)
            self.lb(u - w / 2, u + w / 2, y0 + dh, y1, at - t / 2, at + t / 2, mat, tint)
        else:
            self.lb(at - t / 2, at + t / 2, y0, y1, lo, u - w / 2, mat, tint)
            self.lb(at - t / 2, at + t / 2, y0, y1, u + w / 2, hi, mat, tint)
            self.lb(at - t / 2, at + t / 2, y0 + dh, y1, u - w / 2, u + w / 2, mat, tint)

    @staticmethod
    def pieces(x0, x1, z0, z1, holes):
        """A rectangle less some rectangular holes, as rectangles."""
        xs = sorted({x0, x1} | {h[0] for h in holes} | {h[1] for h in holes})
        xs = [x for x in xs if x0 <= x <= x1]
        out = []
        for (a, b) in zip(xs, xs[1:]):
            zs = sorted({z0, z1} | {h[2] for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6} | {h[3] for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6})
            zs = [z for z in zs if z0 <= z <= z1]
            for (c, d) in zip(zs, zs[1:]):
                mx, mz = (a + b) / 2, (c + d) / 2
                if any(h[0] < mx < h[1] and h[2] < mz < h[3] for h in holes):
                    continue
                out.append((a, b, c, d))
        return out

    def slab(self, x0, x1, z0, z1, y, holes=(), finish='marble', tint=0):
        """A floor whose top is at y: the structure, white underneath (the ceiling of the
        room below), and the finish on top."""
        for (a, b, c, d) in self.pieces(x0, x1, z0, z1, list(holes)):
            self.lb(a, b, y - SLAB, y - 0.06, c, d, 'paint', 0)
            self.lb(a, b, y - 0.06, y, c, d, finish, tint)

    def finish(self, x0, x1, z0, z1, y, mat, tint=0):
        """A different floor finish over part of a slab (laid on it, 2 cm proud)."""
        self.lb(x0, x1, y, y + 0.02, z0, z1, mat, tint)

    def spot(self, x, y, z):
        self.spots.append((round(x, 2), round(y, 2), round(z, 2)))

    def area(self, n, x, z, y, r):
        self.areas.append({'n': n, 'x': round(x, 1), 'z': round(z, 1), 'y': round(y, 2), 'r': r})

    # -- furniture ----------------------------------------------------------------

    def sofa(self, x, z, yaw, y, w=2.4, c=0):
        self.box(x, y + 0.22, z, w / 2, 0.22, 0.48, yaw, 'leather', c)
        ox, oz = rot(0, -0.34, yaw)
        self.box(x + ox, y + 0.6, z + oz, w / 2, 0.22, 0.14, yaw, 'leather', c)
        for sx in (-1, 1):
            ax, az = rot(sx * (w / 2 - 0.1), 0, yaw)
            self.box(x + ax, y + 0.52, z + az, 0.1, 0.1, 0.46, yaw, 'leather', c)

    def armchair(self, x, z, yaw, y, c=0):
        self.sofa(x, z, yaw, y, 1.0, c)

    def table(self, x, z, hx, hz, y, h=0.72, mat='walnut', tint=0, yaw=0.0):
        self.box(x, y + h - 0.03, z, hx, 0.03, hz, yaw, mat, tint)
        for (sx, sz) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            ox, oz = rot(sx * (hx - 0.1), sz * (hz - 0.1), yaw)
            self.box(x + ox, y + (h - 0.06) / 2, z + oz, 0.04, (h - 0.06) / 2, 0.04, yaw, 'chrome', 0)

    def coffee(self, x, z, y, hx=0.7, hz=0.45, yaw=0.0):
        self.box(x, y + 0.2, z, hx, 0.03, hz, yaw, 'marble', 1)
        self.box(x, y + 0.085, z, hx - 0.25, 0.085, hz - 0.2, yaw, 'chrome', 1)

    def chair(self, x, z, yaw, y, c=1):
        self.box(x, y + 0.23, z, 0.24, 0.23, 0.24, yaw, 'leather', c)
        ox, oz = rot(0, -0.2, yaw)
        self.box(x + ox, y + 0.7, z + oz, 0.24, 0.24, 0.04, yaw, 'leather', c)

    def stool(self, x, z, y):
        self.box(x, y + 0.33, z, 0.04, 0.33, 0.04, 0, 'chrome', 0)
        self.box(x, y + 0.7, z, 0.2, 0.04, 0.2, 0, 'leather', 2)

    def bed(self, x, z, yaw, y, w=2.0, c=1):
        """A bed, its head towards -local z."""
        d = 2.1
        self.box(x, y + 0.25, z, w / 2, 0.25, d / 2, yaw, 'fabric', c)
        hx, hz = rot(0, -d / 2 - 0.05, yaw)
        self.box(x + hx, y + 0.6, z + hz, w / 2 + 0.05, 0.6, 0.05, yaw, 'walnut', 0)
        px, pz = rot(0, -d / 2 + 0.35, yaw)
        self.box(x + px, y + 0.57, z + pz, w / 2 - 0.15, 0.07, 0.25, yaw, 'fabric', 3)
        for sx in (-1, 1):
            nx, nz = rot(sx * (w / 2 + 0.45), -d / 2 + 0.3, yaw)
            self.box(x + nx, y + 0.25, z + nz, 0.28, 0.25, 0.25, yaw, 'walnut', 0)

    def wardrobe(self, x0, x1, z0, z1, y):
        self.lb(x0, x1, y, y + 2.4, z0, z1, 'walnut', 0)

    def counter(self, x0, x1, z0, z1, y, top='marble', tint=1, h=0.9):
        self.lb(x0, x1, y, y + h - 0.04, z0, z1, 'lacquer', 0)
        self.lb(x0 - 0.02, x1 + 0.02, y + h - 0.04, y + h, z0 - 0.02, z1 + 0.02, top, tint)

    def cupboards(self, x0, x1, z0, z1, y):
        self.lb(x0, x1, y + 1.5, y + 2.3, z0, z1, 'lacquer', 0)

    def appliance(self, x0, x1, z0, z1, y, h=2.0):
        self.lb(x0, x1, y, y + h, z0, z1, 'chrome', 0)

    def tv(self, x, z, yaw, y, w=2.4, h=1.3, up=1.0):
        ox, oz = rot(0, 0.04, yaw)
        self.box(x + ox, y + up + h / 2, z + oz, w / 2, h / 2, 0.03, yaw, 'lacquer', 0)

    def fireplace(self, x, z, yaw, y, w=3.0):
        # a stone surround with a dark hearth, on a wall whose inside is towards +local z
        self.box(x, y + 0.6, z, w / 2, 0.6, 0.22, yaw, 'marble', 1)
        ox, oz = rot(0, 0.2, yaw)
        self.box(x + ox, y + 0.5, z + oz, 0.7, 0.45, 0.06, yaw, 'lacquer', 0)

    def bookcase(self, x0, x1, z0, z1, y, h=2.6):
        self.lb(x0, x1, y, y + h, z0, z1, 'walnut', 0)
        along_x = (x1 - x0) > (z1 - z0)
        self.dd('books', (x0 + x1) / 2, y, (z0 + z1) / 2, w=round(max(x1 - x0, z1 - z0), 2), yaw=0.0 if along_x else round(math.pi / 2, 4))

    def tub(self, x, z, yaw, y):
        self.box(x, y + 0.3, z, 0.9, 0.3, 0.45, yaw, 'marble', 0)
        self.box(x, y + 0.56, z, 0.72, 0.02, 0.3, yaw, 'water', 0)

    def vanity(self, x0, x1, z0, z1, y, basins=2):
        self.counter(x0, x1, z0, z1, y, 'marble', 0, 0.85)
        along_x = (x1 - x0) > (z1 - z0)
        L = (x1 - x0) if along_x else (z1 - z0)
        for i in range(basins):
            u = (i + 0.5) / basins * L
            bx = x0 + u if along_x else (x0 + x1) / 2
            bz = (z0 + z1) / 2 if along_x else z0 + u
            self.box(bx, y + 0.95, bz, 0.02, 0.1, 0.02, 0, 'chrome', 0)

    def toilet(self, x, z, yaw, y):
        self.box(x, y + 0.2, z, 0.2, 0.2, 0.3, yaw, 'marble', 0)
        ox, oz = rot(0, -0.25, yaw)
        self.box(x + ox, y + 0.5, z + oz, 0.2, 0.3, 0.1, yaw, 'marble', 0)

    def shower(self, x0, x1, z0, z1, y, open_side='S'):
        """A glass cubicle, one side left open."""
        h = 2.1
        if open_side != 'N':
            self.lb(x0, x1, y, y + h, z0 - 0.03, z0 + 0.03, 'rail')
        if open_side != 'S':
            self.lb(x0, x1, y, y + h, z1 - 0.03, z1 + 0.03, 'rail')
        if open_side != 'W':
            self.lb(x0 - 0.03, x0 + 0.03, y, y + h, z0, z1, 'rail')
        if open_side != 'E':
            self.lb(x1 - 0.03, x1 + 0.03, y, y + h, z0, z1, 'rail')
        self.lb((x0 + x1) / 2 - 0.02, (x0 + x1) / 2 + 0.02, y + 1.0, y + h + 0.1, (z0 + z1) / 2 - 0.02, (z0 + z1) / 2 + 0.02, 'chrome')

    def lounger(self, x, z, yaw, y):
        self.box(x, y + 0.2, z, 0.35, 0.05, 0.95, yaw, 'fabric', 1)
        ox, oz = rot(0, -0.8, yaw)
        self.box(x + ox, y + 0.45, z + oz, 0.35, 0.22, 0.05, yaw + 0.5, 'fabric', 1)
        for sz in (-0.75, 0.75):
            px, pz = rot(0, sz, yaw)
            self.box(x + px, y + 0.08, z + pz, 0.3, 0.08, 0.03, yaw, 'chrome', 1)

    def planter(self, x, z, y, hx=0.7, hz=0.7, r=0.75):
        self.box(x, y + 0.35, z, hx, 0.35, hz, 0, 'concrete', 2)
        self.box(x, y + 0.7 + r + 0.3, z, r * 0.8, r + 0.3, r * 0.8, 0, 'inv')
        self.dd('topiary', x, y + 0.7, z, r=r)

    def rail(self, x0, x1, z0, z1, y, h=1.1):
        self.lb(x0, x1, y, y + h, z0, z1, 'rail')
        self.lb(x0 - 0.02, x1 + 0.02, y + h, y + h + 0.05, z0 - 0.02, z1 + 0.02, 'chrome', 0)

    def lamp(self, x, z, y):
        self.box(x, y + 0.75, z, 0.03, 0.75, 0.03, 0, 'chrome', 0)
        self.box(x, y + 1.6, z, 0.22, 0.14, 0.22, 0, 'fabric', 3)
        self.light('bulb', x, y + 1.55, z)

    def rug(self, x, z, y, hx, hz, c=0):
        self.dd('rug', x, y + 0.02, z, yaw=0.0, c=c)

    def painting(self, x, z, yaw, y, w=1.6, h=1.1, c=None):
        self.dd('painting', x, y, z, yaw=round(yaw, 4), w=w, h=h, c=self.rng.randrange(8) if c is None else c)

    def pooltable(self, x, z, y, yaw=0.0):
        self.box(x, y + 0.72, z, 1.35, 0.1, 0.72, yaw, 'carpet', 1)
        self.box(x, y + 0.78, z, 1.42, 0.04, 0.79, yaw, 'walnut', 0)
        for (sx, sz) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            ox, oz = rot(sx * 1.2, sz * 0.58, yaw)
            self.box(x + ox, y + 0.31, z + oz, 0.08, 0.31, 0.08, yaw, 'walnut', 0)

    def piano(self, x, z, y, yaw=0.0):
        self.box(x, y + 0.78, z, 0.8, 0.12, 0.75, yaw, 'lacquer', 0)
        self.box(x, y + 0.5, z, 0.7, 0.2, 0.6, yaw, 'lacquer', 0)
        kx, kz = rot(0, 0.95, yaw)
        self.box(x + kx, y + 0.72, z + kz, 0.72, 0.06, 0.2, yaw, 'paint', 0)
        sx, sz = rot(0, 1.5, yaw)
        self.box(x + sx, y + 0.25, z + sz, 0.45, 0.25, 0.18, yaw, 'lacquer', 0)

    def treadmill(self, x, z, yaw, y):
        self.box(x, y + 0.1, z, 0.4, 0.1, 0.95, yaw, 'lacquer', 0)
        ox, oz = rot(0, -0.85, yaw)
        self.box(x + ox, y + 0.8, z + oz, 0.38, 0.5, 0.06, yaw, 'chrome', 0)

    def weights(self, x, z, yaw, y):
        self.box(x, y + 0.08, z, 0.9, 0.08, 0.3, yaw, 'chrome', 1)
        for sx in (-1, 1):
            ox, oz = rot(sx * 0.75, 0, yaw)
            self.box(x + ox, y + 0.3, z + oz, 0.08, 0.3, 0.3, yaw, 'lacquer', 0)

    def bar(self, x0, x1, z0, z1, y):
        self.lb(x0, x1, y, y + 1.05, z0, z1, 'walnut', 0)
        self.lb(x0 - 0.1, x1 + 0.1, y + 1.05, y + 1.1, z0 - 0.1, z1 + 0.1, 'marble', 1)

    # -- the structure ---------------------------------------------------------------

    def glass_line(self, lv, side, openings=()):
        """One side of a floor, glass from floor to ceiling between steel mullions, with
        a pane in every bay that is not an opening onto the terrace."""
        y = LEVELS[lv]
        if side in ('S', 'N'):
            z = HD if side == 'S' else -HD
            length, start = 2 * HW, -HW
        else:
            z = None
            x = HW if side == 'E' else -HW
            length, start = 2 * HD, -HD
        n = int(round(length / BAY))
        bay = length / n
        yaw = 0.0 if side in ('S', 'N') else math.pi / 2
        for i in range(n + 1):
            u = start + i * bay
            if side in ('S', 'N'):
                self.box(u, y + CEIL / 2, z, 0.06, CEIL / 2, 0.06, 0, 'chrome', 1)
            else:
                self.box(x, y + CEIL / 2, u, 0.06, CEIL / 2, 0.06, 0, 'chrome', 1)
        for i in range(n):
            u0, u1 = start + i * bay, start + (i + 1) * bay
            mid = (u0 + u1) / 2
            if any(a - 0.01 <= u0 and u1 <= b + 0.01 for (a, b) in openings):
                continue
            if side in ('S', 'N'):
                self.pane(mid, y, z, yaw, bay - 0.12, CEIL)
            else:
                self.pane(x, y, mid, yaw, bay - 0.12, CEIL)
        # the slab edge outside, a dark band at every floor
        if side in ('S', 'N'):
            self.lb(-HW - 0.2, HW + 0.2, y - SLAB, y, z - 0.2, z + 0.2, 'paint', 2)
        else:
            self.lb(x - 0.2, x + 0.2, y - SLAB, y, -HD - 0.2, HD + 0.2, 'paint', 2)

    def core(self):
        """The lift shaft and the stairwell, the full height of the three floors."""
        T = 0.15
        # the shaft: west, east and north walls; the south face carries the doors
        self.lb(LIFT_X0 - T, LIFT_X0, -SLAB, ROOF, LIFT_Z0 - T, LIFT_Z1, 'paint', 2)
        self.lb(LIFT_X1, LIFT_X1 + T, -SLAB, ROOF, LIFT_Z0 - T, LIFT_Z1, 'paint', 2)
        self.lb(LIFT_X0 - T, LIFT_X1 + T, -SLAB, ROOF, LIFT_Z0 - T, LIFT_Z0, 'paint', 2)
        for lv, y in enumerate(LEVELS):
            # the door wall at this level: jambs either side of the opening, the head over it
            self.lb(LIFT_X0 - T, -LIFT_W / 2, y, y + FLOOR, LIFT_Z1, LIFT_Z1 + T, 'paint', 2)
            self.lb(LIFT_W / 2, LIFT_X1 + T, y, y + FLOOR, LIFT_Z1, LIFT_Z1 + T, 'paint', 2)
            self.lb(-LIFT_W / 2, LIFT_W / 2, y + LIFT_H, y + FLOOR, LIFT_Z1, LIFT_Z1 + T, 'paint', 2)
            # the car's floor at each level (the drawn car is the client's)
            self.lb(LIFT_X0, LIFT_X1, y - 0.12, y, LIFT_Z0, LIFT_Z1, 'inv')
            # a steel frame round the doors and the call plate beside them
            self.lb(-LIFT_W / 2 - 0.08, -LIFT_W / 2, y, y + LIFT_H + 0.08, LIFT_Z1 + T, LIFT_Z1 + T + 0.04, 'chrome', 0)
            self.lb(LIFT_W / 2, LIFT_W / 2 + 0.08, y, y + LIFT_H + 0.08, LIFT_Z1 + T, LIFT_Z1 + T + 0.04, 'chrome', 0)
            self.lb(-LIFT_W / 2 - 0.08, LIFT_W / 2 + 0.08, y + LIFT_H, y + LIFT_H + 0.08, LIFT_Z1 + T, LIFT_Z1 + T + 0.04, 'chrome', 0)
            self.lb(LIFT_W / 2 + 0.2, LIFT_W / 2 + 0.32, y + 1.0, y + 1.3, LIFT_Z1 + T, LIFT_Z1 + T + 0.03, 'chrome', 1)
        # the top of the shaft, under the roof
        self.lb(LIFT_X0 - T, LIFT_X1 + T, ROOF - 0.2, ROOF, LIFT_Z0 - T, LIFT_Z1 + T, 'paint', 2)

        # the stairwell: a wall each side the full height, open to the lobby on the south
        self.lb(LIFT_X1 + T, ST_X0, -SLAB, ROOF, ST_Z0 - T, ST_Z1, 'paint', 2)
        self.lb(ST_X1, ST_X1 + WT, -SLAB, ROOF, ST_Z0 - T, ST_Z1, 'paint', 2)
        for lv in range(2):
            y = LEVELS[lv]
            solid = lv == 0
            # flight A climbs north along the west half, the landing across the north end,
            # flight B climbs back south along the east half to the floor above
            for i in range(7):
                top = y + (i + 1) * RISE
                za = ST_Z1 - (i + 1) * STEP_D
                self.lb(ST_X0, ST_MID, (y - SLAB) if solid else top - 0.5, top, za, za + STEP_D, 'walnut', 0)
            land = y + 7 * RISE
            zl = ST_Z1 - 7 * STEP_D
            self.lb(ST_X0, ST_X1, (y - SLAB) if solid else land - 0.3, land, ST_Z0, zl, 'walnut', 0)
            for i in range(7):
                top = land + (i + 1) * RISE
                za = zl + i * STEP_D
                self.lb(ST_MID, ST_X1, (y - SLAB) if solid else top - 0.5, top, za, za + STEP_D, 'walnut', 0)
            # a handrail up the middle, and along the landing
            self.lb(ST_MID - 0.02, ST_MID + 0.02, y + 0.2, y + FLOOR + 0.9, zl, ST_Z1, 'chrome', 0)
        # the open sides of the well on the floors above: glass where the drop is
        for lv in (1, 2):
            y = LEVELS[lv]
            self.rail(ST_X0, ST_MID, ST_Z1 - 0.03, ST_Z1 + 0.03, y, 1.05)
            if lv == 2:
                self.lb(ST_MID - 0.03, ST_MID + 0.03, y, y + 1.05, ST_Z0, ST_Z1, 'rail')
        for y in LEVELS:
            self.spot(0.0, y, -9.3)
            self.spot(5.0, y, -6.3)

    def perimeter(self, lv, openings_s=()):
        for side in 'SNWE':
            self.glass_line(lv, side, openings_s if side == 'S' else ())
        # corner columns
        y = LEVELS[lv]
        for sx in (-1, 1):
            for sz in (-1, 1):
                self.box(sx * HW, y + CEIL / 2, sz * HD, 0.18, CEIL / 2, 0.18, 0, 'chrome', 1)

    # -- the floors ---------------------------------------------------------------------

    def level67(self):
        y = 0.0
        holes = []
        self.slab(-IN_X - 0.12, IN_X + 0.12, -IN_Z - 0.12, IN_Z + 0.12, y, holes, 'marble', 0)
        self.perimeter(0, openings_s=((-12.5, -7.5), (-2.5, 2.5), (10.0, 12.5)))
        X0, X1, Z0, Z1 = -IN_X, IN_X, -IN_Z, IN_Z
        # the powder room west of the lift
        self.wall('x', -6.0, Z0, -8.3, y, y + CEIL)
        self.wall('z', -8.3, -6.0, LIFT_X0 - 0.15, y, y + CEIL, doors=[(-5.3, 0.9)])
        self.toilet(-2.0, -12.2, 0.0, y)
        self.vanity(-5.9, -4.7, -12.8, -12.2, y, 1)
        self.area('Powder Room', -3.6, -10.6, y, 2.6)
        # kitchen, north-west: a run of counters along the west glass and the back wall, an island
        self.finish(X0, -6.3, Z0, -2.0, y, 'wood', 0)
        self.counter(X0 + 0.2, X0 + 0.85, Z0 + 0.3, -4.5, y)
        self.counter(X0 + 0.85, -7.0, Z0 + 0.3, Z0 + 0.95, y)
        self.appliance(-12.2, -11.2, Z0 + 0.3, Z0 + 1.0, y)
        self.cupboards(-11.0, -7.0, Z0 + 0.3, Z0 + 0.7, y)
        self.counter(-15.5, -11.5, -7.0, -6.0, y, 'marble', 1, 0.92)
        for x in (-15.0, -14.0, -13.0, -12.0):
            self.stool(x, -5.3, y)
        self.lamp(-7.0, -2.6, y)
        self.area('Kitchen', -13.0, -8.0, y, 7.0)
        self.spot(-16.0, y, -3.5)
        self.spot(-9.5, y, -8.5)
        # dining, south-west: a long table towards the terrace doors
        self.finish(X0, -6.3, -2.0, Z1, y, 'wood', 0)
        self.table(-13.0, 6.0, 2.4, 0.6, y, 0.74, 'walnut')
        for x in (-14.6, -13.0, -11.4):
            self.chair(x, 4.9, 0.0, y, 1)
            self.chair(x, 7.1, math.pi, y, 1)
        self.dd('chandelier', -13.0, y + 2.3, 6.0, r=1.1, top=round(y + CEIL, 2))
        self.counter(X0 + 0.2, X0 + 0.8, 2.0, 9.0, y, 'marble', 1)
        self.painting(X0 + 0.5, 10.5, math.pi / 2, y + 1.2, 1.4, 1.0)
        self.planter(-7.5, 11.5, y, 0.5, 0.5, 0.55)
        self.area('Dining Room', -13.0, 6.0, y, 7.5)
        self.spot(-17.0, y, 10.0)
        self.spot(-9.0, y, 0.5)
        # the great room, in the middle: sofas round a fireplace on the core's south face
        self.fireplace(-3.2, -7.98, 0.0, y, 3.0)
        self.tv(-3.2, -7.98, 0.0, y, 2.4, 1.3, 1.4)
        self.rug(-3.0, -3.5, y, 3.0, 2.5, 3)
        self.sofa(-3.0, -1.0, math.pi, y, 3.2, 1)
        self.sofa(-6.0, -4.0, math.pi / 2, y, 2.4, 1)
        self.sofa(0.0, -4.0, -math.pi / 2, y, 2.4, 1)
        self.coffee(-3.0, -4.0, y, 0.9, 0.55)
        self.armchair(-4.2, 3.5, 2.4, y, 0)
        self.armchair(4.2, 3.5, -2.4, y, 0)
        self.lamp(-5.6, -7.6, y)
        self.lamp(5.2, -5.0, y)
        self.planter(-5.0, 11.8, y, 0.5, 0.5, 0.55)
        self.planter(5.0, 11.8, y, 0.5, 0.5, 0.55)
        self.area('Great Room', 0.0, 0.0, y, 8.0)
        self.area('Lobby 67', 0.0, -9.0, y, 3.0)
        self.spot(0.0, y, 6.0)
        self.spot(-4.5, y, 8.5)
        # the east wing: a study, a bathroom and a pantry, the games room
        self.wall('x', 6.0, Z0, -3.0, y, y + CEIL, doors=[(-7.5, 1.0)])
        self.wall('x', 6.0, -3.0, 2.5, y, y + CEIL, doors=[(-0.25, 0.9)])
        self.opening('x', 6.0, 2.5, Z1, y, y + CEIL, 7.0, 2.6)
        self.wall('z', -3.0, 6.0, X1, y, y + CEIL)
        self.wall('z', 2.5, 6.0, X1, y, y + CEIL, doors=[(15.5, 0.9)])
        self.wall('x', 11.5, -3.0, 2.5, y, y + CEIL)
        # the study
        self.finish(6.1, X1, Z0, -3.1, y, 'wood', 0)
        self.bookcase(6.2, 6.6, -12.4, -8.6, y)
        self.bookcase(8.0, 16.0, Z0 + 0.15, Z0 + 0.55, y)
        self.table(13.0, -7.0, 1.1, 0.6, y, 0.76, 'walnut')
        self.chair(13.0, -5.8, math.pi, y, 0)
        self.armchair(17.5, -4.6, -2.2, y, 0)
        self.lamp(18.5, -11.5, y)
        self.rug(13.0, -7.0, y, 2.5, 2.0, 2)
        self.area('Study', 13.0, -8.0, y, 6.5)
        self.spot(10.0, y, -5.0)
        # the guest bathroom and the pantry
        self.finish(6.1, 11.4, -2.9, 2.4, y, 'marble', 2)
        self.vanity(6.3, 8.3, 1.6, 2.3, y, 1)
        self.toilet(10.6, 1.6, math.pi, y)
        self.shower(8.6, 11.3, -2.8, -0.9, y, 'S')
        self.area('Bathroom', 8.7, -0.2, y, 2.8)
        self.finish(11.6, X1, -2.9, 2.4, y, 'tile', 0)
        self.counter(12.0, X1 - 0.2, -2.8, -2.1, y, 'marble', 1)
        self.appliance(X1 - 1.0, X1 - 0.2, -1.6, -0.4, y)
        self.area('Pantry', 15.7, -0.2, y, 2.8)
        # the games room: a pool table, the bar, a sofa facing the terrace
        self.finish(6.1, X1, 2.6, Z1, y, 'carpet', 0)
        self.pooltable(13.0, 7.5, y)
        self.bar(X1 - 2.2, X1 - 0.6, 4.0, 10.0, y)
        for z in (5.0, 6.6, 8.2):
            self.stool(X1 - 3.0, z, y)
        self.sofa(9.0, 11.6, 0.0, y, 2.4, 2)
        self.tv(X1 - 0.3, 11.0, -math.pi / 2, y, 2.0, 1.1, 1.0)
        self.painting(13.0, Z1 - 0.1, math.pi, y + 1.3, 1.8, 1.2)
        self.area('Games Room', 13.0, 8.0, y, 7.0)
        self.spot(9.0, y, 5.0)
        self.spot(16.0, y, 12.0)

    def terrace(self):
        y = 0.0
        Z0, Z1 = HD, HD + TER_D
        pool = (-6.0, 6.0, 16.0, 21.0)
        for (a, b, c, d) in self.pieces(-HW, HW, Z0, Z1, [pool]):
            self.lb(a, b, y - SLAB, y - 0.06, c, d, 'concrete', 1)
            self.lb(a, b, y - 0.06, y, c, d, 'stone', 0)
        # the pool: a tiled basin a metre and a half deep, steps down at the west end
        px0, px1, pz0, pz1 = pool
        B = -1.5
        self.lb(px0, px1, B - 0.3, B, pz0, pz1, 'tile', 0)
        self.lb(px0, px0 + 0.2, B, y, pz0, pz1, 'tile', 0)
        self.lb(px1 - 0.2, px1, B, y, pz0, pz1, 'tile', 0)
        self.lb(px0, px1, B, y, pz0, pz0 + 0.2, 'tile', 0)
        self.lb(px0, px1, B, y, pz1 - 0.2, pz1, 'tile', 0)
        for i, top in enumerate((-0.4, -0.8, -1.2)):
            self.lb(px0 + 0.2 + i * 0.5, px0 + 0.2 + (i + 1) * 0.5, B, top, pz0 + 0.2, pz1 - 0.2, 'tile', 0)
        self.dd('pool', 0.0, B, 18.5, w=11.6, d=4.6, wy=round(y - 0.25, 2), plain=1)
        self.lb(px0 - 0.25, px1 + 0.25, y, y + 0.04, pz0 - 0.25, pz0, 'marble', 0)
        self.lb(px0 - 0.25, px1 + 0.25, y, y + 0.04, pz1, pz1 + 0.25, 'marble', 0)
        self.lb(px0 - 0.25, px0, y, y + 0.04, pz0, pz1, 'marble', 0)
        self.lb(px1, px1 + 0.25, y, y + 0.04, pz0, pz1, 'marble', 0)
        # the glass balustrade along the edge, and the steel capping
        self.rail(-HW, HW, Z1 - 0.06, Z1, y)
        self.rail(-HW, -HW + 0.06, Z0, Z1, y)
        self.rail(HW - 0.06, HW, Z0, Z1, y)
        # loungers along the pool, planters and trees, an outdoor kitchen, a fire pit
        for x in (-4.5, -2.0, 0.5, 3.0):
            self.lounger(x, 23.0, math.pi, y)
        for x in (-3.0, 1.0, 5.0):
            self.lounger(x, 14.6, 0.0, y)
        for (x, z) in ((-18.0, 23.5), (-13.0, 23.5), (13.0, 23.5), (18.0, 23.5), (-18.5, 14.5), (18.5, 14.5)):
            self.planter(x, z, y, 0.8, 0.8, 0.85)
        self.counter(13.0, 18.5, 14.2, 15.0, y, 'marble', 1)
        self.appliance(15.0, 16.2, 14.2, 15.0, y, 1.0)
        self.table(14.5, 19.5, 1.2, 0.7, y, 0.74, 'walnut')
        for x in (13.5, 14.5, 15.5):
            self.chair(x, 18.4, 0.0, y, 1)
            self.chair(x, 20.6, math.pi, y, 1)
        self.box(-14.0, y + 0.22, 19.0, 0.9, 0.22, 0.9, 0.4, 'concrete', 1)
        for (dx, dz) in ((-2.4, 0), (2.4, 0), (0, -2.4), (0, 2.4)):
            self.sofa(-14.0 + dx, 19.0 + dz, math.atan2(dx, dz) + math.pi if (dx or dz) else 0.0, y, 1.8, 2)
        self.area('The Terrace', -12.0, 19.0, y, 9.0)
        self.area('The Pool', 0.0, 18.5, y, 8.0)
        self.area('Outdoor Kitchen', 15.0, 18.0, y, 6.0)
        for (x, z) in ((-10.0, 15.0), (-17.0, 22.0), (-7.0, 23.5), (10.0, 23.0), (17.0, 18.0), (8.0, 15.0)):
            self.spot(x, y, z)

    def level68(self):
        y = FLOOR
        X0, X1, Z0, Z1 = -IN_X, IN_X, -IN_Z, IN_Z
        holes = [(LIFT_X0 - 0.15, LIFT_X1 + 0.15, LIFT_Z0 - 0.15, LIFT_Z1 + 0.15), (ST_X0, ST_X1, ST_Z0, ST_Z1)]
        self.slab(-IN_X - 0.12, IN_X + 0.12, -IN_Z - 0.12, IN_Z + 0.12, y, holes, 'wood', 0)
        self.perimeter(1)
        # the linen room west of the lift
        self.wall('x', -6.0, Z0, -8.3, y, y + CEIL)
        self.wall('z', -8.3, -6.0, LIFT_X0 - 0.15, y, y + CEIL, doors=[(-3.6, 0.9)])
        self.wardrobe(-5.9, -1.5, Z0, Z0 + 0.6, y)
        self.area('Lobby 68', 0.0, -6.0, y, 4.0)
        # the cinema room, the middle of the floor
        self.wall('z', -3.0, -6.0, 6.0, y, y + CEIL, doors=[(0.0, 1.8)])
        self.wall('x', -6.0, -3.0, Z1, y, y + CEIL)
        self.wall('x', 6.0, -3.0, Z1, y, y + CEIL)
        self.finish(-5.9, 5.9, -2.9, Z1, y, 'carpet', 2)
        self.tv(0.0, Z1 - 0.2, math.pi, y, 5.0, 2.4, 0.6)
        for i, z in enumerate((2.0, 5.0, 8.0)):
            for x in (-3.0, -1.0, 1.0, 3.0):
                self.armchair(x, z, 0.0, y, 2)
            # each row a step up from the one in front
        self.lamp(-5.2, -2.3, y)
        self.lamp(5.2, -2.3, y)
        self.area('Cinema', 0.0, 5.0, y, 7.5)
        self.spot(0.0, y, -1.0)
        self.spot(2.0, y, 10.5)
        # the master suite, west: bedroom, bath, dressing room
        self.wall('x', -6.0, Z0, -3.0, y, y + CEIL, doors=[(-6.0, 1.0)])
        self.wall('z', -1.0, X0, -6.0, y, y + CEIL, doors=[(-9.0, 1.0)])
        self.wall('z', 6.0, X0, -6.0, y, y + CEIL, doors=[(-14.0, 1.0)])
        self.bed(-13.0, -8.5, 0.0, y, 2.0, 1)
        self.rug(-13.0, -7.0, y, 2.5, 2.5, 1)
        self.sofa(-13.0, -3.0, math.pi, y, 2.0, 0)
        self.tv(-6.2, -8.5, math.pi / 2, y, 2.0, 1.1, 1.1)
        self.wardrobe(X0, X0 + 0.6, Z0, -8.0, y)
        self.painting(X0 + 0.1, -5.0, math.pi / 2, y + 1.3, 1.6, 1.1)
        self.area('Master Bedroom', -13.0, -7.0, y, 7.0)
        self.spot(-17.0, y, -4.0)
        self.finish(X0, -6.1, -0.9, 5.9, y, 'marble', 2)
        self.tub(-16.5, 3.5, math.pi / 2, y)
        self.vanity(-13.0, -8.0, -0.8, -0.2, y, 2)
        self.shower(-9.0, -6.2, 3.0, 5.8, y, 'W')
        self.toilet(-12.0, 5.3, math.pi, y)
        self.area('Master Bath', -13.0, 2.5, y, 6.5)
        self.spot(-11.0, y, 2.0)
        self.finish(X0, -6.1, 6.1, Z1, y, 'carpet', 3)
        self.wardrobe(-13.0, -6.3, 6.2, 6.8, y)
        self.wardrobe(X0, X0 + 0.6, 7.0, Z1, y)
        self.box(-13.0, y + 0.22, 10.0, 0.5, 0.22, 0.5, 0, 'leather', 1)
        self.area('Dressing Room', -13.0, 9.5, y, 6.0)
        self.spot(-16.0, y, 10.0)
        # the guest wing, east: a corridor serving two bedrooms and a bath
        self.wall('x', 7.8, Z0, Z1, y, y + CEIL, doors=[(-6.0, 1.0), (-1.2, 0.9), (4.0, 1.0)])
        self.wall('z', -4.0, 7.8, X1, y, y + CEIL)
        self.wall('z', 1.5, 7.8, X1, y, y + CEIL)
        self.wall('x', 6.0, -8.3, -3.0, y, y + CEIL)
        self.finish(6.1, 7.7, -8.2, Z1, y, 'carpet', 0)
        self.painting(6.2, 6.0, math.pi / 2, y + 1.3, 1.2, 0.9)
        self.area('Guest Corridor', 6.9, 3.0, y, 3.0)
        self.bed(15.0, -9.0, 0.0, y, 1.8, 2)
        self.wardrobe(X1 - 0.6, X1, -8.0, -4.2, y)
        self.chair(10.0, -5.5, math.pi / 2, y, 1)
        self.table(10.0, -6.8, 0.5, 0.4, y, 0.74, 'walnut')
        self.rug(15.0, -7.0, y, 2.0, 2.0, 0)
        self.area('Guest Room', 14.0, -8.5, y, 6.0)
        self.spot(16.0, y, -5.0)
        self.finish(7.9, X1, -3.9, 1.4, y, 'marble', 2)
        self.vanity(10.0, 13.0, 0.8, 1.4, y, 2)
        self.tub(17.5, -1.2, 0.0, y)
        self.toilet(8.6, -3.2, 0.0, y)
        self.shower(13.5, 16.0, -3.8, -1.6, y, 'S')
        self.area('Guest Bath', 13.5, -1.2, y, 4.5)
        self.bed(15.0, 10.0, math.pi, y, 1.8, 3)
        self.wardrobe(X1 - 0.6, X1, 2.0, 6.0, y)
        self.sofa(10.0, 11.5, 0.0, y, 1.8, 0)
        self.rug(15.0, 7.0, y, 2.0, 2.0, 4)
        self.area('Guest Room', 14.0, 7.5, y, 6.0)
        self.spot(16.0, y, 4.0)
        self.spot(10.0, y, 8.0)

    def level69(self):
        y = 2 * FLOOR
        X0, X1, Z0, Z1 = -IN_X, IN_X, -IN_Z, IN_Z
        holes = [(LIFT_X0 - 0.15, LIFT_X1 + 0.15, LIFT_Z0 - 0.15, LIFT_Z1 + 0.15), (ST_X0, ST_X1, ST_Z0, ST_Z1)]
        self.slab(-IN_X - 0.12, IN_X + 0.12, -IN_Z - 0.12, IN_Z + 0.12, y, holes, 'marble', 1)
        self.perimeter(2)
        # the store west of the lift
        self.wall('x', -6.0, Z0, -8.3, y, y + CEIL)
        self.wall('z', -8.3, -6.0, LIFT_X0 - 0.15, y, y + CEIL, doors=[(-3.6, 0.9)])
        self.counter(-5.8, -1.6, Z0, Z0 + 0.6, y, 'marble', 1)
        self.appliance(-5.8, -4.8, -10.0, -8.6, y, 1.9)
        self.area('Bar Store', -3.6, -10.6, y, 2.6)
        # the sky lounge: the bar against the core, sofas, a piano by the glass
        self.bar(-4.0, 4.0, -7.4, -6.6, y)
        for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
            self.stool(x, -5.7, y)
        self.sofa(0.0, 0.5, math.pi, y, 3.0, 2)
        self.sofa(-3.4, -2.5, math.pi / 2, y, 2.4, 2)
        self.sofa(3.4, -2.5, -math.pi / 2, y, 2.4, 2)
        self.coffee(0.0, -2.5, y, 0.9, 0.55)
        self.rug(0.0, -2.0, y, 3.0, 2.5, 5)
        self.piano(-3.0, 9.5, y, -0.6)
        self.armchair(3.0, 8.0, 2.6, y, 0)
        self.armchair(5.0, 10.0, 2.2, y, 0)
        self.dd('chandelier', 0.0, y + 2.4, -1.0, r=1.3, top=round(y + CEIL, 2))
        self.lamp(-5.4, 4.0, y)
        self.area('Sky Lounge', 0.0, 0.0, y, 8.5)
        self.area('Lobby 69', 0.0, -8.0, y, 3.0)
        self.spot(0.0, y, 4.0)
        self.spot(-4.0, y, 6.0)
        # the east bay: a dining table in the glass corner
        self.table(13.0, 6.0, 2.0, 0.6, y, 0.74, 'marble', 1)
        for x in (-1.3, 0.0, 1.3):
            self.chair(13.0 + x, 4.9, 0.0, y, 0)
            self.chair(13.0 + x, 7.1, math.pi, y, 0)
        self.dd('chandelier', 13.0, y + 2.3, 6.0, r=1.0, top=round(y + CEIL, 2))
        self.planter(X1 - 1.0, Z1 - 1.0, y, 0.5, 0.5, 0.55)
        self.area('Private Dining', 13.0, 6.0, y, 6.5)
        self.spot(16.0, y, 10.0)
        self.spot(9.0, y, 1.0)
        # the library, north-east
        self.wall('z', -2.0, ST_X1 + WT, X1, y, y + CEIL, doors=[(9.0, 1.0)])
        self.wall('x', ST_X1 + WT / 2, ST_Z1, -2.0, y, y + CEIL, t=WT)
        self.finish(ST_X1 + WT + 0.01, X1, Z0, -2.1, y, 'wood', 0)
        self.bookcase(7.0, 19.0, Z0 + 0.15, Z0 + 0.55, y)
        self.bookcase(6.2, 6.6, -8.0, -3.0, y)
        self.table(13.0, -7.0, 1.3, 0.7, y, 0.76, 'walnut')
        self.chair(13.0, -8.2, 0.0, y, 0)
        self.chair(13.0, -5.8, math.pi, y, 0)
        self.armchair(18.0, -4.0, -2.2, y, 0)
        self.lamp(18.6, -11.4, y)
        self.rug(13.0, -7.0, y, 2.5, 2.0, 2)
        self.area('Library', 13.0, -7.5, y, 6.5)
        self.spot(10.0, y, -4.5)
        # the gym, north-west, and the spa, south-west
        self.wall('x', -6.0, -8.3, Z1, y, y + CEIL, doors=[(-5.0, 1.0), (4.0, 1.0)])
        self.wall('z', 0.0, X0, -6.0, y, y + CEIL)
        self.finish(X0, -6.1, Z0, -0.1, y, 'carpet', 2)
        for x in (-17.0, -15.0, -13.0):
            self.treadmill(x, -11.0, 0.0, y)
        self.weights(-16.0, -4.0, 0.0, y)
        self.weights(-12.0, -4.0, 0.0, y)
        self.box(-9.0, y + 0.25, -7.0, 0.35, 0.25, 0.7, 0, 'leather', 2)
        self.tv(-6.2, -4.0, math.pi / 2, y, 1.8, 1.0, 1.3)
        self.area('Gym', -13.0, -6.5, y, 7.0)
        self.spot(-10.0, y, -2.0)
        self.finish(X0, -6.1, 0.1, Z1, y, 'marble', 2)
        # the hot tub: a sunken square of water, a step down into it
        self.lb(-16.0, -11.0, y - 0.8, y - 0.6, 3.0, 8.0, 'tile', 0)
        for (a, b, c, d) in ((-16.0, -15.8, 3.0, 8.0), (-11.2, -11.0, 3.0, 8.0), (-16.0, -11.0, 3.0, 3.2), (-16.0, -11.0, 7.8, 8.0)):
            self.lb(a, b, y - 0.6, y, c, d, 'tile', 0)
        self.lb(-15.8, -15.3, y - 0.6, y - 0.3, 3.2, 7.8, 'tile', 0)
        self.dd('pool', -13.5, y - 0.6, 5.5, w=4.6, d=4.6, wy=round(y - 0.15, 2), plain=1)
        self.lb(-16.0, -11.0, y - 0.9, y - 0.8, 3.0, 8.0, 'paint', 0)
        # the sauna: a timber box with a glass front, benches inside
        self.lb(X0 + 0.3, -16.0, y, y + 2.4, 9.0, Z1, 'wood', 0)
        self.lb(X0 + 0.3, -16.3, y + 0.3, y + 2.4, 9.3, Z1 - 0.3, 'inv')
        self.lounger(-9.0, 2.5, math.pi, y)
        self.lounger(-7.0, 2.5, math.pi, y)
        self.vanity(-10.5, -7.0, 11.9, 12.5, y, 2)
        self.shower(-14.0, -12.0, 10.3, Z1, y, 'S')
        self.area('Spa', -12.0, 6.0, y, 7.0)
        self.spot(-8.0, y, 7.0)
        self.spot(-18.0, y, 2.0)

    def roof(self):
        """The roof over 69: a slab, a parapet, and the plant on top nobody reaches."""
        y = ROOF
        self.lb(-HW - 0.2, HW + 0.2, y - SLAB, y - 0.08, -HD - 0.2, HD + 0.2, 'paint', 0)
        self.lb(-HW - 0.2, HW + 0.2, y - 0.08, y, -HD - 0.2, HD + 0.2, 'concrete', 1)
        for (a, b, c, d) in ((-HW - 0.2, HW + 0.2, -HD - 0.2, -HD + 0.1), (-HW - 0.2, HW + 0.2, HD - 0.1, HD + 0.2),
                             (-HW - 0.2, -HW + 0.1, -HD, HD), (HW - 0.1, HW + 0.2, -HD, HD)):
            self.lb(a, b, y, y + 1.0, c, d, 'concrete', 1)
        self.lb(-4.0, 4.0, y, y + 2.2, -6.0, -2.0, 'concrete', 0)
        self.lb(8.0, 12.0, y, y + 1.6, 4.0, 8.0, 'chrome', 1)
        self.lb(-14.0, -10.0, y, y + 1.6, 2.0, 6.0, 'chrome', 1)
        self.box(0.0, y + 6.0, 0.0, 0.25, 6.0, 0.25, 0, 'chrome', 1)
        self.box(0.0, y + 12.3, 0.0, 0.1, 0.3, 0.1, 0, 'paint', 3)

    def body(self):
        """The tower below the penthouse, down to the street: glass, with a notch for the pool."""
        z0, z1 = -HD - 0.2, HD + TER_D + 0.2
        cz, hd = (z0 + z1) / 2, (z1 - z0) / 2
        self.box(0.0, (STREET - 2.0) / 2, cz, HW + 0.2, (-2.0 - STREET) / 2, hd, 0, 'glass', 1)
        pool = (-6.0, 6.0, 16.0, 21.0)
        for (a, b, c, d) in self.pieces(-HW - 0.2, HW + 0.2, z0, z1, [pool]):
            self.lb(a, b, -2.0, -SLAB, c, d, 'glass', 1)
        # a plaza at the foot, and a canopy over the doors, for whoever looks straight down
        self.lb(-HW - 14, HW + 14, STREET, STREET + 0.4, z0 - 14, z1 + 14, 'concrete', 2)
        self.lb(-8.0, 8.0, STREET + 5.0, STREET + 5.4, z1, z1 + 6.0, 'chrome', 1)

    # -- the whole thing ----------------------------------------------------------------

    def generate(self):
        self.body()
        self.core()
        self.level67()
        self.terrace()
        self.level68()
        self.level69()
        self.roof()
        self.deco.append({'k': 'skyline', 'seed': self.seed, 'y': STREET, 'hw': HW + 14, 'cz': round(TOWER_Z, 2), 'hd': round(TOWER_HD + 14, 2)})
        # sites, hills and spawns: the pool deck and the sky lounge bar; the great room,
        # the cinema and the spa; spawns spread over the three floors and the terrace
        self.site_a = (0.0, 23.5, 0.0)
        self.site_b = (0.0, -3.5, 2 * FLOOR)
        self.hills = [(0.0, 2.0, 0.0), (0.0, 5.0, FLOOR), (-12.0, 6.0, 2 * FLOOR)]
        self.ffa_spawns = [[x, z, y] for (x, y, z) in self.spots]
        low = [[x, z, y] for (x, y, z) in self.spots if y < 1.0 and z > 12.0]
        high = [[x, z, y] for (x, y, z) in self.spots if y > 2 * FLOOR - 0.5]
        self.team_spawns = [low, high]
        self.spawn_w = (-12.0, 19.0)
        self.spawn_e = (0.0, 4.0)

    def to_json(self):
        m = Town.to_json(self)
        m['sites'] = {'A': [round(v, 2) for v in self.site_a], 'B': [round(v, 2) for v in self.site_b]}
        m['hills'] = [[round(v, 2) for v in h] for h in self.hills]
        # the street, far below, is the ground: one flat cell of height grid
        m['height'] = {'x0': -2000.0, 'z0': -2000.0, 'cell': 4000.0, 'nx': 2, 'nz': 2, 'h': [[STREET, STREET], [STREET, STREET]]}
        m['void'] = VOID
        m['levels'] = list(LEVELS)
        m['levelNames'] = list(NAMES)
        m['lift'] = {'x': 0.0, 'z': round((LIFT_Z0 + LIFT_Z1) / 2, 2), 'hw': LIFT_X1, 'hd': round((LIFT_Z1 - LIFT_Z0) / 2, 2),
                     'dz': round(LIFT_Z1 + 0.075, 3), 'dw': LIFT_W, 'dh': LIFT_H, 'levels': list(LEVELS), 'names': list(NAMES)}
        return m
