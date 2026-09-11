from discord.ext import commands
import discord
import re
import datetime

from utils.economy import get_cash, add_cash, remove_cash, format_cash, parse_amount
from utils.pokemon_db import db, get_pokemon_data

MARKET_MIN_PRICE = 25_000
MARKET_FEE_PCT = 0.05


class PokemonMarket(commands.Cog):
    """Simple Pokémon marketplace. Team/battle/moves systems are intentionally removed."""

    def __init__(self, bot):
        self.bot = bot

    def _inventory(self, user_id: int) -> list[str]:
        if db is None:
            return []
        return get_pokemon_data(user_id).get("inventory", [])

    @commands.command(name="pokemart")
    async def pokemart(self, ctx):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        listings = list(db.pokemon_market.find().sort("listed_at", -1).limit(25))
        if not listings:
            await ctx.send("🏪 The Pokémon market is empty right now.")
            return
        lines = []
        for item in listings:
            seller_id = item.get("seller_id")
            seller = self.bot.get_user(int(seller_id)) if seller_id else None
            seller_name = seller.display_name if seller else f"User {str(seller_id)[-4:] if seller_id else '????'}"
            lines.append(
                f"**{item.get('display', item.get('name', 'Unknown')).title()}** — "
                f"{format_cash(item.get('price', 0))} — {seller_name}"
            )
        embed = discord.Embed(
            title="🏪 Pokémon Market",
            description="\n".join(lines),
            color=0x5865F2,
        )
        embed.set_footer(text="Use .pokemon buy @seller <pokemon> to buy")
        await ctx.send(embed=embed)

    @commands.command(name="pokecheck")
    async def pokecheck(self, ctx, member: discord.Member = None):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        target = member or ctx.author
        listings = list(db.pokemon_market.find({"seller_id": str(target.id)}).sort("listed_at", -1))
        if not listings:
            await ctx.send(f"🏪 **{target.display_name}** has no Pokémon listed for sale.")
            return
        description = "\n".join(
            f"**{item.get('display', item.get('name', 'Unknown')).title()}** — {format_cash(item.get('price', 0))}"
            for item in listings
        )
        await ctx.send(embed=discord.Embed(
            title=f"🏪 {target.display_name}'s Listings",
            description=description,
            color=0x5865F2,
        ))

    @commands.command(name="pokemon")
    async def pokemon(self, ctx, action: str = None, *, args: str = None):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        if action is None:
            await ctx.send(embed=discord.Embed(
                title="🎮 Pokémon Market",
                description=(
                    "`.pokemon sell <name> <price>` — list a Pokémon for sale\n"
                    "`.pokemon buy @seller <name>` — buy a listed Pokémon\n"
                    "`.pokemart` — browse the market"
                ),
                color=0x5865F2,
            ))
            return

        action = action.lower()
        if not args:
            await ctx.send("❌ Use `.pokemon sell <name> <price>` or `.pokemon buy @seller <name>`.")
            return

        if action == "sell":
            parts = args.rsplit(" ", 1)
            if len(parts) != 2:
                await ctx.send("❌ Usage: `.pokemon sell <name> <price>`")
                return
            name_raw, price_raw = parts
            name = name_raw.strip().lower()
            price = parse_amount(price_raw)
            if price is None or price < MARKET_MIN_PRICE:
                await ctx.send(f"❌ Minimum listing price is **{format_cash(MARKET_MIN_PRICE)}**.")
                return
            inventory = [str(x).lower() for x in self._inventory(ctx.author.id)]
            if name not in inventory:
                await ctx.send(f"❌ You don't own **{name_raw.title()}**.")
                return
            existing = db.pokemon_market.find_one({"seller_id": str(ctx.author.id), "name": name})
            if existing:
                await ctx.send("❌ You already have this Pokémon listed.")
                return
            db.pokemon_market.insert_one({
                "seller_id": str(ctx.author.id),
                "name": name,
                "display": name_raw.title(),
                "pokedex_id": 0,
                "price": int(price),
                "listed_at": datetime.datetime.utcnow(),
            })
            await ctx.send(f"✅ Listed **{name_raw.title()}** for **{format_cash(price)}**.")
            return

        if action == "buy":
            if not ctx.message.mentions:
                await ctx.send("❌ Usage: `.pokemon buy @seller <name>`")
                return
            seller = ctx.message.mentions[0]
            name_raw = re.sub(r"<@!?\d+>", "", args).strip()
            name = name_raw.lower()
            if not name:
                await ctx.send("❌ Usage: `.pokemon buy @seller <name>`")
                return
            if seller.id == ctx.author.id:
                await ctx.send("❌ You can't buy your own Pokémon.")
                return
            listing = db.pokemon_market.find_one({"seller_id": str(seller.id), "name": name})
            if not listing:
                await ctx.send(f"❌ **{seller.display_name}** doesn't have **{name_raw.title()}** listed.")
                return
            price = int(listing.get("price", 0))
            if get_cash(ctx.author.id) < price:
                await ctx.send(f"❌ You need **{format_cash(price - get_cash(ctx.author.id))}** more.")
                return
            buyer_inventory = [str(x).lower() for x in self._inventory(ctx.author.id)]
            if name in buyer_inventory:
                await ctx.send("❌ You already own this Pokémon.")
                return
            seller_inventory = self._inventory(seller.id)
            if name not in [str(x).lower() for x in seller_inventory]:
                db.pokemon_market.delete_one({"_id": listing["_id"]})
                await ctx.send("❌ That listing is no longer valid because the seller no longer owns the Pokémon.")
                return
            remove_cash(ctx.author.id, price)
            add_cash(seller.id, int(price * (1 - MARKET_FEE_PCT)))
            db.pokemon_collection.update_one(
                {"_id": seller.id},
                {"$pull": {"inventory": listing["name"]}},
            )
            db.pokemon_collection.update_one(
                {"_id": ctx.author.id},
                {"$push": {"inventory": listing["name"]}},
                upsert=True,
            )
            db.pokemon_market.delete_one({"_id": listing["_id"]})
            await ctx.send(f"🎉 You bought **{listing.get('display', name.title())}** for **{format_cash(price)}**!")
            return

        await ctx.send("❌ Unknown action. Use `sell` or `buy`.")


async def setup(bot):
    await bot.add_cog(PokemonMarket(bot))
