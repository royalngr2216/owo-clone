from discord.ext import commands
import discord
import random

from utils.economy import add_cash, format_cash, create_account
from utils.pokemon_db import db, get_pokemon_data, log_neel_event, get_neel_log

# Neel should be useful, but selling a Pokémon should not print millions.
SELL_PRICE_RANGES = {
    "common":      (500, 1_500),
    "pseudo":      (8_000, 15_000),
    "ultra_beast": (60_000, 75_000),
    "legendary":   (40_000, 60_000),
    "mythical":    (75_000, 100_000),
}
SELL_FLAVOR_TEXT = [
    "This one's got great potential.",
    "I will touch it. For science.",
    "This one asked me not to do that again.",
    "I will touch it a little.",
    "This one still seems upset about the licking.",
    "I've seen its insides.",
    "Collectors will 🍇 over this one.",
    "Rare find. Very very rare.",
    "Not bad. This one is my type.",
]
NEEL_COLOR = 0x2B2D31

# Keep this cog independent from pokemon_spawn.py. A broken optional spawn cog
# must never prevent .neel from loading.
def get_sale_rarity(pokedex_id):
    if pokedex_id is None:
        return "common"
    try:
        pid = int(pokedex_id)
    except (TypeError, ValueError):
        return "common"
    if pid in {144, 145, 146, 150, 151}:
        return "legendary" if pid != 151 else "mythical"
    return "common"

RARITY_LABELS = {
    "common": "⬜ Common",
    "pseudo": "🟪 Pseudo-Legendary",
    "ultra_beast": "🟥 Ultra Beast",
    "legendary": "🌟 Legendary",
    "mythical": "✨ Mythical",
}
RARITY_COLORS = {
    "common": 0x95A5A6,
    "pseudo": 0x9B59B6,
    "ultra_beast": 0xE74C3C,
    "legendary": 0xF1C40F,
    "mythical": 0xE91E63,
}


def _normalize_name(name):
    return "".join(c.lower() for c in str(name) if c.isalnum())


class Neel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="neel", invoke_without_command=True)
    async def neel(self, ctx):
        entries = get_neel_log(limit=10)
        embed = discord.Embed(title="📜 NEEL LOG", color=NEEL_COLOR)
        if not entries:
            embed.description = "🥷 Neel hasn't made a move yet...\n\nStay sharp — he could strike at any catch."
        else:
            embed.description = "\n\n".join(_format_log_line(entry) for entry in entries)
        embed.set_footer(text="Catches have a 10% chance of being stolen by Neel")
        await ctx.send(embed=embed)

    @neel.command(name="sell")
    async def neel_sell(self, ctx, *, pokemon_name: str = None):
        if not pokemon_name:
            await ctx.send(embed=discord.Embed(description="**Usage:** `.neel sell <Pokémon>`\n**Example:** `.neel sell Rayquaza`", color=0xED4245))
            return
        if db is None:
            await ctx.send(embed=discord.Embed(description="❌ MongoDB is not configured.", color=0xED4245))
            return

        create_account(ctx.author.id)
        uid = str(ctx.author.id)
        requested = pokemon_name.strip()
        requested_key = _normalize_name(requested)

        # Current Pokémon storage keeps a user's collection in one document:
        # {_id: user_id, inventory: ["electrike", ...]}. Older Neel code expected
        # one document per Pokémon ({user_id, name}), so support both schemas.
        poke_doc = db.pokemon_collection.find_one({"user_id": uid, "name": requested.lower()})
        storage = "legacy"
        actual_name = requested.lower()

        if not poke_doc:
            user_doc = get_pokemon_data(ctx.author.id)
            inventory = [str(x) for x in user_doc.get("inventory", [])]
            for item in inventory:
                if _normalize_name(item) == requested_key:
                    actual_name = item
                    poke_doc = user_doc
                    storage = "inventory"
                    break

        if not poke_doc:
            await ctx.send(embed=discord.Embed(description=f"❌ You don't own a **{pokemon_name.title()}**.", color=0xED4245))
            return

        if storage == "legacy":
            display = poke_doc.get("display", actual_name.title())
            rarity = get_sale_rarity(poke_doc.get("pokedex_id"))
        else:
            display = actual_name.replace("-", " ").title()
            rarity = "common"

        low, high = SELL_PRICE_RANGES[rarity]
        price = random.randint(low, high)
        flavor = random.choice(SELL_FLAVOR_TEXT)

        if storage == "legacy":
            db.pokemon_collection.delete_one({"_id": poke_doc["_id"]})
            db.pokemon_teams.update_one({"user_id": ctx.author.id}, {"$pull": {"team": actual_name}})
        else:
            db.pokemon_collection.update_one(
                {"_id": ctx.author.id},
                {"$pull": {"inventory": actual_name}, "$inc": {"caught_count": -1}},
            )
            db.pokemon_collection.update_one(
                {"_id": ctx.author.id},
                {"$pull": {"team": actual_name}},
            )

        add_cash(ctx.author.id, price)
        log_neel_event("sale", seller_id=uid, pokemon_display=display, rarity=rarity, price=price)
        embed = discord.Embed(title="💰 DEAL COMPLETE", color=RARITY_COLORS[rarity])
        embed.add_field(name="Pokémon", value=f"**{display}**", inline=True)
        embed.add_field(name="Rarity", value=RARITY_LABELS[rarity], inline=True)
        embed.add_field(name="Price", value=f"**{price:,} NGR**", inline=False)
        embed.description = f"*\"{flavor}\"*"
        embed.set_footer(text="Your balance has been updated.")
        await ctx.send(embed=embed)


def _format_log_line(entry: dict) -> str:
    if entry.get("type") == "steal":
        return f"🥷 Stole **{entry.get('pokemon_display', 'a Pokémon')}** from <@{entry.get('user_id')}>"
    price = entry.get("price", 0)
    return f"💰 Bought **{entry.get('pokemon_display', 'a Pokémon')}** from <@{entry.get('seller_id')}>\nPaid: **{price:,} NGR**"


async def setup(bot):
    await bot.add_cog(Neel(bot))
