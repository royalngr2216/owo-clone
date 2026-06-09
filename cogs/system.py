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

    # Optional role system

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
            title="ECHLEON COMMANDS",
            description=(
                "Use the commands below with the prefix `.`"
            ),
            color=0x5865F2
        )

        # ECONOMY

        embed.add_field(
            name="💰 Economy",
            value=(
                "**`.cash [user]`**\n"
                "View your or another user's balance.\n\n"

                "**`.daily`**\n"
                "Claim daily reward.\n\n"

                "**`.weekly`**\n"
                "Claim weekly reward.\n\n"

                "**`.monthly`**\n"
                "Claim monthly reward.\n\n"

                "**`.give @user amount`**\n"
                "Transfer money to another user.\n\n"

                "**`.rob @user`**\n"
                "Attempt to rob another player."
            ),
            inline=False
        )

        # RANDOMS

        embed.add_field(
            name="🐉 Randoms",
            value=(
                "**`.randoms @user bo amount`**\n"
                "Start a Pokémon random battle.\n\n"

                "`bo` = best of 1 / 3 / 5 / 7 / 9\n\n"

                "**`.pick`**\n"
                "Pick your random Pokémon."
            ),
            inline=False
        )

        # DEATHROLL

        embed.add_field(
            name="💀 Deathroll",
            value=(
                "**`.deathroll @user amount`**\n"
                "Start a deathroll match.\n\n"

                "**`.roll`**\n"
                "Roll the current number."
            ),
            inline=False
        )

        # CRACK

        embed.add_field(
            name="💥 Crack",
            value=(
                "**`.crack @user amount`**\n"
                "Guess the hidden number.\n\n"

                "**`.guess number`**\n"
                "Submit your guess."
            ),
            inline=False
        )

        # CASINO

        embed.add_field(
            name="🎲 Casino",
            value=(
                "**`.dice up amount`**\n"
                "Win if total is 8-12.\n\n"

                "**`.dice down amount`**\n"
                "Win if total is 2-6.\n\n"

                "**`.dice 7 amount`**\n"
                "Exact 7 pays higher.\n\n"

                "**`.cf heads amount`**\n"
                "Coinflip on heads.\n\n"

                "**`.cf tails amount`**\n"
                "Coinflip on tails."
            ),
            inline=False
        )

        # PROFILE

        embed.add_field(
            name="📊 Profile",
            value=(
                "**`.profile [user]`**\n"
                "View player statistics.\n\n"

                "**`.leaderboard`**\n"
                "View richest players."
            ),
            inline=False
        )

        # UTILITY

        embed.add_field(
            name="⚙️ Utility",
            value=(
                "**`.stop`**\n"
                "Force stop active game.\n\n"

                "**`.ping`**\n"
                "View bot latency."
            ),
            inline=False
        )

        embed.set_footer(
            text="Echleon • Discord Gambling Bot"
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
            title="PROFILE",
            description=(
                f"{member.mention}"
            ),
            color=0x2B2D31
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="Wins",
            value=f"**{wins}**",
            inline=True
        )

        embed.add_field(
            name="Losses",
            value=f"**{losses}**",
            inline=True
        )

        embed.add_field(
            name="Matches",
            value=f"**{matches}**",
            inline=True
        )

        embed.add_field(
            name="Win Rate",
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
            title="LEADERBOARD",
            color=0xF1C40F
        )

        text = ""

        for index, user in enumerate(users[:10]):

            user_id = int(user["user_id"])

            cash = user.get(
                "cash",
                0
            )

            fetched_user = self.bot.get_user(user_id)

            if fetched_user:

                name = fetched_user.name

            else:

                name = f"User {user_id}"

            text += (
                f"**#{index+1}** {name}\n"
                f"{format_cash(cash)}\n\n"
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
                    "Active game stopped."
                ),
                color=discord.Color.red()
            )

        else:

            embed = discord.Embed(
                description=(
                    "No active game."
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
                f"Pong: **{latency}ms**"
            ),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        System(bot)
    )
