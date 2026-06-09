from discord.ext import commands
import discord
import random
import asyncio

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    parse_amount,
    format_cash
)


class Coinflip(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(
        aliases=["cf"]
    )
    async def coinflip(
        self,
        ctx,
        choice: str,
        amount: str
    ):

        choice = choice.lower()

        if choice not in [

            "heads",
            "tails",
            "h",
            "t"

        ]:

            await ctx.send(
                "Use: `.cf heads amount`"
            )

            return

        if choice == "h":

            choice = "heads"

        if choice == "t":

            choice = "tails"

        cash = get_cash(
            ctx.author.id
        )

        amount = parse_amount(
            amount,
            cash
        )

        if amount is None:

            await ctx.send(
                "Invalid amount."
            )

            return

        if amount <= 0:

            await ctx.send(
                "Invalid amount."
            )

            return

        if cash < amount:

            await ctx.send(
                "You don't have enough cash."
            )

            return

        suspense_msg = await ctx.send(
            "Flipping the coin... 🪙"
        )

        suspense_texts = [

            "Flipping. 🪙",
            "Flipping.. 🪙",
            "Flipping... 🪙"

        ]

        for text in suspense_texts:

            await suspense_msg.edit(
                content=text
            )

            await asyncio.sleep(0.05)

        # GIFS

        heads_gif = (
            "https://cdn.discordapp.com/attachments/"
            "1356735875517775995/"
            "1360904053567262883/"
            "VN20250413_143452.gif"
        )

        tails_gif = (
            "https://cdn.discordapp.com/attachments/"
            "1356735875517775995/"
            "1360903389403283496/"
            "VN20250413_142456_2.gif"
        )

        # RESULT

        result = random.choice([
            "heads",
            "tails"
        ])

        if result == "heads":

            gif = heads_gif

        else:

            gif = tails_gif

        # WIN

        if choice == result:

            add_cash(
                ctx.author.id,
                amount
            )

            outcome = (
                f"✅ {ctx.author.mention} won "
                f"**{format_cash(amount)}**"
            )

            color = discord.Color.green()

        # LOSE

        else:

            remove_cash(
                ctx.author.id,
                amount
            )

            outcome = (
                f"❌ {ctx.author.mention} lost "
                f"**{format_cash(amount)}**"
            )

            color = discord.Color.red()

        embed = discord.Embed(

            title="🪙 Coin Flip Result",

            description=(

                f"🎯 Result: **{result.upper()}**\n\n"
                f"{outcome}"

            ),

            color=color
        )

        embed.set_image(
            url=gif
        )

        await suspense_msg.edit(

            content=None,
            embed=embed

        )


async def setup(bot):

    await bot.add_cog(
        Coinflip(bot)
    )
