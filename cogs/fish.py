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

from utils.items import (
    FISHING_ITEMS
)


IST = pytz.timezone("Asia/Kolkata")

FISH_COOLDOWN = 7200

FISH_REWARD = 50000


class Fish(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="fish")
    async def fish(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        last_fish = user_data.get(
            "last_fish",
            0
        )


        current_time = int(
            datetime.now(IST).timestamp()
        )


        # ─────────────────────────
        # COOLDOWN
        # ─────────────────────────

        if current_time - last_fish < FISH_COOLDOWN:

            remaining = (

                FISH_COOLDOWN -

                (current_time - last_fish)

            )


            next_time = current_time + remaining


            embed = discord.Embed(

                description=(

                    "❌ Fishing cooldown active.\n\n"

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
                    "last_fish": current_time
                }
            }
        )


        # ─────────────────────────
        # BAD EVENT
        # ─────────────────────────

        robbed = random.randint(1, 100) <= 10


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

                title="🎣 FISHING FAILED",

                description=(

                    f"You tried fishing but "
                    f"**EMIEL** 🍇 you and "
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
            FISH_REWARD
        )


        # ─────────────────────────
        # ITEM DROP
        # ─────────────────────────

        roll = random.randint(1, 100)

        current = 0

        selected_item = None


        for item in FISHING_ITEMS:

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

            title="🎣 FISHING",

            description=(

                f"You went fishing.\n\n"

                f"💰 Earned:\n"
                f"**{format_cash(FISH_REWARD)}**\n\n"

                f"🎁 Found:\n"
                f"{selected_item['emoji']} "
                f"**{selected_item['display']}**"

            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Fish(bot)
          )
