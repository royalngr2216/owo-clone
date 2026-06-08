from discord.ext import commands
import discord
import random

from utils.game_state import (
    crack_games
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


class Crack(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="crack")
    async def crack(
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
                    "`.crack @user 1/3/5 amount`"
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if ctx.channel.id in crack_games:

            embed = discord.Embed(

                description="❌ Crack already active.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        cash1 = get_cash(ctx.author.id)
        cash2 = get_cash(opponent.id)

        if cash1 < amount:

            embed = discord.Embed(

                description=(
                    f"{ctx.author.mention} "
                    f"doesn't have enough cash."
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if cash2 < amount:

            embed = discord.Embed(

                description=(
                    f"{opponent.mention} "
                    f"doesn't have enough cash."
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        wins_required = (
            bo // 2
        ) + 1

        crack_games[ctx.channel.id] = {

            "player1": ctx.author,
            "player2": opponent,

            "amount": amount,

            "wins_required": wins_required,

            "score1": 0,
            "score2": 0,

            "number": random.randint(1, 100),

            "turn": ctx.author
        }

        embed = discord.Embed(

            title="🎯 CRACK",

            description=(

                f"{ctx.author.mention} ⚔️ "
                f"{opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(amount)}**\n\n"

                f"🏆 First to "
                f"**{wins_required}** wins\n\n"

                f"Use `.guess number`"

            ),

            color=0x5865F2
        )

        await ctx.send(embed=embed)

    @commands.command(name="guess")
    async def guess(
        self,
        ctx,
        number: int
    ):

        if ctx.channel.id not in crack_games:

            return

        game = crack_games[ctx.channel.id]

        if ctx.author != game["turn"]:

            return

        target = game["number"]

        if number == target:

            if ctx.author == game["player1"]:

                game["score1"] += 1

            else:

                game["score2"] += 1

            embed = discord.Embed(

                title="✅ CORRECT",

                description=(

                    f"{ctx.author.mention}\n\n"

                    f"🎯 Number was "
                    f"**{target}**"

                ),

                color=0x57F287
            )

            await ctx.send(embed=embed)

            if (
                game["score1"]
                >= game["wins_required"]
                or
                game["score2"]
                >= game["wins_required"]
            ):

                winner = ctx.author

                loser = (
                    game["player1"]
                    if winner == game["player2"]
                    else game["player2"]
                )

                await self.end_match(
                    ctx.channel.id,
                    winner,
                    loser
                )

                return

            game["number"] = random.randint(1, 100)

            return

        if number < target:

            hint = "⬆️ Higher"

        else:

            hint = "⬇️ Lower"

        next_turn = (

            game["player1"]

            if ctx.author == game["player2"]

            else game["player2"]

        )

        game["turn"] = next_turn

        embed = discord.Embed(

            description=(

                f"{hint}\n\n"

                f"🎯 Turn:\n"
                f"{next_turn.mention}"

            ),

            color=0xED4245
        )

        await ctx.send(embed=embed)

    async def end_match(
        self,
        channel_id,
        winner,
        loser
    ):

        game = crack_games[channel_id]

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
            "Crack",
            "WIN",
            amount,
            loser.id
        )

        add_history(
            loser.id,
            "Crack",
            "LOSS",
            amount,
            winner.id
        )

        embed = discord.Embed(

            title="🏆 MATCH WINNER",

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

        del crack_games[channel_id]


async def setup(bot):

    await bot.add_cog(
        Crack(bot)
    )
