from discord.ext import commands
from discord.ext import tasks
import discord
import random
import asyncio
import aiohttp
import sqlite3

# ─────────────────────────────────────────────────────────────────
# GIF URL  (same source as randoms.py)
# ─────────────────────────────────────────────────────────────────

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

def sprite_url(name: str) -> str:
    """Small static sprite for lists."""
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/gen5/{clean}.png"

# ─────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────

DB_PATH = "pokemon.db"

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with get_db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS pokemon_collection (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                display     TEXT    NOT NULL,
                pokedex_id  INTEGER NOT NULL,
                move1       TEXT    DEFAULT NULL,
                move2       TEXT    DEFAULT NULL,
                move3       TEXT    DEFAULT NULL,
                move4       TEXT    DEFAULT NULL,
                caught_at   TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS pokemon_teams (
                user_id TEXT PRIMARY KEY,
                slot1 TEXT, slot2 TEXT, slot3 TEXT,
                slot4 TEXT, slot5 TEXT, slot6 TEXT
            );
            CREATE TABLE IF NOT EXISTS spawn_channels (
                channel_id TEXT PRIMARY KEY,
                guild_id   TEXT NOT NULL
            );
        """)

# ─────────────────────────────────────────────────────────────────
# POKEAPI
# ─────────────────────────────────────────────────────────────────

TOTAL_POKEMON = 898

async def fetch_random_pokemon() -> dict | None:
    pid = random.randint(1, TOTAL_POKEMON)
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{pid}") as r:
            if r.status != 200:
                return None
            data = await r.json()
    return {
        "id":      pid,
        "name":    data["name"],
        "display": data["name"].title(),
    }

# ─────────────────────────────────────────────────────────────────
# ACTIVE SPAWNS  { channel_id: {id, name, display, caught} }
# ─────────────────────────────────────────────────────────────────

active_spawns: dict = {}

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class PokemonSpawn(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        init_db()
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()

    # ── Hourly spawn ──────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def spawn_loop(self):
        with get_db() as con:
            rows = con.execute("SELECT channel_id FROM spawn_channels").fetchall()
        for row in rows:
            ch = self.bot.get_channel(int(row["channel_id"]))
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
            title="A wild Pokémon appeared! 🌿",
            description=(
                f"**Who is that Pokémon?**\n\n"
                f"Type `.catch {poke['display']}` to catch it!\n"
                f"First one to type it correctly wins!"
            ),
            color=0xF1C40F,
        )
        # GIF shown — name hidden until caught
        embed.set_image(url=gif_url(poke["name"]))
        embed.set_footer(text="Be fast! Only one trainer can catch it.")
        await channel.send(embed=embed)

    # ── .catch <name> ─────────────────────────────────────────────

    @commands.command(name="catch")
    async def catch(self, ctx, *, guess: str = None):
        cid = str(ctx.channel.id)
        spawn = active_spawns.get(cid)

        if spawn is None or spawn["caught"]:
            await ctx.send(embed=discord.Embed(
                description="There's no wild Pokémon here right now!",
                color=0xED4245,
            ))
            return

        if guess is None:
            await ctx.send(embed=discord.Embed(
                description=f"❓ Type the Pokémon's name!\nExample: `.catch Charizard`",
                color=0xED4245,
            ))
            return

        if guess.strip().lower() != spawn["name"].lower():
            await ctx.send(embed=discord.Embed(
                description=f"❌ That's not right, **{ctx.author.display_name}**! Keep trying!",
                color=0xED4245,
            ), delete_after=4)
            return

        # Correct! Mark caught immediately (race-condition safe)
        spawn["caught"] = True

        with get_db() as con:
            con.execute(
                "INSERT INTO pokemon_collection (user_id, name, display, pokedex_id) VALUES (?,?,?,?)",
                (str(ctx.author.id), spawn["name"], spawn["display"], spawn["id"]),
            )

        embed = discord.Embed(
            title=f"Gotcha! {spawn['display']} was caught! 🎉",
            description=(
                f"**{ctx.author.display_name}** caught **{spawn['display']}**!\n\n"
                f"Use `.team` to add it, `.moves` to teach it moves!"
            ),
            color=0x57F287,
        )
        embed.set_image(url=gif_url(spawn["name"]))
        embed.set_footer(text=f"Pokédex #{spawn['id']}")
        await ctx.send(embed=embed)

    # ── .pokemon [user] ───────────────────────────────────────────

    @commands.command(name="pokemon", aliases=["pc", "collection"])
    async def pokemon_collection(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        with get_db() as con:
            rows = con.execute(
                "SELECT display, name, pokedex_id FROM pokemon_collection "
                "WHERE user_id=? ORDER BY caught_at DESC",
                (str(target.id),),
            ).fetchall()

        if not rows:
            await ctx.send(embed=discord.Embed(
                description=f"**{target.display_name}** hasn't caught any Pokémon yet!",
                color=0xED4245,
            ))
            return

        # 9 per page — 3 per row using embed fields with small sprites in name
        per_page = 9
        pages = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]
        page = 0

        def make_embed(p: int) -> discord.Embed:
            embed = discord.Embed(
                title=f"📖 {target.display_name}'s Pokémon",
                color=0x5865F2,
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            for row in pages[p]:
                embed.add_field(
                    name=f"{row['display']}",
                    value=f"[🎞]({gif_url(row['name'])}) `#{row['pokedex_id']:03}`",
                    inline=True,
                )
            embed.set_footer(text=f"Page {p+1}/{len(pages)}  •  {len(rows)} total Pokémon")
            return embed

        msg = await ctx.send(embed=make_embed(0))
        if len(pages) == 1:
            return

        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ("⬅️", "➡️")
                and reaction.message.id == msg.id
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)
                if str(reaction.emoji) == "➡️" and page < len(pages) - 1:
                    page += 1
                elif str(reaction.emoji) == "⬅️" and page > 0:
                    page -= 1
                await msg.edit(embed=make_embed(page))
                try:
                    await msg.remove_reaction(reaction, user)
                except Exception:
                    pass
            except asyncio.TimeoutError:
                break

    # ── Admin: set spawn channel ──────────────────────────────────

    @commands.command(name="setspawnchannel")
    @commands.has_permissions(manage_guild=True)
    async def set_spawn_channel(self, ctx):
        with get_db() as con:
            con.execute(
                "INSERT OR REPLACE INTO spawn_channels (channel_id, guild_id) VALUES (?,?)",
                (str(ctx.channel.id), str(ctx.guild.id)),
            )
        await ctx.send(embed=discord.Embed(
            description=f"✅ Pokémon will now spawn in {ctx.channel.mention} every hour!",
            color=0x57F287,
        ))

    @commands.command(name="spawntest")
    @commands.has_permissions(manage_guild=True)
    async def spawn_test(self, ctx):
        await self.do_spawn(ctx.channel)


async def setup(bot):
    await bot.add_cog(PokemonSpawn(bot))
              
