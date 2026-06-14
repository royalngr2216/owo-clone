from discord.ext import commands
import discord
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
import random


# ─────────────────────────
# CONFIG
# ─────────────────────────

MAX_NUMBER = 100
MAX_GUESSES = 7

# Multiplier based on guesses remaining when correct
# Guess on first try = massive payout; last guess = small payout
MULT_BY_GUESSES_LEFT = {
    7: 15.0,   # first guess
    6: 8.0,
    5: 4.0,
    4: 2.5,
    3: 1.75,
    2: 1.3,
    1: 1.1,
}

# ─────────────────────────
# ACTIVE GAMES
# ─────────────────────────

guess_games = {}


class GuessNumber(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["gn", "guess"])
    async def guessnumber(self, ctx, amount: str = None):
        """Guess a number 1–100 in 7 tries. Fewer guesses = bigger payout!"""

        if ctx.author.id in guess_games:
            await ctx.send(embed=discord.Embed(
                description="❌ You already have a game! Finish it first.",
                color=0xED4245
            ))
            return

        if amount is None:
            embed = discord.Embed(
                title="🔢 Guess the Number",
                description=(
                    "**How to play:**\n\n"
                    "Guess a secret number between **1 and 100** in **7 tries**.\n"
                    "You'll get hints after each guess (**too high / too low**).\n\n"
                    "**Multipliers by guesses left when you win:**\n"
                    "```\n"
                    "1st guess  → 15×  🏆\n"
                    "2nd guess  →  8×\n"
                    "3rd guess  →  4×\n"
                    "4th guess  →  2.5×\n"
                    "5th guess  →  1.75×\n"
                    "6th guess  →  1.3×\n"
                    "7th guess  →  1.1×\n"
                    "```\n\n"
                    "Usage: `.guessnumber <amount>` or `.guess <amount>`"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
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

        secret = random.randint(1, MAX_NUMBER)
        guess_games[ctx.author.id] = {
            "bet": bet,
            "secret": secret,
            "guesses_left": MAX_GUESSES,
            "history": [],
            "channel_id": ctx.channel.id,
        }

        embed = discord.Embed(
            title="🔢 Guess the Number",
            description=(
                f"I'm thinking of a number between **1** and **{MAX_NUMBER}**.\n"
                f"You have **{MAX_GUESSES} guesses**.\n\n"
                f"**Type your guess in this channel!**\n"
                f"Type `quit` to give up and lose your bet."
            ),
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        await ctx.send(embed=embed)

        # Wait for guesses
        def check(m):
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and (m.content.isdigit() or m.content.lower() == "quit")
            )

        while True:
            g = guess_games.get(ctx.author.id)
            if not g:
                return

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                del guess_games[ctx.author.id]
                record_loss(ctx.author.id, g["bet"])
                await ctx.send(embed=discord.Embed(
                    description=f"⏰ Time's up! The number was **{g['secret']}**. Lost **{format_cash(g['bet'])}**.",
                    color=0xED4245
                ))
                return

            content = msg.content.lower()

            if content == "quit":
                del guess_games[ctx.author.id]
                record_loss(ctx.author.id, g["bet"])
                await ctx.send(embed=discord.Embed(
                    description=f"🏳️ You gave up! The number was **{g['secret']}**. Lost **{format_cash(g['bet'])}**.",
                    color=0xED4245
                ))
                return

            guess = int(msg.content)
            if guess < 1 or guess > MAX_NUMBER:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Guess must be between **1** and **{MAX_NUMBER}**.",
                    color=0xED4245
                ), delete_after=5)
                continue

            g["guesses_left"] -= 1
            g["history"].append(guess)
            history_str = " | ".join(str(h) for h in g["history"])

            if guess == g["secret"]:
                # WIN
                guesses_left = g["guesses_left"]  # remaining after this guess
                mult = MULT_BY_GUESSES_LEFT.get(guesses_left + 1, 1.1)
                # guesses_left + 1 because we decremented before checking
                guesses_used = MAX_GUESSES - guesses_left
                mult = MULT_BY_GUESSES_LEFT.get(MAX_GUESSES - guesses_left, 1.1)

                payout = int(g["bet"] * mult)
                profit = payout - g["bet"]
                add_cash(ctx.author.id, payout)
                update_biggest_win(ctx.author.id, profit)
                record_win(ctx.author.id, profit)
                del guess_games[ctx.author.id]

                embed = discord.Embed(
                    title="🔢 Guess the Number — CORRECT! 🎉",
                    description=(
                        f"The number was **{g['secret']}**!\n"
                        f"You got it in **{guesses_used}** guess(es)!\n\n"
                        f"Multiplier: **{mult}×**\n"
                        f"💰 Won: **{format_cash(profit)}**!"
                    ),
                    color=0x57F287
                )
                embed.set_footer(text=f"Guesses: {history_str}")
                await ctx.send(embed=embed)
                await check_achievements(self.bot, ctx.author)
                return

            elif g["guesses_left"] == 0:
                # Out of guesses
                del guess_games[ctx.author.id]
                record_loss(ctx.author.id, g["bet"])
                embed = discord.Embed(
                    title="🔢 Guess the Number — OUT OF GUESSES!",
                    description=(
                        f"The number was **{g['secret']}**!\n"
                        f"❌ Lost **{format_cash(g['bet'])}**"
                    ),
                    color=0xED4245
                )
                embed.set_footer(text=f"Your guesses: {history_str}")
                await ctx.send(embed=embed)
                await check_achievements(self.bot, ctx.author)
                return

            else:
                # Hint
                direction = "📈 Too **low**!" if guess < g["secret"] else "📉 Too **high**!"
                guesses_left = g["guesses_left"]
                embed = discord.Embed(
                    description=(
                        f"{direction} You guessed **{guess}**.\n"
                        f"Guesses left: **{guesses_left}**\n"
                        f"History: `{history_str}`"
                    ),
                    color=0xFEE75C
                )
                await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GuessNumber(bot))
