from discord.ext import commands
import discord
import random

from utils.game_state import crack_games

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
        "crack"
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

    number = random.randint(
        1,
        100
    )

    crack_games[
        self.ctx.channel.id
    ] = {

        "player1": self.ctx.author,
        "player2": self.opponent,

        "amount": self.amount,

        "score1": 0,
        "score2": 0,

        "wins_required": wins_required,

        "number": number,

        "turn": self.ctx.author
    }

    embed = discord.Embed(
        description=(

            f"🎯 Crack Started\n\n"

            f"{self.ctx.author.mention} ⚔️ "
            f"{self.opponent.mention}\n\n"

            f"💵 Pot: "
            f"{format_cash(self.amount * 2)}\n\n"

            f"🏆 First to "
            f"**{wins_required}** wins\n\n"

            f"🎲 Hidden Number: "
            f"`1 - 100`\n\n"

            f"Use `.guess number`"

        ),
        color=0x5865F2
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
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
        description=(
            "❌ Challenge declined."
        ),
        color=0xED4245
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )

─────────────────────────

COG

─────────────────────────

class Crack(commands.Cog):

def __init__(self, bot):

    self.bot = bot

# ─────────────────────────
# START GAME
# ─────────────────────────

@commands.command(name="crack")
async def crack(
    self,
    ctx,
    opponent: discord.Member = None,
    bo: int = None,
    amount: int = None
):

    if (
        opponent is None
        or bo is None
        or amount is None
    ):

        return await ctx.send(
            "Use: `.crack @user 1/3/5 amount`"
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

    if ctx.channel.id in crack_games:

        return await ctx.send(
            "A crack game is already active."
        )

    embed = discord.Embed(
        description=(

            f"🎯 Crack Challenge\n\n"

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
# GUESS
# ─────────────────────────

@commands.command(name="guess")
async def guess(
    self,
    ctx,
    number: int = None
):

    if number is None:

        return await ctx.send(
            "Use: `.guess number`"
        )

    if ctx.channel.id not in crack_games:

        return await ctx.send(
            "No active crack game."
        )

    game = crack_games[
        ctx.channel.id
    ]

    if ctx.author != game["turn"]:

        return await ctx.send(
            "It's not your turn."
        )

    if number < 1 or number > 100:

        return await ctx.send(
            "Guess between 1-100."
        )

    target = game["number"]

    # CORRECT

    if number == target:

        if ctx.author == game["player1"]:

            game["score1"] += 1

        else:

            game["score2"] += 1

        embed = discord.Embed(
            description=(

                f"🏆 {ctx.author.mention} "
                f"guessed correctly\n\n"

                f"🎯 Number was "
                f"`{target}`"

            ),
            color=0x57F287
        )

        await ctx.send(
            embed=embed
        )

        # MATCH END

        if (
            game["score1"]
            == game["wins_required"]
            or
            game["score2"]
            == game["wins_required"]
        ):

            await self.end_match(
                ctx.channel.id
            )

            return

        # NEXT ROUND

        game["number"] = random.randint(
            1,
            100
        )

        game["turn"] = ctx.author

        next_embed = discord.Embed(
            description=(

                f"🎯 Next Round\n\n"

                f"{ctx.author.mention} "
                f"starts"

            ),
            color=0x5865F2
        )

        await ctx.send(
            embed=next_embed
        )

        return

    # WRONG

    if number < target:

        hint = "⬆️ Higher"

    else:

        hint = "⬇️ Lower"

    next_turn = (

        game["player1"]

        if ctx.author
        == game["player2"]

        else game["player2"]

    )

    game["turn"] = next_turn

    embed = discord.Embed(
        description=(

            f"❌ Wrong Guess\n\n"

            f"{hint}\n\n"

            f"🎯 {next_turn.mention}'s turn"

        ),
        color=0xED4245
    )

    await ctx.send(
        embed=embed
    )

# ─────────────────────────
# END MATCH
# ─────────────────────────

async def end_match(
    self,
    channel_id
):

    game = crack_games[
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
        "crack",
        "win",
        payout,
        loser.id
    )

    add_history(
        loser.id,
        "crack",
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

    del crack_games[
        channel_id
    ]

async def setup(bot):

await bot.add_cog(
    Crack(bot)
)
