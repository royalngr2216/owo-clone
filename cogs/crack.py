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
    record_loss,
    get_profile
)

from cogs.system import update_roles
from utils.game_state import crack_games


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
                "A crack match is already active."
            )

            return


        # PARSE BET

        amount = amount.lower()


        if amount.endswith("k"):

            bet = int(amount[:-1]) * 1000

        elif amount.endswith("m"):

            bet = int(amount[:-1]) * 1000000

        else:

            bet = int(amount)


        if bet <= 0:

            await ctx.send(
                "Bet must be greater than 0."
            )

            return


        # CREATE ACCOUNTS

        create_account(ctx.author.id)
        create_account(opponent.id)


        # CHECK CASH

        if get_cash(ctx.author.id) < bet:

            await ctx.send(
                f"{ctx.author.mention} does not have enough cash."
            )

            return


        if get_cash(opponent.id) < bet:

            await ctx.send(
                f"{opponent.mention} does not have enough cash."
            )

            return


        # CREATE GAME

        crack_games[ctx.channel.id] = {

            "player1": ctx.author,
            "player2": opponent,
            "bet": bet,
            "secret": random.randint(1, 100),
            "turn": ctx.author

        }


        embed = discord.Embed(

            title="💥 CRACK",

            description=(

                f"{ctx.author.mention} ⚔️ "
                f"{opponent.mention}\n\n"

                f"💵 Wager: **{format_cash(bet)}**\n\n"

                f"🎯 Guess a number between "
                f"**1 and 100**\n\n"

                f"🎮 {ctx.author.mention} goes first\n\n"

                f"Use:\n"
                f"`.guess number`"

            ),

            color=discord.Color.orange()
        )


        await ctx.send(embed=embed)


    # ─────────────────────────
    # GUESS
    # ─────────────────────────

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


        game = crack_games[ctx.channel.id]


        if ctx.author != game["turn"]:

            await ctx.send(
                "Not your turn."
            )

            return


        if number < 1 or number > 100:

            await ctx.send(
                "Guess between 1 and 100."
            )

            return


        secret = game["secret"]

        p1 = game["player1"]
        p2 = game["player2"]


        # CORRECT

        if number == secret:

            winner = ctx.author


            if winner == p1:

                loser = p2

            else:

                loser = p1


            bet = game["bet"]


            # MONEY

            remove_cash(
                loser.id,
                bet
            )


            add_cash(
                winner.id,
                bet
            )


            # STATS

            record_win(winner.id, 0)
            record_loss(loser.id, 0)


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


            # WIN EMBED

            embed = discord.Embed(

                title="🏆 CRACK RESULT",

                description=(

                    f"🎯 Secret Number: "
                    f"**{secret}**\n\n"

                    f"{winner.mention} cracked it!\n\n"

                    f"💵 Won "
                    f"**{format_cash(bet)}**"

                ),

                color=discord.Color.green()
            )


            await ctx.send(embed=embed)


            del crack_games[ctx.channel.id]


            return


        # WRONG GUESS

        if number < secret:

            hint = "📈 Higher"

        else:

            hint = "📉 Lower"


        # SWITCH TURN

        if game["turn"] == p1:

            game["turn"] = p2

        else:

            game["turn"] = p1


        embed = discord.Embed(

            description=(

                f"{hint}\n\n"

                f"🎮 Turn:\n"
                f"{game['turn'].mention}"

            ),

            color=discord.Color.red()
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Crack(bot)
            )
