from discord.ext import commands
import discord
import random
import asyncio

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


class Coinflip(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="cf")
    async def cf(
        self,
        ctx,
        choice: str,
        amount: int
    ):

        choice = choice.lower()

        if choice in ["h", "heads"]:

            choice = "heads"

        elif choice in ["t", "tails"]:

            choice = "tails"

        else:

            embed = discord.Embed(

                description=(
                    "Use:\n"
                    "`.cf h amount`\n"
                    "or\n"
                    "`.cf t amount`"
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if amount <= 0:

            return

        cash = get_cash(ctx.author.id)

        if cash < amount:

            embed = discord.Embed(

                description="❌ Not enough cash.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        remove_cash(
            ctx.author.id,
            amount
        )

        embed = discord.Embed(

            title="🪙 Coin Flip",

            description="Flipping...",

            color=0xFEE75C
        )

        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1.5)

        result = random.choice([
            "heads",
            "tails"
        ])

        if result == choice:

            winnings = amount * 2

            add_cash(
                ctx.author.id,
                winnings
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
                "Bot"
            )

            result_embed = discord.Embed(

                title="✅ YOU WON",

                description=(

                    f"🪙 Result: "
                    f"**{result.upper()}**\n\n"

                    f"💵 Won "
                    f"**{format_cash(amount)}**"

                ),

                color=0x57F287
            )

        else:

            record_loss(
                ctx.author.id,
                amount
            )

            add_history(
                ctx.author.id,
                "Coinflip",
                "LOSS",
                amount,
                "Bot"
            )

            result_embed = discord.Embed(

                title="❌ YOU LOST",

                description=(

                    f"🪙 Result: "
                    f"**{result.upper()}**\n\n"

                    f"💸 Lost "
                    f"**{format_cash(amount)}**"

                ),

                color=0xED4245
            )

        await msg.edit(
            embed=result_embed
        )


async def setup(bot):

    await bot.add_cog(
        Coinflip(bot)
    )
