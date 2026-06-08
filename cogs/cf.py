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

class CoinFlip(commands.Cog):

def __init__(self, bot):

    self.bot = bot

@commands.command(name="cf")
async def cf(
    self,
    ctx,
    choice: str = None,
    amount: int = None
):

    # ─────────────────────────
    # VALIDATION
    # ─────────────────────────

    if choice is None or amount is None:

        return await ctx.send(
            "Use: `.cf h/t amount`"
        )

    choice = choice.lower()

    valid = [
        "h",
        "heads",
        "t",
        "tails"
    ]

    if choice not in valid:

        return await ctx.send(
            "Choose `h` or `t`."
        )

    if amount <= 0:

        return await ctx.send(
            "Invalid amount."
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
    # SUSPENSE
    # ─────────────────────────

    embed = discord.Embed(
        description=(
            "🪙 Flipping Coin."
        ),
        color=0xFEE75C
    )

    msg = await ctx.send(
        embed=embed
    )

    suspense = [
        "🪙 Flipping Coin.",
        "🪙 Flipping Coin..",
        "🪙 Flipping Coin..."
    ]

    for text in suspense:

        embed.description = text

        await msg.edit(
            embed=embed
        )

        await asyncio.sleep(0.6)

    # ─────────────────────────
    # RESULT
    # ─────────────────────────

    result = random.choice([
        "heads",
        "tails"
    ])

    player_won = False

    if choice in ["h", "heads"]:

        if result == "heads":
            player_won = True

    if choice in ["t", "tails"]:

        if result == "tails":
            player_won = True

    # ─────────────────────────
    # WIN
    # ─────────────────────────

    if player_won:

        winnings = amount * 2

        add_cash(
            ctx.author.id,
            winnings
        )

        profit = winnings - amount

        add_history(
            ctx.author.id,
            "coinflip",
            "win",
            profit,
            "bot"
        )

        embed = discord.Embed(
            description=(
                f"🪙 Result: **{result.upper()}**\n\n"
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
            "coinflip",
            "loss",
            amount,
            "bot"
        )

        embed = discord.Embed(
            description=(
                f"🪙 Result: **{result.upper()}**\n\n"
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
    CoinFlip(bot)
)
