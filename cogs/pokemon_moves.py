from discord.ext import commands
import discord
import aiohttp

# ─────────────────────────────────────────────────────────────────
# MONGODB IMPORT
# ─────────────────────────────────────────────────────────────────
from utils.pokemon_db import db

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

# ─────────────────────────────────────────────────────────────────
# FETCH & VALIDATE A MOVE FROM POKEAPI
# ─────────────────────────────────────────────────────────────────

async def fetch_move(move_name: str) -> dict | None:
    """
    Returns move dict {name, display, power, type, category} or None.
    Accepts human-readable names like 'Stealth Rock' or 'stealth-rock'.
    """
    slug = move_name.strip().lower().replace(" ", "-")
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/move/{slug}") as r:
            if r.status != 200:
                return None
            data = await r.json()
    return {
        "name":     data["name"],
        "display":  data["name"].replace("-", " ").title(),
        "power":    data.get("power") or 0,
        "type":     data["type"]["name"],
        "category": data["damage_class"]["name"],
    }

async def validate_learnset(pokemon_name: str, move_name: str) -> bool:
    """Check if the Pokémon can learn this move via PokéAPI."""
    slug = pokemon_name.lower().replace(" ", "-")
    async with aiohttp.ClientSession() as s:
        async with s.get(f"https://pokeapi.co/api/v2/pokemon/{slug}") as r:
            if r.status != 200:
                return False
            data = await r.json()
    learnable = {m["move"]["name"] for m in data["moves"]}
    move_slug = move_name.strip().lower().replace(" ", "-")
    return move_slug in learnable

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class PokemonMoves(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="moves")
    async def moves(self, ctx, pokemon_name: str = None, *, move_args: str = None):
        """
        .moves <pokemon> <move1>, <move2>, <move3>, <move4>

        Teach up to 4 moves to a Pokémon you own.
        Moves are validated against PokéAPI learnset.

        Example:
          .moves Excadrill Stealth Rock, Earthquake, Rapid Spin, Rock Tomb
        """
        uid = str(ctx.author.id)

        # ── Usage check ──────────────────────────────────────────
        if pokemon_name is None or move_args is None:
            await ctx.send(embed=discord.Embed(
                title="📖 How to teach moves",
                description=(
                    "`.moves <Pokémon> <move1>, <move2>, <move3>, <move4>`\n\n"
                    "**Example:**\n"
                    "`.moves Excadrill Stealth Rock, Earthquake, Rapid Spin, Rock Tomb`\n\n"
                    "You can teach 1–4 moves. They must be in that Pokémon's learnset."
                ),
                color=0x5865F2,
            ))
            return

        # ── Ownership check ──────────────────────────────────────
        pname = pokemon_name.strip().lower()
        
        # Check MongoDB to see if they own the Pokemon
        poke_doc = db.pokemon_collection.find_one({"user_id": uid, "name": pname})

        if not poke_doc:
            await ctx.send(embed=discord.Embed(
                description=f"❌ You don't own a **{pokemon_name.title()}**! Catch one first.",
                color=0xED4245,
            ))
            return

        poke_display = poke_doc.get("display", pname.title())

        # ── Parse moves ──────────────────────────────────────────
        raw_moves = [m.strip() for m in move_args.split(",") if m.strip()]
        if len(raw_moves) < 1 or len(raw_moves) > 4:
            await ctx.send(embed=discord.Embed(
                description="❌ Teach between 1 and 4 moves separated by commas.",
                color=0xED4245,
            ))
            return

        # Loading message while we hit the API
        loading = await ctx.send(embed=discord.Embed(
            description=f"⏳ Checking learnset for **{poke_display}**...",
            color=0x5865F2,
        ))

        # ── Validate each move ───────────────────────────────────
        taught    = []
        failed    = []
        cant_learn = []

        for raw in raw_moves:
            move_data = await fetch_move(raw)
            if move_data is None:
                failed.append(raw.title())
                continue
            can = await validate_learnset(pname, move_data["name"])
            if not can:
                cant_learn.append(move_data["display"])
                continue
            taught.append(move_data)

        if not taught:
            lines = []
            if failed:
                lines.append(f"❌ Moves not found: {', '.join(failed)}")
            if cant_learn:
                lines.append(f"🚫 **{poke_display}** can't learn: {', '.join(cant_learn)}")
            await loading.edit(embed=discord.Embed(
                description="\n".join(lines),
                color=0xED4245,
            ))
            return

        # No need to pad with None in MongoDB, we just save the list of slugs
        move_slugs = [m["name"] for m in taught]

        # Update the moves array in MongoDB
        db.pokemon_collection.update_one(
            {"user_id": uid, "name": pname},
            {"$set": {"moves": move_slugs}}
        )

        # ── Success embed ────────────────────────────────────────
        embed = discord.Embed(
            title=f"✅ Moves taught to {poke_display}!",
            color=0x57F287,
        )
        embed.set_image(url=gif_url(pname))

        move_lines = []
        for i, m in enumerate(taught, 1):
            power_txt = f"⚡ {m['power']}" if m["power"] else "— (status)"
            move_lines.append(
                f"`{i}.` **{m['display']}** •  {m['type'].title()}  •  {power_txt}"
            )
        embed.add_field(name="📋 Moveset", value="\n".join(move_lines), inline=False)

        if failed or cant_learn:
            warn = []
            if failed:
                warn.append(f"❌ Not found: {', '.join(failed)}")
            if cant_learn:
                warn.append(f"🚫 Can't learn: {', '.join(cant_learn)}")
            embed.add_field(name="⚠️ Warnings", value="\n".join(warn), inline=False)

        embed.set_footer(text=f"Use .team to add {poke_display} to your team, then .battle!")
        await loading.edit(embed=embed)

    # ── .moveset <pokemon>  — view current moves ─────────────────

    @commands.command(name="moveset", aliases=["ms"])
    async def moveset(self, ctx, pokemon_name: str = None, member: discord.Member = None):
        """View the current moveset of a Pokémon you own."""
        if pokemon_name is None:
            await ctx.send(embed=discord.Embed(
                description="Usage: `.moveset <Pokémon>` or `.moveset <Pokémon> @user`",
                color=0xED4245,
            ))
            return

        target = member or ctx.author
        pname  = pokemon_name.strip().lower()

        # Fetch the Pokémon document from MongoDB
        poke_doc = db.pokemon_collection.find_one({"user_id": str(target.id), "name": pname})

        if not poke_doc:
            await ctx.send(embed=discord.Embed(
                description=f"**{target.display_name}** doesn't own a **{pokemon_name.title()}**.",
                color=0xED4245,
            ))
            return

        # Fetch the moves array, defaulting to an empty list if none exist
        moves = poke_doc.get("moves", [])
        display = poke_doc.get("display", pname.title())

        embed = discord.Embed(
            title=f"📋 {display}'s Moveset",
            color=0x5865F2,
        )
        embed.set_thumbnail(url=gif_url(pname))

        if not moves:
            embed.description = "No moves taught yet!\nUse `.moves` to teach some."
        else:
            embed.description = "\n".join(
                f"`{i+1}.` **{m.replace('-',' ').title()}**"
                for i, m in enumerate(moves)
            )

        embed.set_footer(text=f"Owned by {target.display_name}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PokemonMoves(bot))
    
