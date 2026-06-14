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
from utils.stats import (
    add_stats,
    update_biggest_win,
    record_win,
    record_loss
)
from utils.achievement_checker import check_achievements


# ─────────────────────────
# PLINKO CONFIG
# ─────────────────────────

# 8 rows of pegs → 9 slots at the bottom
ROWS = 8

# Multipliers for each slot (index 0 = leftmost, 8 = rightmost)
# Outer slots = high risk/reward, middle = low
MULTIPLIERS = {
    "low":  [1.5, 1.2, 1.1, 0.5, 0.3, 0.5, 1.1, 1.2, 1.5],
    "mid":  [5.0, 2.0, 1.5, 1.0, 0.5, 1.0, 1.5, 2.0, 5.0],
    "high": [29.0, 4.0, 3.0, 2.0, 0.2, 2.0, 3.0, 4.0, 29.0],
}

RISK_COLORS = {"low": "🟢", "mid": "🟡", "high": "🔴"}

SLOT_EMOJIS = ["🟦", "🟦", "🟦", "🟩", "🟥", "🟩", "🟦", "🟦", "🟦"]


def simulate_plinko(rows=ROWS):
    """Simulate the ball falling. Returns final slot index (0–8)."""
    pos = 0
    for _ in range(rows):
        pos += random.randint(0, 1)
    return pos  # 0-8


def build_plinko_visual(slot, rows=ROWS):
    """Build a visual ASCII-art plinko board."""
    lines = []
    width = rows + 1  # 9 slots

    # Pegs
    for row in range(1, rows + 1):
        pegs = row + 1
        pad = " " * ((rows - row) // 1)
        line = pad + " ".join(["·"] * pegs)
        lines.append(line)

    # Bottom slots
    slot_line = "  ".join(
        f"[{i}]" if i == slot else f" {i} "
        for i in range(width)
    )
    lines.append("")
    lines.append(slot_line)
    return "\n".join(lines)


class Plinko(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["pl"])
    async def plinko(self, ctx, risk: str = None, amount: str = None):
        """Drop the ball down the peg board and land in a multiplier slot!"""

        if risk is None or amount is None:
            embed = discord.Embed(
                title="🎰 Plinko",
                description=(
                    "**How to play:**\n\n"
                    "Drop a ball through **8 rows** of pegs.\n"
                    "It lands in one of 9 slots — each with a different multiplier.\n\n"
                    "Choose a **risk level** to set the multiplier spread:\n\n"
                    "🟢 **Low** — safe middle slots, moderate edges\n"
                    "`0.3× — 0.5× — 1.1× — 1.2× — 1.5×`\n\n"
                    "🟡 **Mid** — balanced risk\n"
                    "`0.5× — 1.0× — 1.5× — 2.0× — 5.0×`\n\n"
                    "🔴 **High** — small chance of massive wins\n"
                    "`0.2× — 2.0× — 3.0× — 4.0× — 29.0×`\n\n"
                    "Usage: `.plinko <low/mid/high> <amount>` or `.pl <risk> <amount>`"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
            return

        risk = risk.lower()
        if risk not in MULTIPLIERS:
            await ctx.send(embed=discord.Embed(
                description="❌ Risk must be `low`, `mid`, or `high`.",
                color=0xED4245
            ))
            return

        cash = get_cash(ctx.author.id)
        bet = parse_amount(amount, cash)

        if bet is None or bet <= 0:
            await ctx.send(embed=discord.Embed(description="❌ Invalid amount.", color=0xED4245))
            return
        if cash < bet:
            await ctx.send(embed=discord.Embed(description="❌ Not enough cash.", color=0xED4245))
            return

        remove_cash(ctx.author.id, bet)
        add_stats(ctx.author.id, games_played=1, total_gambled=bet)

        mults = MULTIPLIERS[risk]
        risk_emoji = RISK_COLORS[risk]

        # Simulate drop
        slot = simulate_plinko()
        mult = mults[slot]

        # Animation — show ball "falling" step by step
        embed = discord.Embed(
            title=f"🎰 Plinko — {risk_emoji} {risk.upper()} Risk",
            description="🔵 Dropping the ball...",
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(0.5)
        bounce_msgs = ["🔵 Bouncing... ⬇️", "🔵 Still going...", "🔵 Almost there..."]
        for bm in bounce_msgs:
            embed.description = bm
            await msg.edit(embed=embed)
            await asyncio.sleep(0.6)

        # Result
        payout = int(bet * mult)
        profit = payout - bet

        if mult >= 1.0:
            add_cash(ctx.author.id, payout)
            if profit > 0:
                update_biggest_win(ctx.author.id, profit)
                record_win(ctx.author.id, profit)
            color = 0x57F287 if profit > 0 else 0xFEE75C
            title = f"🎰 Plinko — {'WIN! 🎉' if profit > 0 else 'Even'}"
        else:
            add_cash(ctx.author.id, payout)
            record_loss(ctx.author.id, bet - payout)
            color = 0xED4245
            title = "🎰 Plinko — LOSE"

        # Build slot row display
        slot_display = "  ".join(
            f"**[{mults[i]}×]**" if i == slot else f"{mults[i]}×"
            for i in range(len(mults))
        )

        embed = discord.Embed(title=title, color=color)
        embed.add_field(
            name="Slots",
            value=slot_display,
            inline=False
        )
        embed.add_field(
            name="Result",
            value=(
                f"🎯 Landed on slot **{slot}** → **{mult}×**\n"
                f"💰 Payout: **{format_cash(payout)}** "
                f"({'**+**' if profit >= 0 else ''}**{format_cash(abs(profit))}**)"
            ),
            inline=False
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)} | Risk: {risk.upper()}")
        await msg.edit(embed=embed)
        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Plinko(bot))
