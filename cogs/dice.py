from discord.ext import commands
import discord
import random

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    parse_amount
)

from utils.stats import (
    record_win,
    record_loss
)


class Dice(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    # ─────────────────────────
    # DICE
    # ─────────────────────────

    @commands.command(name="dice")
    async def dice(
        self,
        ctx,
        side: str,
        amount
    ):

        side = side.lower()

        if side not in [

            "down",
            "7",
            "up"

        ]:

            embed = discord.Embed(

                description=(

                    "Use:\n\n"

                    "`.dice down amount`\n"
                    "`.dice 7 amount`\n"
                    "`.dice up amount`"

                ),

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return


        cash = get_cash(
            ctx.author.id
        )


        amount = parse_amount(
            amount,
            cash
        )


        if amount is None or amount <= 0:

            await ctx.send(
                "Invalid amount."
            )

            return


        if cash < amount:

            embed = discord.Embed(

                description="❌ Not enough cash.",

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return


        # REMOVE BET FIRST

        remove_cash(
            ctx.author.id,
            amount
        )


        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)

        total = dice1 + dice2

        won = False

        multiplier = 0


        # DOWN

        if side == "down":

            if 2 <= total <= 6:

                won = True
                multiplier = 2


        # EXACT 7

        elif side == "7":

            if total == 7:

                won = True
                multiplier = 5


        # UP

        elif side == "up":

            if 8 <= total <= 12:

                won = True
                multiplier = 2


        # RESULT

        if won:

            winnings = amount * multiplier

            add_cash(
                ctx.author.id,
                winnings
            )

            record_win(
                ctx.author.id,
                winnings
            )

            color = discord.Color.green()

            result_text = (
                "✅ You won!"
            )

        else:

            winnings = 0

            record_loss(
                ctx.author.id,
                amount
            )

            color = discord.Color.red()

            result_text = (
                "❌ You lost!"
            )


        embed = discord.Embed(

            title="🎲 DICE",

            description=(

                f"🎯 Bet:\n"
                f"**{side.upper()}**\n\n"

                f"🎲 Rolls:\n"
                f"**{dice1} + {dice2} = {total}**\n\n"

                f"{result_text}"

            ),

            color=color
        )


        if won:

            embed.add_field(

                name="💵 Won",

                value=(
                    f"**{format_cash(winnings)}**"
                ),

                inline=False
            )

        else:

            embed.add_field(

                name="💸 Lost",

                value=(
                    f"**{format_cash(amount)}**"
                ),

                inline=False
            )


        await ctx.send(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        Dice(bot)
    )
