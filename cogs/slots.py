from discord.ext import commands
import discord
import random
import asyncio

from utils.economy import (
    create_account,
    get_cash,
    add_cash,
    remove_cash,
    format_cash
)
from utils.stats import add_stats, update_biggest_win
from utils.achievement_checker import check_achievements


# ─────────────────────────
# PARSE AMOUNT
# ─────────────────────────

def parse_amount(amount):
    amount = amount.lower()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    try:
        if amount[-1] in multipliers:
            return int(float(amount[:-1]) * multipliers[amount[-1]])
        return int(amount)
    except:
        return None


# ─────────────────────────
# SYMBOLS
# ─────────────────────────

SYMBOLS = ["🍒", "🍋", "🍀", "🔔", "💎", "👑", "💀"]

OUTCOMES = {
    "lose":    50,
    "cherry":  22,
    "lemon":   11,
    "clover":   4,
    "bell":     3,
    "diamond":  2,
    "jackpot":  3,
    "troll":    5
}

PAYOUTS = {
    "🍒": 1.5,
    "🍋": 2.0,
    "🍀": 3.0,
    "🔔": 5.0,
    "💎": 6.0,
    "👑": 10.0
}

OUTCOME_SYMBOL = {
    "cherry":  "🍒",
    "lemon":   "🍋",
    "clover":  "🍀",
    "bell":    "🔔",
    "diamond": "💎",
    "jackpot": "👑",
    "troll":   "💀"
}

REEL_TITLES = {
    "spinning": "🎰  ECHLEON  SLOTS  🎰",
    "win":      "✅    Y O U   W I N    ✅",
    "jackpot1": "✨  👑  J A C K P O T  👑  ✨",
    "jackpot2": "🎉  👑  J A C K P O T  👑  🎉",
    "loss":     "❌    N O   M A T C H    ❌",
    "nearmiss": "😱   S O   C L O S E   😱",
    "troll":    "☠️   W I P E D   O U T   ☠️"
}


# ─────────────────────────
# FRAME BUILDER
# ─────────────────────────

def build_frame(reels, title=None, bet=None):
    if title is None:
        title = REEL_TITLES["spinning"]
    r = f"  {reels[0]}  ┃  {reels[1]}  ┃  {reels[2]}  "
    frame = (
        f"```\n"
        f"╔══════════════════════════╗\n"
        f"║  {title}  ║\n"
        f"╠══════════════════════════╣\n"
        f"║{r}║\n"
        f"╚══════════════════════════╝\n"
        f"```"
    )
    return frame


class Slots(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slots")
    async def slots(self, ctx, amount: str = None):

        create_account(ctx.author.id)

        # ─── NO AMOUNT ───
        if amount is None:
            embed = discord.Embed(
                description=(
                    "❌ Enter a bet amount.\n\n"
                    "**Example:** `.slots 100k`\n\n"
                    "**Payouts:**\n"
                    "🍒 ×1.5 │ 🍋 ×2 │ 🍀 ×3\n"
                    "🔔 ×5 │ 💎 ×6 │ 👑 ×10"
                ),
                color=0xED4245
            )
            await ctx.send(embed=embed)
            return

        cash = get_cash(ctx.author.id)

        if amount.lower() == "all":
            amount = cash
        else:
            amount = parse_amount(amount)
            if amount is None:
                await ctx.send(embed=discord.Embed(
                    description="❌ Invalid amount.",
                    color=0xED4245
                ))
                return

        if amount <= 0:
            await ctx.send(embed=discord.Embed(
                description="❌ Bet must be above 0.",
                color=0xED4245
            ))
            return

        if cash < amount:
            await ctx.send(embed=discord.Embed(
                description="❌ Not enough cash.",
                color=0xED4245
            ))
            return

        remove_cash(ctx.author.id, amount)
        add_stats(ctx.author.id, games_played=1, total_gambled=amount)

        # ─── DETERMINE OUTCOME ───
        roll = random.randint(1, 100)
        current = 0
        outcome = "lose"
        for name, chance in OUTCOMES.items():
            current += chance
            if roll <= current:
                outcome = name
                break

        # ─── BUILD RESULT REELS ───
        if outcome in OUTCOME_SYMBOL:
            sym = OUTCOME_SYMBOL[outcome]
            result = [sym, sym, sym]
        else:
            lose_patterns = [
                ["🍒", "💎", "🍋"], ["👑", "🍀", "🍒"],
                ["💀", "🍋", "💎"], ["🔔", "🍒", "💀"],
                ["💎", "🍋", "🍀"], ["👑", "💀", "🍒"],
                ["👑", "👑", "🍒"], ["💎", "💎", "🍋"],
                ["🍒", "🍒", "🍋"], ["🔔", "🔔", "🍀"]
            ]
            result = random.choice(lose_patterns)

        # ─── INITIAL MESSAGE ───
        reels = ["❔", "❔", "❔"]
        embed = discord.Embed(color=0x5865F2)
        embed.description = build_frame(reels)
        embed.set_footer(text=f"Bet: {format_cash(amount)}  •  Good luck!")
        msg = await ctx.send(embed=embed)

        # ─── SPIN ANIMATION ───
        for reel_idx in range(3):
            # Duration increases per reel; 3rd gets extra suspense on near-win
            base_duration = 0.5 + (reel_idx * 0.2)
            if reel_idx == 2 and result[0] == result[1]:
                base_duration = 1.3   # dramatic slow-down

            start = asyncio.get_event_loop().time()
            delay = 0.05  # start fast

            while asyncio.get_event_loop().time() - start < base_duration:
                reels[reel_idx] = random.choice(SYMBOLS)
                embed.description = build_frame(reels)
                try:
                    await msg.edit(embed=embed)
                except:
                    pass
                await asyncio.sleep(delay)
                # gradually slow down in the last 30%
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed > base_duration * 0.6:
                    delay = min(0.14, delay + 0.01)

            # Lock the reel
            reels[reel_idx] = result[reel_idx]
            embed.description = build_frame(reels)
            try:
                await msg.edit(embed=embed)
            except:
                pass
            await asyncio.sleep(0.25)

        # ─── NEAR MISS CHECK ───
        near_miss = (
            (result[0] == result[1] and result[1] != result[2]) or
            (result[1] == result[2] and result[0] != result[1])
        )

        await asyncio.sleep(0.35)

        # ─── TROLL ───
        if outcome == "troll":
            embed = discord.Embed(color=0xED4245)
            embed.description = build_frame(result, REEL_TITLES["troll"])
            embed.add_field(
                name="☠️ WIPED OUT",
                value=(
                    f"EMIEL entered the casino and 🍇 you.\n"
                    f"💸 Lost **{format_cash(amount)}**"
                ),
                inline=False
            )
            embed.set_footer(text=f"Bet: {format_cash(amount)}")
            await msg.edit(embed=embed)
            return

        # ─── LOSE ───
        if outcome == "lose":
            title = REEL_TITLES["nearmiss"] if near_miss else REEL_TITLES["loss"]
            embed = discord.Embed(color=0xED4245)
            embed.description = build_frame(result, title)
            loss_text = f"💸 Lost **{format_cash(amount)}**"
            if near_miss:
                loss_text += "\n\n*Two in a row... next time!*"
            embed.add_field(name="Result", value=loss_text, inline=False)
            embed.set_footer(text=f"Bet: {format_cash(amount)}")
            await msg.edit(embed=embed)
            return

        # ─── WIN ───
        symbol = result[0]
        multiplier = PAYOUTS[symbol]
        winnings = int(amount * multiplier)
        profit = winnings - amount

        add_cash(ctx.author.id, winnings)
        update_biggest_win(ctx.author.id, winnings)

        if outcome == "jackpot":
            # Alternating jackpot celebration frames
            for i in range(3):
                t = REEL_TITLES["jackpot1"] if i % 2 == 0 else REEL_TITLES["jackpot2"]
                c = 0xF1C40F if i % 2 == 0 else 0xFF9900
                embed = discord.Embed(color=c)
                embed.description = build_frame(result, t)
                embed.add_field(
                    name="🏆 JACKPOT",
                    value=(
                        f"Won **{format_cash(winnings)}**\n"
                        f"📈 Profit: **{format_cash(profit)}**\n"
                        f"🎯 Multiplier: **{multiplier}x**"
                    ),
                    inline=False
                )
                embed.set_footer(text=f"Bet: {format_cash(amount)}")
                await msg.edit(embed=embed)
                await asyncio.sleep(0.5)
        else:
            embed = discord.Embed(color=0x57F287)
            embed.description = build_frame(result, REEL_TITLES["win"])
            embed.add_field(
                name="🏆 Winner!",
                value=(
                    f"Won **{format_cash(winnings)}**\n"
                    f"📈 Profit: **{format_cash(profit)}**\n"
                    f"🎯 Multiplier: **{multiplier}x**"
                ),
                inline=False
            )
            embed.set_footer(text=f"Bet: {format_cash(amount)}")
            await msg.edit(embed=embed)

        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Slots(bot))
    
