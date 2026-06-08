from discord.ext import commands
import discord
import time

from utils.economy import (
    create_account,
    get_cash,
    add_cash,
    remove_cash,
    can_claim_daily,
    can_claim_weekly,
    can_claim_monthly,
    update_daily,
    update_weekly,
    update_monthly,
    format_cash
)

class Economy(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # DAILY

    @commands.command(name="daily")
    async def daily(self, ctx):

        create_account(ctx.author.id)

        if not can_claim_daily(ctx.author.id):

            embed = discord.Embed(
                description="❌ You already claimed daily.",
                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        amount = 10000

        add_cash(
            ctx.author.id,
            amount
        )

        update_daily(ctx.author.id)

        embed = discord.Embed(
            title="💸 DAILY CLAIMED",
            description=(
                f"{ctx.author.mention}\n\n"
                f"+ **{format_cash(amount)}**"
            ),
            color=0x57F287
        )

        await ctx.send(embed=embed)

    # WEEKLY

    @commands.command(name="weekly")
    async def weekly(self, ctx):

        create_account(ctx.author.id)

        if not can_claim_weekly(ctx.author.id):

            embed = discord.Embed(
                description="❌ You already claimed weekly.",
                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        amount = 100000

        add_cash(
            ctx.author.id,
            amount
        )

        update_weekly(ctx.author.id)

        embed = discord.Embed(
            title="💰 WEEKLY CLAIMED",
            description=(
                f"{ctx.author.mention}\n\n"
                f"+ **{format_cash(amount)}**"
            ),
            color=0x5865F2
        )

        await ctx.send(embed=embed)

    # MONTHLY

    @commands.command(name="monthly")
    async def monthly(self, ctx):

        create_account(ctx.author.id)

        if not can_claim_monthly(ctx.author.id):

            embed = discord.Embed(
                description="❌ You already claimed monthly.",
                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        amount = 1000000

        add_cash(
            ctx.author.id,
            amount
        )

        update_monthly(ctx.author.id)

        embed = discord.Embed(
            title="🏆 MONTHLY CLAIMED",
            description=(
                f"{ctx.author.mention}\n\n"
                f"+ **{format_cash(amount)}**"
            ),
            color=0xFEE75C
        )

        await ctx.send(embed=embed)

    # CASH

    @commands.command(name="cash")
    async def cash(
        self,
        ctx,
        member: discord.Member = None
    ):

        if member is None:

            member = ctx.author

        create_account(member.id)

        cash = get_cash(member.id)

        embed = discord.Embed(
            title="💵 CASH",
            description=(
                f"{member.mention}\n\n"
                f"## {format_cash(cash)}"
            ),
            color=0x2B2D31
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        await ctx.send(embed=embed)

async def setup(bot):

    await bot.add_cog(
        Economy(bot)
    )
