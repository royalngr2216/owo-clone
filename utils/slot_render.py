"""
Slot machine reel rendering — smooth Pillow-animated GIF instead of
discord.py message-edit-through-emoji animation.

Each reel scrolls through a strip of symbol tiles with an ease-out
curve (fast start, smooth deceleration), with motion blur applied
proportional to instantaneous speed so it actually reads as "spinning"
rather than symbols just teleporting past. Reels stop staggered
(reel 0 first, then 1, then 2) same pacing philosophy as before, just
continuous motion instead of discrete jumps.
"""

from PIL import Image, ImageDraw, ImageFilter
import io
import random

from utils.slot_icons import get_symbol_icon, EMOJI_TO_KEY
from utils.visuals import COLORS, FONT_BOLD, rounded_rectangle, vertical_gradient, add_glow, text_with_shadow

TILE = 130
REEL_W = TILE
REEL_GAP = 22
WINDOW_H = int(TILE * 2.3)
N_REELS = 3
PADDING = 34

CANVAS_W = PADDING * 2 + REEL_W * N_REELS + REEL_GAP * (N_REELS - 1)
CANVAS_H = PADDING * 2 + WINDOW_H

FPS = 20
FRAME_MS = int(1000 / FPS)

ALL_KEYS = ["cherry", "lemon", "clover", "bell", "diamond", "crown", "skull"]


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def _ease_out_speed(t: float) -> float:
    """Derivative of ease_out_cubic — used to scale motion blur."""
    return 3 * (1 - t) ** 2


def _build_strip(target_key: str, n_pre: int = 10, n_post: int = 3):
    """
    Vertical strip of random symbol tiles with the target symbol at
    index n_pre. n_post extra tiles are appended AFTER the target so
    there's always enough strip height to center the target tile in
    the window without the crop clamping against the strip's bottom
    edge (which would land it off-center on the payline).
    """
    keys = (
        [random.choice(ALL_KEYS) for _ in range(n_pre)]
        + [target_key]
        + [random.choice(ALL_KEYS) for _ in range(n_post)]
    )

    strip = Image.new("RGBA", (TILE, TILE * len(keys)), (0, 0, 0, 0))
    for i, k in enumerate(keys):
        icon = get_symbol_icon(k, TILE - 14)
        strip.alpha_composite(icon, (7, i * TILE + 7))
    return strip, n_pre + 1  # tile-count "up to and including target", used for centering math


def _reel_frame(strip: Image.Image, target_index: int, t: float, blur_max: float = 7.0) -> Image.Image:
    """Crops+blurs the strip at progress t (0..1) so the target tile centers in the window at t=1."""
    target_center = target_index * TILE + TILE / 2
    final_offset = target_center - WINDOW_H / 2
    offset = final_offset * _ease_out_cubic(t)
    offset = max(0, min(offset, strip.height - WINDOW_H))

    crop = strip.crop((0, int(offset), TILE, int(offset) + WINDOW_H))

    if t < 1.0:
        blur_radius = blur_max * _ease_out_speed(t)
        if blur_radius > 0.4:
            crop = crop.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    return crop


def _draw_casing(glow_color=None) -> Image.Image:
    """Base machine frame: dark panel, accent border, per-reel window backgrounds."""
    base = vertical_gradient((CANVAS_W, CANVAS_H), COLORS["bg_panel"], COLORS["bg_dark"])
    draw = ImageDraw.Draw(base)
    rounded_rectangle(draw, (2, 2, CANVAS_W - 3, CANVAS_H - 3), 24,
                       outline=(glow_color or COLORS["accent"]), width=4)

    for i in range(N_REELS):
        x = PADDING + i * (REEL_W + REEL_GAP)
        rounded_rectangle(draw, (x - 6, PADDING - 6, x + REEL_W + 6, PADDING + WINDOW_H + 6),
                           14, fill=COLORS["bg_dark"])

    # payline strip through the middle
    mid_y = PADDING + WINDOW_H // 2
    draw.rectangle((PADDING - 10, mid_y - TILE // 2, CANVAS_W - PADDING + 10, mid_y + TILE // 2),
                    outline=(*COLORS["gold"][:3], 90), width=2)

    return base


def build_spin_gif(result_emojis: list[str], near_miss: bool = False) -> tuple[io.BytesIO, float]:
    """
    result_emojis: e.g. ['🍒','🍒','🍒'] — the final symbols each reel lands on.
    Returns (gif_bytes, total_duration_seconds).
    """
    target_keys = [EMOJI_TO_KEY.get(e, "skull") for e in result_emojis]

    # Staggered stop times per reel, in seconds (reel 0 stops first).
    stop_times = [1.1, 1.9, 3.1 if near_miss else 2.7]
    total_duration = stop_times[-1] + 0.15
    n_frames = int(total_duration * FPS)

    strips = []
    for k in target_keys:
        strip, target_index = _build_strip(k)
        strips.append((strip, target_index))

    casing = _draw_casing()
    frames = []

    for f in range(n_frames + 1):
        now = f / FPS
        frame = casing.copy()

        for i, (strip, target_index) in enumerate(strips):
            stop_t = stop_times[i]
            t = min(1.0, now / stop_t) if stop_t > 0 else 1.0
            reel_img = _reel_frame(strip, target_index, t)

            x = PADDING + i * (REEL_W + REEL_GAP)
            frame.alpha_composite(reel_img.convert("RGBA"), (x, PADDING))

        frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=200))

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        # No `loop` kwarg at all: omitting it skips the Netscape loop
        # extension entirely, so viewers play the GIF once and stop on
        # the last frame instead of looping (which would replay the
        # spin forever until we edit the message).
        optimize=True,
        disposal=2,
    )
    buf.seek(0)
    return buf, total_duration


def build_result_frame(result_emojis: list[str], win: bool, jackpot: bool = False) -> io.BytesIO:
    """Crisp static final frame — used to replace the GIF once it's done playing."""
    target_keys = [EMOJI_TO_KEY.get(e, "skull") for e in result_emojis]

    glow_color = None
    if jackpot:
        glow_color = COLORS["gold"][:3]
    elif win:
        glow_color = COLORS["success"][:3]

    casing = _draw_casing(glow_color=(*glow_color, 255) if glow_color else None)

    for i, k in enumerate(target_keys):
        icon = get_symbol_icon(k, TILE - 14)
        x = PADDING + i * (REEL_W + REEL_GAP)
        y = PADDING + WINDOW_H // 2 - TILE // 2

        if glow_color:
            glow = add_glow(icon, (*glow_color, 255), blur=14, intensity=0.8)
            casing.alpha_composite(glow, (x - 14, y - 14 + 7))

        casing.alpha_composite(icon, (x + 7, y + 7))

    buf = io.BytesIO()
    casing.save(buf, format="PNG")
    buf.seek(0)
    return buf
