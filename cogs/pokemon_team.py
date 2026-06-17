from discord.ext import tasks
import datetime

class PokemonTeam(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cleanup_market.start() # Start the background task

    def cog_unload(self):
        self.cleanup_market.cancel() # Stop the task if the cog is reloaded/unloaded

    # ─────────────────────────────────────────────────────────────
    # BACKGROUND TASK: Auto-remove listings older than 2 days
    # ─────────────────────────────────────────────────────────────
    @tasks.loop(hours=1) # Checks every 1 hour
    async def cleanup_market(self):
        """Removes market listings older than 48 hours."""
        if db is None: 
            return
            
        # Calculate the exact time 2 days ago
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        
        # Delete all listings where 'listed_at' is older than the cutoff time
        # Because the seller never lost the Pokémon from their collection when selling,
        # simply deleting the market listing safely cancels the sale.
        result = db.pokemon_market.delete_many({"listed_at": {"$lt": cutoff_time}})
        
        if result.deleted_count > 0:
            print(f"[Market Cleanup] Removed {result.deleted_count} expired listings.")

    cleanup_market.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

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
                doc = db.pokemon_collection.find_one({"user_id": uid, "name": name})
                
                moves_txt = "No moves set"
                if doc and doc.get("moves"):
                    m = [move.replace("-", " ").title() for move in doc["moves"]]
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

        # Update in MongoDB
        db.pokemon_teams.update_one(
            {"user_id": uid},
            {"$set": {"team": names}},
            upsert=True
        )

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

            if not owns_pokemon(uid, poke_name):
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You don't own a **{poke_name_raw.title()}**!",
                    color=0xED4245,
                ))
                return

            existing = db.pokemon_market.find_one({"seller_id": uid, "name": poke_name})

            if existing:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You already have **{poke_name_raw.title()}** listed in the market!\nRemove the old listing first (contact an admin).",
                    color=0xED4245,
                ))
                return

            prow = db.pokemon_collection.find_one({"user_id": uid, "name": poke_name})

            if not prow:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Couldn't find **{poke_name_raw.title()}** in your collection.",
                    color=0xED4245,
                ))
                return

            display = prow.get("display", poke_name.title())
            pokedex_id = prow.get("pokedex_id", 0)

            db.pokemon_market.insert_one({
                "seller_id": uid,
                "name": poke_name,
                "display": display,
                "pokedex_id": pokedex_id,
                "price": price,
                "listed_at": datetime.datetime.utcnow()
            })

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

            listing = db.pokemon_market.find_one({"seller_id": seller_id, "name": poke_name})

            if not listing:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ **{seller.display_name}** doesn't have a **{poke_name_raw.title()}** listed for sale!",
                    color=0xED4245,
                ))
                return

            price = listing["price"]
            display = listing["display"]
            pokedex_id = listing["pokedex_id"]

            if owns_pokemon(buyer_id, poke_name):
                await ctx.send(embed=discord.Embed(
                    description=f"❌ You already own a **{display}**! Each trainer can only have one of each species.",
                    color=0xED4245,
                ))
                return

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
            remove_cash(buyer_id, price)
            add_cash(seller_id, price)
            
            seller_poke = db.pokemon_collection.find_one({"user_id": seller_id, "name": poke_name})
            moves = seller_poke.get("moves", []) if seller_poke else []

            db.pokemon_collection.insert_one({
                "user_id": buyer_id,
                "name": poke_name,
                "display": display,
                "pokedex_id": pokedex_id,
                "moves": moves
            })
            
            db.pokemon_collection.delete_one({"user_id": seller_id, "name": poke_name})
            db.pokemon_market.delete_one({"seller_id": seller_id, "name": poke_name})
            
            seller_team_doc = db.pokemon_teams.find_one({"user_id": seller_id})
            if seller_team_doc:
                current_team = seller_team_doc.get("team", [])
                new_team = [p for p in current_team if p.lower() != poke_name]
                db.pokemon_teams.update_one(
                    {"user_id": seller_id},
                    {"$set": {"team": new_team}}
                )

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
                pass

        else:
            await ctx.send(embed=discord.Embed(
                description=f"❌ Unknown action `{action}`.\nUse `.pokemon sell` or `.pokemon buy`.",
                color=0xED4245,
            ))

    # ─────────────────────────────────────────────────────────────
    # .pokemart — browse all Pokémon listed for sale (REWRITTEN UI)
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="pokemart")
    async def pokemart(self, ctx):
        """Browse all Pokémon currently listed for sale in a visual grid."""
        listings = list(db.pokemon_market.find().sort("listed_at", -1))

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

        # Send a temporary loading message since image generation + fetching can take a moment
        loading_msg = await ctx.send(embed=discord.Embed(
            description="⏳ **Loading the PokéMart... Fetching sprites!**",
            color=0x5865F2
        ))

        # Instantiate View and get first page UI
        view = MarketPaginationView(listings, ctx.guild)
        embed, file = await view.get_current_ui()

        # Delete loading message and send final beautiful interactive UI
        await loading_msg.delete()
        await ctx.send(embed=embed, file=file, view=view)


    # ─────────────────────────────────────────────────────────────
    # .pokecheck @user — view someone's listed Pokémon in market
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="pokecheck")
    async def pokecheck(self, ctx, member: discord.Member = None):
        """See what a specific trainer has listed in the market."""
        target = member or ctx.author
        listings = list(db.pokemon_market.find({"seller_id": str(target.id)}).sort("listed_at", -1))

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
