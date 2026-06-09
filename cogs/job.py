from discord.ext import commands
import discord
import random
from datetime import datetime, timedelta
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

JOB_COOLDOWN = 7200

JOB_REWARD = 100000


class Job(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="job")
    async def job(self, ctx):

        create_account(ctx.author.id)

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        last_job = user_data.get(
            "last_job",
            0
        )


        current_time = int(
            datetime.now(IST).timestamp()
        )


        # ─────────────────────────
        # COOLDOWN
        # ─────────────────────────

        if current_time - last_job < JOB_COOLDOWN:

            remaining = (

                JOB_COOLDOWN -

                (current_time - last_job)

            )


            next_time = current_time + remaining


            embed = discord.Embed(

                description=(

                    "❌ Job cooldown active.\n\n"

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
                    "last_job": current_time
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

                title="💼 JOB FAILED",

                description=(

                    f"You went for work but "
                    f"**FURRY** 🍇 you and "
                    f"took **{format_cash(loss)}**."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # SUCCESS
        # ─────────────────────────

        add_cash(
            ctx.author.id,
            JOB_REWARD
        )


        embed = discord.Embed(

            title="💼 JOB COMPLETE",

            description=(

                f"You completed your shift.\n\n"

                f"💰 Earned:\n"
                f"**{format_cash(JOB_REWARD)}**"

            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Job(bot)
          )
