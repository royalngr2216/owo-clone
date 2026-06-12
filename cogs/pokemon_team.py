from discord.ext import commands
import discord
import sqlite3
import aiohttp

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

    # Use player's saved moves if available
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
        # Fallback: auto-pick 4 damaging moves from learnset
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


async def setup(bot):
    await bot.add_cog(PokemonTeam(bot))
  
