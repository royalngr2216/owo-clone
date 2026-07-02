"""
Hand-drawn (via Pillow primitives) slot machine symbol icons.

Why not just render the emoji glyphs? Pillow has no reliable color-emoji
font rendering without bundling a huge NotoColorEmoji bitmap font, and
platform emoji fonts render inconsistently. Drawing flat-style vector
icons ourselves means full control over style/colors (matches our
palette) and guaranteed consistent rendering anywhere this runs.

All icons are drawn at 4x supersampling then downscaled — same trick
used in battle_renderer.py — for clean anti-aliased edges.
"""

from PIL import Image, ImageDraw, ImageFilter
import functools
import math

SUPERSAMPLE = 4

SYMBOL_KEYS = ["cherry", "lemon", "clover", "bell", "diamond", "crown", "skull"]

# Emoji shown in embeds/text elsewhere in the bot map to these icon keys
EMOJI_TO_KEY = {
    "🍒": "cherry",
    "🍋": "lemon",
    "🍀": "clover",
    "🔔": "bell",
    "💎": "diamond",
    "👑": "crown",
    "💀": "skull",
}


def _canvas(size):
    hi = size * SUPERSAMPLE
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), hi


def _finish(img, size):
    return img.resize((size, size), Image.LANCZOS)


def _draw_cherry(size):
    img, d, hi = _canvas(size)
    cx = hi // 2
    r = hi * 0.20

    stem_top = (cx, hi * 0.12)
    left_c = (cx - r * 0.85, hi * 0.66)
    right_c = (cx + r * 0.55, hi * 0.52)

    d.line([stem_top, left_c], fill=(60, 150, 70, 255), width=int(hi * 0.045))
    d.line([stem_top, right_c], fill=(60, 150, 70, 255), width=int(hi * 0.045))

    # leaf
    leaf_box = (cx - hi * 0.02, hi * 0.05, cx + hi * 0.22, hi * 0.16)
    d.ellipse(leaf_box, fill=(80, 190, 90, 255))

    for c in (left_c, right_c):
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(210, 40, 55, 255))
        # highlight
        hl = r * 0.35
        d.ellipse(
            (c[0] - r * 0.35 - hl, c[1] - r * 0.35 - hl, c[0] - r * 0.35 + hl, c[1] - r * 0.35 + hl),
            fill=(255, 140, 150, 180),
        )

    return _finish(img, size)


def _draw_lemon(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi // 2
    w, h = hi * 0.34, hi * 0.44

    d.ellipse((cx - w, cy - h, cx + w, cy + h), fill=(247, 213, 60, 255))
    # pointy tips
    d.polygon([(cx, cy - h - hi * 0.06), (cx - hi * 0.05, cy - h + hi * 0.03), (cx + hi * 0.05, cy - h + hi * 0.03)],
              fill=(247, 213, 60, 255))
    d.polygon([(cx, cy + h + hi * 0.06), (cx - hi * 0.05, cy + h - hi * 0.03), (cx + hi * 0.05, cy + h - hi * 0.03)],
              fill=(247, 213, 60, 255))

    hl = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    hld = ImageDraw.Draw(hl)
    hld.ellipse((cx - w * 0.5, cy - h * 0.6, cx + w * 0.05, cy - h * 0.05), fill=(255, 250, 210, 140))
    img.alpha_composite(hl)

    return _finish(img, size)


def _draw_clover(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi // 2
    r = hi * 0.20
    off = r * 0.95

    centers = [(cx - off, cy - off), (cx + off, cy - off), (cx - off, cy + off), (cx + off, cy + off)]
    for c in centers:
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(60, 175, 90, 255))

    for c in centers:
        hl = r * 0.4
        d.ellipse((c[0] - r * 0.3 - hl, c[1] - r * 0.3 - hl, c[0] - r * 0.3 + hl, c[1] - r * 0.3 + hl),
                  fill=(130, 220, 140, 150))

    d.line([(cx, cy), (cx, cy + hi * 0.32)], fill=(50, 130, 65, 255), width=int(hi * 0.035))

    return _finish(img, size)


def _draw_bell(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi * 0.46

    d.ellipse((cx - hi * 0.05, hi * 0.10, cx + hi * 0.05, hi * 0.18), fill=(230, 185, 60, 255))

    body = [
        (cx - hi * 0.05, hi * 0.16),
        (cx - hi * 0.30, hi * 0.55),
        (cx - hi * 0.38, hi * 0.68),
        (cx + hi * 0.38, hi * 0.68),
        (cx + hi * 0.30, hi * 0.55),
        (cx + hi * 0.05, hi * 0.16),
    ]
    d.polygon(body, fill=(250, 205, 70, 255))

    d.ellipse((cx - hi * 0.40, hi * 0.60, cx + hi * 0.40, hi * 0.76), fill=(235, 180, 55, 255))
    d.ellipse((cx - hi * 0.06, hi * 0.78, cx + hi * 0.06, hi * 0.90), fill=(120, 90, 40, 255))

    hl = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    hld = ImageDraw.Draw(hl)
    hld.ellipse((cx - hi * 0.20, hi * 0.30, cx - hi * 0.02, hi * 0.55), fill=(255, 240, 190, 130))
    img.alpha_composite(hl)

    return _finish(img, size)


def _draw_diamond(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi // 2
    w, h = hi * 0.32, hi * 0.36

    top = (cx, cy - h)
    left = (cx - w, cy - h * 0.15)
    right = (cx + w, cy - h * 0.15)
    bottom = (cx, cy + h)

    d.polygon([top, right, bottom, left], fill=(90, 195, 245, 255))
    # facet lines
    d.line([left, (cx - w * 0.35, cy - h * 0.15)], fill=(200, 240, 255, 255), width=max(1, int(hi * 0.015)))
    d.polygon([top, (cx - w * 0.35, cy - h * 0.15), (cx + w * 0.35, cy - h * 0.15)], fill=(150, 225, 255, 255))
    d.polygon([left, (cx - w * 0.35, cy - h * 0.15), (cx, bottom[1])], fill=(60, 160, 220, 255))
    d.polygon([right, (cx + w * 0.35, cy - h * 0.15), (cx, bottom[1])], fill=(75, 180, 235, 255))

    return _finish(img, size)


def _draw_crown(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi * 0.58

    base = (cx - hi * 0.32, cy, cx + hi * 0.32, cy + hi * 0.16)
    d.rounded_rectangle(base, radius=hi * 0.03, fill=(250, 205, 70, 255))

    pts = [
        (cx - hi * 0.32, cy),
        (cx - hi * 0.32, cy - hi * 0.05),
        (cx - hi * 0.20, cy - hi * 0.30),
        (cx - hi * 0.08, cy - hi * 0.08),
        (cx, cy - hi * 0.36),
        (cx + hi * 0.08, cy - hi * 0.08),
        (cx + hi * 0.20, cy - hi * 0.30),
        (cx + hi * 0.32, cy - hi * 0.05),
        (cx + hi * 0.32, cy),
    ]
    d.polygon(pts, fill=(255, 217, 90, 255))

    for gx, color in [(cx - hi * 0.20, (210, 60, 70, 255)),
                       (cx, (80, 160, 230, 255)),
                       (cx + hi * 0.20, (210, 60, 70, 255))]:
        r = hi * 0.035
        d.ellipse((gx - r, cy - hi * 0.28 - r, gx + r, cy - hi * 0.28 + r), fill=color)

    return _finish(img, size)


def _draw_skull(size):
    img, d, hi = _canvas(size)
    cx, cy = hi // 2, hi * 0.42

    d.ellipse((cx - hi * 0.30, cy - hi * 0.30, cx + hi * 0.30, cy + hi * 0.24), fill=(235, 235, 238, 255))
    d.rounded_rectangle((cx - hi * 0.20, cy + hi * 0.05, cx + hi * 0.20, cy + hi * 0.32),
                         radius=hi * 0.04, fill=(235, 235, 238, 255))

    eye_r = hi * 0.09
    for ex in (cx - hi * 0.13, cx + hi * 0.13):
        d.ellipse((ex - eye_r, cy - eye_r * 0.4, ex + eye_r, cy + eye_r * 1.6), fill=(25, 26, 32, 255))

    d.polygon([(cx, cy + hi * 0.10), (cx - hi * 0.05, cy + hi * 0.22), (cx + hi * 0.05, cy + hi * 0.22)],
              fill=(25, 26, 32, 255))

    for tx in (cx - hi * 0.13, cx - hi * 0.045, cx + hi * 0.045, cx + hi * 0.13):
        d.rectangle((tx - hi * 0.02, cy + hi * 0.26, tx + hi * 0.02, cy + hi * 0.34), fill=(25, 26, 32, 255))

    return _finish(img, size)


_DRAWERS = {
    "cherry": _draw_cherry,
    "lemon": _draw_lemon,
    "clover": _draw_clover,
    "bell": _draw_bell,
    "diamond": _draw_diamond,
    "crown": _draw_crown,
    "skull": _draw_skull,
}


@functools.lru_cache(maxsize=None)
def get_symbol_icon(key: str, size: int = 150) -> Image.Image:
    """Returns an RGBA tile for the given symbol key ('cherry', 'crown', etc), cached."""
    if key in EMOJI_TO_KEY:
        key = EMOJI_TO_KEY[key]
    drawer = _DRAWERS.get(key, _draw_skull)
    return drawer(size)
