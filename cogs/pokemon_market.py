from discord.ext import commands
import discord
import re
import datetime

from utils.economy import get_cash, add_cash, remove_cash, format_cash, parse_amount
from utils.pokemon_db import db, get_pokemon_data, owns_pokemon

MARKET_MIN_PRICE = 25_000
MARKET_FEE_PCT = 0.05


def normalize_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


class PokemonMarket(commands.Cog):
    """Simple Pokémon marketplace with one-of-each-species ownership."""

    def __init__(self, bot):
        self.bot = bot

    def _inventory(self, user_id: int) -> list[str]:
        if db is None:
            return []
        return get_pokemon_data(user_id).get("inventory", [])

    def _has_pokemon(self, user_id: int, name: str) -> bool:
        return owns_pokemon(user_id, name)

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
            lines.append(f"**{item.get('display', item.get('name', 'Unknown')).title()}** — {format_cash(item.get('price', 0))} — {seller_name}")
        embed = discord.Embed(title="🏪 Pokémon Market", description="\n".join(lines), color=0x5865F2)
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
        description = "\n".join(f"**{item.get('display', item.get('name', 'Unknown')).title()}** — {format_cash(item.get('price', 0))}" for item in listings)
        await ctx.send(embed=discord.Embed(title=f"🏪 {target.display_name}'s Listings", description=description, color=0x5865F2))

    @commands.command(name="pokemon")
    async def pokemon(self, ctx, action: str = None, *, args: str = None):
        if db is None:
            await ctx.send("❌ MongoDB is not configured.")
            return
        if action is None:
            await ctx.send(embed=discord.Embed(title="🎮 Pokémon Market", description="`.pokemon sell <name> <price>` — list a Pokémon for sale\n`.pokemon buy @seller <name>` — buy a listed Pokémon\n`.pokemart` — browse the market", color=0x5865F2))
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
            name = normalize_name(name_raw.strip())
            price = parse_amount(price_raw)
            if price is None or price < MARKET_MIN_PRICE:
                await ctx.send(f"❌ Minimum listing price is **{format_cash(MARKET_MIN_PRICE)}**.")
                return
            inventory = self._inventory(ctx.author.id)
            owned_name = next((str(x) for x in inventory if normalize_name(x) == name), None)
            if owned_name is None:
                await ctx.send(f"❌ You don't own **{name_raw.title()}**.")
                return
            existing = db.pokemon_market.find_one({"seller_id": str(ctx.author.id), "name_key": name})
            if existing:
                await ctx.send("❌ You already have this Pokémon listed.")
                return
            db.pokemon_market.insert_one({
                "seller_id": str(ctx.author.id),
                "name": owned_name,
                "name_key": name,
                "display": owned_name.replace("-", " ").title(),
                "pokedex_id": 0,
                "price": int(price),
                "listed_at": datetime.datetime.utcnow(),
            })
            await ctx.send(f"✅ Listed **{owned_name.replace('-', ' ').title()}** for **{format_cash(price)}**.")
            return

        if action == "buy":
            if not ctx.message.mentions:
                await ctx.send("❌ Usage: `.pokemon buy @seller <name>`")
                return
            seller = ctx.message.mentions[0]
            name_raw = re.sub(r"<@!?\d+>", "", args).strip()
            name = normalize_name(name_raw)
            if not name:
                await ctx.send("❌ Usage: `.pokemon buy @seller <name>`")
                return
            if seller.id == ctx.author.id:
                await ctx.send("❌ You can't buy your own Pokémon.")
                return

            # One species per player: buying a Pokémon already in the collection
            # is rejected before any cash is removed.
            if self._has_pokemon(ctx.author.id, name):
                await ctx.send(f"❌ You already own **{name_raw.title()}**. You can only own one of each Pokémon.")
                return

            listing = db.pokemon_market.find_one({"seller_id": str(seller.id), "$or": [{"name_key": name}, {"name": name_raw.lower()}]})
            if not listing:
                await ctx.send(f"❌ **{seller.display_name}** doesn't have **{name_raw.title()}** listed.")
                return
            price = int(listing.get("price", 0))
            if get_cash(ctx.author.id) < price:
                await ctx.send(f"❌ You need **{format_cash(price - get_cash(ctx.author.id))}** more.")
                return

            seller_inventory = self._inventory(seller.id)
            seller_name = next((str(x) for x in seller_inventory if normalize_name(x) == name), None)
            if seller_name is None:
                db.pokemon_market.delete_one({"_id": listing["_id"]})
                await ctx.send("❌ That listing is no longer valid because the seller no longer owns the Pokémon.")
                return

            # Re-check ownership immediately before charging the buyer.
            if self._has_pokemon(ctx.author.id, name):
                await ctx.send(f"❌ You already own **{name_raw.title()}**. You can only own one of each Pokémon.")
                return

            remove_cash(ctx.author.id, price)
            add_cash(seller.id, int(price * (1 - MARKET_FEE_PCT)))
            db.pokemon_collection.update_one(
                {"_id": seller.id},
                {"$pull": {"inventory": seller_name}, "$inc": {"caught_count": -1}},
            )
            db.pokemon_collection.update_one(
                {"_id": ctx.author.id},
                {"$addToSet": {"inventory": seller_name}, "$inc": {"caught_count": 1}},
                upsert=True,
            )
            db.pokemon_market.delete_one({"_id": listing["_id"]})
            await ctx.send(f"🎉 You bought **{listing.get('display', seller_name.replace('-', ' ').title())}** for **{format_cash(price)}**!")
            return

        await ctx.send("❌ Unknown action. Use `sell` or `buy`.")


async def setup(bot):
    await bot.add_cog(PokemonMarket(bot))
