from discord.ext import commands
import discord
import random

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    add_history,
    parse_amount
)

from utils.stats import (
    record_win,
    record_loss
)


class CF(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="cf")
    async def cf(
        self,
        ctx,
        side: str,
        amount
    ):

        amount = parse_amount(
            amount
        )

        side = side.lower()

        if side not in [

            "h",
            "t",
            "heads",
            "tails"

        ]:

            embed = discord.Embed(

                description=(
                    "Use:\n"
                    "`.cf h amount`\n"
                    "`.cf t amount`"
                ),

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return

        if amount <= 0:

            return

        cash = get_cash(
            ctx.author.id
        )

        if cash < amount:

            embed = discord.Embed(

                description="❌ Not enough cash.",

                color=discord.Color.red()
            )

            await ctx.send(
                embed=embed
            )

            return

        result = random.choice([
            "h",
            "t"
        ])

        won = side[0] == result

        if won:

            add_cash(
                ctx.author.id,
                amount
            )

            record_win(
                ctx.author.id,
                amount
            )

            add_history(

                ctx.author.id,

                "Coinflip",

                "WIN",

                amount,

                None
            )

            color = discord.Color.green()

            result_text = (
                "✅ You won!"
            )

        else:

            remove_cash(
                ctx.author.id,
                amount
            )

            record_loss(
                ctx.author.id,
                amount
            )

            add_history(

                ctx.author.id,

                "Coinflip",

                "LOSS",

                amount,

                None
            )

            color = discord.Color.red()

            result_text = (
                "❌ You lost!"
            )

        flip = (
            "🪙 Heads"
            if result == "h"
            else "🪙 Tails"
        )

        embed = discord.Embed(

            title="🪙 COINFLIP",

            description=(

                f"🎯 Bet:\n"
                f"**{side.upper()}**\n\n"

                f"{flip}\n\n"

                f"{result_text}"

            ),

            color=color
        )

        if won:

            embed.add_field(

                name="💵 Won",

                value=(
                    f"**{format_cash(amount)}**"
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
        CF(bot)
    )
