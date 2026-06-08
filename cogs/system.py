from discord.ext import commands
import discord

from utils.stats import (
get_profile
)

from utils.economy import (
get_cash,
format_cash,
economy_collection
)

class System(commands.Cog):

def __init__(self, bot):

    self.bot = bot

# ─────────────────────────
# PROFILE
# ─────────────────────────

@commands.command(name="profile")
async def profile(
    self,
    ctx,
    member: discord.Member = None
):

    if member is None:
        member = ctx.author

    stats = get_profile(member.id)

    cash = get_cash(member.id)

    wins = stats["wins"]
    losses = stats["losses"]

    total_games = wins + losses

    embed = discord.Embed(

        description=(

            f"# 👤 {member.display_name}\n\n"

            f"💵 Cash\n"
            f"## {format_cash(cash)}\n\n"

            f"🏆 Wins: `{wins}`\n"
            f"💀 Losses: `{losses}`\n"
            f"🎮 Matches: `{total_games}`\n"
            f"📈 Winrate: `{stats['winrate']}%`\n\n"

            f"🔥 Current Streak: "
            f"`{stats.get('streak', 0)}`\n"

            f"👑 Best Streak: "
            f"`{stats.get('best_streak', 0)}`"

        ),

        color=0x2B2D31
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)

# ─────────────────────────
# CASH LEADERBOARD
# ─────────────────────────

@commands.command(name="leaderboard")
async def leaderboard(self, ctx):

    users = economy_collection.find()

    leaderboard = []

    for user in users:

        leaderboard.append(

            (
                user["user_id"],
                user.get("cash", 0)
            )

        )

    leaderboard.sort(
        key=lambda x: x[1],
        reverse=True
    )

    top_10 = leaderboard[:10]

    embed = discord.Embed(
        title="🏆 Richest Players",
        color=0xFEE75C
    )

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    lines = []

    for i, (
        user_id,
        cash
    ) in enumerate(top_10):

        rank = (
            medals[i]
            if i < 3
            else f"`#{i+1}`"
        )

        lines.append(

            f"{rank} <@{user_id}>\n"
            f"💵 {format_cash(cash)}"

        )

    embed.description = "\n\n".join(lines)

    await ctx.send(embed=embed)

# ─────────────────────────
# PING
# ─────────────────────────

@commands.command(name="ping")
async def ping(self, ctx):

    latency = round(
        self.bot.latency * 1000
    )

    embed = discord.Embed(
        description=(
            f"🏓 `{latency}ms`"
        ),
        color=0x2B2D31
    )

    await ctx.send(embed=embed)

# ─────────────────────────
# HELP
# ─────────────────────────

@commands.command(name="help")
async def help(self, ctx):

    embed = discord.Embed(
        title="🎮 Royal Economy",
        color=0x2B2D31
    )

    embed.add_field(
        name="💵 Economy",
        value=(

            "`.cash`\n"
            "`.daily`\n"
            "`.weekly`\n"
            "`.monthly`\n"
            "`.give`\n"
            "`.history`"

        ),
        inline=False
    )

    embed.add_field(
        name="🎲 Gambling",
        value=(

            "`.cf h/t amount`\n"
            "`.dice 6/7/9 amount`\n"
            "`.deathroll @user bo amount`"

        ),
        inline=False
    )

    embed.add_field(
        name="🐉 Games",
        value=(

            "`.randoms @user bo amount`\n"
            "`.crack @user bo amount`\n"
            "`.average`\n"
            "`.jackpot`"

        ),
        inline=False
    )

    embed.add_field(
        name="📊 Profile",
        value=(

            "`.profile`\n"
            "`.leaderboard`"

        ),
        inline=False
    )

    embed.set_footer(
        text="Royal Economy"
    )

    await ctx.send(embed=embed)

async def setup(bot):

await bot.add_cog(
    System(bot)
)
