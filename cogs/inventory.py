from discord.ext import commands
import discord

from utils.economy import (
    economy_collection,
    add_cash,
    format_cash,
    create_account
)

from utils.items import (
    ALL_ITEMS
)


class Inventory(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    # ─────────────────────────
    # INVENTORY
    # ─────────────────────────

    @commands.command(name="inventory")
    async def inventory(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        inventory = user_data.get(
            "inventory",
            {}
        )


        embed = discord.Embed(

            title="📦 INVENTORY",

            color=0x5865F2
        )


        if not inventory:

            embed.description = (
                "Your inventory is empty."
            )

            await ctx.send(embed=embed)

            return


        text = ""


        total_value = 0


        for item_name, amount in inventory.items():

            if item_name not in ALL_ITEMS:

                continue


            item = ALL_ITEMS[item_name]

            value = item["price"] * amount

            total_value += value


            text += (

                f"{item['emoji']} "
                f"**{item['display']}** × {amount}\n"

            )


        embed.description = text


        embed.add_field(

            name="💰 Inventory Value",

            value=f"**{format_cash(total_value)}**",

            inline=False
        )


        await ctx.send(embed=embed)


    # ─────────────────────────
    # SELL
    # ─────────────────────────

    @commands.command(name="sell")
    async def sell(
        self,
        ctx,
        item_name: str,
        amount: str
    ):

        create_account(ctx.author.id)

        item_name = item_name.lower()

        if item_name not in ALL_ITEMS:

            embed = discord.Embed(

                description="❌ Invalid item.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        inventory = user_data.get(
            "inventory",
            {}
        )


        owned = inventory.get(
            item_name,
            0
        )


        if owned <= 0:

            embed = discord.Embed(

                description="❌ You don't own this item.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ALL

        if amount.lower() == "all":

            amount = owned

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


        if amount <= 0:

            return


        if amount > owned:

            embed = discord.Embed(

                description="❌ You don't own that many.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        item = ALL_ITEMS[item_name]

        earned = item["price"] * amount


        inventory[item_name] -= amount


        if inventory[item_name] <= 0:

            del inventory[item_name]


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


        add_cash(
            ctx.author.id,
            earned
        )


        embed = discord.Embed(

            title="💰 ITEMS SOLD",

            description=(

                f"Sold **{amount}x** "
                f"{item['emoji']} "
                f"**{item['display']}**\n\n"

                f"Earned:\n"
                f"**{format_cash(earned)}**"

            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Inventory(bot)
      )
