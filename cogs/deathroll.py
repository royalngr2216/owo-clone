from discord.ext import commands
import discord
import random

from utils.game_state import (
    deathroll_games
)

from utils.economy import (
    parse_amount,
    get_cash,
    format_cash
)

from utils.stats import (
    record_win,
    record_loss,
    get_profile
)

from cogs.system import (
    update_roles
)


# ─────────────────────────
# CONFIRM VIEW
# ─────────────────────────

class DeathrollConfirmView(
    discord.ui.View
):

    def __init__(
        self,
        ctx,
        opponent,
        bo,
        amount
    ):

        super().__init__(timeout=30)

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

            await interaction.response.send_message(
                "❌ This is not for you.",
                ephemeral=True
            )

            return

        if self.ctx.channel.id in deathroll_games:

            await interaction.response.send_message(
                "❌ Match already active.",
                ephemeral=True
            )

            return

        if get_cash(
            self.ctx.author.id
        ) < self.amount:

            await interaction.response.send_message(
                "❌ Challenger no longer has enough cash.",
                ephemeral=True
            )

            return

        if get_cash(
            self.opponent.id
        ) < self.amount:

            await interaction.response.send_message(
                "❌ You no longer have enough cash.",
                ephemeral=True
            )

            return

        wins_required = (
            self.bo // 2
        ) + 1

        deathroll_games[
            self.ctx.channel.id
        ] = {

            "player1": self.ctx.author,
            "player2": self.opponent,

            "amount": self.amount,

            "bo": self.bo,

            "wins_required": wins_required,

            "score1": 0,
            "score2": 0,

            "current": 1000,

            "turn": self.ctx.author
        }

        embed = discord.Embed(

            title="💀 DEATHROLL",

            description=(

                f"{self.ctx.author.mention} ⚔️ "
                f"{self.opponent.mention}\n\n"

                f"💵 Bet\n"
                f"**{format_cash(self.amount)}**\n\n"

                f"🏆 First to "
                f"**{wins_required}** wins\n\n"

                f"🎲 Use `.roll`"

            ),

            color=discord.Color.red()
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

            await interaction.response.send_message(
                "❌ This is not for you.",
                ephemeral=True
            )

            return

        embed = discord.Embed(

            description="❌ Challenge declined.",

            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )


# ─────────────────────────
# DEATHROLL
# ─────────────────────────

class Deathroll(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="deathroll")
    async def deathroll(
        self,
        ctx,
        opponent: discord.Member,
        bo,
        amount
    ):

        amount = parse_amount(
            amount
        )

        bo = int(bo)

        if opponent == ctx.author:

            return

        if opponent.bot:

            return

        if bo not in [1, 3, 5, 7, 9]:

            return

        if amount <= 0:

            return

        if ctx.channel.id in deathroll_games:

            embed = discord.Embed(

                description="❌ Match already active.",

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return

        if get_cash(
            ctx.author.id
        ) < amount:

            embed = discord.Embed(

                description="❌ You don't have enough cash.",

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return

        if get_cash(
            opponent.id
        ) < amount:

            embed = discord.Embed(

                description=(
                    f"❌ {opponent.mention} "
                    f"doesn't have enough cash."
                ),

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return

        embed = discord.Embed(

            title="💀 DEATHROLL CHALLENGE",

            description=(

                f"{ctx.author.mention} challenged "
                f"{opponent.mention}\n\n"

                f"💵 Bet\n"
                f"**{format_cash(amount)}**\n\n"

                f"🏆 Best Of "
                f"**{bo}**"

            ),

            color=discord.Color.blurple()
        )

        await ctx.send(

            embed=embed,

            view=DeathrollConfirmView(
                ctx,
                opponent,
                bo,
                amount
            )
        )

    @commands.command(name="roll")
    async def roll(self, ctx):

        if ctx.channel.id not in deathroll_games:

            return

        game = deathroll_games[
            ctx.channel.id
        ]

        if ctx.author != game["turn"]:

            return

        roll = random.randint(
            1,
            game["current"]
        )

        # LOST ROUND

        if roll == 1:

            loser = ctx.author

            winner = (

                game["player1"]

                if loser == game["player2"]

                else game["player2"]

            )

            if winner == game["player1"]:

                game["score1"] += 1

            else:

                game["score2"] += 1

            embed = discord.Embed(

                description=(

                    f"💀 {loser.mention} "
                    f"rolled **1**\n\n"

                    f"🏆 {winner.mention} "
                    f"wins the round!\n\n"

                    f"📊 Score\n"
                    f"# {game['score1']} - "
                    f"{game['score2']}"

                ),

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            game["current"] = 1000

            game["turn"] = winner

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

            next_embed = discord.Embed(

                description=(

                    f"🎲 New round started\n\n"

                    f"🎯 Turn\n"
                    f"{winner.mention}"

                ),

                color=discord.Color.blurple()
            )

            await ctx.send(
                embed=next_embed
            )

            return

        # CONTINUE

        game["current"] = roll

        next_turn = (

            game["player1"]

            if ctx.author == game["player2"]

            else game["player2"]

        )

        game["turn"] = next_turn

        embed = discord.Embed(

            description=(

                f"🎲 {ctx.author.mention} "
                f"rolled\n"

                f"# {roll}\n\n"

                f"🎯 Turn\n"
                f"{next_turn.mention}"

            ),

            color=discord.Color.blurple()
        )

        await ctx.send(
            embed=embed
        )

    async def end_match(
        self,
        channel_id
    ):

        game = deathroll_games[
            channel_id
        ]

        if game["score1"] > game["score2"]:

            winner = game["player1"]
            loser = game["player2"]

        else:

            winner = game["player2"]
            loser = game["player1"]

        record_win(
            winner.id,
            game["amount"]
        )

        record_loss(
            loser.id,
            game["amount"]
        )

        winner_stats = get_profile(
            winner.id
        )

        loser_stats = get_profile(
            loser.id
        )

        await update_roles(
            winner,
            winner_stats["matches"]
        )

        await update_roles(
            loser,
            loser_stats["matches"]
        )

        embed = discord.Embed(

            description=(

                f"🏆 {winner.mention} "
                f"wins the match!\n\n"

                f"💵 Won\n"
                f"**{format_cash(game['amount'])}**\n\n"

                f"📊 Final Score\n"
                f"# {game['score1']} - "
                f"{game['score2']}"

            ),

            color=discord.Color.gold()
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
