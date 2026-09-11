from discord.ext import commands
import discord

from utils.economy import (
    create_account, get_cash, add_cash,
    can_claim_daily, can_claim_weekly, can_claim_monthly,
    update_daily, update_weekly, update_monthly,
    get_daily_reset, get_weekly_reset, get_monthly_reset,
    format_cash
)
from utils.branding import brand
from utils.titles import title_badge

DAILY_REWARD = 5_000
WEEKLY_REWARD = 25_000
MONTHLY_REWARD = 100_000

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="daily")
    async def daily(self, ctx):
        create_account(ctx.author.id)
        if not can_claim_daily(ctx.author.id):
            next_claim = get_daily_reset()
            embed = discord.Embed(description=f"❌ You already claimed daily.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>", color=0xED4245)
            brand(embed); await ctx.send(embed=embed); return
        add_cash(ctx.author.id, DAILY_REWARD); update_daily(ctx.author.id)
        embed = discord.Embed(title="💸 DAILY CLAIMED", description=f"{ctx.author.mention}\n\n+ **{format_cash(DAILY_REWARD)}**", color=0x57F287)
        brand(embed); await ctx.send(embed=embed)

    @commands.command(name="weekly")
    async def weekly(self, ctx):
        create_account(ctx.author.id)
        if not can_claim_weekly(ctx.author.id):
            next_claim = get_weekly_reset()
            embed = discord.Embed(description=f"❌ You already claimed weekly.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>", color=0xED4245)
            brand(embed); await ctx.send(embed=embed); return
        add_cash(ctx.author.id, WEEKLY_REWARD); update_weekly(ctx.author.id)
        embed = discord.Embed(title="💰 WEEKLY CLAIMED", description=f"{ctx.author.mention}\n\n+ **{format_cash(WEEKLY_REWARD)}**", color=0x5865F2)
        brand(embed); await ctx.send(embed=embed)

    @commands.command(name="monthly")
    async def monthly(self, ctx):
        create_account(ctx.author.id)
        if not can_claim_monthly(ctx.author.id):
            next_claim = get_monthly_reset()
            embed = discord.Embed(description=f"❌ You already claimed monthly.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>", color=0xED4245)
            brand(embed); await ctx.send(embed=embed); return
        add_cash(ctx.author.id, MONTHLY_REWARD); update_monthly(ctx.author.id)
        embed = discord.Embed(title="🏆 MONTHLY CLAIMED", description=f"{ctx.author.mention}\n\n+ **{format_cash(MONTHLY_REWARD)}**", color=0xFEE75C)
        brand(embed); await ctx.send(embed=embed)

    @commands.command(name="cash")
    async def cash(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        create_account(member.id)
        cash = get_cash(member.id); badge = title_badge(member.id)
        embed = discord.Embed(title="💵 CASH", description=f"{badge}{member.mention}\n\n# {format_cash(cash)}", color=0x2B2D31)
        embed.set_thumbnail(url=member.display_avatar.url); brand(embed); await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
