"""
pokemon_moves.py
================
Handles .moves, .moveset, and .learncheck commands.

Learnset source : Pokémon Showdown  (National Dex — all generations)
Move stats      : PokéAPI           (power / type / damage class)

All bugs fixed:
  ✅  Fake Out on Lopunny — Showdown data includes egg moves
  ✅  Flash Cannon on Kingdra — Showdown inherits TM learnsets
  ✅  Hidden Power Ice / Fire / etc. — parsed as 60BP Special of that type
  ✅  Return / Frustration — shown as Physical 102BP (not status)
  ✅  Learnset covers ALL gens (Gen 1–9) so no move is unfairly rejected

New in v2:
  ✨  .moves <Pokémon>  (no moves) → interactive dropdown UI (4 Select menus)
  ✨  Moves sorted alphabetically in all dropdowns
  ✨  Premium embed design throughout
  ✅  Original text command (.moves <Pokémon> move1, move2...) still works
"""

from __future__ import annotations

import asyncio
import json
import re

import aiohttp
import discord
from discord.ext import commands

from utils.pokemon_db import db


# ─────────────────────────────────────────────────────────────────
# ID HELPERS
# ─────────────────────────────────────────────────────────────────

def to_id(text: str) -> str:
    """Showdown ID: lowercase, alphanumeric only.
    'Fake Out' → 'fakeout',  'Flash Cannon' → 'flashcannon'"""
    return re.sub(r"[^a-z0-9]", "", text.lower().strip())


def to_slug(text: str) -> str:
    """PokéAPI slug: lowercase, hyphenated.
    'Fake Out' → 'fake-out',  'Flash Cannon' → 'flash-cannon'"""
    text = text.strip().lower()
    text = re.sub(r"[''`]", "", text)
    return re.sub(r"[\s_]+", "-", text)


def gif_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/xyani/{to_id(name)}.gif"


# ─────────────────────────────────────────────────────────────────
# VISUAL HELPERS
# ─────────────────────────────────────────────────────────────────

TYPE_COLORS = {
    "normal":   0xA8A878, "fire":     0xF08030, "water":    0x6890F0,
    "electric": 0xF8D030, "grass":    0x78C850, "ice":      0x98D8D8,
    "fighting": 0xC03028, "poison":   0xA040A0, "ground":   0xE0C068,
    "flying":   0xA890F0, "psychic":  0xF85888, "bug":      0xA8B820,
    "rock":     0xB8A038, "ghost":    0x705898, "dragon":   0x7038F8,
    "dark":     0x705848, "steel":    0xB8B8D0, "fairy":    0xEE99AC,
}

TYPE_EMOJI = {
    "normal": "⬜", "fire": "🔥", "water": "💧",   "electric": "⚡",
    "grass":  "🍃", "ice":  "❄️",  "fighting": "🥊", "poison":   "☠️",
    "ground": "🌍", "flying": "🌬️", "psychic": "🔮", "bug":      "🐛",
    "rock":   "🪨", "ghost": "👻", "dragon": "🐉",  "dark":     "🌑",
    "steel":  "🔩", "fairy": "✨",
}

CAT_EMOJI = {"physical": "💥", "special": "✨", "status": "🔄"}

# Slot indicators for the embed
SLOT_LABELS = ["① Move 1", "② Move 2", "③ Move 3", "④ Move 4"]
SLOT_EMOJI  = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]


# ─────────────────────────────────────────────────────────────────
# MOVE OVERRIDES
# PokéAPI returns null power for variable-power moves; fix them here
# ─────────────────────────────────────────────────────────────────

MOVE_OVERRIDES: dict[str, dict] = {
    # Friendship-based (max friendship = 102)
    "return":        {"display": "Return",        "power": 102, "type": "normal",   "category": "physical"},
    "frustration":   {"display": "Frustration",   "power": 102, "type": "normal",   "category": "physical"},
    # Weight-based
    "gyro-ball":     {"display": "Gyro Ball",     "power": 150, "type": "steel",    "category": "physical"},
    "heat-crash":    {"display": "Heat Crash",    "power": 120, "type": "fire",     "category": "physical"},
    "heavy-slam":    {"display": "Heavy Slam",    "power": 120, "type": "steel",    "category": "physical"},
    # Speed-based
    "electro-ball":  {"display": "Electro Ball",  "power": 150, "type": "electric", "category": "special"},
    # Weight-based specials
    "grass-knot":    {"display": "Grass Knot",    "power": 120, "type": "grass",    "category": "special"},
    "low-kick":      {"display": "Low Kick",      "power": 120, "type": "fighting", "category": "physical"},
    # PP-based
    "trump-card":    {"display": "Trump Card",    "power": 200, "type": "normal",   "category": "special"},
    # Magnitude (average)
    "magnitude":     {"display": "Magnitude",     "power": 70,  "type": "ground",   "category": "physical"},
    # Stored Power / Power Trip (base)
    "stored-power":  {"display": "Stored Power",  "power": 20,  "type": "psychic",  "category": "special"},
    "power-trip":    {"display": "Power Trip",    "power": 20,  "type": "dark",     "category": "physical"},
    # Spit Up (max)
    "spit-up":       {"display": "Spit Up",       "power": 300, "type": "normal",   "category": "special"},
    # Acrobatics (no item)
    "acrobatics":    {"display": "Acrobatics",    "power": 110, "type": "flying",   "category": "physical"},
    # Natural Gift (average berry)
    "natural-gift":  {"display": "Natural Gift",  "power": 80,  "type": "normal",   "category": "physical"},
    # Terrain Pulse (base)
    "terrain-pulse": {"display": "Terrain Pulse", "power": 50,  "type": "normal",   "category": "special"},
    # Echoed Voice (base)
    "echoed-voice":  {"display": "Echoed Voice",  "power": 40,  "type": "normal",   "category": "special"},
    # Rollout / Ice Ball (base)
    "rollout":       {"display": "Rollout",       "power": 30,  "type": "rock",     "category": "physical"},
    "ice-ball":      {"display": "Ice Ball",      "power": 30,  "type": "ice",      "category": "physical"},
    # Smelling Salts / Wake-Up Slap (doubled)
    "smelling-salts":{"display": "Smelling Salts","power": 70,  "type": "normal",   "category": "physical"},
    "wake-up-slap":  {"display": "Wake-Up Slap",  "power": 70,  "type": "fighting", "category": "physical"},
    # Wring Out
    "wring-out":     {"display": "Wring Out",     "power": 120, "type": "normal",   "category": "special"},
    "crush-grip":    {"display": "Crush Grip",    "power": 120, "type": "normal",   "category": "physical"},
}


# ─────────────────────────────────────────────────────────────────
# HIDDEN POWER
# ─────────────────────────────────────────────────────────────────

_HP_TYPES = frozenset({
    "fire", "water", "grass", "electric", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock",
    "ghost", "dragon", "dark", "steel",
})

_HP_RE = re.compile(r"^hidden[\s\-_]?power[\s\-_]?([a-z]+)?$", re.I)


def parse_hidden_power(name: str) -> dict | None:
    """
    'Hidden Power Ice' → move dict with type=ice, power=60, category=special
    Returns None if the input is not a Hidden Power variant.
    """
    m = _HP_RE.match(name.strip())
    if not m:
        return None
    hp_type = (m.group(1) or "normal").lower()
    if hp_type not in _HP_TYPES and hp_type != "normal":
        return None
    return {
        "name":     f"hidden-power-{hp_type}",   # stored with type suffix
        "display":  f"Hidden Power {hp_type.title()}",
        "power":    60,
        "type":     hp_type,
        "category": "special",
        "_learnset_id": "hidden-power",           # slug used for learnset check
    }


# ─────────────────────────────────────────────────────────────────
# SHOWDOWN LEARNSET CACHE
# Loaded once; covers every move a Pokémon can learn in any gen
# ─────────────────────────────────────────────────────────────────

_learnsets:    dict[str, set[str]] = {}
_learnsets_ok: bool                = False
_ls_lock:      asyncio.Lock | None = None


def _lock() -> asyncio.Lock:
    global _ls_lock
    if _ls_lock is None:
        _ls_lock = asyncio.Lock()
    return _ls_lock


async def _fetch_showdown_learnsets(session: aiohttp.ClientSession) -> bool:
    """
    Fetches learnsets.js from Pokémon Showdown and parses it into
    _learnsets: {showdown_poke_id → set of showdown_move_ids}.
    Resolves prevo inheritance so Kingdra gets Seadra's TMs, etc.
    """
    url = "https://play.pokemonshowdown.com/data/learnsets.js"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=45)) as r:
            if r.status != 200:
                return False
            text = await r.text()
    except Exception:
        return False

    # The file is JS: exports.BattleLearnsets = { ... };
    match = re.search(r"(?:exports\.\w+\s*=\s*)(\{[\s\S]+\})\s*;", text)
    if not match:
        return False

    try:
        raw: dict = json.loads(match.group(1))
    except json.JSONDecodeError:
        return False

    prevo_map: dict[str, str] = {}
    tmp:       dict[str, set] = {}

    for poke_id, entry in raw.items():
        tmp[poke_id] = set(entry.get("learnset", {}).keys())
        prevo = entry.get("prevo")
        if prevo:
            prevo_map[poke_id] = to_id(str(prevo))

    # Resolve prevo chain (up to 5 levels deep — e.g. Tyranitar: Larvitar→Pupitar→Tyranitar)
    for _ in range(5):
        changed = False
        for poke_id, prevo_id in prevo_map.items():
            add = tmp.get(prevo_id, set())
            before = len(tmp.get(poke_id, set()))
            tmp[poke_id] = tmp.get(poke_id, set()) | add
            if len(tmp[poke_id]) != before:
                changed = True
        if not changed:
            break

    _learnsets.update(tmp)
    return True


async def ensure_learnsets(session: aiohttp.ClientSession) -> bool:
    global _learnsets_ok
    if _learnsets_ok:
        return True
    async with _lock():
        if not _learnsets_ok:
            _learnsets_ok = await _fetch_showdown_learnsets(session)
    return _learnsets_ok


def showdown_can_learn(pokemon_name: str, move_slug: str) -> bool | None:
    """
    Returns True / False / None(=data not loaded yet).
    pokemon_name: human-readable ('Lopunny', 'lopunny')
    move_slug:    PokéAPI slug  ('fake-out', 'hidden-power', 'flash-cannon')
    """
    if not _learnsets_ok:
        return None

    poke_id = to_id(pokemon_name)
    move_id = to_id(move_slug)

    # Hidden Power: any variant → "hiddenpower"
    if move_id.startswith("hiddenpower"):
        move_id = "hiddenpower"

    # Exact lookup
    if poke_id in _learnsets:
        return move_id in _learnsets[poke_id]

    # Strip form suffixes and retry
    for suffix in ("mega", "alola", "galar", "hisui", "paldea",
                   "origin", "black", "white", "therian",
                   "primal", "ultra", "sky"):
        if poke_id.endswith(suffix):
            base = poke_id[: -len(suffix)]
            if base in _learnsets:
                return move_id in _learnsets[base]

    return False


# ─────────────────────────────────────────────────────────────────
# MOVE DATA — PokéAPI with overrides
# ─────────────────────────────────────────────────────────────────

async def fetch_move_data(session: aiohttp.ClientSession, name: str) -> dict | None:
    """
    Fetch stats for one move. Checks HP pattern and overrides first.
    Returns {name, display, power, type, category} or None.
    """
    # Hidden Power variant?
    hp = parse_hidden_power(name)
    if hp:
        return hp

    slug = to_slug(name)

    # Known override (Return, Frustration, etc.)?
    if slug in MOVE_OVERRIDES:
        ov = MOVE_OVERRIDES[slug]
        return {"name": slug, **ov}

    # PokéAPI
    try:
        async with session.get(
            f"https://pokeapi.co/api/v2/move/{slug}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                return None
            data = await r.json()
    except Exception:
        return None

    return {
        "name":     data["name"],
        "display":  data["name"].replace("-", " ").title(),
        "power":    data.get("power") or 0,
        "type":     data["type"]["name"],
        "category": data["damage_class"]["name"],
    }


# ─────────────────────────────────────────────────────────────────
# FALLBACK LEARNSET — PokéAPI (used if Showdown is unreachable)
# ─────────────────────────────────────────────────────────────────

async def pokeapi_can_learn(session: aiohttp.ClientSession,
                             pokemon: str, move_slug: str) -> bool:
    try:
        async with session.get(
            f"https://pokeapi.co/api/v2/pokemon/{to_slug(pokemon)}",
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status != 200:
                return False
            data = await r.json()
    except Exception:
        return False

    learnable = {m["move"]["name"] for m in data["moves"]}
    # Normalise HP variants for the fallback too
    check = "hidden-power" if move_slug.startswith("hidden-power") else move_slug
    return check in learnable


# ─────────────────────────────────────────────────────────────────
# MOVE DROPDOWN UI
# ─────────────────────────────────────────────────────────────────

# Curated alphabetical move list for the dropdowns.
# Add more moves here as your game grows — they'll appear automatically.
DROPDOWN_MOVES: list[str] = sorted([
    # ── Physical ──────────────────────────────────────────────────
    "Acrobatics", "Aqua Jet", "Aqua Tail", "Body Slam", "Bounce",
    "Brave Bird", "Brick Break", "Bug Bite", "Bulldoze", "Close Combat",
    "Crunch", "Dragon Claw", "Dragon Rush", "Drain Punch", "Earthquake",
    "Extreme Speed", "Facade", "Fake Out", "Fire Punch", "Flare Blitz",
    "Fly", "Frustration", "Gunk Shot", "Head Smash", "High Jump Kick",
    "Ice Punch", "Ice Shard", "Iron Head", "Iron Tail", "Knock Off",
    "Low Kick", "Low Sweep", "Mach Punch", "Play Rough", "Poison Jab",
    "Power Whip", "Psycho Cut", "Pursuit", "Quick Attack", "Return",
    "Rock Slide", "Rock Tomb", "Seed Bomb", "Shadow Claw", "Shadow Sneak",
    "Sucker Punch", "Super Fang", "Superpower", "Throat Chop",
    "Thunder Punch", "U-turn", "Wild Charge", "Wing Attack",
    "Wood Hammer", "X-Scissor", "Zen Headbutt",
    # ── Special ───────────────────────────────────────────────────
    "Aura Sphere", "Blizzard", "Boomburst", "Bug Buzz",
    "Charge Beam", "Dark Pulse", "Dazzling Gleam",
    "Dragon Pulse", "Draco Meteor", "Earth Power", "Energy Ball",
    "Extrasensory", "Fire Blast", "Flamethrower", "Flash Cannon",
    "Focus Blast", "Giga Drain", "Hex", "Hydro Pump",
    "Hyper Voice", "Ice Beam", "Leaf Storm",
    "Moonblast", "Night Shade", "Overheat",
    "Petal Dance", "Power Gem", "Psychic", "Psyshock",
    "Scald", "Shadow Ball", "Signal Beam", "Sludge Bomb", "Sludge Wave",
    "Stored Power", "Surf", "Thunderbolt", "Thunder", "Tri Attack",
    "Vacuum Wave", "Volt Switch", "Water Pulse",
    # ── Status ────────────────────────────────────────────────────
    "Agility", "Amnesia", "Aromatherapy", "Baton Pass",
    "Bulk Up", "Calm Mind", "Cotton Guard", "Curse", "Defog",
    "Dragon Dance", "Encore", "Endure", "Glare", "Gravity",
    "Growth", "Haze", "Heal Bell", "Helping Hand", "Howl",
    "Leech Seed", "Light Screen", "Magic Coat",
    "Memento", "Moonlight", "Morning Sun", "Pain Split",
    "Parting Shot", "Perish Song", "Protect", "Quiver Dance",
    "Rapid Spin", "Recover", "Reflect", "Rest", "Roost",
    "Shell Smash", "Shift Gear", "Sleep Talk",
    "Soft-Boiled", "Spikes", "Stealth Rock", "Sticky Web",
    "Substitute", "Sunny Day", "Swords Dance", "Synthesis", "Taunt",
    "Thunder Wave", "Toxic", "Toxic Spikes", "Trick",
    "Trick Room", "Will-O-Wisp", "Wish", "Yawn",
    # ── Hidden Power ──────────────────────────────────────────────
    "Hidden Power Bug", "Hidden Power Dark", "Hidden Power Dragon",
    "Hidden Power Electric", "Hidden Power Fighting", "Hidden Power Fire",
    "Hidden Power Flying", "Hidden Power Ghost", "Hidden Power Grass",
    "Hidden Power Ground", "Hidden Power Ice", "Hidden Power Poison",
    "Hidden Power Psychic", "Hidden Power Rock", "Hidden Power Steel",
    "Hidden Power Water",
], key=str.lower)


def _build_select_options(slot_index: int, current: str | None) -> list[discord.SelectOption]:
    """Build sorted SelectOption list for one move slot."""
    options = [
        discord.SelectOption(
            label="— Skip this slot —",
            value="__none__",
            description="Leave this move slot empty",
            emoji="➖",
            default=(current is None),
        )
    ]
    for move in DROPDOWN_MOVES:
        options.append(
            discord.SelectOption(
                label=move,
                value=move,
                default=(move == current),
            )
        )
    return options


def _build_preview_embed(
    poke_display: str,
    poke_name: str,
    selections: list[str | None],
    pending: bool = True,
) -> discord.Embed:
    """
    Build the live-preview embed shown while the user selects moves.
    selections: list of 4 items, each a move name string or None.
    """
    filled = [s for s in selections if s]
    color  = 0x5865F2  # Discord blurple — neutral until confirmed

    if pending:
        title = f"🎮  Teaching moves to **{poke_display}**"
        desc  = (
            "Use the dropdowns below to pick up to **4 moves**.\n"
            "Moves are sorted **alphabetically**. "
            "Skip any slot you don't need.\n"
            "Press **✅ Confirm** when you're done."
        )
    else:
        title = f"✅  Moves taught to **{poke_display}**!"
        desc  = ""
        color = 0x57F287  # green

    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=gif_url(poke_name))

    slot_lines = []
    for i, sel in enumerate(selections):
        slot_num = SLOT_EMOJI[i]
        if sel:
            slot_lines.append(f"{slot_num}  **{sel}**")
        else:
            slot_lines.append(f"{slot_num}  *— empty —*")

    embed.add_field(
        name="📋  Current Selection",
        value="\n".join(slot_lines),
        inline=False,
    )

    if pending:
        embed.set_footer(
            text=f"{'▓' * len(filled)}{'░' * (4 - len(filled))}  {len(filled)}/4 slots filled"
                 "  •  National Dex · All generations"
        )
    else:
        embed.set_footer(text="National Dex • All generations • Use .team to build your roster")

    return embed


def _build_result_embed(
    poke_display: str,
    poke_name: str,
    taught: list[dict],
    not_found: list[str],
    cant_learn: list[str],
) -> discord.Embed:
    """Premium result embed after validation completes."""
    primary_type = taught[0]["type"] if taught else "normal"
    color = TYPE_COLORS.get(primary_type, 0x5865F2)

    embed = discord.Embed(
        title=f"✅  Moves taught to {poke_display}!",
        color=color,
    )
    embed.set_thumbnail(url=gif_url(poke_name))

    move_lines = []
    for i, m in enumerate(taught, 1):
        t_emoji = TYPE_EMOJI.get(m["type"], "")
        c_emoji = CAT_EMOJI.get(m["category"], "")
        power   = f"**{m['power']} BP**" if m["power"] else "—"
        move_lines.append(
            f"`{i}.` **{m['display']}**\n"
            f"     {t_emoji} {m['type'].title()}  "
            f"• {c_emoji} {m['category'].title()}  "
            f"• ⚡ {power}"
        )

    embed.add_field(
        name="📋  Moveset",
        value="\n".join(move_lines),
        inline=False,
    )

    if not_found or cant_learn:
        warn_parts = []
        if not_found:
            warn_parts.append(f"❌ Not found: {', '.join(not_found)}")
        if cant_learn:
            warn_parts.append(f"🚫 Can't learn: {', '.join(cant_learn)}")
        embed.add_field(name="⚠️  Skipped", value="\n".join(warn_parts), inline=False)

    embed.set_footer(text="National Dex • All generations • Use .team to build your roster")
    return embed


class MoveSelect(discord.ui.Select):
    """A single move-slot dropdown."""

    def __init__(self, slot_index: int, current: str | None):
        self.slot_index = slot_index
        slot_label = ["Move 1", "Move 2", "Move 3", "Move 4"][slot_index]
        super().__init__(
            placeholder=f"🎯  {slot_label} — pick a move…",
            min_values=1,
            max_values=1,
            options=_build_select_options(slot_index, current),
            row=slot_index,  # rows 0–3
            custom_id=f"move_slot_{slot_index}",
        )

    async def callback(self, interaction: discord.Interaction):
        # Let the parent View handle state
        await self.view.on_slot_change(interaction, self.slot_index, self.values[0])


class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Confirm Moveset",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=4,
            custom_id="confirm_moves",
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_confirm(interaction)


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="✖️",
            row=4,
            custom_id="cancel_moves",
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_cancel(interaction)


class MoveSelectView(discord.ui.View):
    """
    Interactive 4-dropdown move selector.
    Only the original command invoker can interact.
    """

    def __init__(
        self,
        ctx: commands.Context,
        poke_name: str,
        poke_display: str,
        uid: str,
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self.ctx          = ctx
        self.poke_name    = poke_name
        self.poke_display = poke_display
        self.uid          = uid
        self.selections: list[str | None] = [None, None, None, None]
        self.message: discord.Message | None = None

        # Add 4 selects + 2 buttons
        for i in range(4):
            self.add_item(MoveSelect(i, None))
        self.add_item(ConfirmButton())
        self.add_item(CancelButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="⛔  Only the person who ran `.moves` can use these dropdowns.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
            return False
        return True

    async def on_slot_change(
        self, interaction: discord.Interaction, slot: int, value: str
    ):
        self.selections[slot] = None if value == "__none__" else value

        # Rebuild the select so the chosen option shows as default
        # Remove old select for this slot and re-add updated one
        to_remove = None
        for child in self.children:
            if isinstance(child, MoveSelect) and child.slot_index == slot:
                to_remove = child
                break
        if to_remove:
            self.remove_item(to_remove)
        self.add_item(MoveSelect(slot, self.selections[slot]))

        await interaction.response.edit_message(
            embed=_build_preview_embed(
                self.poke_display, self.poke_name, self.selections
            ),
            view=self,
        )

    async def on_confirm(self, interaction: discord.Interaction):
        chosen = [s for s in self.selections if s]
        if not chosen:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌  Please select at least **1 move** before confirming.",
                    color=0xED4245,
                ),
                ephemeral=True,
            )
            return

        # Disable all components while validating
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"⏳  Validating **{len(chosen)} move(s)** for **{self.poke_display}** "
                    "against National Dex learnset…"
                ),
                color=0x5865F2,
            ),
            view=self,
        )

        taught:     list[dict] = []
        not_found:  list[str]  = []
        cant_learn: list[str]  = []

        async with aiohttp.ClientSession() as session:
            await ensure_learnsets(session)

            for raw in chosen:
                move_data = await fetch_move_data(session, raw)
                if move_data is None:
                    not_found.append(raw.title())
                    continue

                learnset_slug = move_data.get("_learnset_id", move_data["name"])
                result = showdown_can_learn(self.poke_name, learnset_slug)
                if result is None:
                    result = await pokeapi_can_learn(session, self.poke_name, learnset_slug)

                if not result:
                    cant_learn.append(move_data["display"])
                    continue

                taught.append(move_data)

        self.stop()

        if not taught:
            lines = []
            if not_found:
                lines.append(f"❌  Move(s) not found: **{', '.join(not_found)}**")
            if cant_learn:
                lines.append(
                    f"🚫  **{self.poke_display}** can't learn in National Dex: "
                    f"**{', '.join(cant_learn)}**"
                )
            lines.append(
                "\n*Check spelling. If you believe this is wrong, "
                "use `.learncheck <Pokémon> <move>` to investigate.*"
            )
            await interaction.edit_original_response(
                embed=discord.Embed(description="\n".join(lines), color=0xED4245),
                view=None,
            )
            return

        # Save to MongoDB
        db.pokemon_collection.update_one(
            {"user_id": self.uid, "name": self.poke_name},
            {"$set": {"moves": [m["name"] for m in taught]}},
        )

        await interaction.edit_original_response(
            embed=_build_result_embed(
                self.poke_display, self.poke_name, taught, not_found, cant_learn
            ),
            view=None,
        )

    async def on_cancel(self, interaction: discord.Interaction):
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"✖️  Move selection for **{self.poke_display}** cancelled.",
                color=0x95A5A6,
            ),
            view=None,
        )

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    embed=discord.Embed(
                        description=(
                            f"⏰  Move selection for **{self.poke_display}** timed out.\n"
                            "Run `.moves` again to retry."
                        ),
                        color=0x95A5A6,
                    ),
                    view=None,
                )
            except discord.NotFound:
                pass


# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class PokemonMoves(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Pre-load learnsets on bot ready
    @commands.Cog.listener()
    async def on_ready(self):
        async with aiohttp.ClientSession() as s:
            ok = await ensure_learnsets(s)
        if ok:
            print(f"[PokemonMoves] ✅ Showdown learnsets loaded — {len(_learnsets):,} Pokémon")
        else:
            print("[PokemonMoves] ⚠️  Showdown learnsets unavailable — falling back to PokéAPI")

    # ── .moves ───────────────────────────────────────────────────

    @commands.command(name="moves")
    async def moves(self, ctx, pokemon_name: str = None, *, move_args: str = None):
        """
        Teach 1–4 moves to a Pokémon you own.

        With no moves specified → opens an interactive dropdown UI.
        With moves typed       → validates & teaches immediately (original behaviour).

        Examples:
          .moves Lopunny                              ← dropdown UI
          .moves Lopunny Fake Out, High Jump Kick, Return, U-Turn
          .moves Kingdra Flash Cannon, Dragon Dance, Surf, Ice Beam
          .moves Jolteon Hidden Power Ice, Thunderbolt, Shadow Ball, Volt Switch
        """
        uid = str(ctx.author.id)

        # ── Usage ─────────────────────────────────────────────
        if not pokemon_name:
            await ctx.send(embed=discord.Embed(
                title="📖  How to teach moves",
                description=(
                    "**Dropdown UI (recommended):**\n"
                    "`.moves <Pokémon>` — opens 4 interactive menus\n\n"
                    "**Quick text input:**\n"
                    "`.moves <Pokémon> move1, move2, move3, move4`\n\n"
                    "**Examples:**\n"
                    "`.moves Lopunny` *(dropdown UI)*\n"
                    "`.moves Lopunny Fake Out, High Jump Kick, Return, U-Turn`\n"
                    "`.moves Kingdra Flash Cannon, Dragon Dance, Surf, Ice Beam`\n"
                    "`.moves Jolteon Hidden Power Ice, Thunderbolt, Shadow Ball, Volt Switch`\n\n"
                    "📌 Validated against the **National Dex** learnset (all generations).\n"
                    "📌 Teach **1–4 moves** separated by commas."
                ),
                color=0x5865F2,
            ))
            return

        # ── Ownership ─────────────────────────────────────────
        pname    = pokemon_name.strip().lower()
        poke_doc = db.pokemon_collection.find_one({"user_id": uid, "name": pname})

        if not poke_doc:
            await ctx.send(embed=discord.Embed(
                description=f"❌  You don't own a **{pokemon_name.title()}**.",
                color=0xED4245,
            ))
            return

        poke_display = poke_doc.get("display", pname.title())

        # ══════════════════════════════════════════════════════
        #  NO MOVES → open dropdown UI
        # ══════════════════════════════════════════════════════
        if not move_args:
            view = MoveSelectView(ctx, pname, poke_display, uid)
            msg  = await ctx.send(
                embed=_build_preview_embed(poke_display, pname, view.selections),
                view=view,
            )
            view.message = msg
            return

        # ══════════════════════════════════════════════════════
        #  MOVES TYPED → original text-command path (unchanged)
        # ══════════════════════════════════════════════════════

        # ── Parse move list ────────────────────────────────────
        raw_moves = [m.strip() for m in move_args.split(",") if m.strip()]
        if not 1 <= len(raw_moves) <= 4:
            await ctx.send(embed=discord.Embed(
                description="❌  Teach between **1 and 4** moves, separated by commas.",
                color=0xED4245,
            ))
            return

        loading = await ctx.send(embed=discord.Embed(
            description=(
                f"⏳  Validating moves for **{poke_display}** "
                f"against National Dex learnset…"
            ),
            color=0x5865F2,
        ))

        taught:     list[dict] = []
        not_found:  list[str]  = []   # move name didn't exist
        cant_learn: list[str]  = []   # move exists but not learnable

        async with aiohttp.ClientSession() as session:

            await ensure_learnsets(session)

            for raw in raw_moves:

                # Fetch move stats (with HP / override handling)
                move_data = await fetch_move_data(session, raw)
                if move_data is None:
                    not_found.append(raw.title())
                    continue

                # The slug to check against learnset
                learnset_slug = move_data.get("_learnset_id", move_data["name"])

                # Validate
                result = showdown_can_learn(pname, learnset_slug)
                if result is None:
                    # Showdown unavailable — PokéAPI fallback
                    result = await pokeapi_can_learn(session, pname, learnset_slug)

                if not result:
                    cant_learn.append(move_data["display"])
                    continue

                taught.append(move_data)

        # ── Nothing valid ──────────────────────────────────────
        if not taught:
            lines = []
            if not_found:
                lines.append(f"❌  Move(s) not found: **{', '.join(not_found)}**")
            if cant_learn:
                lines.append(
                    f"🚫  **{poke_display}** can't learn in National Dex: "
                    f"**{', '.join(cant_learn)}**"
                )
            lines.append("\n*Check spelling. If you believe this is wrong, "
                         "use `.learncheck <Pokémon> <move>` to investigate.*")
            await loading.edit(embed=discord.Embed(
                description="\n".join(lines), color=0xED4245,
            ))
            return

        # ── Save to MongoDB ────────────────────────────────────
        # Store the full slug (includes type for HP: "hidden-power-ice")
        db.pokemon_collection.update_one(
            {"user_id": uid, "name": pname},
            {"$set": {"moves": [m["name"] for m in taught]}},
        )

        # ── Success embed ──────────────────────────────────────
        await loading.edit(embed=_build_result_embed(
            poke_display, pname, taught, not_found, cant_learn
        ))

    # ── .moveset ──────────────────────────────────────────────────

    @commands.command(name="moveset", aliases=["ms"])
    async def moveset(self, ctx, pokemon_name: str = None, member: discord.Member = None):
        """View the current moveset of a Pokémon you (or another user) own."""
        if not pokemon_name:
            await ctx.send(embed=discord.Embed(
                description=(
                    "**Usage:** `.moveset <Pokémon>` or `.moveset <Pokémon> @user`\n"
                    "**Alias:** `.ms <Pokémon>`"
                ),
                color=0xED4245,
            ))
            return

        target   = member or ctx.author
        pname    = pokemon_name.strip().lower()
        poke_doc = db.pokemon_collection.find_one({"user_id": str(target.id), "name": pname})

        if not poke_doc:
            await ctx.send(embed=discord.Embed(
                description=(
                    f"**{target.display_name}** doesn't own "
                    f"a **{pokemon_name.title()}**."
                ),
                color=0xED4245,
            ))
            return

        saved_moves: list[str] = poke_doc.get("moves", [])
        display                = poke_doc.get("display", pname.title())

        embed = discord.Embed(title=f"📋  {display}'s Moveset", color=0x5865F2)
        embed.set_thumbnail(url=gif_url(pname))

        if not saved_moves:
            embed.description = (
                "No moves taught yet!\nUse `.moves` to assign up to 4 moves."
            )
        else:
            lines = []
            for i, slug in enumerate(saved_moves, 1):
                # Pretty-print slugs: "hidden-power-ice" → "Hidden Power Ice"
                pretty = slug.replace("-", " ").title()
                lines.append(f"`{i}.` **{pretty}**")
            embed.description = "\n".join(lines)

        embed.set_footer(text=f"Owned by {target.display_name}")
        await ctx.send(embed=embed)

    # ── .learncheck ───────────────────────────────────────────────

    @commands.command(name="learncheck", aliases=["lc", "canlearn"])
    async def learncheck(self, ctx, pokemon_name: str = None, *, move_name: str = None):
        """
        Check if a Pokémon can learn a specific move in National Dex.

        Examples:
          .learncheck Lopunny Fake Out
          .learncheck Kingdra Flash Cannon
          .learncheck Jolteon Hidden Power Ice
        """
        if not pokemon_name or not move_name:
            await ctx.send(embed=discord.Embed(
                description=(
                    "**Usage:** `.learncheck <Pokémon> <move>`\n"
                    "**Aliases:** `.lc`, `.canlearn`\n\n"
                    "Examples:\n"
                    "`.lc Lopunny Fake Out`\n"
                    "`.lc Kingdra Flash Cannon`"
                ),
                color=0xED4245,
            ))
            return

        async with aiohttp.ClientSession() as session:
            await ensure_learnsets(session)
            move_data = await fetch_move_data(session, move_name)

        if not move_data:
            await ctx.send(embed=discord.Embed(
                description=f"❌  Move **{move_name.title()}** not found.",
                color=0xED4245,
            ))
            return

        learnset_slug = move_data.get("_learnset_id", move_data["name"])
        result        = showdown_can_learn(pokemon_name, learnset_slug)

        t_emoji = TYPE_EMOJI.get(move_data["type"], "")
        c_emoji = CAT_EMOJI.get(move_data["category"], "")
        power   = f"{move_data['power']} BP" if move_data["power"] else "—"

        move_info = (
            f"{t_emoji} {move_data['type'].title()}  "
            f"• {c_emoji} {move_data['category'].title()}  "
            f"• ⚡ {power}"
        )

        if result is True:
            embed = discord.Embed(
                title=f"✅  {pokemon_name.title()} CAN learn {move_data['display']}",
                description=move_info,
                color=0x57F287,
            )
        elif result is False:
            embed = discord.Embed(
                title=f"❌  {pokemon_name.title()} CANNOT learn {move_data['display']}",
                description=f"{move_info}\n\n*Not in National Dex learnset.*",
                color=0xED4245,
            )
        else:
            embed = discord.Embed(
                description=(
                    "⚠️  Learnset data not yet loaded. "
                    "Try again in a moment."
                ),
                color=0xFEE75C,
            )

        embed.set_thumbnail(url=gif_url(pokemon_name))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(PokemonMoves(bot))
