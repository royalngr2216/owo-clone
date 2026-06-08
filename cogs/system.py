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

    # HELP

    @commands.command(name="help")
    async def help(self, ctx):

        embed = discord.Embed(

            title="🎰 Royal Economy",

            description=(
                "Competitive gambling bot."
            ),

            color=0x5865F2
        )

        embed.add_field(

            name="💵 Economy",

            value=(

                "```yaml\n"

                ".cash\n"
                ".daily\n"
                ".weekly\n"
                ".monthly\n"
                ".give @user amount\n"

                "```"

            ),

            inline=False
        )

        embed.add_field(

            name="🎲 Gambling",

            value=(

                "```yaml\n"

                ".cf h/t amount\n"
                ".dice 6/7/9 amount\n"
                ".deathroll @user bo amount\n"

                "```"

            ),

            inline=False
        )

        embed.add_field(

            name="🐉 Games",

            value=(

                "```yaml\n"

                ".randoms @user bo amount\n"
                ".crack @user bo amount\n"
                ".guess number\n"

                "```"

            ),

            inline=False
        )

        embed.add_field(

            name="📊 Profile",

            value=(

                "```yaml\n"

                ".profile\n"
                ".leaderboard\n"
                ".history\n"
                ".ping\n"

                "```"

            ),

            inline=False
        )

        await ctx.send(embed=embed)

    # PROFILE

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

        embed = discord.Embed(

            title=f"{member.display_name}",

            description=(
                f"💵 Cash: "
                f"**{format_cash(cash)}**"
            ),

            color=0x2B2D31
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="🏆 Wins",
            value=stats["wins"]
        )

        embed.add_field(
            name="💀 Losses",
            value=stats["losses"]
        )

        embed.add_field(
            name="📈 Winrate",
            value=f"{stats['winrate']}%"
        )

        embed.add_field(
            name="🔥 Streak",
            value=stats["streak"]
        )

        embed.add_field(
            name="👑 Best",
            value=stats["best_streak"]
        )

        await ctx.send(embed=embed)

    # LEADERBOARD

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):

        users = economy_collection.find()

        data = []

        for user in users:

            data.append(

                (
                    user["user_id"],
                    user.get("cash", 0)
                )

            )

        data.sort(
            key=lambda x: x[1],
            reverse=True
        )

        top = data[:10]

        embed = discord.Embed(
            title="🏆 Richest Players",
            color=0xFEE75C
        )

        lines = []

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        for i, (
            uid,
            cash
        ) in enumerate(top):

            rank = (
                medals[i]
                if i < 3
                else f"`#{i+1}`"
            )

            lines.append(

                f"{rank} <@{uid}>\n"
                f"💵 {format_cash(cash)}"

            )

        embed.description = "\n\n".join(lines)

        await ctx.send(embed=embed)

    # PING

    @commands.command(name="ping")
    async def ping(self, ctx):

        latency = round(
            self.bot.latency * 1000
        )

        embed = discord.Embed(

            description=(
                f"🏓 {latency}ms"
            ),

            color=0x2B2D31
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        System(bot)
    )
