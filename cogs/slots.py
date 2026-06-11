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
from utils.stats import (
    add_stats,
    update_biggest_win
)
from utils.achievement_checker import (
    check_achievements
)


# ─────────────────────────
# PARSE MONEY
# ─────────────────────────

def parse_amount(amount: str):
    amount = amount.lower()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    try:
        if amount[-1] in multipliers:
            return int(float(amount[:-1]) * multipliers[amount[-1]])
        return int(amount)
    except Exception:
        return None


# ─────────────────────────
# SYMBOLS & CONFIG
# ─────────────────────────

# Your animated slot emoji from the developer portal.
# Discord renders it as a spinning GIF on any reel that hasn't landed yet —
# exactly like OwO's <a:slot_gif:...>.
SPINNING = "<a:slots:1514761192193789982>"

PAYOUTS = {
    "🍒": 1.5,
    "🍋": 2,
    "🍀": 3,
    "🔔": 5,
    "💎": 6,
    "👑": 10,
}

OUTCOMES = {
    "lose":    50,
    "cherry":  22,
    "lemon":   11,
    "clover":   4,
    "bell":     3,
    "diamond":  2,
    "jackpot":  3,
    "troll":    5,
}


# ─────────────────────────
# BUILD SLOT UI
# ─────────────────────────

def build_slots(r0, r1, r2, author_name: str, bet: int, footer: str = ""):
    """
    Matches OwO's plain-text layout:

      **  `___SLOTS___`**
      `  ` 🍒 <spinning> <spinning> `  `  PlayerName bet 🪙 500
        `|         |`
        `|         |`   and won 🪙 750
    """
    line2 = f"` ` {r0} {r1} {r2} ` `   **{author_name}** bet 🪙 {format_cash(bet)}"
    line4 = "`|         |`" + (f"   {footer}" if footer else "")
    return "\n".join([
        "**  `___SLOTS___`**",
        line2,
        "`|         |`",
        line4,
    ])


class Slots(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slots", aliases=["slot", "s"])
    async def slots(self, ctx, amount: str = None):

        create_account(ctx.author.id)
        name = ctx.author.display_name

        # ── No argument ──────────────────────────────────────────────────
        if amount is None:
            await ctx.send(
                embed=discord.Embed(
                    description="❌ Enter a bet amount.  Example: `.slots 100k`",
                    color=0xED4245,
                )
            )
            return

        # ── Parse bet ────────────────────────────────────────────────────
        cash = get_cash(ctx.author.id)

        if amount.lower() == "all":
            amount = cash
        else:
            amount = parse_amount(amount)
            if amount is None:
                await ctx.send(
                    embed=discord.Embed(description="❌ Invalid amount.", color=0xED4245)
                )
                return

        if amount <= 0:
            await ctx.send(
                embed=discord.Embed(description="❌ Bet must be above 0.", color=0xED4245)
            )
            return

        if cash < amount:
            await ctx.send(
                embed=discord.Embed(
                    description="❌ You don't have enough cash.", color=0xED4245
                )
            )
            return

        # ── Deduct bet ───────────────────────────────────────────────────
        remove_cash(ctx.author.id, amount)
        add_stats(ctx.author.id, games_played=1, total_gambled=amount)

        # ── Determine outcome ────────────────────────────────────────────
        roll = random.randint(1, 100)
        current = 0
        outcome = "lose"
        for name_key, chance in OUTCOMES.items():
            current += chance
            if roll <= current:
                outcome = name_key
                break

        # ── Build result reels ───────────────────────────────────────────
        outcome_reels = {
            "cherry":  ["🍒", "🍒", "🍒"],
            "lemon":   ["🍋", "🍋", "🍋"],
            "clover":  ["🍀", "🍀", "🍀"],
            "bell":    ["🔔", "🔔", "🔔"],
            "diamond": ["💎", "💎", "💎"],
            "jackpot": ["👑", "👑", "👑"],
            "troll":   ["💀", "💀", "💀"],
        }

        if outcome in outcome_reels:
            result = outcome_reels[outcome]
        else:
            lose_patterns = [
                ["🍒", "💎", "🍋"],
                ["👑", "🍀", "🍒"],
                ["💀", "🍋", "💎"],
                ["🔔", "🍒", "💀"],
                ["💎", "🍋", "🍀"],
                ["👑", "💀", "🍒"],
                ["👑", "👑", "🍒"],  # near-miss
                ["💎", "💎", "🍋"],  # near-miss
            ]
            result = random.choice(lose_patterns)

        near_miss = (result[0] == result[1]) and (outcome == "lose")

        # ── ANIMATION ────────────────────────────────────────────────────
        #
        # Mirrors OwO's setTimeout chain exactly.
        # The animated emoji spins itself in Discord — no looping needed.
        #
        #   send          →  spinning  spinning  spinning
        #   +1.0 s edit   →  reel0     spinning  spinning
        #   +0.7 s edit   →  reel0     reel1     spinning
        #   +1.0 s edit   →  reel0     reel1     reel2   + footer
        #
        # Near-miss: last delay stretches to 2.0 s for extra suspense.

        S = SPINNING

        # Step 0 — send, all spinning
        msg = await ctx.send(build_slots(S, S, S, name, amount))

        # Step 1 — reel 0 lands (+1.0 s)
        await asyncio.sleep(1.0)
        await msg.edit(content=build_slots(result[0], S, S, name, amount))

        # Step 2 — reel 1 lands (+0.7 s)
        await asyncio.sleep(0.7)
        await msg.edit(content=build_slots(result[0], result[1], S, name, amount))

        # Step 3 — reel 2 lands + result footer (+1.0 s, or +2.0 s near-miss)
        await asyncio.sleep(2.0 if near_miss else 1.0)

        # ── Final frame ──────────────────────────────────────────────────

        if outcome == "troll":
            footer = "☠ EMIEL entered the casino and 🍇 you."
            await msg.edit(content=build_slots(result[0], result[1], result[2], name, amount, footer))
            return

        if outcome == "lose":
            footer = (
                f"💔 SO close...  lost 🪙 {format_cash(amount)}"
                if near_miss
                else f"❌ and lost 🪙 {format_cash(amount)}"
            )
            await msg.edit(content=build_slots(result[0], result[1], result[2], name, amount, footer))
            return

        # Win
        symbol     = result[0]
        multiplier = PAYOUTS[symbol]
        winnings   = int(amount * multiplier)
        profit     = winnings - amount

        add_cash(ctx.author.id, winnings)
        update_biggest_win(ctx.author.id, winnings)

        footer = (
            f"✨ JACKPOT!  won 🪙 {format_cash(winnings)}"
            if outcome == "jackpot"
            else f"and won 🪙 {format_cash(winnings)}  ({multiplier}x)"
        )

        await msg.edit(content=build_slots(result[0], result[1], result[2], name, amount, footer))
        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Slots(bot))
    
