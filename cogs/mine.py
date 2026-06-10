from discord.ext import commands
import discord
import random
from datetime import datetime
import pytz

from utils.economy import (
    economy_collection,
    add_cash,
    remove_cash,
    format_cash,
    create_account,
    get_cash
)


IST = pytz.timezone("Asia/Kolkata")

MINE_COOLDOWN = 10800

MINE_REWARD = 150000


# ─────────────────────────
# ORES
# ─────────────────────────

ORES = {

    "stone": {
        "emoji": "🪨",
        "chance": 35
    },

    "iron": {
        "emoji": "🔩",
        "chance": 25
    },

    "gold": {
        "emoji": "⚜️",
        "chance": 18
    },

    "diamond": {
        "emoji": "💎",
        "chance": 10
    },

    "emerald": {
        "emoji": "🔮",
        "chance": 7
    },

    "ruby": {
        "emoji": ♦️",
        "chance": 4
    },

    "void_crystal": {
        "emoji": "🌌",
        "chance": 1
    }
}


class Mine(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="mine")
    async def mine(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        # ─────────────────────────
        # SHOVEL CHECK
        # ─────────────────────────

        if not user_data.get("shovel", False):

            embed = discord.Embed(

                description=(

                    "❌ You need a **Shovel** "
                    "to use `.mine`\n\n"

                    "Buy one from `.shop`"

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # COOLDOWN
        # ─────────────────────────

        last_mine = user_data.get(
            "last_mine",
            0
        )


        current_time = int(
            datetime.now(IST).timestamp()
        )


        if current_time - last_mine < MINE_COOLDOWN:

            remaining = (

                MINE_COOLDOWN -

                (current_time - last_mine)

            )


            next_time = current_time + remaining


            embed = discord.Embed(

                description=(

                    "❌ Mining cooldown active.\n\n"

                    f"⏰ Try again <t:{next_time}:R>"

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # SAVE COOLDOWN
        # ─────────────────────────

        economy_collection.update_one(

            {
                "user_id": str(ctx.author.id)
            },

            {
                "$set": {
                    "last_mine": current_time
                }
            }
        )


        # ─────────────────────────
        # RISK EVENTS
        # ─────────────────────────

        risk_roll = random.randint(1, 100)


        # ─────────────────────────
        # CAVE COLLAPSE
        # ─────────────────────────

        if risk_roll <= 5:

            loss = random.randint(
                50000,
                150000
            )

            cash = get_cash(ctx.author.id)

            if loss > cash:

                loss = cash


            remove_cash(
                ctx.author.id,
                loss
            )


            embed = discord.Embed(

                title="⛰ CAVE COLLAPSE",

                description=(

                    "The mine suddenly collapsed on top of you.\n\n"

                    "You escaped alive but dropped\n"
                    f"**{format_cash(loss)}** "
                    "while running away."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # LAVA DISASTER
        # ─────────────────────────

        if risk_roll <= 10:

            add_cash(
                ctx.author.id,
                MINE_REWARD
            )


            embed = discord.Embed(

                title="🌋 LAVA DISASTER",

                description=(

                    "You finally found valuable ore...\n\n"

                    "but lava instantly swallowed it.\n\n"

                    "You Escaped with Cash tho survived.\n\n"

                    f"💰 Earned:\n"
                    f"**{format_cash(MINE_REWARD)}**"

                ),

                color=0xE67E22
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # ANCIENT MINER
        # ─────────────────────────

        if risk_roll <= 15:

            embed = discord.Embed(

                title="👴 ANCIENT MINER",

                description=(

                    "An ancient ngr appeared from the shadows.\n\n"

                    "He said:\n"
                    "\"These mines belong to me.\"\n\n"

                    "Then took everything and vanished."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # GIVE MONEY
        # ─────────────────────────

        add_cash(
            ctx.author.id,
            MINE_REWARD
        )


        # ─────────────────────────
        # DETERMINE ORE
        # ─────────────────────────

        roll = random.randint(1, 100)

        current = 0

        selected_ore = "stone"


        for ore, data in ORES.items():

            current += data["chance"]

            if roll <= current:

                selected_ore = ore

                break


        ore_data = ORES[selected_ore]


        # ─────────────────────────
        # INVENTORY
        # ─────────────────────────

        inventory = user_data.get(
            "inventory",
            {}
        )


        inventory[selected_ore] = (

            inventory.get(selected_ore, 0) + 1

        )


        economy_collection.update_one(

            {
                "user_id": str(ctx.author.id)
            },

            {
                "$set": {
                    "inventory": inventory
                }
            }
        )


        # ─────────────────────────
        # SUCCESS EMBED
        # ─────────────────────────

        embed = discord.Embed(

            title="⛏ MINING SUCCESS",

            description=(

                "You mined deep underground.\n\n"

                f"💰 Earned:\n"
                f"**{format_cash(MINE_REWARD)}**\n\n"

                f"📦 Found Ore:\n"
                f"{ore_data['emoji']} "
                f"**{selected_ore.replace('_', ' ').title()}**"

            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Mine(bot)
      )
