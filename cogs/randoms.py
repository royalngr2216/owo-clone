from discord.ext import commands
import discord
import random

from data.pokemon import POKEMON_LIST

from utils.game_state import (
randoms_games
)

from utils.wagers import (
create_wager,
complete_wager
)

from utils.economy import (
format_cash,
add_history
)

from utils.stats import (
record_win,
record_loss
)

─────────────────────────

ACCEPT VIEW

─────────────────────────

class AcceptView(discord.ui.View):

def __init__(
    self,
    cog,
    ctx,
    opponent,
    bo,
    amount
):

    super().__init__(timeout=30)

    self.cog = cog
    self.ctx = ctx
    self.opponent = opponent
    self.bo = bo
    self.amount = amount

@discord.ui.button(
    label="Accept",
    style=discord.ButtonStyle.success
)
async def accept(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if interaction.user != self.opponent:

        return await interaction.response.send_message(
            "This challenge is not for you.",
            ephemeral=True
        )

    success, message = create_wager(
        self.ctx.author.id,
        self.opponent.id,
        self.amount,
        "randoms"
    )

    if not success:

        embed = discord.Embed(
            description=f"❌ {message}",
            color=0xED4245
        )

        return await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    wins_required = (
        self.bo // 2
    ) + 1

    randoms_games[
        self.ctx.channel.id
    ] = {

        "player1": self.ctx.author,
        "player2": self.opponent,

        "amount": self.amount,

        "score1": 0,
        "score2": 0,

        "wins_required": wins_required,

        "picks": {}
    }

    embed = discord.Embed(
        description=(

            f"🐉 Randoms Started\n\n"

            f"{self.ctx.author.mention} ⚔️ "
            f"{self.opponent.mention}\n\n"

            f"🏆 First to "
            f"**{wins_required}** wins\n\n"

            f"💵 Pot: "
            f"{format_cash(self.amount * 2)}"

        ),
        color=0x5865F2
    )

    view = PickView(
        self.cog,
        self.ctx.channel.id
    )

    await interaction.response.edit_message(
        embed=embed,
        view=view
    )

@discord.ui.button(
    label="Decline",
    style=discord.ButtonStyle.danger
)
async def decline(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if interaction.user != self.opponent:

        return await interaction.response.send_message(
            "This challenge is not for you.",
            ephemeral=True
        )

    embed = discord.Embed(
        description="❌ Challenge declined.",
        color=0xED4245
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )

─────────────────────────

PICK VIEW

─────────────────────────

class PickView(discord.ui.View):

def __init__(
    self,
    cog,
    channel_id
):

    super().__init__(timeout=None)

    self.cog = cog
    self.channel_id = channel_id

@discord.ui.button(
    label="Pick Pokémon",
    style=discord.ButtonStyle.primary,
    emoji="🎴"
)
async def pick(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if self.channel_id not in randoms_games:

        return await interaction.response.send_message(
            "No active game.",
            ephemeral=True
        )

    game = randoms_games[
        self.channel_id
    ]

    if interaction.user not in [

        game["player1"],
        game["player2"]

    ]:

        return await interaction.response.send_message(
            "You are not in this match.",
            ephemeral=True
        )

    if interaction.user in game["picks"]:

        return await interaction.response.send_message(
            "You already picked.",
            ephemeral=True
        )

    pokemon = random.choice(
        POKEMON_LIST
    )

    game["picks"][
        interaction.user
    ] = pokemon

    clean_name = (

        pokemon.name.lower()
        .replace(" ", "")
        .replace(".", "")
        .replace("'", "")

    )

    gif_url = (
        "https://play.pokemonshowdown.com/"
        f"sprites/xyani/{clean_name}.gif"
    )

    embed = discord.Embed(
        description=(

            f"🎴 {interaction.user.mention} picked\n\n"

            f"# {pokemon.name}\n\n"

            f"💥 Total Power: "
            f"**{pokemon.total_stats}**"

        ),
        color=0x5865F2
    )

    embed.set_image(
        url=gif_url
    )

    await interaction.response.send_message(
        embed=embed
    )

    # BOTH PICKED

    if len(game["picks"]) == 2:

        await self.cog.resolve_round(
            self.channel_id
        )

─────────────────────────

COG

─────────────────────────

class Randoms(commands.Cog):

def __init__(self, bot):

    self.bot = bot

@commands.command(name="randoms")
async def randoms(
    self,
    ctx,
    opponent: discord.Member = None,
    bo: int = None,
    amount: int = None
):

    # VALIDATION

    if (
        opponent is None
        or bo is None
        or amount is None
    ):

        return await ctx.send(
            "Use: `.randoms @user 1/3/5 amount`"
        )

    if opponent.bot:

        return await ctx.send(
            "You cannot challenge bots."
        )

    if opponent == ctx.author:

        return await ctx.send(
            "You cannot challenge yourself."
        )

    if bo not in [1, 3, 5]:

        return await ctx.send(
            "Choose 1, 3 or 5."
        )

    if amount < 10_000:

        return await ctx.send(
            "Minimum wager is $10,000."
        )

    if ctx.channel.id in randoms_games:

        return await ctx.send(
            "A randoms game is already active."
        )

    # CHALLENGE

    embed = discord.Embed(
        description=(

            f"🐉 Randoms Challenge\n\n"

            f"{ctx.author.mention} challenged "
            f"{opponent.mention}\n\n"

            f"🏆 BO{bo}\n"
            f"💵 Wager: "
            f"{format_cash(amount)}"

        ),
        color=0x2B2D31
    )

    view = AcceptView(
        self,
        ctx,
        opponent,
        bo,
        amount
    )

    await ctx.send(
        embed=embed,
        view=view
    )

# ─────────────────────────
# RESOLVE ROUND
# ─────────────────────────

async def resolve_round(
    self,
    channel_id
):

    game = randoms_games[
        channel_id
    ]

    p1 = game["player1"]
    p2 = game["player2"]

    poke1 = game["picks"][p1]
    poke2 = game["picks"][p2]

    channel = self.bot.get_channel(
        channel_id
    )

    # WINNER

    if poke1.total_stats > poke2.total_stats:

        winner = p1
        loser = p2

        game["score1"] += 1

    elif poke2.total_stats > poke1.total_stats:

        winner = p2
        loser = p1

        game["score2"] += 1

    else:

        winner = None

    # RESULT

    if winner:

        embed = discord.Embed(
            description=(

                f"🏆 {winner.mention} "
                f"wins the round\n\n"

                f"📊 Score\n"
                f"`{game['score1']} - "
                f"{game['score2']}`"

            ),
            color=0x57F287
        )

    else:

        embed = discord.Embed(
            description=(
                "🤝 Round tied."
            ),
            color=0xFEE75C
        )

    await channel.send(
        embed=embed
    )

    # RESET PICKS

    game["picks"] = {}

    # MATCH END

    if (
        game["score1"]
        == game["wins_required"]
        or
        game["score2"]
        == game["wins_required"]
    ):

        await self.end_match(
            channel_id
        )

        return

    # NEXT ROUND

    next_embed = discord.Embed(
        description=(
            "🎴 Next Round\n\n"
            "Press button to pick."
        ),
        color=0x5865F2
    )

    view = PickView(
        self,
        channel_id
    )

    await channel.send(
        embed=next_embed,
        view=view
    )

# ─────────────────────────
# END MATCH
# ─────────────────────────

async def end_match(
    self,
    channel_id
):

    game = randoms_games[
        channel_id
    ]

    if game["score1"] > game["score2"]:

        winner = game["player1"]
        loser = game["player2"]

    else:

        winner = game["player2"]
        loser = game["player1"]

    payout = complete_wager(
        winner.id,
        loser.id,
        game["amount"]
    )

    # HISTORY

    add_history(
        winner.id,
        "randoms",
        "win",
        payout,
        loser.id
    )

    add_history(
        loser.id,
        "randoms",
        "loss",
        game["amount"],
        winner.id
    )

    # STATS

    record_win(
        winner.id,
        payout
    )

    record_loss(
        loser.id,
        game["amount"]
    )

    embed = discord.Embed(
        description=(

            f"🏆 {winner.mention} "
            f"wins the match\n\n"

            f"💰 Won "
            f"{format_cash(payout)}"

        ),
        color=0x57F287
    )

    channel = self.bot.get_channel(
        channel_id
    )

    await channel.send(
        embed=embed
    )

    del randoms_games[
        channel_id
    ]

async def setup(bot):

await bot.add_cog(
    Randoms(bot)
  )
