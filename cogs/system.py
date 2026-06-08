from discord.ext import commands
import discord

from utils.stats import get_profile
from utils.economy import (
    economy_collection,
    format_cash
)


# ─────────────────────────
# ROLE UPDATE FUNCTION
# ─────────────────────────

async def update_roles(member, matches):

    # OPTIONAL ROLE SYSTEM
    # Customize later if wanted

    return


class System(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ─────────────────────────
    # HELP
    # ─────────────────────────

    @commands.command(name="help")
    async def help(self, ctx):

        embed = discord.Embed(
            title="📖 COMMANDS",
            description=(
                "Use the commands below.\n"
                "Prefix: `.`"
            ),
            color=discord.Color.blurple()
        )

        # ECONOMY

        embed.add_field(
            name="💰 Economy",
            value=(
                "`.cash`\n"
                "`.daily`\n"
                "`.weekly`\n"
                "`.monthly`"
            ),
            inline=False
        )

        # RANDOMS

        embed.add_field(
            name="🐉 Randoms",
            value=(
                "`.randoms @user bo amount`\n"
                "`.pick`"
            ),
            inline=False
        )

        # DEATHROLL

        embed.add_field(
            name="💀 Deathroll",
            value=(
                "`.deathroll @user amount`\n"
                "`.roll`"
            ),
            inline=False
        )

        # DICE

        embed.add_field(
            name="🎲 Dice",
            value=(
                "`.dice up amount`\n"
                "`.dice 7 amount`\n"
                "`.dice down amount`"
            ),
            inline=False
        )

        # CRACK

        embed.add_field(
            name="💥 Crack",
            value=(
                "`.crack @user amount`\n"
                "`.guess number`"
            ),
            inline=False
        )

        # PROFILE

        embed.add_field(
            name="📊 Profile",
            value=(
                "`.profile`\n"
                "`.leaderboard`"
            ),
            inline=False
        )

        # STOP

        embed.add_field(
            name="🛑 Utility",
            value=(
                "`.stop`\n"
                "`.ping`"
            ),
            inline=False
        )

        embed.set_footer(
            text="Made with discord.py"
        )

        await ctx.send(embed=embed)

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

        wins = stats["wins"]
        losses = stats["losses"]
        matches = stats["matches"]

        if matches > 0:

            winrate = round(
                (wins / matches) * 100,
                1
            )

        else:

            winrate = 0

        embed = discord.Embed(
            title="📊 PROFILE",
            description=(
                f"{member.mention}"
            ),
            color=discord.Color.dark_embed()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="🏆 Wins",
            value=f"**{wins}**",
            inline=True
        )

        embed.add_field(
            name="❌ Losses",
            value=f"**{losses}**",
            inline=True
        )

        embed.add_field(
            name="🎮 Matches",
            value=f"**{matches}**",
            inline=True
        )

        embed.add_field(
            name="📈 Winrate",
            value=f"**{winrate}%**",
            inline=False
        )

        await ctx.send(embed=embed)

    # ─────────────────────────
    # LEADERBOARD
    # ─────────────────────────

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):

        users = list(
            economy_collection.find()
        )

        users.sort(
            key=lambda x: x.get(
                "cash",
                0
            ),
            reverse=True
        )

        embed = discord.Embed(
            title="🏆 LEADERBOARD",
            color=discord.Color.gold()
        )

        text = ""

        for index, user in enumerate(users[:10]):

            user_id = user["user_id"]

            cash = user.get(
                "cash",
                0
            )

            text += (
                f"**#{index+1}** "
                f"<@{user_id}>\n"
                f"💵 {format_cash(cash)}\n\n"
            )

        if text == "":

            text = "No data."

        embed.description = text

        await ctx.send(embed=embed)

    # ─────────────────────────
    # STOP
    # ─────────────────────────

    @commands.command(name="stop")
    async def stop(self, ctx):

        from utils.game_state import (
            randoms_games,
            deathroll_games,
            crack_games
        )

        stopped = False

        # RANDOMS

        if ctx.channel.id in randoms_games:

            del randoms_games[
                ctx.channel.id
            ]

            stopped = True

        # DEATHROLL

        if ctx.channel.id in deathroll_games:

            del deathroll_games[
                ctx.channel.id
            ]

            stopped = True

        # CRACK

        if ctx.channel.id in crack_games:

            del crack_games[
                ctx.channel.id
            ]

            stopped = True

        # RESULT

        if stopped:

            embed = discord.Embed(
                description=(
                    "🛑 Active game stopped."
                ),
                color=discord.Color.red()
            )

        else:

            embed = discord.Embed(
                description=(
                    "❌ No active game."
                ),
                color=discord.Color.red()
            )

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
                f"🏓 Pong!\n"
                f"**{latency}ms**"
            ),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        System(bot)
    )
