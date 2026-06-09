from discord.ext import commands
import discord
from datetime import datetime

from utils.economy import (
    economy_collection,
    get_cash,
    remove_cash,
    format_cash,
    create_account
)


PADLOCK_PRICE = 250000
WORKER_PRICE = 5000000
LOCK_AND_KEY_PRICE = 2500000


# ─────────────────────────
# SHOP VIEW
# ─────────────────────────

class ShopView(discord.ui.View):

    def __init__(self, ctx):

        super().__init__(timeout=60)

        self.ctx = ctx


    @discord.ui.select(

        placeholder="Choose an item to purchase",

        options=[

            discord.SelectOption(

                label="Padlock",

                description="250K NGR • 1 day protection",

                emoji="🛡"

            ),

            discord.SelectOption(

                label="Worker",

                description="5M NGR • Passive income worker",

                emoji="⚒"

            ),

            discord.SelectOption(

                label="Lock and Key",

                description="2.5M NGR • 20 rob attempts",

                emoji="🔐"

            )

        ]
    )

    async def select_callback(

        self,
        interaction: discord.Interaction,
        select: discord.ui.Select

    ):

        if interaction.user != self.ctx.author:

            await interaction.response.send_message(

                "❌ This menu is not for you.",

                ephemeral=True
            )

            return


        create_account(interaction.user.id)

        user_data = economy_collection.find_one({

            "user_id": str(interaction.user.id)

        })


        workers = user_data.get(
            "workers",
            {}
        )


        # ─────────────────────────
        # PADLOCK
        # ─────────────────────────

        if select.values[0] == "Padlock":

            cash = get_cash(
                interaction.user.id
            )

            if cash < PADLOCK_PRICE:

                embed = discord.Embed(

                    description=(

                        "❌ You don't have enough cash.\n\n"

                        f"Required: **{format_cash(PADLOCK_PRICE)}**"

                    ),

                    color=0xED4245
                )

                await interaction.response.send_message(

                    embed=embed,
                    ephemeral=True
                )

                return


            remove_cash(
                interaction.user.id,
                PADLOCK_PRICE
            )


            current_time = int(
                datetime.now().timestamp()
            )


            current_padlock = user_data.get(
                "padlock_until",
                0
            )


            if current_padlock < current_time:

                current_padlock = current_time


            new_time = current_padlock + 86400


            economy_collection.update_one(

                {
                    "user_id": str(interaction.user.id)
                },

                {
                    "$set": {
                        "padlock_until": new_time
                    }
                }
            )


            remaining_days = (

                new_time - current_time

            ) // 86400


            embed = discord.Embed(

                title="🛡 PADLOCK PURCHASED",

                description=(

                    "Your account is now protected from robbing.\n\n"

                    f"⏰ Total Protection:\n"
                    f"**{remaining_days} Days**"

                ),

                color=0x5865F2
            )

            embed.set_footer(

                text="Protection activates instantly"
            )

            await interaction.response.send_message(

                embed=embed
            )

            return


        # ─────────────────────────
        # WORKER
        # ─────────────────────────

        if select.values[0] == "Worker":

            owned_workers = len(workers)

            if owned_workers >= 5:

                embed = discord.Embed(

                    description=(

                        "❌ You already own the maximum number of workers."

                    ),

                    color=0xED4245
                )

                await interaction.response.send_message(

                    embed=embed,
                    ephemeral=True
                )

                return


            cash = get_cash(
                interaction.user.id
            )

            if cash < WORKER_PRICE:

                embed = discord.Embed(

                    description=(

                        "❌ You don't have enough cash.\n\n"

                        f"Required: **{format_cash(WORKER_PRICE)}**"

                    ),

                    color=0xED4245
                )

                await interaction.response.send_message(

                    embed=embed,
                    ephemeral=True
                )

                return


            remove_cash(
                interaction.user.id,
                WORKER_PRICE
            )


            worker_name = (
                f"worker-{owned_workers + 1}"
            )


            workers[worker_name] = {

                "level": 1,

                "stored": 0,

                "total_earned": 0,

                "last_claim": int(
                    datetime.now().timestamp()
                )

            }


            economy_collection.update_one(

                {
                    "user_id": str(interaction.user.id)
                },

                {
                    "$set": {
                        "workers": workers
                    }
                }
            )


            embed = discord.Embed(

                title="⚒ WORKER PURCHASED",

                description=(

                    f"Purchased **{worker_name}**\n\n"

                    "💰 Income:\n"
                    "**100K NGR / Day**\n\n"

                    "📦 Max Storage:\n"
                    "**100K NGR**"

                ),

                color=0x57F287
            )

            embed.set_footer(

                text="Use .workers to manage workers"
            )

            await interaction.response.send_message(

                embed=embed
            )

            return


        # ─────────────────────────
        # LOCK AND KEY
        # ─────────────────────────

        if select.values[0] == "Lock and Key":

            if user_data.get("lock_and_key"):

                embed = discord.Embed(

                    description=(

                        "❌ You already own "
                        "**Lock and Key**."

                    ),

                    color=0xED4245
                )

                await interaction.response.send_message(

                    embed=embed,
                    ephemeral=True
                )

                return


            cash = get_cash(
                interaction.user.id
            )


            if cash < LOCK_AND_KEY_PRICE:

                embed = discord.Embed(

                    description=(

                        "❌ You don't have enough cash.\n\n"

                        f"Required: **{format_cash(LOCK_AND_KEY_PRICE)}**"

                    ),

                    color=0xED4245
                )

                await interaction.response.send_message(

                    embed=embed,
                    ephemeral=True
                )

                return


            remove_cash(
                interaction.user.id,
                LOCK_AND_KEY_PRICE
            )


            economy_collection.update_one(

                {
                    "user_id": str(interaction.user.id)
                },

                {
                    "$set": {
                        "lock_and_key": True
                    }
                }
            )


            embed = discord.Embed(

                title="🔐 LOCK AND KEY PURCHASED",

                description=(

                    "Your rob attempts have increased.\n\n"

                    "📈 Rob Attempts:\n"
                    "**10 → 20**"

                ),

                color=0x57F287
            )

            embed.set_footer(

                text="Permanent Upgrade"
            )

            await interaction.response.send_message(

                embed=embed
            )

            return


# ─────────────────────────
# SHOP COMMAND
# ─────────────────────────

class Shop(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="shop")
    async def shop(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        workers = user_data.get(
            "workers",
            {}
        )


        current_time = int(
            datetime.now().timestamp()
        )


        padlock_until = user_data.get(
            "padlock_until",
            0
        )


        active_days = 0

        if padlock_until > current_time:

            active_days = (

                padlock_until - current_time

            ) // 86400


        lock_and_key = user_data.get(
            "lock_and_key",
            False
        )


        embed = discord.Embed(

            title="🛒 ECHLEON SHOP",

            description=(

                "Purchase upgrades, protection, "
                "and passive income systems.\n\n"

                "Use the dropdown menu below "
                "to buy items."

            ),

            color=0x5865F2
        )


        # PADLOCK

        embed.add_field(

            name="🛡 Padlock",

            value=(

                "Protects your account from rob attempts.\n\n"

                "• Price: **250K NGR**\n"
                "• Duration: **1 Day**\n"
                f"• Active Time: **{active_days} Days**"

            ),

            inline=False
        )


        # WORKERS

        embed.add_field(

            name="⚒ Workers",

            value=(

                "Passive income generators.\n\n"

                "• Base Income: **100K/day**\n"
                "• Upgradeable: **Yes**\n"
                "• Max Workers: **5**\n"
                f"• Owned: **{len(workers)}/5**\n\n"

                "Workers stop generating "
                "once storage becomes full."

            ),

            inline=False
        )


        # LOCK AND KEY

        embed.add_field(

            name="🔐 Lock and Key",

            value=(

                "Increase rob attempts permanently.\n\n"

                "• Price: **2.5M NGR**\n"
                "• Rob Attempts: **10 → 20**\n"
                f"• Owned: **{'Yes' if lock_and_key else 'No'}**"

            ),

            inline=False
        )


        embed.set_footer(

            text="ECHLEON Economy System"
        )


        await ctx.send(

            embed=embed,

            view=ShopView(ctx)
        )


async def setup(bot):

    await bot.add_cog(
        Shop(bot)
        )
