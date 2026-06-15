from discord.ext import commands, tasks
import discord
import random
import asyncio
import aiohttp
import datetime
import io
import math

from PIL import Image, ImageDraw, ImageFont

from utils.pokemon_db import db


# ─────────────────────────────────────────────────────────────────────
# URL HELPERS
# ─────────────────────────────────────────────────────────────────────

def _clean(name: str) -> str:
    return name.lower().replace(" ", "").replace(".", "").replace("'", "")

def gif_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/xyani/{_clean(name)}.gif"

def sprite_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/gen5/{_clean(name)}.png"


# ─────────────────────────────────────────────────────────────────────
# DEX IMAGE CONSTANTS
# ─────────────────────────────────────────────────────────────────────

COLS      = 3        # cards per row
CELL_W    = 112      # card width  (px)
CELL_H    = 150      # card height (px)
PAD       = 14       # outer padding
GAP       = 10       # gap between cards
SPRITE_SZ = 84       # sprite bounding box

# Discord dark-mode palette
BG_COLOR   = (32,  34,  37)
CARD_COLOR = (47,  49,  54)
SHADOW_CLR = (22,  23,  25)
ACCENT_CLR = (88, 101, 242)   # blurple
WHITE      = (255, 255, 255)
SUBTEXT    = (148, 155, 164)


# ─────────────────────────────────────────────────────────────────────
# FONT LOADER
# ─────────────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    suffix = "-Bold" if bold else ""
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{suffix}.ttf",
        f"/usr/share/fonts/truetype/freefont/FreeSans{'Bold' if bold else ''}.ttf",
        f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────

def _draw_centered(draw, cx, y, text, font, fill):
    """Draw text horizontally centered at pixel x = cx."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, y), text, fill=fill, font=font)


async def _fetch_sprite(session, name):
    """Download a gen-5 sprite; return an RGBA Image or None on failure."""
    try:
        async with session.get(
            sprite_url(name),
            timeout=aiohttp.ClientTimeout(total=6),
        ) as r:
            if r.status != 200:
                return None
            return Image.open(io.BytesIO(await r.read())).convert("RGBA")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────
# BUILD THE GRID IMAGE
# ─────────────────────────────────────────────────────────────────────

async def build_dex_image(rows: list) -> io.BytesIO:
    """
    Render a sprite-grid dex card for up to 9 Pokemon.
    Returns a BytesIO PNG ready to attach to a Discord message.
    """
    n      = len(rows)
    n_cols = COLS
    n_rows = math.ceil(n / COLS)

    iw = PAD + n_cols * CELL_W + (n_cols - 1) * GAP + PAD
    ih = PAD + n_rows * CELL_H + (n_rows - 1) * GAP + PAD

    img  = Image.new("RGBA", (iw, ih), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_name = _load_font(12, bold=True)
    font_id   = _load_font(11)
    font_unk  = _load_font(30, bold=True)

    # Download all sprites concurrently
    async with aiohttp.ClientSession() as sess:
        sprites = await asyncio.gather(
            *[_fetch_sprite(sess, r["name"]) for r in rows]
        )

    for i, (row, spr) in enumerate(zip(rows, sprites)):
        col = i % COLS
        ri  = i // COLS
        x   = PAD + col * (CELL_W + GAP)
        y   = PAD + ri  * (CELL_H + GAP)

        # Drop shadow
        draw.rounded_rectangle(
            [x + 3, y + 3, x + CELL_W + 3, y + CELL_H + 3],
            radius=12, fill=SHADOW_CLR,
        )
        # Card body
        draw.rounded_rectangle(
            [x, y, x + CELL_W, y + CELL_H],
            radius=12, fill=CARD_COLOR,
        )
        # Blurple accent bar at top of card
        draw.rounded_rectangle(
            [x + 8, y + 5, x + CELL_W - 8, y + 9],
            radius=4, fill=ACCENT_CLR,
        )

        # Sprite
        sprite_top = y + 16
        if spr:
            spr.thumbnail((SPRITE_SZ, SPRITE_SZ), Image.LANCZOS)
            sw, sh = spr.size
            sx = x + (CELL_W - sw) // 2
            sy = sprite_top + (SPRITE_SZ - sh) // 2
            img.paste(spr, (sx, sy), spr)
        else:
            _draw_centered(
                draw,
                x + CELL_W // 2,
                sprite_top + SPRITE_SZ // 2 - 18,
                "?", font_unk, SUBTEXT,
            )

        # Name + Dex number
        ty    = sprite_top + SPRITE_SZ + 7
        cx    = x + CELL_W // 2
        label = row["display"]
        if len(label) > 13:
            label = label[:12] + "\u2026"

        _draw_centered(draw, cx, ty,      label,                      font_name, WHITE)
        _draw_centered(draw, cx, ty + 17, f"#{row['pokedex_id']:03}", font_id,   SUBTEXT)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────
# PAGINATED DEX VIEW  (modern Discord Buttons)
# ─────────────────────────────────────────────────────────────────────

class DexView(discord.ui.View):

    def __init__(self, rows: list, target: discord.Member):
        super().__init__(timeout=120)
        self.rows   = rows
        self.target = target
        self.pages  = [rows[i : i + 9] for i in range(0, len(rows), 9)]
        self.page   = 0
        self.msg    = None
        self._sync_buttons()

    def _sync_buttons(self):
        self.btn_prev.disabled = self.page == 0
        self.btn_next.disabled = self.page >= len(self.pages) - 1
        self.btn_page.label    = f"{self.page + 1} / {len(self.pages)}"

    async def build(self):
        """Return (embed, file) for the current page."""
        buf  = await build_dex_image(self.pages[self.page])
        file = discord.File(buf, filename="dex.png")

        embed = discord.Embed(
            title=f"\U0001f4d6  {self.target.display_name}'s Pokedex",
            color=0x5865F2,
        )
        embed.set_author(
            name     = f"{len(self.rows)} Pokemon in collection",
            icon_url = self.target.display_avatar.url,
        )
        embed.set_image(url="attachment://dex.png")
        embed.set_footer(
            text=(
                f"Page {self.page + 1} of {len(self.pages)}  |  "
                ".pokemon sell <name> <price> to trade"
            )
        )
        return embed, file

    @discord.ui.button(emoji="\u2b05\ufe0f", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._sync_buttons()
        embed, file = await self.build()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.primary, disabled=True)
    async def btn_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(emoji="\u27a1\ufe0f", style=discord.ButtonStyle.secondary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._sync_buttons()
        embed, file = await self.build()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.msg:
            try:
                await self.msg.edit(view=self)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────
# SPAWN HELPERS
# ─────────────────────────────────────────────────────────────────────

TOTAL_POKEMON = 898
active_spawns: dict = {}


async def fetch_random_pokemon():
    pid = random.randint(1, TOTAL_POKEMON)
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{pid}") as r:
            if r.status != 200:
                return None
            data = await r.json()
    return {"id": pid, "name": data["name"], "display": data["name"].title()}


# ─────────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────────

class PokemonSpawn(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()

    @tasks.loop(minutes=10)
    async def spawn_loop(self):
        if db is None:
            return
        for doc in db.pokemon_spawn_channels.find():
            ch = self.bot.get_channel(int(doc["channel_id"]))
            if ch:
                await self.do_spawn(ch)

    @spawn_loop.before_loop
    async def before_spawn(self):
        await self.bot.wait_until_ready()

    async def do_spawn(self, channel: discord.TextChannel):
        poke = await fetch_random_pokemon()
        if not poke:
            return
        active_spawns[str(channel.id)] = {**poke, "caught": False}
        embed = discord.Embed(
            title="A wild Pokemon appeared! \U0001f33f",
            description=(
                "**Who's that Pokemon?** \U0001f914\n\n"
                "Type `.catch <pokemon name>` to catch it!\n"
                "First trainer to guess correctly wins!\n\n"
                "\u26a0\ufe0f You can only catch each species **once**!"
            ),
            color=0xF1C40F,
        )
        embed.set_image(url=gif_url(poke["name"]))
        embed.set_footer(text="Be fast! Only one trainer can catch it.")
        await channel.send(embed=embed)

    @commands.command(name="catch")
    async def catch(self, ctx, *, guess: str = None):
        cid   = str(ctx.channel.id)
        spawn = active_spawns.get(cid)

        if spawn is None or spawn["caught"]:
            await ctx.send(embed=discord.Embed(
                description="There's no wild Pokemon here right now!",
                color=0xED4245,
            ))
            return

        if guess is None:
            await ctx.send(embed=discord.Embed(
                description="Type the Pokemon's name!\nExample: `.catch Charizard`",
                color=0xED4245,
            ))
            return

        if guess.strip().lower() != spawn["name"].lower():
            await ctx.send(embed=discord.Embed(
                description=f"\u274c That's not right, **{ctx.author.display_name}**! Keep trying!",
                color=0xED4245,
            ), delete_after=4)
            return

        uid     = str(ctx.author.id)
        already = db.pokemon_collection.find_one({"user_id": uid, "name": spawn["name"]})
        if already:
            await ctx.send(embed=discord.Embed(
                title="Already caught! \U0001f6ab",
                description=(
                    f"**{ctx.author.display_name}**, you already own a **{spawn['display']}**!\n"
                    "Each trainer can only catch one of each species.\n\n"
                    "Let someone else catch it! \U0001f3af"
                ),
                color=0xFFA500,
            ), delete_after=8)
            return

        spawn["caught"] = True
        db.pokemon_collection.insert_one({
            "user_id":    uid,
            "name":       spawn["name"],
            "display":    spawn["display"],
            "pokedex_id": spawn["id"],
            "moves":      [],
            "caught_at":  datetime.datetime.utcnow(),
        })

        embed = discord.Embed(
            title=f"Gotcha! {spawn['display']} was caught! \U0001f389",
            description=(
                f"**{ctx.author.display_name}** caught **{spawn['display']}**!\n\n"
                f"Use `.team` to add it, `.moves` to teach it moves!\n"
                f"Want to sell? Use `.pokemon sell {spawn['display']} <price>`"
            ),
            color=0x57F287,
        )
        embed.set_image(url=gif_url(spawn["name"]))
        embed.set_footer(text=f"Pokedex #{spawn['id']}")
        await ctx.send(embed=embed)

    @commands.command(name="pokemons", aliases=["pc", "collection"])
    async def pokemon_collection(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        rows   = list(
            db.pokemon_collection
            .find({"user_id": str(target.id)})
            .sort("caught_at", -1)
        )

        if not rows:
            await ctx.send(embed=discord.Embed(
                title="\U0001f4d6  Empty Pokedex",
                description=(
                    f"**{target.display_name}** hasn't caught any Pokemon yet!\n\n"
                    "Pokemon spawn every 10 minutes — type `.catch <name>` when one appears!"
                ),
                color=0xED4245,
            ))
            return

        view         = DexView(rows, target)
        embed, file  = await view.build()
        msg          = await ctx.send(embed=embed, file=file, view=view)
        view.msg     = msg

    @commands.command(name="setspawnchannel")
    @commands.has_permissions(manage_guild=True)
    async def set_spawn_channel(self, ctx):
        db.pokemon_spawn_channels.update_one(
            {"channel_id": str(ctx.channel.id)},
            {"$set": {"guild_id": str(ctx.guild.id)}},
            upsert=True,
        )
        await ctx.send(embed=discord.Embed(
            description=f"\u2705 Pokemon will now spawn in {ctx.channel.mention} every 10 minutes!",
            color=0x57F287,
        ))


async def setup(bot):
    await bot.add_cog(PokemonSpawn(bot))
