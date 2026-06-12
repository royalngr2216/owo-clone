from discord.ext import commands
import discord
import sqlite3
import aiohttp

# ─────────────────────────────────────────────────────────────────
# IMPORTS — uses the same MongoDB economy as the rest of the bot
# ─────────────────────────────────────────────────────────────────
from utils.economy import get_cash, add_cash, remove_cash, format_cash, parse_amount

DB_PATH = "pokemon.db"

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

# ─────────────────────────────────────────────────────────────────
# SHARED HELPERS  (imported by pokemon_battle.py)
# ─────────────────────────────────────────────────────────────────

def get_team(user_id: str) -> list[str]:
    with get_db() as con:
        row = con.execute(
            "SELECT slot1,slot2,slot3,slot4,slot5,slot6 FROM pokemon_teams WHERE user_id=?",
            (user_id,),
        ).fetchone()
    if row is None:
        return []
    return [row[f"slot{i}"] for i in range(1, 7) if row[f"slot{i}"]]

def owns_pokemon(user_id: str, name: str) -> bool:
    with get_db() as con:
        row = con.execute(
            "SELECT id FROM pokemon_collection WHERE user_id=? AND name=? LIMIT 1",
            (user_id, name.lower()),
        ).fetchone()
    return row is not None

def get_pokemon_moves(user_id: str, name: str) -> list[dict]:
    """Return the saved moveset for a specific Pokémon."""
    with get_db() as con:
        row = con.execute(
            "SELECT move1,move2,move3,move4 FROM pokemon_collection "
            "WHERE user_id=? AND name=? LIMIT 1",
            (user_id, name.lower()),
        ).fetchone()
    if row is None:
        return []
    return [row[f"move{i}"] for i in range(1, 5) if row[f"move{i}"]]

async def fetch_pokemon_data(name: str, user_id: str = None) -> dict | None:
    """
    Full Pokémon data from PokéAPI.
    If user_id given, uses their saved moveset (falls back to learnset).
    """
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{name.lower()}") as r:
            if r.status != 200:
                return None
            data = await r.json()

    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    types = [t["type"]["name"] for t in data["types"]]

    saved_moves = get_pokemon_moves(user_id, name) if user_id else []

    if saved_moves:
        moves = []
        async with aiohttp.ClientSession() as s:
            for mslug in saved_moves:
                async with s.get(f"https://pokeapi.co/api/v2/move/{mslug}") as r:
                    if r.status != 200:
                        continue
                    mdata = await r.json()
                    moves.append({
                        "name":     mdata["name"],
                        "display":  mdata["name"].replace("-", " ").title(),
                        "power":    mdata.get("power") or 0,
                        "type":     mdata["type"]["name"],
                        "category": mdata["damage_class"]["name"],
                    })
    else:
        all_moves = [m["move"]["name"] for m in data["moves"]][:20]
        moves = []
        async with aiohttp.ClientSession() as s:
            for mslug in all_moves:
                if len(moves) >= 4:
                    break
                async with s.get(f"https://pokeapi.co/api/v2/move/{mslug}") as r:
                    if r.status != 200:
                        continue
                    mdata = await r.json()
                    if mdata.get("power") and mdata["power"] >= 40:
                        moves.append({
                            "name":     mdata["name"],
                            "display":  mdata["name"].replace("-", " ").title(),
                            "power":    mdata.get("power") or 40,
                            "type":     mdata["type"]["name"],
                            "category": mdata["damage_class"]["name"],
                        })
        while len(moves) < 4:
            moves.append({"name": "tackle", "display": "Tackle",
                          "power": 40, "type": "normal", "category": "physical"})

    sprite = (
        data["sprites"]["other"]["official-artwork"]["front_default"]
        or data["sprites"]["front_default"]
    )

    return {
        "id":      data["id"],
        "name":    data["name"],
        "display": data["name"].title(),
        "stats":   stats,
        "types":   types,
        "moves":   moves,
        "sprite":  sprite,
        "gif":     gif_url(data["name"]),
    }


# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class PokemonTeam(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────────────────────
    # .team — view / set active team
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="team")
    async def team(self, ctx, *, args: str = None):
        uid = str(ctx.author.id)

        # View team
        if args is None:
            slots = get_team(uid)
            if not slots:
                await ctx.send(embed=discord.Embed(
                    title="⚔️ Your Team",
                    description=(
                        "You don't have a team yet!\n\n"
                        "**Set one with:**\n"
                        "`.team Charizard, Blastoise, Snorlax`"
                    ),
                    color=0xED4245,
                ))
                return

            embed = discord.Embed(
                title=f"⚔️ {ctx.author.display_name}'s Team",
                color=0x5865F2,
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            for i, name in enumerate(slots, 1):
                with get_db() as con:
                    row = con.execute(
                        "SELECT move1,move2,move3,move4 FROM pokemon_collection "
                        "WHERE user_id=? AND name=? LIMIT 1",
                        (uid, name),
                    ).fetchone()
                moves_txt = "No moves set"
                if row:
                    m = [row[f"move{j}"].replace("-", " ").title()
                         for j in range(1, 5) if row[f"move{j}"]]
                    if m:
                        moves_txt = " • ".join(m)
                embed.add_field(
                    name=f"`{i}.` {name.title()}",
                    value=f"[🎞]({gif_url(name)})  {moves_txt}",
                    inline=False,
                )
            embed.set_footer(text="Use .battle @user <amount> to fight!")
            await ctx.send(embed=embed)
            return

        # Set team
        names = [n.strip().lower() for n in args.split(",") if n.strip()]
        if not 1 <= len(names) <= 6:
            await ctx.send(embed=discord.Embed(
                description="List 1–6 Pokémon separated by commas.\n`.team Charizard, Blastoise, Snorlax`",
                color=0xED4245,
            ))
            return

        not_owned = [n for n in names if not owns_pokemon(uid, n)]
        if not_owned:
            await ctx.send(embed=discord.Embed(
                description=f"❌ You don't own: **{', '.join(n.title() for n in not_owned)}**",
                color=0xED4245,
            ))
            return

        padded = names + [None] * (6 - len(names))
        with get_db() as con:
            con.execute("""
                INSERT INTO pokemon_teams (user_id,slot1,slot2,slot3,slot4,slot5,slot6)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                    slot1=excluded.slot1, slot2=excluded.slot2,
                    slot3=excluded.slot3, slot4=excluded.slot4,
                    slot5=excluded.slot5, slot6=excluded.slot6
            """, (uid, *padded))

        embed = discord.Embed(
            title="✅ Team Updated!",
            description="\n".join(f"`{i+1}.` {n.title()}" for i, n in enumerate(names)),
            color=0x57F287,
        )
        embed.set_footer(text="Use .battle @user <amount> to challenge someone!")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # .pokemon sell <name> <price>
    # List a Pokémon on the market for other players to buy
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="pokemon")
    async def pokemon_cmd(self, ctx, action: str = None, *, args: str = None):
        """
        .pokemon sell <name> <price>   — list a Pokémon for sale
        .pokemon buy @seller <name>    — buy from the market
        """
        if action is None:
            embed = discord.Embed(
                title="🎮 Pokémon Commands",
                description=(
                    "`.pokemon sell <name> <price>` — list a Pokémon for sale\n"
                    "`.pokemon buy @seller <name>` — buy a Pokémon from the market\n"
                    "`.pokemons` — view your Pokémon collection\n"
                    "`.pokemart` — browse the Pokémon market\n"
                    "`.team` — view / set your battle team"
                ),
                color=0x5865F2,
            )
            await ctx.send(embed=embed)
            return

        action = action.lower()

        # ── SELL ──────────────────────────────────────────────────
        if action == "sell":
            if args is None:
                await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `.pokemon sell <name> <price>`\nExample: `.pokemon sell Excadrill 400k`",
                    color=0xED4245,
                ))
                return

            # Parse: last token is price, everything before is the name
            parts = args.rsplit(" ", 1)
            if len(parts) < 2:
                await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `.pokemon sell <name> <price>`\nExample: `.pokemon sell Excadrill 400k`",
                    color=0xED4245,
                ))
                return

            poke_name_raw, price_raw = parts[0].strip(), parts[1].strip()
            poke_name = poke_name_raw.lower()
            price = parse_amount(price_raw)

            if price is None or price <= 0:
                await ctx.send(embed=discord.Embed(
                    description="❌ Invalid price. Use a number like `400k`, `1m`, or `50000`.",
                    color=0xED4245,
                ))
                return

            uid = str(ctx.author.id)

            # Must own the Pokémon
            if not owns_pokemon(uid, poke_name):
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You don't own a **{poke_name_raw.title()}**!",
                    color=0xED4245,
                ))
                return

            # Can't already have it listed
            with get_db() as con:
                existing = con.execute(
                    "SELECT id FROM pokemon_market WHERE seller_id=? AND name=?",
                    (uid, poke_name),
                ).fetchone()

            if existing:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You already have **{poke_name_raw.title()}** listed in the market!\nRemove the old listing first (contact an admin).",
                    color=0xED4245,
                ))
                return

            # Get display & pokedex_id from collection
            with get_db() as con:
                prow = con.execute(
                    "SELECT display, pokedex_id FROM pokemon_collection WHERE user_id=? AND name=? LIMIT 1",
                    (uid, poke_name),
                ).fetchone()

            if not prow:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Couldn't find **{poke_name_raw.title()}** in your collection.",
                    color=0xED4245,
                ))
                return

            display = prow["display"]
            pokedex_id = prow["pokedex_id"]

            # Add to market
            with get_db() as con:
                con.execute(
                    "INSERT INTO pokemon_market (seller_id, name, display, pokedex_id, price) VALUES (?,?,?,?,?)",
                    (uid, poke_name, display, pokedex_id, price),
                )

            embed = discord.Embed(
                title="🏪 Pokémon Listed!",
                description=(
                    f"**{display}** has been listed in the market!\n\n"
                    f"💰 Price: **{format_cash(price)}**\n"
                    f"🎞 [View GIF]({gif_url(poke_name)})\n\n"
                    f"Players can buy it with:\n"
                    f"`.pokemon buy {ctx.author.mention} {display}`"
                ),
                color=0x57F287,
            )
            embed.set_thumbnail(url=gif_url(poke_name))
            embed.set_footer(text=f"Pokédex #{pokedex_id}")
            await ctx.send(embed=embed)

        # ── BUY ───────────────────────────────────────────────────
        elif action == "buy":
            if args is None or not ctx.message.mentions:
                await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `.pokemon buy @seller <name>`\nExample: `.pokemon buy @Alice Excadrill`",
                    color=0xED4245,
                ))
                return

            seller = ctx.message.mentions[0]

            # Strip the mention from args to get the Pokémon name
            # args may look like "@Alice Excadrill" or "<@123456> Excadrill"
            import re
            poke_name_raw = re.sub(r"<@!?\d+>", "", args).strip()
            if not poke_name_raw:
                await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `.pokemon buy @seller <name>`\nExample: `.pokemon buy @Alice Excadrill`",
                    color=0xED4245,
                ))
                return

            poke_name = poke_name_raw.lower()
            buyer_id = str(ctx.author.id)
            seller_id = str(seller.id)

            if buyer_id == seller_id:
                await ctx.send(embed=discord.Embed(
                    description="❌ You can't buy your own Pokémon!",
                    color=0xED4245,
                ))
                return

            # Look up the listing
            with get_db() as con:
                listing = con.execute(
                    "SELECT * FROM pokemon_market WHERE seller_id=? AND name=?",
                    (seller_id, poke_name),
                ).fetchone()

            if not listing:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ **{seller.display_name}** doesn't have a **{poke_name_raw.title()}** listed for sale!",
                    color=0xED4245,
                ))
                return

            price = listing["price"]
            display = listing["display"]
            pokedex_id = listing["pokedex_id"]

            # Buyer must not already own this species
            if owns_pokemon(buyer_id, poke_name):
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You already own a **{display}**! Each trainer can only have one of each species.",
                    color=0xED4245,
                ))
                return

            # Check buyer has enough cash
            buyer_cash = get_cash(buyer_id)
            if buyer_cash < price:
                await ctx.send(embed=discord.Embed(
                    description=(
                        f"❌ You don't have enough money!\n\n"
                        f"💰 Price: **{format_cash(price)}**\n"
                        f"👛 Your balance: **{format_cash(buyer_cash)}**\n"
                        f"💸 You need: **{format_cash(price - buyer_cash)}** more"
                    ),
                    color=0xED4245,
                ))
                return

            # ── Execute the trade ──────────────────────────────────
            # 1. Deduct from buyer
            remove_cash(buyer_id, price)
            # 2. Pay seller
            add_cash(seller_id, price)
            # 3. Move Pokémon from seller's collection to buyer's
            with get_db() as con:
                # Copy with moves intact
                seller_poke = con.execute(
                    "SELECT move1,move2,move3,move4 FROM pokemon_collection "
                    "WHERE user_id=? AND name=? LIMIT 1",
                    (seller_id, poke_name),
                ).fetchone()

                move1 = seller_poke["move1"] if seller_poke else None
                move2 = seller_poke["move2"] if seller_poke else None
                move3 = seller_poke["move3"] if seller_poke else None
                move4 = seller_poke["move4"] if seller_poke else None

                con.execute(
                    "INSERT INTO pokemon_collection (user_id, name, display, pokedex_id, move1, move2, move3, move4) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (buyer_id, poke_name, display, pokedex_id, move1, move2, move3, move4),
                )
                # Remove from seller's collection
                con.execute(
                    "DELETE FROM pokemon_collection WHERE user_id=? AND name=? LIMIT 1",
                    (seller_id, poke_name),
                )
                # Remove from market
                con.execute(
                    "DELETE FROM pokemon_market WHERE seller_id=? AND name=?",
                    (seller_id, poke_name),
                )
                # Remove from seller's team if it was in there
                team_row = con.execute(
                    "SELECT * FROM pokemon_teams WHERE user_id=?",
                    (seller_id,),
                ).fetchone()
                if team_row:
                    new_slots = []
                    for i in range(1, 7):
                        slot_val = team_row[f"slot{i}"]
                        if slot_val and slot_val.lower() != poke_name:
                            new_slots.append(slot_val)
                    padded = new_slots + [None] * (6 - len(new_slots))
                    con.execute("""
                        INSERT INTO pokemon_teams (user_id,slot1,slot2,slot3,slot4,slot5,slot6)
                        VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            slot1=excluded.slot1, slot2=excluded.slot2,
                            slot3=excluded.slot3, slot4=excluded.slot4,
                            slot5=excluded.slot5, slot6=excluded.slot6
                    """, (seller_id, *padded))

            embed = discord.Embed(
                title=f"✅ Trade Complete! {display} has a new trainer!",
                description=(
                    f"**{ctx.author.display_name}** bought **{display}** from **{seller.display_name}**!\n\n"
                    f"💰 Amount paid: **{format_cash(price)}**\n"
                    f"🎞 [View GIF]({gif_url(poke_name)})\n\n"
                    f"**{display}** has been added to your collection!\n"
                    f"Use `.team` to add it to your battle team."
                ),
                color=0x57F287,
            )
            embed.set_thumbnail(url=gif_url(poke_name))
            embed.set_footer(text=f"Pokédex #{pokedex_id}")
            await ctx.send(embed=embed)

            # DM the seller
            try:
                seller_embed = discord.Embed(
                    title="💰 Your Pokémon was sold!",
                    description=(
                        f"**{display}** was purchased by **{ctx.author.display_name}**!\n\n"
                        f"💰 You received: **{format_cash(price)}**"
                    ),
                    color=0x57F287,
                )
                await seller.send(embed=seller_embed)
            except Exception:
                pass  # DMs might be off

        else:
            await ctx.send(embed=discord.Embed(
                description=f"❌ Unknown action `{action}`.\nUse `.pokemon sell` or `.pokemon buy`.",
                color=0xED4245,
            ))

    # ─────────────────────────────────────────────────────────────
    # .pokemart — browse all Pokémon listed for sale
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="pokemart")
    async def pokemart(self, ctx):
        """Browse all Pokémon currently listed for sale."""
        with get_db() as con:
            listings = con.execute(
                "SELECT * FROM pokemon_market ORDER BY listed_at DESC"
            ).fetchall()

        if not listings:
            await ctx.send(embed=discord.Embed(
                title="🏪 Pokémon Market",
                description=(
                    "The market is empty right now!\n\n"
                    "List your Pokémon with:\n"
                    "`.pokemon sell <name> <price>`"
                ),
                color=0xFFA500,
            ))
            return

        per_page = 4
        pages = [listings[i:i+per_page] for i in range(0, len(listings), per_page)]
        page = 0

        def make_embed(p: int) -> discord.Embed:
            embed = discord.Embed(
                title="🏪 Pokémon Market",
                description=f"**{len(listings)}** Pokémon available for sale!\nBuy with: `.pokemon buy @seller <name>`",
                color=0xF1C40F,
            )
            for listing in pages[p]:
                seller_id = listing["seller_id"]
                seller = ctx.guild.get_member(int(seller_id))
                seller_name = seller.display_name if seller else f"<@{seller_id}>"

                embed.add_field(
                    name=f"🎴 {listing['display']} — {format_cash(listing['price'])}",
                    value=(
                        f"[🎞 View GIF]({gif_url(listing['name'])})\n"
                        f"📦 Seller: **{seller_name}**\n"
                        f"🏷️ Buy: `.pokemon buy @{seller_name} {listing['display']}`\n"
                        f"📖 Pokédex #{listing['pokedex_id']:03}"
                    ),
                    inline=False,
                )
            embed.set_footer(text=f"Page {p+1}/{len(pages)}  •  Use reactions to browse")
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

        import asyncio
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

    # ─────────────────────────────────────────────────────────────
    # .pokecheck @user — view someone's listed Pokémon in market
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="pokecheck")
    async def pokecheck(self, ctx, member: discord.Member = None):
        """See what a specific trainer has listed in the market."""
        target = member or ctx.author
        with get_db() as con:
            listings = con.execute(
                "SELECT * FROM pokemon_market WHERE seller_id=? ORDER BY listed_at DESC",
                (str(target.id),),
            ).fetchall()

        if not listings:
            await ctx.send(embed=discord.Embed(
                description=f"**{target.display_name}** has no Pokémon listed for sale.",
                color=0xED4245,
            ))
            return

        embed = discord.Embed(
            title=f"🏪 {target.display_name}'s Listings",
            color=0xF1C40F,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        for listing in listings:
            embed.add_field(
                name=f"🎴 {listing['display']} — {format_cash(listing['price'])}",
                value=(
                    f"[🎞 View GIF]({gif_url(listing['name'])})\n"
                    f"📖 Pokédex #{listing['pokedex_id']:03}\n"
                    f"Buy: `.pokemon buy {target.mention} {listing['display']}`"
                ),
                inline=True,
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(PokemonTeam(bot))
