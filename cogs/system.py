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
    # HELP
    # ─────────────────────────

    @commands.command(name="help")
    async def help(self, ctx):

        embed = discord.Embed(

            title="👑 ROYAL BOT",

            description=(

                ">>> "
                "**Gambling Bot**\n"
                "Challenge players, gamble cash,\n"
                "Climb leaderboards and dominate."

            ),

            color=0x5865F2
        )

        embed.add_field(

            name="💸 ECONOMY",

            value=(

                "```yaml\n"

                ".cash\n"
                ".daily\n"
                ".weekly\n"
                ".monthly\n"
                ".give @user amount\n"

                "```"

            ),

            inline=True
        )

        embed.add_field(

            name="🎲 SOLO GAMBLING",

            value=(

                "```yaml\n"

                ".cf h/t amount\n"
                ".dice down amount\n"
                ".dice 7 amount\n"
                ".dice up amount\n"

                "```"

            ),

            inline=True
        )

        embed.add_field(

            name="⚔️ GAMBLING GAMES",

            value=(

                "```yaml\n"

                ".randoms @user bo amount\n"
                ".crack @user bo amount\n"
                ".deathroll @user bo amount\n"

                "```"

            ),

            inline=False
        )

        embed.add_field(

            name="🎮 MATCH COMMANDS",

            value=(

                "```yaml\n"

                ".pick\n"
                ".guess number\n"
                ".roll\n"
                ".stop\n"

                "```"

            ),

            inline=True
        )

        embed.add_field(

            name="📊 PROFILE",

            value=(

                "```yaml\n"

                ".profile\n"
                ".leaderboard\n"
                ".history\n"
                ".ping\n"

                "```"

            ),

            inline=True
        )

        embed.add_field(

            name="💰 CASH EXAMPLES",

            value=(

                "```yaml\n"

                "10k = 10,000\n"
                "1m = 1,000,000\n"
                "1b = 1,000,000,000\n"

                "```"

            ),

            inline=False
        )

        embed.set_footer(

            text=(
                f"Requested by "
                f"{ctx.author.display_name}"
            ),

            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(
            embed=embed
        )

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

        stats = get_profile(
            member.id
        )

        cash = get_cash(
            member.id
        )

        embed = discord.Embed(

            title=f"👤 {member.display_name}",

            description=(

                f"💵 Cash\n"
                f"# {format_cash(cash)}"

            ),

            color=0x2B2D31
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="🏆 Wins",
            value=f"**{stats['wins']}**",
            inline=True
        )

        embed.add_field(
            name="💀 Losses",
            value=f"**{stats['losses']}**",
            inline=True
        )

        embed.add_field(
            name="📈 Winrate",
            value=f"**{stats['winrate']}%**",
            inline=True
        )

        embed.add_field(
            name="🔥 Streak",
            value=f"**{stats['streak']}**",
            inline=True
        )

        embed.add_field(
            name="👑 Best Streak",
            value=f"**{stats['best_streak']}**",
            inline=True
        )

        embed.add_field(
            name="🎮 Matches",
            value=f"**{stats['matches']}**",
            inline=True
        )

        await ctx.send(
            embed=embed
        )

    # ─────────────────────────
    # LEADERBOARD
    # ─────────────────────────

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

            title="🏆 RICHEST PLAYERS",

            description=(
                ">>> Top richest players\n"
                "across the server."
            ),

            color=0xFEE75C
        )

        medals = [

            "🥇",
            "🥈",
            "🥉"
        ]

        lines = []

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
                f"💵 **{format_cash(cash)}**"

            )

        embed.description += (
            "\n\n" +
            "\n\n".join(lines)
        )

        await ctx.send(
            embed=embed
        )

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
                f"🏓 Pong!\n"
                f"## {latency}ms"
            ),

            color=0x57F287
        )

        await ctx.send(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        System(bot)
    )
