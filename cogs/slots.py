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
from utils.slot_render import (
    build_spin_gif,
    build_result_frame
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
# CONFIG
# ─────────────────────────

PAYOUTS = {
    "🍒": 1.1,
    "🍋": 1.4,
    "🍀": 2.0,
    "🔔": 3.5,
    "💎": 4.0,
    "👑": 7.0,
}

# REBALANCED ECONOMY:
# Old table paid out 124% of every bet on average (positive EV, no house
# edge), which let a single player mint unlimited money by going all-in
# repeatedly. This table pays out ~87% on average (a normal casino-style
# house edge) so the house wins over time instead of bleeding money.
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

MAX_BET = 5_000_000

# Embed colors per state
COLOR_SPIN    = 0x5865F2   # blurple — spinning
COLOR_WIN     = 0x57F287   # green   — won
COLOR_JACKPOT = 0xF1C40F   # gold    — jackpot
COLOR_LOSE    = 0xED4245   # red     — lost
COLOR_TROLL   = 0x36393F   # dark    — troll


# ─────────────────────────
# BUILD EMBED
# ─────────────────────────

def build_embed(
    author: discord.Member,
    bet: int,
    *,
    color: int = COLOR_SPIN,
    result_line: str = "",
    image_filename: str = "spin.gif",
) -> discord.Embed:
    """
    Single embed used for every state (spinning + final result).
    The reels themselves are the attached image now, not text.
    """
    embed = discord.Embed(
        title="🎰  S L O T S",
        color=color,
    )

    embed.add_field(name="Bet", value=f"🪙 **{format_cash(bet)}**", inline=True)

    if result_line:
        embed.add_field(name="Result", value=result_line, inline=True)
    else:
        embed.add_field(name="Result", value="*Spinning…*", inline=True)

    embed.set_image(url=f"attachment://{image_filename}")

    embed.set_footer(
        text=author.display_name,
        icon_url=author.display_avatar.url,
    )

    return embed


class Slots(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="slots", aliases=["slot", "s"])
    async def slots(self, ctx, amount: str = None):

        create_account(ctx.author.id)

        # ── No argument ──────────────────────────────────────────────────
        if amount is None:
            embed = discord.Embed(
                title="🎰 Slots",
                description=(
                    "You need to enter a bet amount.\n\n"
                    "**Usage:** `.slots <amount>`\n"
                    "**Example:** `.slots 100k`  •  `.slots all`"
                ),
                color=COLOR_LOSE,
            )
            await ctx.send(embed=embed)
            return

        # ── Parse bet ────────────────────────────────────────────────────
        cash = get_cash(ctx.author.id)

        if amount.lower() == "all":
            amount = cash
        else:
            amount = parse_amount(amount)
            if amount is None:
                await ctx.send(
                    embed=discord.Embed(
                        title="🎰 Slots",
                        description="❌ That's not a valid amount.",
                        color=COLOR_LOSE,
                    )
                )
                return

        if amount <= 0:
            await ctx.send(
                embed=discord.Embed(
                    title="🎰 Slots",
                    description="❌ Bet must be greater than 0.",
                    color=COLOR_LOSE,
                )
            )
            return

        if cash < amount:
            await ctx.send(
                embed=discord.Embed(
                    title="🎰 Slots",
                    description=f"❌ You only have 🪙 **{format_cash(cash)}** — not enough to bet that.",
                    color=COLOR_LOSE,
                )
            )
            return

        if amount > MAX_BET:
            await ctx.send(
                embed=discord.Embed(
                    title="🎰 Slots",
                    description=f"❌ Max bet is 🪙 **{format_cash(MAX_BET)}**.",
                    color=COLOR_LOSE,
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
                ["👑", "👑", "🍒"],   # near-miss
                ["💎", "💎", "🍋"],   # near-miss
            ]
            result = random.choice(lose_patterns)

        near_miss = (result[0] == result[1]) and (outcome == "lose")

        # ── ANIMATION ────────────────────────────────────────────────────
        #
        # One smooth Pillow-rendered GIF (eased deceleration + motion
        # blur per reel, staggered stop times) instead of 3 discrete
        # message edits swapping emoji text. Built off the event loop
        # via to_thread since Pillow rendering is CPU-bound.

        gif_buf, duration = await asyncio.to_thread(build_spin_gif, result, near_miss)

        embed = build_embed(ctx.author, amount, image_filename="spin.gif")
        msg = await ctx.send(embed=embed, file=discord.File(gif_buf, filename="spin.gif"))

        await asyncio.sleep(duration)

        # ── Final result render ─────────────────────────────────────────

        # TROLL
        if outcome == "troll":
            png_buf = await asyncio.to_thread(build_result_frame, result, win=False)
            embed = build_embed(
                ctx.author, amount,
                color=COLOR_TROLL,
                result_line=f"☠️ EMIEL entered the casino and <a:sex:1514766414248939610> you.\n💸 Lost **{format_cash(amount)}**",
                image_filename="result.png",
            )
            await msg.edit(embed=embed, attachments=[discord.File(png_buf, filename="result.png")])
            return

        # LOSE
        if outcome == "lose":
            png_buf = await asyncio.to_thread(build_result_frame, result, win=False)
            result_line = (
                f"<:komedi:1482793353748680956> **So close!**\n-🪙 {format_cash(amount)}"
                if near_miss
                else f"<:bj:1492588515253551144> Better luck next time!\n"
            )
            embed = build_embed(
                ctx.author, amount,
                color=COLOR_LOSE,
                result_line=result_line,
                image_filename="result.png",
            )
            await msg.edit(embed=embed, attachments=[discord.File(png_buf, filename="result.png")])
            return

        # WIN
        symbol     = result[0]
        multiplier = PAYOUTS[symbol]
        winnings   = int(amount * multiplier)
        profit     = winnings - amount

        add_cash(ctx.author.id, winnings)
        update_biggest_win(ctx.author.id, winnings)

        jackpot = outcome == "jackpot"
        png_buf = await asyncio.to_thread(build_result_frame, result, win=True, jackpot=jackpot)

        if jackpot:
            result_line = (
                f"<:3845happycat:1072237341357387786> **JACKPOT!** `{multiplier}x`\n"
                f"+🪙 {format_cash(profit)}"
            )
            color = COLOR_JACKPOT
        else:
            result_line = (
                f"<:Pray:1509654308705145033> **You won!** `{multiplier}x`\n"
                f"+🪙 {format_cash(profit)}"
            )
            color = COLOR_WIN

        embed = build_embed(
            ctx.author, amount,
            color=color,
            result_line=result_line,
            image_filename="result.png",
        )
        await msg.edit(embed=embed, attachments=[discord.File(png_buf, filename="result.png")])
        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Slots(bot))
