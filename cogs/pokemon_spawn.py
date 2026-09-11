from discord.ext import commands, tasks
import discord
import random
import aiohttp

from utils.pokemon_db import (
    db,
    get_pokemon_data,
    add_pokemon,
    get_balls,
    remove_ball,
    pokemon_spawn_channels,
)


def _clean(name: str) -> str:
    return name.lower().replace(" ", "").replace(".", "").replace("'", "").replace("-", "")


def gif_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/ani/{_clean(name)}.gif"


BALLS = {
    "pokeball": {"name": "Poké Ball", "db": "pokeball"},
    "ultraball": {"name": "Ultra Ball", "db": "ultraball"},
    "masterball": {"name": "Master Ball", "db": "masterball"},
}
BALL_ALIASES = {"pb": "pokeball", "ub": "ultraball", "mb": "masterball"}
BALL_EMOJI = {
    "pokeball": "<:pb:1517998351227031632>",
    "ultraball": "<:ub:1517997681564324114>",
    "masterball": "<a:mb:1517997721288704111>",
}
CATCH_RATES = {
    "pokeball": {"common": 35, "pseudo": 15, "ultra_beast": 15, "legendary": 7, "mythical": 3},
    "ultraball": {"common": 60, "pseudo": 30, "ultra_beast": 30, "legendary": 15, "mythical": 6},
    "masterball": {"common": 100, "pseudo": 100, "ultra_beast": 100, "legendary": 100, "mythical": 100},
}
MYTHICAL_IDS = frozenset({151, 251, 385, 386, 489, 490, 491, 492, 493, 494, 647, 648, 649, 719, 720, 721, 801, 802, 807, 808, 809, 893})
LEGENDARY_IDS = frozenset({144,145,146,150,243,244,245,249,250,377,378,379,380,381,382,383,384,480,481,482,483,484,485,486,638,639,640,641,642,643,644,645,646,716,717,718,785,786,787,788,789,790,791,792,800,888,889,890,891,892,894,895,896,897,898,905,1001,1002,1003,1004,1007,1008,1009,1010,1017,1024,1025})
ULTRA_BEAST_IDS = frozenset({793,794,795,796,797,798,799,803,804,805,806})
PSEUDO_LEGENDARY_IDS = frozenset({149,248,373,376,445,635,706,784,887,998})


def get_rarity(pokedex_id: int) -> str:
    if pokedex_id in MYTHICAL_IDS: return "mythical"
    if pokedex_id in LEGENDARY_IDS: return "legendary"
    if pokedex_id in ULTRA_BEAST_IDS: return "ultra_beast"
    if pokedex_id in PSEUDO_LEGENDARY_IDS: return "pseudo"
    return "common"

RARITY_LABELS = {"mythical": "✨ Mythical", "legendary": "👑 Legendary", "ultra_beast": "🔮 Ultra Beast", "pseudo": "🔥 Pseudo-Legendary", "common": "🟢 Common"}
RARITY_EMBED_COLORS = {"mythical": 0xFFD700, "legendary": 0xA349E8, "ultra_beast": 0x20D2D2, "pseudo": 0xE86420, "common": 0x57F287}
RARITY_SPAWN_EXTRA = {
    "mythical": "✨ **A MYTHICAL Pokémon has appeared — incredibly rare!** ✨",
    "legendary": "👑 **A LEGENDARY Pokémon has appeared!** 👑",
    "ultra_beast": "🔮 **An ULTRA BEAST has appeared!** 🔮",
    "pseudo": "🔥 **A powerful Pseudo-Legendary has appeared!** 🔥",
    "common": "",
}


async def fetch_pokemon_info(names):
    unique = {str(name).lower() for name in names}
    result = {}
    if not unique:
        return result
    try:
        async with aiohttp.ClientSession() as session:
            async def fetch(name):
                try:
                    async with session.get(f"https://pokeapi.co/api/v2/pokemon/{name.replace(' ', '-')}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            return name, data.get("id", 9999)
                except Exception:
                    pass
                return name, 9999
            values = await __import__("asyncio").gather(*(fetch(name) for name in unique))
            for name, pokedex_id in values:
                result[name] = pokedex_id
    except Exception:
        pass
    return result


class PokemonCollectionView(discord.ui.View):
    def __init__(self, ctx, entries, title, page=0):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.entries = entries
        self.title = title
        self.page = page
        self.per_page = 9
        self.total_pages = max(1, (len(entries) + self.per_page - 1) // self.per_page)
        self._update_buttons()

    def _update_buttons(self):
        self.clear_items()
        previous = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, disabled=self.page <= 0)
        next_button = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, disabled=self.page >= self.total_pages - 1)
        previous.callback = self.previous_page
        next_button.callback = self.next_page
        self.add_item(previous)
        self.add_item(next_button)

    async def _render(self):
        start = self.page * self.per_page
        current = self.entries[start:start + self.per_page]
        embed = discord.Embed(title=self.title, color=0x5865F2)
        lines = []
        for index, item in enumerate(current, start=start + 1):
            name, pokedex_id, count = item
            rarity = get_rarity(pokedex_id)
            lines.append(f"**{index}. {name}** × `{count}`\n{RARITY_LABELS[rarity]}")
            embed.add_field(name="‎", value=f"[![{name}]({gif_url(name)})]({gif_url(name)})", inline=True)
        if not current:
            embed.description = "No Pokémon found."
        else:
            embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"Page {self.page + 1}/{self.total_pages} • 9 Pokémon per page • Sorted by Pokédex")
        self._update_buttons()
        return embed

    async def previous_page(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ This Pokémon list isn't yours.", ephemeral=True)
            return
        self.page -= 1
        await interaction.response.edit_message(embed=await self._render(), view=self)

    async def next_page(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ This Pokémon list isn't yours.", ephemeral=True)
            return
        self.page += 1
        await interaction.response.edit_message(embed=await self._render(), view=self)


class PokemonSpawn(commands.Cog):
    SPAWN_INTERVAL_MINUTES = 30
    NATIONAL_DEX_MAX = 1025

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if not self.spawn_loop.is_running(): self.spawn_loop.start()

    def cog_unload(self): self.spawn_loop.cancel()

    async def _collection(self, ctx, unique=False):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        target = ctx.author
        data = get_pokemon_data(target.id)
        inventory = [str(name) for name in data.get("inventory", [])]
        if not inventory:
            await ctx.send(f"📦 **{target.display_name}** has no Pokémon yet.")
            return
        counts = {}
        for name in inventory:
            counts[name.lower()] = counts.get(name.lower(), 0) + 1
        names = list(counts.keys())
        ids = await fetch_pokemon_info(names)
        if unique:
            entries = [(name.title(), ids.get(name, 9999), 1) for name in names]
        else:
            entries = [(name.title(), ids.get(name, 9999), counts[name]) for name in names]
        entries.sort(key=lambda x: (x[1], x[0].lower()))
        title = f"📖 {target.display_name}'s Pokédex" if unique else f"📦 {target.display_name}'s Pokémon"
        view = PokemonCollectionView(ctx, entries, title)
        await ctx.send(embed=await view._render(), view=view)

    @commands.command(name="pokemons")
    async def pokemons(self, ctx):
        await self._collection(ctx, unique=False)

    @commands.command(name="dex", aliases=["pokedex"])
    async def dex(self, ctx):
        await self._collection(ctx, unique=True)

    @commands.group(name="spawn", invoke_without_command=True)
    @commands.guild_only()
    async def spawn(self, ctx):
        if not ctx.invoked_subcommand:
            config = pokemon_spawn_channels.find_one({"_id": ctx.guild.id}) if pokemon_spawn_channels is not None else None
            channel_id = config.get("channel_id") if config else None
            channel = ctx.guild.get_channel(channel_id) if channel_id else None
            if channel:
                await ctx.send(f"🐾 Pokémon spawns are enabled in {channel.mention}.\nUse `.spawn disable` to turn them off.")
            else:
                await ctx.send("❌ Pokémon spawns are not configured. Use `.spawn set #channel`.")

    @spawn.command(name="set")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def spawn_set(self, ctx, channel: discord.TextChannel):
        if pokemon_spawn_channels is None:
            await ctx.send("❌ MongoDB is not configured, so spawn settings cannot be saved.")
            return
        pokemon_spawn_channels.update_one({"_id": ctx.guild.id}, {"$set": {"channel_id": channel.id, "enabled": True}}, upsert=True)
        await ctx.send(f"✅ Pokémon spawns are now enabled in {channel.mention}.\nA Pokémon will spawn there every **{self.SPAWN_INTERVAL_MINUTES} minutes**.")
        await self.spawn_in_guild(ctx.guild)

    @spawn.command(name="disable")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def spawn_disable(self, ctx):
        if pokemon_spawn_channels is not None:
            pokemon_spawn_channels.update_one({"_id": ctx.guild.id}, {"$set": {"enabled": False}, "$unset": {"active": ""}}, upsert=True)
        await ctx.send("🛑 Pokémon spawns have been disabled for this server.")

    @commands.command(name="forcespawn")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def force_spawn(self, ctx):
        if pokemon_spawn_channels is None:
            await ctx.send("❌ MongoDB is not configured, so spawn settings cannot be used.")
            return
        config = pokemon_spawn_channels.find_one({"_id": ctx.guild.id})
        if not config or not config.get("enabled"):
            await ctx.send("❌ Spawns are disabled. Use `.spawn set #channel` first.")
            return
        await self.spawn_in_guild(ctx.guild, force=True)
        await ctx.send("⚡ Forced Pokémon spawn!")

    async def spawn_in_guild(self, guild, force=False):
        if pokemon_spawn_channels is None: return
        config = pokemon_spawn_channels.find_one({"_id": guild.id})
        if not config or not config.get("enabled"): return
        channel = guild.get_channel(config.get("channel_id"))
        if channel is None: return
        try:
            async with aiohttp.ClientSession() as session:
                pokemon_id = random.randint(1, self.NATIONAL_DEX_MAX)
                async with session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}", timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status != 200: return
                    data = await response.json()
            name = data["name"].replace("-", " ").title()
            rarity = get_rarity(pokemon_id)
            embed = discord.Embed(title="✨ A wild Pokémon has appeared!", description=f"{RARITY_SPAWN_EXTRA[rarity]}\n\nType **`.catch pokeball`**, **`.catch ultraball`**, or **`.catch masterball`** to catch it!", color=RARITY_EMBED_COLORS[rarity])
            embed.set_image(url=gif_url(name))
            embed.set_footer(text="First successful catch gets the Pokémon!")
            message = await channel.send(embed=embed)
            pokemon_spawn_channels.update_one({"_id": guild.id}, {"$set": {"active": {"name": name, "pokedex_id": pokemon_id, "rarity": rarity, "message_id": message.id}}}, upsert=True)
        except Exception as exc:
            print(f"Pokemon spawn error in {guild.id}: {exc}")

    @tasks.loop(minutes=SPAWN_INTERVAL_MINUTES)
    async def spawn_loop(self):
        for guild in self.bot.guilds: await self.spawn_in_guild(guild)

    @spawn_loop.before_loop
    async def before_spawn_loop(self): await self.bot.wait_until_ready()

    @commands.command(name="catch")
    @commands.guild_only()
    async def catch(self, ctx, ball: str = "pokeball"):
        if pokemon_spawn_channels is None: return
        config = pokemon_spawn_channels.find_one({"_id": ctx.guild.id})
        if not config or not config.get("enabled") or not config.get("active"):
            await ctx.send("❌ There is no Pokémon to catch right now.")
            return
        if config.get("channel_id") != ctx.channel.id:
            await ctx.send(f"❌ Pokémon are spawning in <#{config.get('channel_id')}>.")
            return
        ball = ball.lower()
        ball = BALL_ALIASES.get(ball, ball)
        if ball not in BALLS:
            await ctx.send("❌ Use `.catch pokeball`, `.catch ultraball`, or `.catch masterball`.")
            return
        balls = get_balls(ctx.author.id)
        ball_db = BALLS[ball]["db"]
        if balls.get(ball_db, 0) <= 0:
            await ctx.send(f"❌ You don't have a {BALLS[ball]['name']}.")
            return
        active = config["active"]
        remove_ball(ctx.author.id, ball_db, 1)
        if random.randint(1, 100) <= CATCH_RATES[ball][active["rarity"]]:
            add_pokemon(ctx.author.id, active["name"])
            pokemon_spawn_channels.update_one({"_id": ctx.guild.id}, {"$unset": {"active": ""}})
            await ctx.send(f"🎉 **{ctx.author.display_name} caught {active['name']}!** {BALL_EMOJI[ball]}\n**Ball used:** {BALLS[ball]['name']}\n**Rarity:** {RARITY_LABELS[active['rarity']]}" )
        else:
            await ctx.send(f"💨 **The Pokémon broke free!** {BALLS[ball]['name']} was used. Try again with another ball.")


async def setup(bot):
    await bot.add_cog(PokemonSpawn(bot))
