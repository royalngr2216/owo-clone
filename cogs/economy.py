from discord.ext import commands
import discord

from datetime import datetime, timedelta

from utils.economy import (
ensure_account,
get_cash,
add_cash,
format_cash,
economy_collection
)

class Economy(commands.Cog):

def __init__(self, bot):

    self.bot = bot

# ─────────────────────────
# CASH
# ─────────────────────────

@commands.command(name="cash")
async def cash(
    self,
    ctx,
    member: discord.Member = None
):

    if member is None:
        member = ctx.author

    ensure_account(member.id)

    cash = get_cash(member.id)

    embed = discord.Embed(
        description=(
            f"💵 {member.display_name}'s Cash\n\n"
            f"# {format_cash(cash)}"
        ),
        color=0x2B2D31
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)

# ─────────────────────────
# DAILY
# ─────────────────────────

@commands.command(name="daily")
async def daily(self, ctx):

    user = ensure_account(ctx.author.id)

    last_claim = user.get("daily_claimed")

    now = datetime.utcnow()

    if last_claim:

        last_claim = datetime.fromisoformat(
            last_claim
        )

        remaining = (
            last_claim + timedelta(days=1)
        ) - now

        if remaining.total_seconds() > 0:

            hours, remainder = divmod(
                int(remaining.total_seconds()),
                3600
            )

            minutes = remainder // 60

            embed = discord.Embed(
                description=(
                    "⏳ Daily already claimed.\n\n"
                    f"Try again in "
                    f"`{hours}h {minutes}m`"
                ),
                color=0xED4245
            )

            return await ctx.send(
                embed=embed
            )

    reward = 10_000

    add_cash(
        ctx.author.id,
        reward
    )

    economy_collection.update_one(
        {
            "user_id": str(ctx.author.id)
        },
        {
            "$set": {
                "daily_claimed": now.isoformat()
            }
        }
    )

    embed = discord.Embed(
        description=(
            "🎁 Daily Claimed\n\n"
            f"+ {format_cash(reward)}"
        ),
        color=0x57F287
    )

    await ctx.send(embed=embed)

# ─────────────────────────
# WEEKLY
# ─────────────────────────

@commands.command(name="weekly")
async def weekly(self, ctx):

    user = ensure_account(ctx.author.id)

    last_claim = user.get("weekly_claimed")

    now = datetime.utcnow()

    if last_claim:

        last_claim = datetime.fromisoformat(
            last_claim
        )

        remaining = (
            last_claim + timedelta(days=7)
        ) - now

        if remaining.total_seconds() > 0:

            days = remaining.days

            hours = (
                remaining.seconds // 3600
            )

            embed = discord.Embed(
                description=(
                    "⏳ Weekly already claimed.\n\n"
                    f"Try again in "
                    f"`{days}d {hours}h`"
                ),
                color=0xED4245
            )

            return await ctx.send(
                embed=embed
            )

    reward = 100_000

    add_cash(
        ctx.author.id,
        reward
    )

    economy_collection.update_one(
        {
            "user_id": str(ctx.author.id)
        },
        {
            "$set": {
                "weekly_claimed": now.isoformat()
            }
        }
    )

    embed = discord.Embed(
        description=(
            "🎉 Weekly Claimed\n\n"
            f"+ {format_cash(reward)}"
        ),
        color=0x57F287
    )

    await ctx.send(embed=embed)

# ─────────────────────────
# MONTHLY
# ─────────────────────────

@commands.command(name="monthly")
async def monthly(self, ctx):

    user = ensure_account(ctx.author.id)

    last_claim = user.get("monthly_claimed")

    now = datetime.utcnow()

    if last_claim:

        last_claim = datetime.fromisoformat(
            last_claim
        )

        remaining = (
            last_claim + timedelta(days=30)
        ) - now

        if remaining.total_seconds() > 0:

            days = remaining.days

            embed = discord.Embed(
                description=(
                    "⏳ Monthly already claimed.\n\n"
                    f"Try again in "
                    f"`{days} days`"
                ),
                color=0xED4245
            )

            return await ctx.send(
                embed=embed
            )

    reward = 1_000_000

    add_cash(
        ctx.author.id,
        reward
    )

    economy_collection.update_one(
        {
            "user_id": str(ctx.author.id)
        },
        {
            "$set": {
                "monthly_claimed": now.isoformat()
            }
        }
    )

    embed = discord.Embed(
        description=(
            "💎 Monthly Claimed\n\n"
            f"+ {format_cash(reward)}"
        ),
        color=0x57F287
    )

    await ctx.send(embed=embed)

async def setup(bot):

await bot.add_cog(
    Economy(bot)
)
