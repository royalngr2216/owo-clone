@commands.command(name="profile")
async def profile(
self,
ctx,
member: discord.Member = None
):

if member is None:
    member = ctx.author

stats = get_profile(member.id)

from utils.economy import (
    get_cash,
    format_cash
)

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
