from discord.ext import commands
import discord
import random

from utils.game_state import deathroll_games

from utils.wagers import (
create_wager,
complete_wager,
refund_wager
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

# ─────────────────────────
# ACCEPT
# ─────────────────────────

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

    # CREATE WAGER

    success, message = create_wager(
        self.ctx.author.id,
        self.opponent.id,
        self.amount,
        "deathroll"
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

    deathroll_games[
        self.ctx.channel.id
    ] = {

        "player1": self.ctx.author,
        "player2": self.opponent,

        "amount": self.amount,

        "score1": 0,
        "score2": 0,

        "wins_required": wins_required,

        "max_number": 1000,

        "turn": self.ctx.author
    }

    embed = discord.Embed(
        description=(

            f"💀 Deathroll Started\n\n"

            f"{self.ctx.author.mention} ⚔️ "
            f"{self.opponent.mention}\n\n"

            f"💵 Pot: "
            f"{format_cash(self.amount * 2)}\n\n"

            f"🏆 First to "
            f"**{wins_required}** wins"

        ),
        color=0x5865F2
    )

    view = RollView(
        self.cog,
        self.ctx.channel.id
    )

    await interaction.response.edit_message(
        embed=embed,
        view=view
    )

# ─────────────────────────
# DECLINE
# ─────────────────────────

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

# ─────────────────────────
# TIMEOUT
# ─────────────────────────

async def on_timeout(self):

    try:

        embed = discord.Embed(
            description=(
                "⌛ Challenge expired."
            ),
            color=0xED4245
        )

        await self.message.edit(
            embed=embed,
            view=None
        )

    except:
        pass

─────────────────────────

ROLL VIEW

─────────────────────────

class RollView(discord.ui.View):

def __init__(
    self,
    cog,
    channel_id
):

    super().__init__(timeout=None)

    self.cog = cog
    self.channel_id = channel_id

@discord.ui.button(
    label="🎲 Roll",
    style=discord.ButtonStyle.danger
)
async def roll(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if self.channel_id not in deathroll_games:

        return await interaction.response.send_message(
            "No active game.",
            ephemeral=True
        )

    game = deathroll_games[
        self.channel_id
    ]

    if interaction.user != game["turn"]:

        return await interaction.response.send_message(
            "It's not your turn.",
            ephemeral=True
        )

    # ─────────────────────────
    # ROLL
    # ─────────────────────────

    roll = random.randint(
        1,
        game["max_number"]
    )

    # ─────────────────────────
    # ROLL 1
    # ─────────────────────────

    if roll == 1:

        if interaction.user == game["player1"]:

            loser = game["player1"]
            winner = game["player2"]

            game["score2"] += 1

        else:

            loser = game["player2"]
            winner = game["player1"]

            game["score1"] += 1

        embed = discord.Embed(
            description=(

                f"💀 {loser.mention} "
                f"rolled **1**\n\n"

                f"🏆 {winner.mention} "
                f"wins the round"

            ),
            color=0xED4245
        )

        await interaction.response.send_message(
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

            await self.cog.end_match(
                self.channel_id
            )

            return

        # NEXT ROUND

        game["max_number"] = 1000
        game["turn"] = winner

        next_embed = discord.Embed(
            description=(

                f"🎯 Next Round\n\n"

                f"{winner.mention}'s turn"

            ),
            color=0x5865F2
        )

        next_view = RollView(
            self.cog,
            self.channel_id
        )

        await interaction.channel.send(
            embed=next_embed,
            view=next_view
        )

        return

    # ─────────────────────────
    # NORMAL ROLL
    # ─────────────────────────

    game["max_number"] = roll

    next_turn = (
        game["player1"]
        if interaction.user
        == game["player2"]
        else game["player2"]
    )

    game["turn"] = next_turn

    embed = discord.Embed(
        description=(

            f"🎲 {interaction.user.mention} "
            f"rolled **{roll}**\n\n"

            f"🎯 {next_turn.mention}'s turn"

        ),
        color=0xFEE75C
    )

    next_view = RollView(
        self.cog,
        self.channel_id
    )

    await interaction.response.send_message(
        embed=embed,
        view=next_view
    )

─────────────────────────

COG

─────────────────────────

class Deathroll(commands.Cog):

def __init__(self, bot):

    self.bot = bot

@commands.command(name="deathroll")
async def deathroll(
    self,
    ctx,
    opponent: discord.Member = None,
    bo: int = None,
    amount: int = None
):

    # ─────────────────────────
    # VALIDATION
    # ─────────────────────────

    if (
        opponent is None
        or bo is None
        or amount is None
    ):

        return await ctx.send(
            "Use: `.deathroll @user 1/3/5 amount`"
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

    if ctx.channel.id in deathroll_games:

        return await ctx.send(
            "A deathroll game is already active."
        )

    # ─────────────────────────
    # CHALLENGE
    # ─────────────────────────

    embed = discord.Embed(
        description=(

            f"💀 Deathroll Challenge\n\n"

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

    msg = await ctx.send(
        embed=embed,
        view=view
    )

    view.message = msg

# ─────────────────────────
# END MATCH
# ─────────────────────────

async def end_match(
    self,
    channel_id
):

    game = deathroll_games[
        channel_id
    ]

    # WINNER

    if game["score1"] > game["score2"]:

        winner = game["player1"]
        loser = game["player2"]

    else:

        winner = game["player2"]
        loser = game["player1"]

    # PAYOUT

    payout = complete_wager(
        winner.id,
        loser.id,
        game["amount"]
    )

    # HISTORY

    add_history(
        winner.id,
        "deathroll",
        "win",
        payout,
        loser.id
    )

    add_history(
        loser.id,
        "deathroll",
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

    del deathroll_games[
        channel_id
    ]

async def setup(bot):

await bot.add_cog(
    Deathroll(bot)
  )
