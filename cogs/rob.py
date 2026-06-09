from discord.ext import commands
import discord
import random
from datetime import datetime, timedelta
import pytz

from utils.economy import (
    create_account,
    get_cash,
    add_cash,
    remove_cash,
    format_cash,
    economy_collection
)


IST = pytz.timezone("Asia/Kolkata")


class Rob(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    @commands.command(name="rob")
    async def rob(
        self,
        ctx,
        member: discord.Member = None
    ):

        # ─────────────────────────
        # NO USER
        # ─────────────────────────

        if member is None:

            embed = discord.Embed(

                description="❌ Mention someone to rob.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # SELF ROB
        # ─────────────────────────

        if member.id == ctx.author.id:

            embed = discord.Embed(

                description="❌ You cannot rob yourself.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # BOT CHECK
        # ─────────────────────────

        if member.bot:

            embed = discord.Embed(

                description="❌ You cannot rob bots.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        create_account(ctx.author.id)
        create_account(member.id)

        robber_cash = get_cash(ctx.author.id)

        victim_cash = get_cash(member.id)


        # ─────────────────────────
        # ROB LIMIT RESET
        # ─────────────────────────

        user_data = economy_collection.find_one({

            "user_id": str(ctx.author.id)

        })


        rob_uses = user_data.get(
            "rob_uses",
            0
        )

        rob_reset = user_data.get(
            "rob_reset",
            0
        )


        now = datetime.now(IST)

        reset_time = now.replace(

            hour=5,
            minute=30,
            second=0,
            microsecond=0

        )


        if now < reset_time:

            reset_time -= timedelta(days=1)


        current_reset = int(
            reset_time.timestamp()
        )


        # NEW DAY RESET

        if rob_reset < current_reset:

            rob_uses = 0

            economy_collection.update_one(

                {
                    "user_id": str(ctx.author.id)
                },

                {
                    "$set": {

                        "rob_uses": 0,

                        "rob_reset": current_reset
                    }
                }
            )


        # ─────────────────────────
        # DAILY LIMIT
        # ─────────────────────────

        if rob_uses >= 10:

            next_reset = reset_time + timedelta(days=1)

            embed = discord.Embed(

                description=(

                    "❌ You used all 10 rob attempts today.\n\n"

                    f"⏰ Reset <t:{int(next_reset.timestamp())}:R>\n"
                    f"📅 <t:{int(next_reset.timestamp())}:F>"

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # TOO RICH TO ROB
        # ─────────────────────────

        if robber_cash > 200000:

            embed = discord.Embed(

                description=(

                    "❌ You are too rich to rob people.\n\n"

                    "Rob is only available for users under "
                    "**$200K**."

                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # VICTIM TOO BROKE
        # ─────────────────────────

        if victim_cash < 100:

            embed = discord.Embed(

                description="❌ That user is too broke to rob.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # ADD ROB USE
        # ─────────────────────────

        economy_collection.update_one(

            {
                "user_id": str(ctx.author.id)
            },

            {
                "$inc": {
                    "rob_uses": 1
                },

                "$set": {
                    "rob_reset": current_reset
                }
            }
        )


        # ─────────────────────────
        # 40% SUCCESS CHANCE
        # ─────────────────────────

        success = random.randint(1, 100) <= 40


        # ─────────────────────────
        # SUCCESS
        # ─────────────────────────

        if success:

            stolen = int(victim_cash * 0.05)

            if stolen < 1:

                stolen = 1


            remove_cash(
                member.id,
                stolen
            )

            add_cash(
                ctx.author.id,
                stolen
            )


            embed = discord.Embed(

                title="🦹 ROB SUCCESS",

                description=(

                    f"{ctx.author.mention} robbed {member.mention}\n\n"

                    f"💰 Stole **{format_cash(stolen)}**\n\n"

                    f"📊 Remaining Attempts: "
                    f"**{10 - (rob_uses + 1)} / 10**"

                ),

                color=0x57F287
            )

            await ctx.send(embed=embed)

            return


        # ─────────────────────────
        # FAILED ROB
        # ─────────────────────────

        loss = int(robber_cash * 0.50)

        if loss < 1:

            loss = 1


        remove_cash(
            ctx.author.id,
            loss
        )

        add_cash(
            member.id,
            loss
        )


        embed = discord.Embed(

            title="🚔 ROB FAILED",

            description=(

                f"{ctx.author.mention} got caught robbing {member.mention}\n\n"

                f"💸 Lost **{format_cash(loss)}**\n\n"

                f"📊 Remaining Attempts: "
                f"**{10 - (rob_uses + 1)} / 10**"

            ),

            color=0xED4245
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Rob(bot)
    )
