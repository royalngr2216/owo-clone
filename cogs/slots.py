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


# ─────────────────────────
# PARSE MONEY
# ─────────────────────────

def parse_amount(amount):

    amount = amount.lower()

    multipliers = {

        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000
    }

    try:

        if amount[-1] in multipliers:

            return int(
                float(amount[:-1])
                * multipliers[amount[-1]]
            )

        return int(amount)

    except:

        return None


# ─────────────────────────
# SYMBOLS
# ─────────────────────────

SYMBOLS = [
    "🍒",
    "🍋",
    "🍀",
    "🔔",
    "💎",
    "👑",
    "💀"
]


# ─────────────────────────
# OUTCOME CHANCES
# ─────────────────────────

OUTCOMES = {

    "lose": 50,

    "cherry": 22,

    "lemon": 11,

    "clover": 4,

    "bell": 3,

    "diamond": 2,

    "jackpot": 3,

    "troll": 5
}


# ─────────────────────────
# PAYOUTS
# ─────────────────────────

PAYOUTS = {

    "🍒": 1.5,
    "🍋": 2,
    "🍀": 3,
    "🔔": 5,
    "💎": 6,
    "👑": 10
}


# ─────────────────────────
# BUILD SLOT UI
# ─────────────────────────

def build_slots(top, middle, bottom):

    return (

        "╔════════════════════╗\n"
        "║   🎰 ECHLEON SLOTS   ║\n"
        "╚════════════════════╝\n\n"

        "┌─────┬─────┬─────┐\n"

        f"│  {top[0]}  │  {top[1]}  │  {top[2]}  │\n"
        f"│  {middle[0]}  │  {middle[1]}  │  {middle[2]}  │\n"
        f"│  {bottom[0]}  │  {bottom[1]}  │  {bottom[2]}  │\n"

        "└─────┴─────┴─────┘"

    )


class Slots(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="slots")
    async def slots(
        self,
        ctx,
        amount: str = None
    ):

        create_account(ctx.author.id)

        # ─────────────────────────
        # NO AMOUNT
        # ─────────────────────────

        if amount is None:

            embed = discord.Embed(

                description=(

                    "❌ Enter a bet amount.\n\n"

                    "Example:\n"
                    "`.slots 100k`"

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # PARSE BET
        # ─────────────────────────

        cash = get_cash(ctx.author.id)


        if amount.lower() == "all":

            amount = cash

        else:

            amount = parse_amount(amount)

            if amount is None:

                embed = discord.Embed(

                    description="❌ Invalid amount.",

                    color=0xED4245
                )

                await ctx.send(embed=embed)

                return


        if amount <= 0:

            embed = discord.Embed(

                description="❌ Bet must be above 0.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        if cash < amount:

            embed = discord.Embed(

                description="❌ You don't have enough cash.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # REMOVE BET
        # ─────────────────────────

        remove_cash(
            ctx.author.id,
            amount
        )


        # ─────────────────────────
        # DETERMINE OUTCOME
        # ─────────────────────────

        roll = random.randint(1, 100)

        current = 0

        outcome = "lose"


        for name, chance in OUTCOMES.items():

            current += chance

            if roll <= current:

                outcome = name

                break


        # ─────────────────────────
        # FINAL RESULTS
        # ─────────────────────────

        if outcome == "cherry":

            result = ["🍒", "🍒", "🍒"]

        elif outcome == "lemon":

            result = ["🍋", "🍋", "🍋"]

        elif outcome == "clover":

            result = ["🍀", "🍀", "🍀"]

        elif outcome == "bell":

            result = ["🔔", "🔔", "🔔"]

        elif outcome == "diamond":

            result = ["💎", "💎", "💎"]

        elif outcome == "jackpot":

            result = ["👑", "👑", "👑"]

        elif outcome == "troll":

            result = ["💀", "💀", "💀"]

        else:

            lose_patterns = [

                ["🍒", "💎", "🍋"],
                ["👑", "🍀", "🍒"],
                ["💀", "🍋", "💎"],
                ["🔔", "🍒", "💀"],
                ["💎", "🍋", "🍀"],
                ["👑", "💀", "🍒"],

                ["👑", "👑", "🍒"],
                ["💎", "💎", "🍋"]
            ]

            result = random.choice(
                lose_patterns
            )


        # ─────────────────────────
        # START EMBED
        # ─────────────────────────

        embed = discord.Embed(

            color=0x5865F2
        )

        embed.description = build_slots(

            ["❔", "❔", "❔"],
            ["❔", "❔", "❔"],
            ["❔", "❔", "❔"]

        )

        embed.set_footer(
            text=f"Bet: {format_cash(amount)}"
        )

        msg = await ctx.send(embed=embed)


        # ─────────────────────────
        # SPIN REELS
        # ─────────────────────────

        reels = ["❔", "❔", "❔"]


        for reel_index in range(3):

            start = asyncio.get_event_loop().time()

            duration = 0.7

            # suspense if first 2 match

            if reel_index == 2:

                if result[0] == result[1]:

                    duration = 1.2


            while asyncio.get_event_loop().time() - start < duration:

                reels[reel_index] = random.choice(
                    SYMBOLS
                )

                top = [

                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS)
                ]

                bottom = [

                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS)
                ]

                embed.description = build_slots(

                    top,
                    reels,
                    bottom
                )

                await msg.edit(embed=embed)

                await asyncio.sleep(0.05)


            reels[reel_index] = result[reel_index]

            top = [

                random.choice(SYMBOLS),
                random.choice(SYMBOLS),
                random.choice(SYMBOLS)
            ]

            bottom = [

                random.choice(SYMBOLS),
                random.choice(SYMBOLS),
                random.choice(SYMBOLS)
            ]

            embed.description = build_slots(

                top,
                reels,
                bottom
            )

            await msg.edit(embed=embed)

            await asyncio.sleep(0.2)


        # ─────────────────────────
        # FINAL RESULT
        # ─────────────────────────

        embed = discord.Embed(

            color=0x5865F2
        )

        final_ui = build_slots(

            [random.choice(SYMBOLS) for _ in range(3)],
            result,
            [random.choice(SYMBOLS) for _ in range(3)]

        )


        # ─────────────────────────
        # TROLL
        # ─────────────────────────

        if outcome == "troll":

            embed.description = (

                final_ui +

                "\n\n☠ **EMIEL entered the casino and 🍇 you.**\n"

                f"💸 Lost **{format_cash(amount)}**"
            )

            embed.color = 0xED4245

            await msg.edit(embed=embed)

            return


        # ─────────────────────────
        # LOSE
        # ─────────────────────────

        if outcome == "lose":

            embed.description = (

                final_ui +

                f"\n\n❌ Lost **{format_cash(amount)}**"
            )

            embed.color = 0xED4245

            await msg.edit(embed=embed)

            return


        # ─────────────────────────
        # WIN
        # ─────────────────────────

        symbol = result[0]

        multiplier = PAYOUTS[symbol]

        winnings = int(amount * multiplier)

        profit = winnings - amount


        add_cash(
            ctx.author.id,
            winnings
        )


        embed.description = (

            final_ui +

            f"\n\n🏆 Won **{format_cash(winnings)}**\n"
            f"📈 Profit: **{format_cash(profit)}**\n"
            f"🎯 Multiplier: **{multiplier}x**"
        )


        if outcome == "jackpot":

            embed.color = 0xF1C40F

            embed.description += (

                "\n\n✨ 👑 JACKPOT WIN 👑 ✨"
            )

        else:

            embed.color = 0x57F287


        await msg.edit(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Slots(bot)
        )
