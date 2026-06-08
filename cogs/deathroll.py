from discord.ext import commands
import discord
import random

from utils.game_state import (
    deathroll_games
)

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    add_history
)

from utils.stats import (
    record_win,
    record_loss
)


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

            return

        game = deathroll_games[
            self.channel_id
        ]

        if interaction.user != game["turn"]:

            await interaction.response.send_message(
                "❌ Not your turn.",
                ephemeral=True
            )

            return

        result = random.randint(
            1,
            game["max"]
        )

        if result == 1:

            loser = interaction.user

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

                title="💀 DEATHROLL",

                description=(

                    f"{loser.mention} "
                    f"rolled **1**\n\n"

                    f"🏆 "
                    f"{winner.mention} "
                    f"wins the round!"

                ),

                color=0xED4245
            )

            await interaction.response.send_message(
                embed=embed
            )

            game["max"] = 1000

            game["turn"] = winner

            if (
                game["score1"]
                >= game["wins_required"]
                or
                game["score2"]
                >= game["wins_required"]
            ):

                await self.cog.end_match(
                    self.channel_id,
                    winner,
                    loser
                )

                return

            next_embed = discord.Embed(

                description=(

                    f"🎯 Next Turn\n"
                    f"{winner.mention}"

                ),

                color=0x5865F2
            )

            await interaction.channel.send(

                embed=next_embed,

                view=RollView(
                    self.cog,
                    self.channel_id
                )
            )

            return

        game["max"] = result

        next_turn = (

            game["player1"]

            if interaction.user == game["player2"]

            else game["player2"]

        )

        game["turn"] = next_turn

        embed = discord.Embed(

            title="🎲 ROLL",

            description=(

                f"{interaction.user.mention}\n"
                f"rolled **{result}**\n\n"

                f"🎯 Turn:\n"
                f"{next_turn.mention}"

            ),

            color=0x5865F2
        )

        await interaction.response.send_message(

            embed=embed,

            view=RollView(
                self.cog,
                self.channel_id
            )
        )


class Deathroll(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="deathroll")
    async def deathroll(
        self,
        ctx,
        opponent: discord.Member,
        bo: int,
        amount: int
    ):

        if opponent.bot:

            return

        if opponent == ctx.author:

            return

        if bo not in [1, 3, 5]:

            embed = discord.Embed(

                description=(
                    "Use:\n"
                    "`.deathroll @user 1/3/5 amount`"
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if ctx.channel.id in deathroll_games:

            embed = discord.Embed(

                description="❌ Game active.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        cash1 = get_cash(ctx.author.id)
        cash2 = get_cash(opponent.id)

        if cash1 < amount:

            return

        if cash2 < amount:

            return

        wins_required = (
            bo // 2
        ) + 1

        deathroll_games[
            ctx.channel.id
        ] = {

            "player1": ctx.author,
            "player2": opponent,

            "amount": amount,

            "score1": 0,
            "score2": 0,

            "wins_required": wins_required,

            "max": 1000,

            "turn": ctx.author
        }

        embed = discord.Embed(

            title="💀 DEATHROLL",

            description=(

                f"{ctx.author.mention} ⚔️ "
                f"{opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(amount)}**\n\n"

                f"🏆 First to "
                f"**{wins_required}** wins"

            ),

            color=0xED4245
        )

        await ctx.send(

            embed=embed,

            view=RollView(
                self,
                ctx.channel.id
            )
        )

    async def end_match(
        self,
        channel_id,
        winner,
        loser
    ):

        game = deathroll_games[
            channel_id
        ]

        amount = game["amount"]

        remove_cash(
            loser.id,
            amount
        )

        add_cash(
            winner.id,
            amount
        )

        record_win(
            winner.id,
            amount
        )

        record_loss(
            loser.id,
            amount
        )

        add_history(
            winner.id,
            "Deathroll",
            "WIN",
            amount,
            loser.id
        )

        add_history(
            loser.id,
            "Deathroll",
            "LOSS",
            amount,
            winner.id
        )

        embed = discord.Embed(

            title="👑 MATCH WINNER",

            description=(

                f"{winner.mention}\n\n"

                f"💵 Won "
                f"**{format_cash(amount)}**"

            ),

            color=0xFEE75C
        )

        channel = self.bot.get_channel(
            channel_id
        )

        await channel.send(embed=embed)

        del deathroll_games[
            channel_id
        ]


async def setup(bot):

    await bot.add_cog(
        Deathroll(bot)
    )
