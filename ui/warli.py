"""
Warli panels, drawn in the page.

The home screen used to carry four hotlinked stock photographs: a child with a
watering can in what is plainly an English allotment, a European market stall,
a trowel in potting compost, and a wheat field at sunset. Nothing in any of
them was Indian, which is an odd thing to show a Marathi farmer, and all four
were megabytes fetched from Unsplash over whatever connection the farmer has.

So they are gone, and these are drawn instead.

Why Warli specifically
----------------------
Warli is the folk painting of the Warli people of northern Maharashtra --
white rice-paste figures on a mud wall, geometry reduced until a person is two
triangles and a circle. It is the art of this app's actual users' region,
not a generic "Indian motif", and its subjects are already farming: ploughing,
sowing, the harvest, the tarpa dance.

These are drawn in the traditional style, which is a centuries-old folk
tradition rather than any particular artist's work. Nothing here is a copy of
an existing painting.

Practically it also beats photographs on every axis that matters here: no
network request, nothing to 404, legible at any size, and it scales to a phone
screen without becoming a brown smear.
"""

from __future__ import annotations

# mud wall and rice paste
WALL_FROM = "#9d5531"
WALL_TO = "#7f4226"
PASTE = "#f6efe2"

VIEW_W, VIEW_H = 200, 140


def _person(x: float, y: float, s: float = 1.0, arms: str = "down",
            stride: float = 1.0) -> str:
    """
    One Warli figure: two triangles meeting at the waist, a circle for a head.

    `arms` is the pose -- "down", "up" (celebrating, or holding something
    overhead), "out" (holding a tool, or joined to the next dancer), "work"
    (one arm forward and down, which reads as sowing or reaping).
    """
    head_r = 3.6 * s
    shoulder = 7.0 * s
    waist_y = y + 14 * s
    hip_y = y + 25 * s
    hip_x = 5.6 * s
    leg = 19 * s * stride

    parts = [
        f'<circle cx="{x}" cy="{y}" r="{head_r}"/>',
        # torso: apex-down triangle over apex-up triangle
        f'<path d="M{x - shoulder} {y + head_r + 1} L{x + shoulder} '
        f'{y + head_r + 1} L{x} {waist_y} Z"/>',
        f'<path d="M{x} {waist_y} L{x - hip_x} {hip_y} L{x + hip_x} {hip_y} Z"/>',
        # legs
        f'<line x1="{x - hip_x}" y1="{hip_y}" x2="{x - hip_x - leg * .42}" '
        f'y2="{hip_y + leg}"/>',
        f'<line x1="{x + hip_x}" y1="{hip_y}" x2="{x + hip_x + leg * .42}" '
        f'y2="{hip_y + leg}"/>',
    ]

    shoulder_y = y + head_r + 2
    if arms == "up":
        parts += [
            f'<line x1="{x - shoulder + 1}" y1="{shoulder_y}" '
            f'x2="{x - shoulder - 7 * s}" y2="{shoulder_y - 11 * s}"/>',
            f'<line x1="{x + shoulder - 1}" y1="{shoulder_y}" '
            f'x2="{x + shoulder + 7 * s}" y2="{shoulder_y - 11 * s}"/>',
        ]
    elif arms == "out":
        parts += [
            f'<line x1="{x - shoulder + 1}" y1="{shoulder_y}" '
            f'x2="{x - shoulder - 11 * s}" y2="{shoulder_y - 2 * s}"/>',
            f'<line x1="{x + shoulder - 1}" y1="{shoulder_y}" '
            f'x2="{x + shoulder + 11 * s}" y2="{shoulder_y - 2 * s}"/>',
        ]
    elif arms == "work":
        parts += [
            f'<line x1="{x - shoulder + 1}" y1="{shoulder_y}" '
            f'x2="{x - shoulder - 9 * s}" y2="{shoulder_y + 9 * s}"/>',
            f'<line x1="{x + shoulder - 1}" y1="{shoulder_y}" '
            f'x2="{x + shoulder + 5 * s}" y2="{shoulder_y + 11 * s}"/>',
        ]
    elif arms == "link":
        pass                      # the caller joins this figure to the next
    else:  # down
        parts += [
            f'<line x1="{x - shoulder + 1}" y1="{shoulder_y}" '
            f'x2="{x - shoulder - 4 * s}" y2="{shoulder_y + 12 * s}"/>',
            f'<line x1="{x + shoulder - 1}" y1="{shoulder_y}" '
            f'x2="{x + shoulder + 4 * s}" y2="{shoulder_y + 12 * s}"/>',
        ]
    return "".join(parts)


def _bullock(x: float, y: float, s: float = 1.0) -> str:
    """A bullock: the same two-triangle body, lying on its side."""
    body = 15 * s
    depth = 7.0 * s
    leg = 13 * s
    waist = 1.6 * s        # the pinch between the two triangles
    return "".join([
        # body: two triangles meeting at a narrow waist, the animal form of
        # the same hourglass the people are built from
        f'<path d="M{x} {y - depth} L{x} {y + depth} L{x + body - waist} {y} Z"/>',
        f'<path d="M{x + body * 2} {y - depth} L{x + body * 2} {y + depth} '
        f'L{x + body + waist} {y} Z"/>',
        f'<line x1="{x + body - waist}" y1="{y}" x2="{x + body + waist}" y2="{y}"/>',
        # legs
        f'<line x1="{x + body * .5}" y1="{y + depth * .6}" '
        f'x2="{x + body * .4}" y2="{y + depth + leg}"/>',
        f'<line x1="{x + body * .8}" y1="{y + depth * .8}" '
        f'x2="{x + body * .9}" y2="{y + depth + leg}"/>',
        f'<line x1="{x + body * 1.3}" y1="{y + depth * .8}" '
        f'x2="{x + body * 1.2}" y2="{y + depth + leg}"/>',
        f'<line x1="{x + body * 1.6}" y1="{y + depth * .6}" '
        f'x2="{x + body * 1.7}" y2="{y + depth + leg}"/>',
        # neck, head and a proper pair of horns
        f'<line x1="{x + body * 2}" y1="{y - depth * .5}" '
        f'x2="{x + body * 2 + 7 * s}" y2="{y - depth - 3 * s}"/>',
        f'<circle cx="{x + body * 2 + 9 * s}" cy="{y - depth - 5 * s}" r="{3.4 * s}"/>',
        f'<path d="M{x + body * 2 + 6 * s} {y - depth - 8 * s} '
        f'Q {x + body * 2 + 2 * s} {y - depth - 17 * s} '
        f'{x + body * 2 + 7 * s} {y - depth - 18 * s}" fill="none"/>',
        f'<path d="M{x + body * 2 + 12 * s} {y - depth - 8 * s} '
        f'Q {x + body * 2 + 16 * s} {y - depth - 17 * s} '
        f'{x + body * 2 + 11 * s} {y - depth - 18 * s}" fill="none"/>',
        # tail
        f'<path d="M{x} {y - depth * .4} Q {x - 9 * s} {y - 2 * s} '
        f'{x - 6 * s} {y + 9 * s}" fill="none"/>',
    ])


def _tree(x: float, y: float, h: float = 34) -> str:
    """A Warli tree: a trunk with branches radiating off it."""
    parts = [f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - h}"/>']
    for i, frac in enumerate((0.42, 0.62, 0.80, 0.95)):
        at = y - h * frac
        reach = (h * 0.30) * (1 - frac * 0.45)
        lift = reach * 0.75
        parts.append(f'<line x1="{x}" y1="{at}" x2="{x - reach}" y2="{at - lift}"/>')
        parts.append(f'<line x1="{x}" y1="{at}" x2="{x + reach}" y2="{at - lift}"/>')
    return "".join(parts)


def _sun(x: float, y: float, r: float = 7) -> str:
    rays = []
    import math
    for i in range(12):
        a = math.radians(i * 30)
        rays.append(
            f'<line x1="{x + math.cos(a) * (r + 2):.1f}" '
            f'y1="{y + math.sin(a) * (r + 2):.1f}" '
            f'x2="{x + math.cos(a) * (r + 7):.1f}" '
            f'y2="{y + math.sin(a) * (r + 7):.1f}"/>')
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="none"/>' + "".join(rays)


def _sprouts(y: float, xs: tuple, h: float = 9) -> str:
    """A row of young plants, each a stem with two leaves."""
    out = []
    for x in xs:
        out.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - h}"/>')
        out.append(f'<line x1="{x}" y1="{y - h * .55}" x2="{x - h * .5}" '
                   f'y2="{y - h * 1.05}"/>')
        out.append(f'<line x1="{x}" y1="{y - h * .55}" x2="{x + h * .5}" '
                   f'y2="{y - h * 1.05}"/>')
    return "".join(out)


def _ground(y: float) -> str:
    return f'<line x1="6" y1="{y}" x2="{VIEW_W - 6}" y2="{y}"/>'


# ───────────────────────────── the four scenes ─────────────────────────────

def _scene_plough() -> str:
    return (
        _sun(170, 24, 5.5)
        + _bullock(22, 70, 0.95)
        + _person(132, 56, 0.92, arms="out")
        # the plough: beam running back from the yoke to the share in the soil
        + '<line x1="78" y1="62" x2="124" y2="72"/>'      # beam
        + '<line x1="124" y1="72" x2="120" y2="96"/>'     # body
        + '<line x1="120" y1="96" x2="134" y2="99"/>'     # share
        + '<line x1="124" y1="72" x2="140" y2="64"/>'     # handle to his hand
        + _ground(100)
        + '<path d="M14 110 Q 100 103 186 110" fill="none" opacity=".75"/>'
        + _tree(186, 100, 34)
    )


def _scene_sow() -> str:
    import math

    # seed leaving the hand and falling in an arc, which is what sowing by
    # hand actually looks like from a distance
    throw = []
    for i in range(9):
        t = i / 8
        throw.append(f'<circle cx="{78 + t * 58:.0f}" '
                     f'cy="{72 + (t * t) * 32 - t * 6:.0f}" r="1.6"/>')
    return (
        _tree(22, 106, 34)
        + _person(66, 56, 0.98, arms="work")
        # the seed basket, carried at the hip
        + '<path d="M50 78 L66 78 L62 90 L54 90 Z" fill="none"/>'
        + "".join(throw)
        + _person(150, 60, 0.82, arms="work")
        + _ground(106)
        + _sprouts(106, (104, 116, 128), 7)
    )


def _scene_rain() -> str:
    """
    Rain on a standing crop.

    No drawn cloud. Warli has no outlined-cloud convention -- rain is slanted
    strokes falling from the top of the wall, and that is what this is.
    """
    drops = "".join(
        f'<line x1="{x}" y1="{10 + (i % 3) * 9}" x2="{x - 7}" '
        f'y2="{30 + (i % 3) * 9}"/>'
        for i, x in enumerate(range(22, 190, 11)))
    # a crop at different heights, because a real field is not a comb
    heights = (15, 19, 13, 21, 17, 22, 14, 20, 16, 18)
    plants = "".join(
        _sprouts(104, (24 + i * 17,), h) for i, h in enumerate(heights))
    return (
        drops + plants + _ground(104)
        + '<path d="M10 116 Q 100 110 190 116" fill="none" opacity=".75"/>'
    )


def _scene_dance() -> str:
    """
    The tarpa dance: the figures that everyone recognises as Warli.

    A ring of dancers, arms joined, around the piper. It is the harvest
    picture in this tradition -- the painting a village makes when the crop
    is in.
    """
    import math

    cx, cy, rx, ry = 100, 74, 72, 30
    count, scale = 7, 0.60
    shoulder_dx = 7.0 * scale
    head_r = 3.6 * scale

    spots = []
    for i in range(count):
        a = math.radians(i * (360 / count) - 90)
        spots.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry))

    ring = [_person(x, y - 13, scale, arms="link") for x, y in spots]

    # join each dancer's right shoulder to the next one's left shoulder. The
    # linked ring is the whole subject of the painting, so it has to close.
    arms = []
    for i, (x, y) in enumerate(spots):
        nx, ny = spots[(i + 1) % count]
        sy = (y - 13) + head_r + 2
        ny_s = (ny - 13) + head_r + 2
        arms.append(f'<line x1="{x + shoulder_dx:.1f}" y1="{sy:.1f}" '
                    f'x2="{nx - shoulder_dx:.1f}" y2="{ny_s:.1f}"/>')

    return (
        _sun(22, 20, 4.5)
        + "".join(arms) + "".join(ring)
        + _person(100, 60, 0.62, arms="up")       # the piper, in the middle
    )


SCENES = {
    "plough": _scene_plough,
    "sow": _scene_sow,
    "rain": _scene_rain,
    "harvest": _scene_dance,
}


def panel(scene: str, caption: str = "") -> str:
    """One framed panel, as inline SVG. No network, nothing to break."""
    draw = SCENES.get(scene)
    if draw is None:
        return ""
    label = (f'<div class="wcap">{caption}</div>') if caption else ""
    return (
        f'<div class="warli">'
        f'<svg viewBox="0 0 {VIEW_W} {VIEW_H}" role="img" '
        f'aria-label="{caption or scene}" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="{WALL_FROM}"/>'
        f'<rect width="{VIEW_W}" height="{VIEW_H}" fill="url(#wall)"/>'
        f'<g fill="{PASTE}" stroke="{PASTE}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round">{draw()}</g>'
        f"</svg>{label}</div>"
    )


def defs() -> str:
    """The shared mud-wall gradient, emitted once per page."""
    return (
        '<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
        '<defs><linearGradient id="wall" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{WALL_FROM}"/>'
        f'<stop offset="100%" stop-color="{WALL_TO}"/>'
        "</linearGradient></defs></svg>"
    )


# ───────────────────── motifs used by the page chrome ──────────────────────

def band(motifs: int = 16) -> str:
    """
    A running border of figures and triangles.

    Warli paintings are edged with a repeating band like this, and it is the
    single cheapest way to make a page read as painted rather than templated.
    Used as a section divider and along the foot of the hero.
    """
    import math

    step = 1200 / motifs
    out = []
    for i in range(motifs):
        x = i * step + step / 2
        if i % 2 == 0:
            out.append(_person(x, 9, 0.30, arms="out"))
        else:
            # the hourglass on its own, which is the motif the figures are
            # built from and the commonest filler in a real border
            out.append(f'<path d="M{x - 5} 6 L{x + 5} 6 L{x} 15 Z"/>')
            out.append(f'<path d="M{x} 15 L{x - 5} 24 L{x + 5} 24 Z"/>')
    return (
        f'<svg class="wband" viewBox="0 0 1200 32" preserveAspectRatio="none" '
        f'aria-hidden="true"><rect width="1200" height="32" fill="{WALL_FROM}"/>'
        f'<rect width="1200" height="32" fill="url(#wall)"/>'
        f'<g fill="{PASTE}" stroke="{PASTE}" stroke-width="1.3" '
        f'stroke-linecap="round" stroke-linejoin="round">{"".join(out)}</g></svg>'
    )


def watermark() -> str:
    """
    The large, faint motif behind the hero.

    It replaces a 🌾 emoji, which rendered as a different picture on every
    device and said nothing about where this app is from.
    """
    return (
        '<svg class="wm" viewBox="0 0 210 150" aria-hidden="true">'
        f'<g fill="{PASTE}" stroke="{PASTE}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        + _tree(40, 140, 96)
        + _person(108, 58, 1.25, arms="up")
        + _person(158, 70, 1.05, arms="out")
        + _sun(176, 26, 8)
        + "</g></svg>"
    )
