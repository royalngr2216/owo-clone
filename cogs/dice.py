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


class Dice(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="dice")
    async def dice(
        self,
        ctx,
        target: int,
        amount: int
    ):

        if target not in [6, 7, 9]:

            embed = discord.Embed(

                description=(
                    "Use:\n"
                    "`.dice 6 amount`\n"
                    "`.dice 7 amount`\n"
                    "`.dice 9 amount`"
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

            title="🎲 Rolling Dice",

            description="Rolling...",

            color=0x5865F2
        )

        msg = await ctx.send(embed=embed)

        await asyncio.sleep(2)

        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)

        total = dice1 + dice2

        won = False
        payout = 0

        # TARGET 6

        if target == 6:

            if total < 7:

                won = True
                payout = amount * 2

        # TARGET 9

        elif target == 9:

            if total > 7:

                won = True
                payout = amount * 2

        # TARGET 7

        elif target == 7:

            if total == 7:

                won = True
                payout = amount * 7

        # WIN

        if won:

            add_cash(
                ctx.author.id,
                payout
            )

            record_win(
                ctx.author.id,
                amount
            )

            add_history(
                ctx.author.id,
                "Dice",
                "WIN",
                payout - amount,
                "Bot"
            )

            embed = discord.Embed(

                title="✅ YOU WON",

                description=(

                    f"🎲 Dice Rolled\n"
                    f"**{dice1} + {dice2} = {total}**\n\n"

                    f"💵 Won "
                    f"**{format_cash(payout - amount)}**"

                ),

                color=0x57F287
            )

        # LOSS

        else:

            record_loss(
                ctx.author.id,
                amount
            )

            add_history(
                ctx.author.id,
                "Dice",
                "LOSS",
                amount,
                "Bot"
            )

            embed = discord.Embed(

                title="❌ YOU LOST",

                description=(

                    f"🎲 Dice Rolled\n"
                    f"**{dice1} + {dice2} = {total}**\n\n"

                    f"💸 Lost "
                    f"**{format_cash(amount)}**"

                ),

                color=0xED4245
            )

        await msg.edit(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        Dice(bot)
    )
