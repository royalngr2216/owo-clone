from discord.ext import commands
import discord
import asyncio
import random

from utils.economy import (
can_afford,
remove_cash,
add_cash,
format_cash,
add_history
)

DICE_EMOJIS = {
1: "⚀",
2: "⚁",
3: "⚂",
4: "⚃",
5: "⚄",
6: "⚅"
}

class Dice(commands.Cog):

def __init__(self, bot):

    self.bot = bot

@commands.command(name="dice")
async def dice(
    self,
    ctx,
    mode: int = None,
    amount: int = None
):

    # ─────────────────────────
    # VALIDATION
    # ─────────────────────────

    if mode is None or amount is None:

        return await ctx.send(
            "Use: `.dice 6/7/9 amount`"
        )

    if mode not in [6, 7, 9]:

        return await ctx.send(
            "Choose 6, 7 or 9."
        )

    if amount < 10_000:

        return await ctx.send(
            "Minimum bet is $10,000."
        )

    if not can_afford(
        ctx.author.id,
        amount
    ):

        return await ctx.send(
            "You don't have enough cash."
        )

    # ─────────────────────────
    # REMOVE CASH
    # ─────────────────────────

    remove_cash(
        ctx.author.id,
        amount
    )

    # ─────────────────────────
    # ANIMATION
    # ─────────────────────────

    embed = discord.Embed(
        description=(
            "🎲 Rolling Dice."
        ),
        color=0x5865F2
    )

    msg = await ctx.send(
        embed=embed
    )

    suspense = [
        "🎲 Rolling Dice.",
        "🎲 Rolling Dice..",
        "🎲 Rolling Dice..."
    ]

    for text in suspense:

        embed.description = text

        await msg.edit(
            embed=embed
        )

        await asyncio.sleep(0.7)

    # ─────────────────────────
    # ROLL
    # ─────────────────────────

    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)

    total = dice1 + dice2

    emoji1 = DICE_EMOJIS[dice1]
    emoji2 = DICE_EMOJIS[dice2]

    won = False
    payout = 0

    # ─────────────────────────
    # MODE 6
    # ─────────────────────────

    if mode == 6:

        if total < 7:

            won = True
            payout = amount * 2

    # ─────────────────────────
    # MODE 9
    # ─────────────────────────

    elif mode == 9:

        if total > 7:

            won = True
            payout = amount * 2

    # ─────────────────────────
    # MODE 7
    # ─────────────────────────

    elif mode == 7:

        if total == 7:

            won = True
            payout = amount * 7

    # ─────────────────────────
    # WIN
    # ─────────────────────────

    if won:

        add_cash(
            ctx.author.id,
            payout
        )

        profit = payout - amount

        add_history(
            ctx.author.id,
            "dice",
            "win",
            profit,
            "bot"
        )

        embed = discord.Embed(
            description=(

                f"{emoji1} + {emoji2}\n\n"

                f"🎯 Total: **{total}**\n\n"

                f"✅ You won\n"
                f"+ {format_cash(profit)}"

            ),
            color=0x57F287
        )

    # ─────────────────────────
    # LOSS
    # ─────────────────────────

    else:

        add_history(
            ctx.author.id,
            "dice",
            "loss",
            amount,
            "bot"
        )

        embed = discord.Embed(
            description=(

                f"{emoji1} + {emoji2}\n\n"

                f"🎯 Total: **{total}**\n\n"

                f"❌ You lost\n"
                f"- {format_cash(amount)}"

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
