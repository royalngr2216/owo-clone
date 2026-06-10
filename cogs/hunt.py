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
from utils.stats import (
    add_stats,
    update_biggest_win
)
from utils.achievement_checker import (
    check_achievements
)

from utils.items import (
    HUNTING_ITEMS
)


IST = pytz.timezone("Asia/Kolkata")

HUNT_COOLDOWN = 1800

HUNT_REWARD = 50000


class Hunt(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="hunt")
    async def hunt(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        last_hunt = user_data.get(
            "last_hunt",
            0
        )


        current_time = int(
            datetime.now(IST).timestamp()
        )


        # ─────────────────────────
        # COOLDOWN
        # ─────────────────────────

        if current_time - last_hunt < HUNT_COOLDOWN:

            remaining = (

                HUNT_COOLDOWN -

                (current_time - last_hunt)

            )


            next_time = current_time + remaining


            embed = discord.Embed(

                description=(

                    "❌ Hunting cooldown active.\n\n"

                    f"⏰ Try again <t:{next_time}:R>"

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # SAVE TIME

        economy_collection.update_one(

            {
                "user_id": str(ctx.author.id)
            },

            {
                "$set": {
                    "last_hunt": current_time
                }
            }
        )


        # ─────────────────────────
        # BAD EVENT
        # ─────────────────────────

        robbed = random.randint(1, 100) <= 15


        if robbed:

            loss = 100000

            cash = get_cash(ctx.author.id)

            if cash < loss:

                loss = cash


            remove_cash(
                ctx.author.id,
                loss
            )


            embed = discord.Embed(

                title="🏹 HUNT FAILED",

                description=(

                    f"You tried hunting but "
                    f"**Royal NGR** 🍇 you and "
                    f"took **{format_cash(loss)}**."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # MONEY REWARD
        # ─────────────────────────

        add_cash(
            ctx.author.id,
            HUNT_REWARD
        )


        # ─────────────────────────
        # ITEM DROP
        # ─────────────────────────

        roll = random.randint(1, 100)

        current = 0

        selected_item = None


        for item in HUNTING_ITEMS:

            current += item["chance"]

            if roll <= current:

                selected_item = item

                break


        inventory = user_data.get(
            "inventory",
            {}
        )


        item_name = selected_item["name"]

        inventory[item_name] = (

            inventory.get(item_name, 0) + 1

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


        embed = discord.Embed(

            title="🏹 HUNTING",

            description=(

                f"You went hunting.\n\n"

                f"💰 Earned:\n"
                f"**{format_cash(HUNT_REWARD)}**\n\n"

                f"🎁 Found:\n"
                f"{selected_item['emoji']} "
                f"**{selected_item['display']}**"

            ),

            color=0x57F287
        )


        add_stats(
            ctx.author.id,
            total_hunts=1
        )
        await check_achievements(
            self.bot,
            ctx.author
        )
        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Hunt(bot)
    )
