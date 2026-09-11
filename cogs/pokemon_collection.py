from discord.ext import commands
import discord
import aiohttp
import asyncio
import io

from PIL import Image, ImageDraw, ImageFont
from utils.pokemon_db import db, get_pokemon_data

RARITY_IDS = {
    "mythical": {151,251,385,386,489,490,491,492,493,494,647,648,649,719,720,721,801,802,807,808,809,893},
    "legendary": {144,145,146,150,243,244,245,249,250,377,378,379,380,381,382,383,384,480,481,482,483,484,485,486,638,639,640,641,642,643,644,645,646,716,717,718,785,786,787,788,789,790,791,792,800,888,889,890,891,892,894,895,896,897,898,905,1001,1002,1003,1004,1007,1008,1009,1010,1017,1024,1025},
    "ultra_beast": {793,794,795,796,797,798,799,803,804,805,806},
    "pseudo": {149,248,373,376,445,635,706,784,887,998},
}
RARITY_NAMES = {"mythical":"Mythical","legendary":"Legendary","ultra_beast":"Ultra Beast","pseudo":"Pseudo-Legendary","common":"Common"}
RARITY_COLORS = {"mythical":(255,205,55),"legendary":(178,92,245),"ultra_beast":(45,210,210),"pseudo":(240,120,45),"common":(100,220,125)}


def rarity_for(pid):
    for rarity, ids in RARITY_IDS.items():
        if pid in ids:
            return rarity
    return "common"


def normalize(name):
    return "".join(c.lower() for c in str(name) if c.isalnum())


def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


_META_CACHE = {}


async def fetch_meta(session, name):
    key = normalize(name)
    if key in _META_CACHE:
        return _META_CACHE[key]
    try:
        api_name = str(name).lower().replace(" ", "-")
        async with session.get(f"https://pokeapi.co/api/v2/pokemon/{api_name}", timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status != 200:
                return None
            data = await r.json()
        sprites = data.get("sprites", {})
        other = sprites.get("other", {})
        showdown = other.get("showdown", {}).get("front_default")
        artwork = other.get("official-artwork", {}).get("front_default")
        meta = {"name": str(name).title(), "id": int(data["id"]), "rarity": rarity_for(int(data["id"])), "sprite": artwork or showdown or sprites.get("front_default")}
        _META_CACHE[key] = meta
        return meta
    except Exception:
        return None


async def build_image(entries, title, total_caught, unique_count):
    W, H = 1200, 1180
    img = Image.new("RGB", (W, H), (18, 21, 28))
    d = ImageDraw.Draw(img)
    d.text((50, 28), title, fill=(245,245,248), font=font(38, True))
    d.text((52, 76), f"{total_caught} caught  •  {unique_count} unique  •  Sorted by Pokédex #", fill=(155,165,180), font=font(19))

    async with aiohttp.ClientSession() as session:
        async def load(entry):
            try:
                async with session.get(entry["sprite"], timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        return Image.open(io.BytesIO(await r.read())).convert("RGBA")
            except Exception:
                pass
            return None
        sprites = await asyncio.gather(*(load(e) for e in entries))

    margin_x, top = 40, 120
    card_w, card_h, gap = 360, 320, 20
    for i, (entry, sprite) in enumerate(zip(entries, sprites)):
        row, col = divmod(i, 3)
        x = margin_x + col * (card_w + gap)
        y = top + row * (card_h + gap)
        rarity = entry["rarity"]
        accent = RARITY_COLORS[rarity]
        d.rounded_rectangle((x,y,x+card_w,y+card_h), radius=22, fill=(27,32,42), outline=(58,67,82), width=2)
        d.rounded_rectangle((x,y,x+8,y+card_h), radius=4, fill=accent)

        if sprite:
            sprite.thumbnail((255,220), Image.Resampling.LANCZOS)
            px = x + (card_w - sprite.width)//2
            py = y + 8
            img.paste(sprite, (px, py), sprite)
        else:
            d.text((x+125,y+90), "Image unavailable", fill=(130,140,155), font=font(18))

        d.text((x+22,y+235), f"#{entry['id']:03}", fill=(150,160,175), font=font(18))
        d.text((x+22,y+260), entry["name"], fill=(248,248,250), font=font(25, True))
        d.text((x+22,y+292), RARITY_NAMES[rarity], fill=accent, font=font(18, True))
        count = entry.get("count", 1)
        if count > 1:
            badge = f"×{count}"
            bbox = d.textbbox((0,0), badge, font=font(18, True))
            bw = bbox[2]-bbox[0]+22
            d.rounded_rectangle((x+card_w-bw-14,y+14,x+card_w-14,y+43), radius=12, fill=(48,55,70))
            d.text((x+card_w-bw-3,y+17), badge, fill=(235,238,245), font=font(18, True))

    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    out.seek(0)
    return out


class CollectionView(discord.ui.View):
    def __init__(self, ctx, entries, total_caught, unique_count):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.entries = entries
        self.total_caught = total_caught
        self.unique_count = unique_count
        self.page = 0
        self.per_page = 9
        self.total_pages = max(1, (len(entries)+8)//9)
        self.refresh_buttons()

    def refresh_buttons(self):
        self.prev.disabled = self.page <= 0
        self.next.disabled = self.page >= self.total_pages-1

    async def render(self):
        current = self.entries[self.page*9:(self.page+1)*9]
        image = await build_image(current, f"{self.ctx.author.display_name}'s Pokémon", self.total_caught, self.unique_count)
        file = discord.File(image, filename="pokemon_collection.png")
        embed = discord.Embed(title="Pokémon Collection", description=f"**Page {self.page+1}/{self.total_pages}**", color=0x5865F2)
        embed.set_image(url="attachment://pokemon_collection.png")
        embed.set_footer(text="9 Pokémon per page • Pokédex order • Buttons expire after 3 minutes")
        self.refresh_buttons()
        return embed, file

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ This collection isn't yours.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        self.page -= 1
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        self.page += 1
        embed, file = await self.render()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)


class PokemonCollection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.remove_command("pokemons")
        bot.remove_command("dex")
        bot.remove_command("pokedex")

    @commands.command(name="pokemons")
    async def pokemons(self, ctx):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        inventory = [str(x) for x in get_pokemon_data(ctx.author.id).get("inventory", [])]
        if not inventory:
            await ctx.send(f"📦 **{ctx.author.display_name}** has no Pokémon yet.")
            return
        counts = {}
        for name in inventory:
            key = normalize(name)
            counts[key] = counts.get(key, 0) + 1
        async with aiohttp.ClientSession() as session:
            metas = await asyncio.gather(*(fetch_meta(session, name) for name in counts))
        entries = []
        for meta in metas:
            if meta:
                meta["count"] = counts.get(normalize(meta["name"]), 1)
                entries.append(meta)
        entries.sort(key=lambda x: (x["id"], x["name"].lower()))
        total = len(inventory)
        unique = len(entries)
        view = CollectionView(ctx, entries, total, unique)
        embed, file = await view.render()
        await ctx.send(embed=embed, file=file, view=view)


async def setup(bot):
    await bot.add_cog(PokemonCollection(bot))
