from discord.ext import commands
import discord
from datetime import datetime

from utils.economy import (
    economy_collection,
    add_cash,
    format_cash,
    create_account
)

from utils.workers import (
    update_workers,
    WORKER_LEVELS
)


class Workers(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    # ─────────────────────────
    # WORKERS
    # ─────────────────────────

    @commands.command(name="workers")
    async def workers(self, ctx):

        create_account(ctx.author.id)

        update_workers(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        workers = user_data.get(
            "workers",
            {}
        )


        if not workers:

            embed = discord.Embed(

                description=(

                    "❌ You do not own any workers.\n\n"

                    "Use `.shop` to purchase one."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        embed = discord.Embed(

            title="⚒ YOUR WORKERS",

            description=(

                "Passive income overview."

            ),

            color=0x5865F2
        )


        total_unclaimed = 0


        for worker_name, worker in workers.items():

            level = worker.get(
                "level",
                1
            )

            total_earned = worker.get(
                "total_earned",
                0
            )

            income = WORKER_LEVELS[level]["income"]

            last_claim = worker.get(
                "last_claim",
                int(datetime.now().timestamp())
            )


            current_time = int(
                datetime.now().timestamp()
            )


            seconds_passed = (

                current_time - last_claim
            )


            unclaimed = int(

                (seconds_passed / 86400)

                * income
            )


            total_unclaimed += unclaimed


            embed.add_field(

                name=f"⚒ {worker_name.upper()}",

                value=(

                    f"📈 Level: **{level}**\n"
                    f"💰 Income: **{format_cash(income)} / day**\n"
                    f"💵 Unclaimed: **{format_cash(unclaimed)}**\n"
                    f"🏦 Lifetime Earned: **{format_cash(total_earned)}**"

                ),

                inline=False
            )


        embed.add_field(

            name="💰 Total Unclaimed",

            value=f"**{format_cash(total_unclaimed)}**",

            inline=False
        )


        embed.set_footer(

            text="Use .claim to collect all worker earnings"
        )


        await ctx.send(embed=embed)


    # ─────────────────────────
    # CLAIM
    # ─────────────────────────

    @commands.command(name="claim")
    async def claim(self, ctx):

        create_account(ctx.author.id)

        update_workers(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        workers = user_data.get(
            "workers",
            {}
        )


        if not workers:

            embed = discord.Embed(

                description="❌ You do not own any workers.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        total_claimed = 0

        claim_text = ""


        current_time = int(
            datetime.now().timestamp()
        )


        for worker_name, worker in workers.items():

            level = worker.get(
                "level",
                1
            )

            income = WORKER_LEVELS[level]["income"]

            last_claim = worker.get(
                "last_claim",
                current_time
            )


            seconds_passed = (

                current_time - last_claim
            )


            earned = int(

                (seconds_passed / 86400)

                * income
            )


            if earned <= 0:

                continue


            total_claimed += earned


            claim_text += (

                f"{worker_name} → "
                f"**{format_cash(earned)}**\n"

            )


            worker["last_claim"] = current_time

            worker["total_earned"] = (

                worker.get(
                    "total_earned",
                    0
                ) + earned
            )


        if total_claimed <= 0:

            embed = discord.Embed(

                description=(

                    "❌ Your workers have no earnings yet."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        add_cash(
            ctx.author.id,
            total_claimed
        )


        economy_collection.update_one(

            {
                "user_id": str(ctx.author.id)
            },

            {
                "$set": {
                    "workers": workers
                }
            }
        )


        embed = discord.Embed(

            title="💰 WORKER CLAIM",

            description=(

                f"Collected **{format_cash(total_claimed)}**\n\n"

                f"{claim_text}"

            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Workers(bot)
            )
