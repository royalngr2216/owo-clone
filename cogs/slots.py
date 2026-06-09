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

    "lose": 49,

    "cherry": 20,

    "lemon": 12,

    "clover": 6,

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
# SLOTS COG
# ─────────────────────────

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
                    "`.slots 100000`"

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

            try:

                amount = int(amount)

            except:

                embed = discord.Embed(

                    description="❌ Invalid amount.",

                    color=0xED4245
                )

                await ctx.send(embed=embed)

                return


        # ─────────────────────────
        # INVALID BET
        # ─────────────────────────

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
        # GENERATE FINAL SYMBOLS
        # ─────────────────────────

        if outcome == "cherry":

            final_slots = ["🍒", "🍒", "🍒"]

        elif outcome == "lemon":

            final_slots = ["🍋", "🍋", "🍋"]

        elif outcome == "clover":

            final_slots = ["🍀", "🍀", "🍀"]

        elif outcome == "bell":

            final_slots = ["🔔", "🔔", "🔔"]

        elif outcome == "diamond":

            final_slots = ["💎", "💎", "💎"]

        elif outcome == "jackpot":

            final_slots = ["👑", "👑", "👑"]

        elif outcome == "troll":

            final_slots = ["💀", "💀", "💀"]

        else:

            while True:

                final_slots = [

                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS),
                    random.choice(SYMBOLS)
                ]

                if len(set(final_slots)) != 1:

                    break


        # ─────────────────────────
        # START ANIMATION
        # ─────────────────────────

        embed = discord.Embed(

            title="🎰 ECHLEON SLOTS",

            description=(

                "🎲 Rolling...\n\n"

                "❔ ❔ ❔"

            ),

            color=0x5865F2
        )

        msg = await ctx.send(embed=embed)


        # ─────────────────────────
        # REEL 1
        # ─────────────────────────

        for _ in range(3):

            embed.description = (

                "🎲 Rolling...\n\n"

                f"{random.choice(SYMBOLS)} ❔ ❔"
            )

            await msg.edit(embed=embed)

            await asyncio.sleep(0.3)


        reel1 = final_slots[0]

        embed.description = (

            "🎲 Rolling...\n\n"

            f"{reel1} ❔ ❔"
        )

        await msg.edit(embed=embed)

        await asyncio.sleep(0.5)


        # ─────────────────────────
        # REEL 2
        # ─────────────────────────

        for _ in range(3):

            embed.description = (

                "🎲 Rolling...\n\n"

                f"{reel1} {random.choice(SYMBOLS)} ❔"
            )

            await msg.edit(embed=embed)

            await asyncio.sleep(0.3)


        reel2 = final_slots[1]

        embed.description = (

            "🎲 Rolling...\n\n"

            f"{reel1} {reel2} ❔"
        )

        await msg.edit(embed=embed)

        await asyncio.sleep(0.5)


        # ─────────────────────────
        # REEL 3
        # ─────────────────────────

        for _ in range(3):

            embed.description = (

                "🎲 Rolling...\n\n"

                f"{reel1} {reel2} {random.choice(SYMBOLS)}"
            )

            await msg.edit(embed=embed)

            await asyncio.sleep(0.3)


        reel3 = final_slots[2]


        # ─────────────────────────
        # FINAL RESULT
        # ─────────────────────────

        embed = discord.Embed(

            title="🎰 ECHLEON SLOTS",

            color=0x5865F2
        )


        # ─────────────────────────
        # TROLL
        # ─────────────────────────

        if outcome == "troll":

            embed.description = (

                f"{reel1} {reel2} {reel3}\n\n"

                "☠ EMIEL came and 🍇 you "
                "in the slot machine.\n\n"

                f"💸 Lost **{format_cash(amount)}**"
            )

            await msg.edit(embed=embed)

            return


        # ─────────────────────────
        # LOSE
        # ─────────────────────────

        if outcome == "lose":

            embed.description = (

                f"{reel1} {reel2} {reel3}\n\n"

                f"❌ Lost **{format_cash(amount)}**"
            )

            await msg.edit(embed=embed)

            return


        # ─────────────────────────
        # WIN
        # ─────────────────────────

        symbol = reel1

        multiplier = PAYOUTS[symbol]

        winnings = int(amount * multiplier)

        profit = winnings - amount


        add_cash(
            ctx.author.id,
            winnings
        )


        embed.description = (

            f"{reel1} {reel2} {reel3}\n\n"

            f"🏆 Won **{format_cash(winnings)}**\n"

            f"📈 Profit: **{format_cash(profit)}**\n\n"

            f"🎯 Multiplier: **{multiplier}x**"
        )


        if outcome == "jackpot":

            embed.color = 0xF1C40F

            embed.description += (

                "\n\n👑 JACKPOT WIN 👑"
            )


        await msg.edit(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Slots(bot)
      )
