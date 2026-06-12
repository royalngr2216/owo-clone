from discord.ext import commands
from discord.ext import tasks
import discord
import random
import asyncio
import aiohttp
import datetime

# ─────────────────────────────────────────────────────────────────
# MONGODB IMPORT
# ─────────────────────────────────────────────────────────────────
from utils.pokemon_db import db

# ─────────────────────────────────────────────────────────────────
# GIF / SPRITE URLS
# ─────────────────────────────────────────────────────────────────

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

def sprite_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/gen5/{clean}.png"

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
        self.spawn_loop.start()

    def cog_unload(self):
        self.spawn_loop.cancel()

    # ── Hourly spawn ──────────────────────────────────────────────

    @tasks.loop(minutes=10)
    async def spawn_loop(self):
        if db is None:
            return
            
        # Fetch all registered spawn channels from MongoDB
        channels = db.pokemon_spawn_channels.find()
        for doc in channels:
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
            title="A wild Pokémon appeared! 🌿",
            description=(
                "**Who's that Pokémon?** 🤔\n\n"
                "Type `.catch <pokémon name>` to catch it!\n"
                "First trainer to guess correctly wins!\n\n"
                "⚠️ You can only catch each species **once**!"
            ),
            color=0xF1C40F,
        )
        # GIF shown — name is intentionally hidden so players must guess
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
                description="❓ Type the Pokémon's name!\nExample: `.catch Charizard`",
                color=0xED4245,
            ))
            return

        if guess.strip().lower() != spawn["name"].lower():
            await ctx.send(embed=discord.Embed(
                description=f"❌ That's not right, **{ctx.author.display_name}**! Keep trying!",
                color=0xED4245,
            ), delete_after=4)
            return

        # ── One-species-per-player check ──────────────────────────
        uid = str(ctx.author.id)
        
        # Check MongoDB if player already owns this Pokémon
        already = db.pokemon_collection.find_one({
            "user_id": uid, 
            "name": spawn["name"]
        })

        if already:
            await ctx.send(embed=discord.Embed(
                title="Already caught! 🚫",
                description=(
                    f"**{ctx.author.display_name}**, you already own a **{spawn['display']}**!\n"
                    "Each trainer can only catch one of each species.\n\n"
                    "Let someone else catch it! 🎯"
                ),
                color=0xFFA500,
            ), delete_after=8)
            return

        # Correct and not a duplicate — mark caught immediately (race-condition safe)
        spawn["caught"] = True

        # Save the newly caught Pokémon to MongoDB
        db.pokemon_collection.insert_one({
            "user_id": uid,
            "name": spawn["name"],
            "display": spawn["display"],
            "pokedex_id": spawn["id"],
            "moves": [], # Default to no moves set
            "caught_at": datetime.datetime.utcnow()
        })

        embed = discord.Embed(
            title=f"Gotcha! {spawn['display']} was caught! 🎉",
            description=(
                f"**{ctx.author.display_name}** caught **{spawn['display']}**!\n\n"
                f"Use `.team` to add it, `.moves` to teach it moves!\n"
                f"Want to sell? Use `.pokemon sell {spawn['display']} <price>`"
            ),
            color=0x57F287,
        )
        embed.set_image(url=gif_url(spawn["name"]))
        embed.set_footer(text=f"Pokédex #{spawn['id']}")
        await ctx.send(embed=embed)

    # ── .pokemon [user] ───────────────────────────────────────────

    @commands.command(name="pokemons", aliases=["pc", "collection"])
    async def pokemon_collection(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        
        # Fetch collection from MongoDB, sorted by newest catch first
        rows = list(db.pokemon_collection.find({"user_id": str(target.id)}).sort("caught_at", -1))

        if not rows:
            await ctx.send(embed=discord.Embed(
                description=f"**{target.display_name}** hasn't caught any Pokémon yet!",
                color=0xED4245,
            ))
            return

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
        # Update or insert the channel for this specific guild
        db.pokemon_spawn_channels.update_one(
            {"channel_id": str(ctx.channel.id)},
            {"$set": {"guild_id": str(ctx.guild.id)}},
            upsert=True
        )
        
        await ctx.send(embed=discord.Embed(
            description=f"✅ Pokémon will now spawn in {ctx.channel.mention} every hour!",
            color=0x57F287,
        ))

async def setup(bot):
    await bot.add_cog(PokemonSpawn(bot))
    
