from discord.ext import commands
import discord
import random
import asyncio

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    parse_amount
)
from utils.stats import (
    record_win,
    record_loss,
    add_stats,
    update_biggest_win
)
from utils.achievement_checker import check_achievements


# ─────────────────────────
# DIE FACES
# ─────────────────────────

DIE_FACES = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
DIE_SPIN  = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


def build_dice_display(d1, d2, total=None):
    if total is not None:
        return f"## {d1}  {d2}\n**Total: {total}**"
    return f"## {d1}  {d2}"


class Dice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dice")
    async def dice(self, ctx, side: str = None, amount: str = None):

        if side is None or side.lower() not in ["down", "7", "up"]:
            embed = discord.Embed(
                title="🎲 DICE",
                description=(
                    "**How to play:**\n\n"
                    "`.dice down amount` — Win on **2–6** (×2)\n"
                    "`.dice 7 amount`   — Win on **exactly 7** (×5)\n"
                    "`.dice up amount`  — Win on **8–12** (×2)\n\n"
                    "*Two dice, 2d6 total. Beat the odds.*"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
            return

        side = side.lower()

        if amount is None:
            await ctx.send(embed=discord.Embed(
                description="❌ Enter a bet amount.",
                color=0xED4245
            ))
            return

        cash = get_cash(ctx.author.id)
        amount = parse_amount(amount, cash)

        if amount is None or amount <= 0:
            await ctx.send(embed=discord.Embed(
                description="❌ Invalid amount.",
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

        # ─── ROLL DICE ───
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        # ─── WIN CHECK ───
        won = False
        multiplier = 0

        if side == "down" and 2 <= total <= 6:
            won = True
            multiplier = 2
        elif side == "7" and total == 7:
            won = True
            multiplier = 5
        elif side == "up" and 8 <= total <= 12:
            won = True
            multiplier = 2

        # ─── ANIMATION START ───
        side_display = side.upper() if side == "7" else side.capitalize()
        d_spin = random.choice(DIE_SPIN)

        embed = discord.Embed(
            title="🎲 DICE",
            description=build_dice_display("❓", "❓"),
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(amount)}  •  Betting: {side_display}")
        msg = await ctx.send(embed=embed)

        # ─── ROLLING FRAMES ───
        for _ in range(5):
            r1 = random.choice(DIE_SPIN)
            r2 = random.choice(DIE_SPIN)
            embed.description = build_dice_display(r1, r2)
            try:
                await msg.edit(embed=embed)
            except:
                pass
            await asyncio.sleep(0.12)

        # ─── LOCK DIE 1 ───
        await asyncio.sleep(0.05)
        for _ in range(3):
            r2 = random.choice(DIE_SPIN)
            embed.description = build_dice_display(DIE_FACES[dice1], r2)
            try:
                await msg.edit(embed=embed)
            except:
                pass
            await asyncio.sleep(0.14)

        # ─── LOCK DIE 2 ───
        await asyncio.sleep(0.2)
        embed.description = build_dice_display(DIE_FACES[dice1], DIE_FACES[dice2], total)
        embed.color = 0x57F287 if won else 0xED4245
        try:
            await msg.edit(embed=embed)
        except:
            pass
        await asyncio.sleep(0.4)

        # ─── FINAL RESULT ───
        if won:
            winnings = amount * multiplier
            profit   = winnings - amount

            add_cash(ctx.author.id, winnings)
            record_win(ctx.author.id, winnings)
            update_biggest_win(ctx.author.id, winnings)

            embed = discord.Embed(
                title="🎲 DICE — YOU WIN!",
                color=0x57F287
            )
            embed.description = build_dice_display(
                DIE_FACES[dice1], DIE_FACES[dice2], total
            )
            embed.add_field(name="🎯 Bet",          value=f"**{side_display}**",         inline=True)
            embed.add_field(name="🏆 Won",           value=f"**{format_cash(winnings)}**", inline=True)
            embed.add_field(name="📈 Profit",        value=f"**{format_cash(profit)}**",   inline=True)
            embed.add_field(name="🎯 Multiplier",    value=f"**{multiplier}x**",           inline=True)
            embed.set_footer(text=f"Bet: {format_cash(amount)}")

        else:
            embed = discord.Embed(
                title="🎲 DICE — YOU LOSE",
                color=0xED4245
            )
            embed.description = build_dice_display(
                DIE_FACES[dice1], DIE_FACES[dice2], total
            )
            embed.add_field(name="🎯 Bet",    value=f"**{side_display}**",       inline=True)
            embed.add_field(name="💸 Lost",   value=f"**{format_cash(amount)}**", inline=True)
            embed.set_footer(text=f"Bet: {format_cash(amount)}")

            record_loss(ctx.author.id, amount)

        await msg.edit(embed=embed)
        await check_achievements(self.bot, ctx.author)


async def setup(bot):
    await bot.add_cog(Dice(bot))
            
