from discord.ext import commands
import discord
import random

from utils.economy import (
    create_account,
    get_cash,
    add_cash,
    remove_cash,
    format_cash
)

from utils.stats import (
    record_win,
    record_loss
)

from utils.game_state import (
    crack_games
)


class Crack(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="crack")
    async def crack(
        self,
        ctx,
        opponent: discord.Member,
        amount: str
    ):

        if opponent == ctx.author:

            await ctx.send(
                "You cannot play yourself."
            )

            return

        if ctx.channel.id in crack_games:

            await ctx.send(
                "A crack game is already active."
            )

            return

        amount = amount.lower()

        if amount.endswith("k"):

            amount = int(
                float(amount[:-1]) * 1000
            )

        elif amount.endswith("m"):

            amount = int(
                float(amount[:-1]) * 1000000
            )

        else:

            amount = int(amount)

        if amount <= 0:

            await ctx.send(
                "Amount must be greater than 0."
            )

            return

        create_account(ctx.author.id)
        create_account(opponent.id)

        if get_cash(ctx.author.id) < amount:

            await ctx.send(
                f"{ctx.author.mention} does not have enough cash."
            )

            return

        if get_cash(opponent.id) < amount:

            await ctx.send(
                f"{opponent.mention} does not have enough cash."
            )

            return

        crack_games[ctx.channel.id] = {

            "player1": ctx.author,
            "player2": opponent,

            "turn": ctx.author,

            "bet": amount,

            "number": random.randint(
                1,
                25
            )
        }

        embed = discord.Embed(

            title="💥 CRACK",

            description=(

                f"{ctx.author.mention} ⚔️ "
                f"{opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(amount)}**\n\n"

                f"🎯 Guess the hidden number\n"
                f"between **1 - 25**\n\n"

                f"Use `.guess number`"

            ),

            color=discord.Color.orange()
        )

        await ctx.send(embed=embed)

    @commands.command(name="guess")
    async def guess(
        self,
        ctx,
        number: int
    ):

        if ctx.channel.id not in crack_games:

            await ctx.send(
                "No active crack game."
            )

            return

        game = crack_games[
            ctx.channel.id
        ]

        if ctx.author != game["turn"]:

            await ctx.send(
                "It is not your turn."
            )

            return

        target = game["number"]

        if number == target:

            loser = ctx.author

            if loser == game["player1"]:

                winner = game["player2"]

            else:

                winner = game["player1"]

            amount = game["bet"]

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

            embed = discord.Embed(

                title="💥 CRACKED",

                description=(

                    f"{loser.mention} guessed "
                    f"the hidden number!\n\n"

                    f"🎯 Number was "
                    f"**{target}**\n\n"

                    f"🏆 Winner: "
                    f"{winner.mention}\n"

                    f"💵 Won: "
                    f"**{format_cash(amount)}**"

                ),

                color=discord.Color.red()
            )

            await ctx.send(embed=embed)

            del crack_games[
                ctx.channel.id
            ]

            return

        hint = (

            "⬆️ Higher"

            if number < target

            else "⬇️ Lower"
        )

        embed = discord.Embed(

            description=(

                f"{ctx.author.mention} guessed "
                f"**{number}**\n\n"

                f"{hint}"

            ),

            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

        if game["turn"] == game["player1"]:

            game["turn"] = game["player2"]

        else:

            game["turn"] = game["player1"]


async def setup(bot):

    await bot.add_cog(
        Crack(bot)
    )
