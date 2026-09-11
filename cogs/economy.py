from discord.ext import commands
import discord

from utils.economy import (
    create_account, get_cash, add_cash, remove_cash,
    can_claim_daily, can_claim_weekly, can_claim_monthly,
    update_daily, update_weekly, update_monthly,
    get_daily_reset, get_weekly_reset, get_monthly_reset,
    format_cash, MAX_BALANCE
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
            embed = discord.Embed(
                description=f"❌ You already claimed daily.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>",
                color=0xED4245,
            )
            brand(embed)
            await ctx.send(embed=embed)
            return
        add_cash(ctx.author.id, DAILY_REWARD)
        update_daily(ctx.author.id)
        embed = discord.Embed(
            title="💸 DAILY CLAIMED",
            description=f"{ctx.author.mention}\n\n+ **{format_cash(DAILY_REWARD)}**",
            color=0x57F287,
        )
        brand(embed)
        await ctx.send(embed=embed)

    @commands.command(name="weekly")
    async def weekly(self, ctx):
        create_account(ctx.author.id)
        if not can_claim_weekly(ctx.author.id):
            next_claim = get_weekly_reset()
            embed = discord.Embed(
                description=f"❌ You already claimed weekly.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>",
                color=0xED4245,
            )
            brand(embed)
            await ctx.send(embed=embed)
            return
        add_cash(ctx.author.id, WEEKLY_REWARD)
        update_weekly(ctx.author.id)
        embed = discord.Embed(
            title="💰 WEEKLY CLAIMED",
            description=f"{ctx.author.mention}\n\n+ **{format_cash(WEEKLY_REWARD)}**",
            color=0x5865F2,
        )
        brand(embed)
        await ctx.send(embed=embed)

    @commands.command(name="monthly")
    async def monthly(self, ctx):
        create_account(ctx.author.id)
        if not can_claim_monthly(ctx.author.id):
            next_claim = get_monthly_reset()
            embed = discord.Embed(
                description=f"❌ You already claimed monthly.\n\n⏰ Try again <t:{next_claim}:R>\n📅 <t:{next_claim}:F>",
                color=0xED4245,
            )
            brand(embed)
            await ctx.send(embed=embed)
            return
        add_cash(ctx.author.id, MONTHLY_REWARD)
        update_monthly(ctx.author.id)
        embed = discord.Embed(
            title="🏆 MONTHLY CLAIMED",
            description=f"{ctx.author.mention}\n\n+ **{format_cash(MONTHLY_REWARD)}**",
            color=0xFEE75C,
        )
        brand(embed)
        await ctx.send(embed=embed)

    @commands.command(name="cash")
    async def cash(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        create_account(member.id)
        cash = get_cash(member.id)
        badge = title_badge(member.id)
        embed = discord.Embed(
            title="💵 CASH",
            description=f"{badge}{member.mention}\n\n# {format_cash(cash)}",
            color=0x2B2D31,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        brand(embed)
        await ctx.send(embed=embed)

    async def _transfer_cash(self, ctx, member, amount_text):
        if member is None:
            await ctx.send("❌ Mention a user to give money to.\nUsage: `.give @user 1000`")
            return

        if member.bot:
            await ctx.send("❌ You can't give money to a bot.")
            return

        if member.id == ctx.author.id:
            await ctx.send("❌ You can't give money to yourself.")
            return

        try:
            raw = str(amount_text).lower().strip().replace(",", "")
            if raw.endswith("k"):
                amount = int(float(raw[:-1]) * 1_000)
            elif raw.endswith("m"):
                amount = int(float(raw[:-1]) * 1_000_000)
            else:
                amount = int(raw)
        except (TypeError, ValueError):
            await ctx.send("❌ Invalid amount. Use a number like `1000`, `10k`, or `1m`.")
            return

        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return

        create_account(ctx.author.id)
        create_account(member.id)
        sender_balance = get_cash(ctx.author.id)
        receiver_balance = get_cash(member.id)

        if sender_balance < amount:
            await ctx.send(
                f"❌ You don't have enough NGR. You have **{format_cash(sender_balance)}**."
            )
            return

        if receiver_balance + amount > MAX_BALANCE:
            remaining = MAX_BALANCE - receiver_balance
            await ctx.send(
                f"❌ That would put {member.mention}'s balance over the **{format_cash(MAX_BALANCE)}** limit.\n"
                f"Maximum you can give them right now: **{format_cash(max(0, remaining))}**."
            )
            return

        # Debit only if the sender still has enough at the moment of the update.
        result = __import__("utils.economy", fromlist=["economy_collection"]).economy_collection.update_one(
            {"user_id": str(ctx.author.id), "cash": {"$gte": amount}},
            {"$inc": {"cash": -amount}},
        )
        if result.modified_count != 1:
            await ctx.send("❌ Your balance changed before the transfer could complete. Please try again.")
            return

        receiver_result = __import__("utils.economy", fromlist=["economy_collection"]).economy_collection.update_one(
            {"user_id": str(member.id), "cash": {"$lte": MAX_BALANCE - amount}},
            {"$inc": {"cash": amount}},
        )
        if receiver_result.modified_count != 1:
            # Roll the debit back if the receiver update failed.
            add_cash(ctx.author.id, amount)
            await ctx.send("❌ Transfer couldn't be completed. Your money has been returned.")
            return

        embed = discord.Embed(
            title="💸 MONEY SENT",
            description=(
                f"{ctx.author.mention} sent **{format_cash(amount)}** to {member.mention}.\n\n"
                f"💵 Your balance: **{format_cash(sender_balance - amount)}**"
            ),
            color=0x57F287,
        )
        brand(embed)
        await ctx.send(embed=embed)

    @commands.command(name="give", aliases=["donate"])
    async def give(self, ctx, member: discord.Member = None, amount: str = None):
        """Give NGR to another user. `.donate` is an alias of `.give`."""
        if member is None or amount is None:
            await ctx.send("❌ Usage: `.give @user <amount>`\nExample: `.give @user 10k`\nAlias: `.donate @user <amount>`")
            return
        await self._transfer_cash(ctx, member, amount)


async def setup(bot):
    await bot.add_cog(Economy(bot))
