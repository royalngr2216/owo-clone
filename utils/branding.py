import discord

# ─────────────────────────────────────────────────────────────────
# SHARED BRAND FOOTER
# ─────────────────────────────────────────────────────────────────
# A handful of cogs (e.g. rob.py) already stamp "SARKARI ADDA" in their
# footer, most don't. This makes it consistent everywhere without
# stomping on footers that already carry useful info (timers, page
# counts, etc.) — those get "SARKARI ADDA  •  <existing text>" instead.

BRAND = "SARKARI ADDA"


def brand(embed: discord.Embed, extra: str | None = None) -> discord.Embed:
    """Stamp the SARKARI ADDA footer on an embed, preserving any existing footer text."""
    existing = embed.footer.text if embed.footer else None
    parts = [BRAND]
    if extra:
        parts.append(extra)
    elif existing:
        parts.append(existing)
    embed.set_footer(text="  •  ".join(parts))
    return embed
