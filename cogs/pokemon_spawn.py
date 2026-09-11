from discord.ext import commands, tasks
import discord
import random
import aiohttp
import asyncio
import io

from PIL import Image, ImageDraw, ImageFont

from utils.pokemon_db import db, get_pokemon_data, add_pokemon, get_balls, remove_ball, pokemon_spawn_channels


def _clean(name: str) -> str:
    return name.lower().replace(" ", "").replace(".", "").replace("'", "").replace("-", "")


def sprite_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/gen9/{_clean(name)}.png"


def spawn_gif_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/ani/{_clean(name)}.gif"


def normalize_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


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
MYTHICAL_IDS = frozenset({151,251,385,386,489,490,491,492,493,494,647,648,649,719,720,721,801,802,807,808,809,893})
LEGENDARY_IDS = frozenset({144,145,146,150,243,244,245,249,250,377,378,379,380,381,382,383,384,480,481,482,483,484,485,486,638,639,640,641,642,643,644,645,646,716,717,718,785,786,787,788,789,790,791,792,800,888,889,890,891,892,894,895,896,897,898,905,1001,1002,1003,1004,1007,1008,1009,1010,1017,1024,1025})
ULTRA_BEAST_IDS = frozenset({793,794,795,796,797,798,799,803,804,805,806})
PSEUDO_LEGENDARY_IDS = frozenset({149,248,373,376,445,635,706,784,887,998})
RARITY_LABELS = {"mythical":"✨ Mythical","legendary":"👑 Legendary","ultra_beast":"🔮 Ultra Beast","pseudo":"🔥 Pseudo-Legendary","common":"🟢 Common"}
RARITY_EMBED_COLORS = {"mythical":0xFFD700,"legendary":0xA349E8,"ultra_beast":0x20D2D2,"pseudo":0xE86420,"common":0x57F287}
RARITY_TEXT_COLORS = {"mythical":(255,215,0),"legendary":(163,73,232),"ultra_beast":(32,210,210),"pseudo":(232,100,32),"common":(87,242,135)}
RARITY_SPAWN_EXTRA = {"mythical":"✨ **A MYTHICAL Pokémon has appeared — incredibly rare!** ✨","legendary":"👑 **A LEGENDARY Pokémon has appeared!** 👑","ultra_beast":"🔮 **An ULTRA BEAST has appeared!** 🔮","pseudo":"🔥 **A powerful Pseudo-Legendary has appeared!** 🔥","common":""}
RARITY_SORT_ORDER = {"mythical": 0, "legendary": 1, "ultra_beast": 2, "pseudo": 3, "common": 4}


def get_rarity(pokedex_id: int) -> str:
    if pokedex_id in MYTHICAL_IDS: return "mythical"
    if pokedex_id in LEGENDARY_IDS: return "legendary"
    if pokedex_id in ULTRA_BEAST_IDS: return "ultra_beast"
    if pokedex_id in PSEUDO_LEGENDARY_IDS: return "pseudo"
    return "common"


_META_CACHE = {}


async def fetch_pokemon_meta(name: str):
    key = normalize_name(name)
    if key in _META_CACHE:
        return _META_CACHE[key]
    try:
        api_name = str(name).lower().replace(" ", "-")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pokeapi.co/api/v2/pokemon/{api_name}", timeout=aiohttp.ClientTimeout(total=8)) as response:
                if response.status != 200: return None
                data = await response.json()
        pid = int(data["id"])
        meta = {"name": str(name).title(), "id": pid, "rarity": get_rarity(pid), "sprite": data.get("sprites", {}).get("front_default") or sprite_url(name)}
        _META_CACHE[key] = meta
        return meta
    except Exception:
        return None


async def build_collection_image(items, title):
    width, height = 900, 960
    image = Image.new("RGB", (width, height), (22, 25, 32))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 17)
    except Exception:
        title_font = name_font = small_font = ImageFont.load_default()
    draw.text((35, 28), title, fill=(245,245,245), font=title_font)
    async with aiohttp.ClientSession() as session:
        async def load(item):
            try:
                async with session.get(item["sprite"], timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status == 200:
                        return Image.open(io.BytesIO(await response.read())).convert("RGBA")
            except Exception: pass
            return None
        sprites = await asyncio.gather(*(load(item) for item in items))
    card_w, card_h, gap = 270, 255, 20
    for index, (item, sprite) in enumerate(zip(items, sprites)):
        row, col = divmod(index, 3)
        x, y = 35 + col*(card_w+gap), 90 + row*(card_h+gap)
        rarity = item["rarity"]
        rarity_color = RARITY_TEXT_COLORS[rarity]
        draw.rounded_rectangle((x,y,x+card_w,y+card_h), radius=16, fill=(28,33,42), outline=rarity_color, width=3)
        if sprite:
            sprite.thumbnail((150,150), Image.Resampling.LANCZOS)
            image.paste(sprite, (x+(card_w-sprite.width)//2,y+5), sprite)
        else:
            draw.text((x+100,y+65), "No image", fill=(150,155,165), font=small_font)
        draw.text((x+14,y+165), f"#{item['id']:03}", fill=(180,185,195), font=small_font)
        draw.text((x+14,y+188), item["name"], fill=(250,250,250), font=name_font)
        draw.text((x+14,y+219), RARITY_LABELS[rarity], fill=rarity_color, font=small_font)
    output = io.BytesIO(); image.save(output, format="PNG"); output.seek(0); return output


class PokemonCollectionView(discord.ui.View):
    def __init__(self, ctx, entries, title):
        super().__init__(timeout=180)
        self.ctx, self.entries, self.title = ctx, entries, title
        self.page, self.per_page = 0, 9
        self.sort_mode = "pokedex"
        self.total_pages = max(1, (len(entries)+8)//9)
        self._sort_entries()
        self._update_buttons()

    def _sort_entries(self):
        if self.sort_mode == "rarity":
            self.entries.sort(key=lambda x: (RARITY_SORT_ORDER.get(x["rarity"], 99), x["id"], x["name"].lower()))
        else:
            self.entries.sort(key=lambda x: (x["id"], x["name"].lower()))
        self.total_pages = max(1, (len(self.entries)+self.per_page-1)//self.per_page)
        self.page = min(self.page, self.total_pages - 1)

    def _update_buttons(self):
        self.previous.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.total_pages-1
        self.rarity_sort.disabled = self.sort_mode == "rarity"
        self.pokedex_sort.disabled = self.sort_mode == "pokedex"

    async def render(self):
        current = self.entries[self.page*self.per_page:(self.page+1)*self.per_page]
        image = await build_collection_image(current, self.title)
        file = discord.File(image, filename="pokemon_collection.png")
        sort_label = "Rarity" if self.sort_mode == "rarity" else "Pokédex #"
        embed = discord.Embed(
            title=self.title,
            description=f"Page **{self.page+1}/{self.total_pages}** • Sorted by **{sort_label}**",
            color=0x5865F2,
        )
        embed.set_image(url="attachment://pokemon_collection.png")
        embed.set_footer(text=f"{len(self.entries)} {'unique species' if 'Pokédex' in self.title else 'Pokémon'} • 9 per page")
        self._update_buttons()
        return embed, file

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ This Pokémon list isn't yours.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✨ Rarity", style=discord.ButtonStyle.primary, row=0)
    async def rarity_sort(self, interaction, button):
        self.sort_mode = "rarity"
        self.page = 0
        self._sort_entries()
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="📖 Pokédex", style=discord.ButtonStyle.secondary, row=0)
    async def pokedex_sort(self, interaction, button):
        self.sort_mode = "pokedex"
        self.page = 0
        self._sort_entries()
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def previous(self, interaction, button):
        self.page -= 1
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary, row=1)
    async def next_button(self, interaction, button):
        self.page += 1
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)


class PokemonSpawn(commands.Cog):
    SPAWN_INTERVAL_MINUTES = 30
    NATIONAL_DEX_MAX = 1025

    def __init__(self, bot): self.bot = bot

    async def cog_load(self):
        if not self.spawn_loop.is_running(): self.spawn_loop.start()

    def cog_unload(self): self.spawn_loop.cancel()

    async def _collection(self, ctx, unique=False):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        target = ctx.author
        inventory = [str(x) for x in get_pokemon_data(target.id).get("inventory", [])]
        if not inventory:
            await ctx.send(f"📦 **{target.display_name}** has no Pokémon yet.")
            return
        names = list(dict.fromkeys(inventory))
        info = await asyncio.gather(*(fetch_pokemon_meta(name) for name in names))
        by_name = {normalize_name(x["name"]): x for x in info if x}
        entries = []
        if unique:
            entries = [by_name[normalize_name(name)] for name in names if normalize_name(name) in by_name]
        else:
            for name in inventory:
                item = by_name.get(normalize_name(name))
                if item: entries.append(item.copy())
        entries.sort(key=lambda x: (x["id"], x["name"].lower()))
        title = f"📖 {target.display_name}'s Pokédex" if unique else f"📦 {target.display_name}'s Pokémon"
        view = PokemonCollectionView(ctx, entries, title)
        embed, file = await view.render()
        await ctx.send(embed=embed, file=file, view=view)

    @commands.command(name="pokemons")
    async def pokemons(self, ctx): await self._collection(ctx, unique=False)

    @commands.command(name="dex", aliases=["pokedex"])
    async def dex(self, ctx): await self._collection(ctx, unique=True)

    @commands.group(name="spawn", invoke_without_command=True)
    @commands.guild_only()
    async def spawn(self, ctx):
        if not ctx.invoked_subcommand:
            config = pokemon_spawn_channels.find_one({"_id":ctx.guild.id}) if pokemon_spawn_channels is not None else None
            channel_id = config.get("channel_id") if config else None
            channel = ctx.guild.get_channel(channel_id) if channel_id else None
            await ctx.send(f"🐾 Pokémon spawns are enabled in {channel.mention}.\nUse `.spawn disable` to turn them off." if channel else "❌ Pokémon spawns are not configured. Use `.spawn set #channel`.")

    @spawn.command(name="set")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def spawn_set(self, ctx, channel: discord.TextChannel):
        if pokemon_spawn_channels is None:
            await ctx.send("❌ MongoDB is not configured, so spawn settings cannot be saved.")
            return
        pokemon_spawn_channels.update_one({"_id":ctx.guild.id},{"$set":{"channel_id":channel.id,"enabled":True}},upsert=True)
        await ctx.send(f"✅ Pokémon spawns are now enabled in {channel.mention}.\nA Pokémon will spawn there every **{self.SPAWN_INTERVAL_MINUTES} minutes**.")
        await self.spawn_in_guild(ctx.guild)

    @spawn.command(name="disable")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def spawn_disable(self, ctx):
        if pokemon_spawn_channels is not None:
            pokemon_spawn_channels.update_one({"_id":ctx.guild.id},{"$set":{"enabled":False},"$unset":{"active":""}},upsert=True)
        await ctx.send("🛑 Pokémon spawns have been disabled for this server.")

    @commands.command(name="forcespawn")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def force_spawn(self, ctx):
        if pokemon_spawn_channels is None:
            await ctx.send("❌ MongoDB is not configured, so spawn settings cannot be used.")
            return
        config = pokemon_spawn_channels.find_one({"_id":ctx.guild.id})
        if not config or not config.get("enabled"):
            await ctx.send("❌ Spawns are disabled. Use `.spawn set #channel` first.")
            return
        await self.spawn_in_guild(ctx.guild, force=True)
        await ctx.send("⚡ Forced Pokémon spawn!")

    async def spawn_in_guild(self, guild, force=False):
        if pokemon_spawn_channels is None: return
        config = pokemon_spawn_channels.find_one({"_id":guild.id})
        if not config or not config.get("enabled"): return
        channel = guild.get_channel(config.get("channel_id"))
        if channel is None: return
        try:
            async with aiohttp.ClientSession() as session:
                pokemon_id = random.randint(1,self.NATIONAL_DEX_MAX)
                async with session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}",timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status != 200: return
                    data = await response.json()
            name = data["name"].replace("-"," ").title()
            rarity = get_rarity(pokemon_id)
            embed=discord.Embed(title="✨ A wild Pokémon has appeared!",description=f"{RARITY_SPAWN_EXTRA[rarity]}\n\nCatch it with:\n**`.catch pokeball <name>`**\n**`.catch ultraball <name>`**\n**`.catch masterball <name>`**",color=RARITY_EMBED_COLORS[rarity])
            embed.set_image(url=spawn_gif_url(name))
            embed.set_footer(text="First successful catch gets the Pokémon!")
            message=await channel.send(embed=embed)
            pokemon_spawn_channels.update_one({"_id":guild.id},{"$set":{"active":{"name":name,"pokedex_id":pokemon_id,"rarity":rarity,"message_id":message.id}}},upsert=True)
        except Exception as exc:
            print(f"Pokemon spawn error in {guild.id}: {exc}")

    @tasks.loop(minutes=SPAWN_INTERVAL_MINUTES)
    async def spawn_loop(self):
        for guild in self.bot.guilds: await self.spawn_in_guild(guild)

    @spawn_loop.before_loop
    async def before_spawn_loop(self): await self.bot.wait_until_ready()

    @commands.command(name="catch")
    @commands.guild_only()
    async def catch(self, ctx, ball: str = None, *, pokemon_name: str = None):
        if pokemon_spawn_channels is None: return
        config=pokemon_spawn_channels.find_one({"_id":ctx.guild.id})
        if not config or not config.get("enabled") or not config.get("active"):
            await ctx.send("❌ There is no Pokémon to catch right now.")
            return
        if config.get("channel_id") != ctx.channel.id:
            await ctx.send(f"❌ Pokémon are spawning in <#{config.get('channel_id')}>.")
            return
        if not ball or not pokemon_name:
            await ctx.send("❌ Use `.catch pokeball <name>`, `.catch ultraball <name>`, or `.catch masterball <name>`.")
            return
        ball=BALL_ALIASES.get(ball.lower(),ball.lower())
        if ball not in BALLS:
            await ctx.send("❌ Ball must be `pokeball`, `ultraball`, or `masterball`.")
            return
        active=config["active"]
        if normalize_name(pokemon_name) != normalize_name(active["name"]):
            await ctx.send("❌ That's not the Pokémon that spawned. Check the image and try again.")
            return
        balls=get_balls(ctx.author.id)
        ball_db=BALLS[ball]["db"]
        if balls.get(ball_db,0)<=0:
            await ctx.send(f"❌ You don't have a {BALLS[ball]['name']}.")
            return
        remove_ball(ctx.author.id,ball_db,1)
        rarity=active["rarity"]
        if random.randint(1,100)<=CATCH_RATES[ball][rarity]:
            add_pokemon(ctx.author.id,active["name"])
            pokemon_spawn_channels.update_one({"_id":ctx.guild.id},{"$unset":{"active":""}})
            embed=discord.Embed(title="🎉 You caught it!",description=f"**Pokémon:** {active['name']}\n**Rarity:** {RARITY_LABELS[rarity]}\n**Pokédex #:** `{active['pokedex_id']:03}`\n**Ball Used:** {BALLS[ball]['name']}\n\n{active['name']} has been added to your collection!",color=RARITY_EMBED_COLORS[rarity])
            embed.set_image(url=sprite_url(active["name"]))
            await ctx.send(embed=embed)
        else:
            embed=discord.Embed(title="💨 The Pokémon broke free!",description=f"The wild **{active['name']}** escaped!\n**Ball Used:** {BALLS[ball]['name']}",color=0xED4245)
            embed.set_image(url=sprite_url(active["name"]))
            await ctx.send(embed=embed)


async def setup(bot): await bot.add_cog(PokemonSpawn(bot))