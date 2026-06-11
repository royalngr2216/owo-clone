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
from utils.stats import add_stats, update_biggest_win
from utils.achievement_checker import check_achievements


# ─────────────────────────
# COIN SPIN FRAMES
# Simulates a coin tumbling through the air
# ─────────────────────────

COIN_SPIN = ["🪙", "⬜", "🪙", "⬜", "🪙"]

HEADS_GIF = (
    "https://cdn.discordapp.com/attachments/"
    "1356735875517775995/"
    "1360904053567262883/"
    "VN20250413_143452.gif"
)
TAILS_GIF = (
    "https://cdn.discordapp.com/attachments/"
    "1356735875517775995/"
    "1360903389403283496/"
    "VN20250413_142456_2.gif"
)


class Coinflip(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["cf"])
    async def coinflip(self, ctx, choice: str = None, amount: str = None):

        # ─── USAGE CHECK ───
        if choice is None or amount is None:
            embed = discord.Embed(
                title="🪙 COINFLIP",
                description=(
                    "**Usage:** `.cf heads amount` or `.cf tails amount`\n\n"
                    "**Shortcuts:** `.cf h 100k` or `.cf t all`\n\n"
                    "Win your bet on a correct call. **2x payout.**"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
            return

        choice = choice.lower()
        if choice == "h":
            choice = "heads"
        elif choice == "t":
            choice = "tails"

        if choice not in ["heads", "tails"]:
            await ctx.send(embed=discord.Embed(
                description="❌ Choose **heads** or **tails**.",
                color=0xED4245
            ))
            return

        cash   = get_cash(ctx.author.id)
        amount = parse_amount(amount, cash)

        if amount is None:
            await ctx.send(embed=discord.Embed(description="❌ Invalid amount.", color=0xED4245))
            return
        if amount <= 0:
            await ctx.send(embed=discord.Embed(description="❌ Bet must be above 0.", color=0xED4245))
            return
        if cash < amount:
            await ctx.send(embed=discord.Embed(description="❌ Not enough cash.", color=0xED4245))
            return

        # ─── DETERMINE RESULT BEFORE ANIMATION ───
        result = random.choice(["heads", "tails"])
        won    = (choice == result)

        add_stats(ctx.author.id, games_played=1, total_gambled=amount)

        # ─────────────────────────
        # SPINNING ANIMATION
        # ─────────────────────────

        embed = discord.Embed(
            title="🪙 COINFLIP",
            description=(
                f"**Your call:** {choice.upper()}\n\n"
                "🪙  *Flipping...*"
            ),
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(amount)}")
        msg = await ctx.send(embed=embed)

        spin_texts = [
            "🪙  *It's in the air...*",
            "⬜  *Spinning...*",
            "🪙  *Almost...*",
            "⬜  *Slowing down...*",
            "🪙  *Landing...*",
        ]

        for text in spin_texts:
            await asyncio.sleep(0.18)
            embed.description = f"**Your call:** {choice.upper()}\n\n{text}"
            try:
                await msg.edit(embed=embed)
            except:
                pass

        await asyncio.sleep(0.4)

        # ─────────────────────────
        # RESULT
        # ─────────────────────────

        if won:
            add_cash(ctx.author.id, amount)
            update_biggest_win(ctx.author.id, amount)

            embed = discord.Embed(
                title="🪙 COINFLIP — WIN!",
                description=(
                    f"**Your call:** {choice.upper()}\n"
                    f"**Result:** {result.upper()}\n\n"
                    f"✅ {ctx.author.mention} won **{format_cash(amount)}**"
                ),
                color=0x57F287
            )
        else:
            remove_cash(ctx.author.id, amount)

            embed = discord.Embed(
                title="🪙 COINFLIP — LOSS",
                description=(
                    f"**Your call:** {choice.upper()}\n"
                    f"**Result:** {result.upper()}\n\n"
                    f"❌ {ctx.author.mention} lost **{format_cash(amount)}**"
                ),
                color=0xED4245
            )

        embed.set_image(url=HEADS_GIF if result == "heads" else TAILS_GIF)
        embed.set_footer(text=f"Bet: {format_cash(amount)}")
        await msg.edit(embed=embed)

        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Coinflip(bot))
    
