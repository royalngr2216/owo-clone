from discord.ext import commands
import discord

from utils.stats import get_profile


# ─────────────────────────
# ROLE UPDATE FUNCTION
# ─────────────────────────

async def update_roles(member, matches):

    # OPTIONAL ROLE SYSTEM
    # Add custom rank roles later if wanted

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
                "`.profile @user`"
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


async def setup(bot):

    await bot.add_cog(
        System(bot)
    )
