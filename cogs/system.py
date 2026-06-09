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

            title="Commands",

            description=(
                "Prefix: `.`"
            ),

            color=discord.Color.blurple()
        )


        embed.add_field(

            name="Economy",

            value=(
                "`.cash`\n"
                "`.daily`\n"
                "`.weekly`\n"
                "`.monthly`\n"
                "`.rob`\n"
                "`.give`"
            ),

            inline=False
        )


        embed.add_field(

            name="Games",

            value=(
                "`.randoms @user bo amount`\n"
                "`.pick`\n\n"

                "`.deathroll @user amount`\n"
                "`.roll`\n\n"

                "`.crack @user amount`\n"
                "`.guess number`\n\n"

                "`.dice up amount`\n"
                "`.dice 7 amount`\n"
                "`.dice down amount`\n\n"

                "`.cf heads amount`\n"
                "`.cf tails amount`"
            ),

            inline=False
        )


        embed.add_field(

            name="Profile",

            value=(
                "`.profile`\n"
                "`.leaderboard`"
            ),

            inline=False
        )


        embed.add_field(

            name="Utility",

            value=(
                "`.stop`\n"
                "`.ping`"
            ),

            inline=False
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

            title="Profile",

            description=member.mention,

            color=discord.Color.dark_embed()
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
            name="Winrate",
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

            economy_collection.find({

                "cash": {
                    "$gte": 0
                }

            })

        )


        users.sort(

            key=lambda x: x.get(
                "cash",
                0
            ),

            reverse=True
        )


        embed = discord.Embed(

            title="Leaderboard",

            color=discord.Color.gold()
        )


        text = ""


        for index, user in enumerate(users[:10]):

            user_id = int(user["user_id"])

            cash = user.get(
                "cash",
                0
            )


            member = self.bot.get_user(user_id)


            if member:

                name = member.name

            else:

                name = f"Unknown User"


            text += (

                f"**#{index+1}** "
                f"**{name}**\n"

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

                description="Game stopped.",

                color=discord.Color.red()
            )

        else:

            embed = discord.Embed(

                description="No active game.",

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
