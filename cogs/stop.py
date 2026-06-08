from discord.ext import commands
import discord

from utils.game_state import (
    randoms_games,
    crack_games,
    deathroll_games
)


class Stop(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="stop")
    async def stop(self, ctx):

        channel_id = ctx.channel.id

        stopped = False

        # RANDOMS

        if channel_id in randoms_games:

            del randoms_games[
                channel_id
            ]

            stopped = True

        # CRACK

        if channel_id in crack_games:

            del crack_games[
                channel_id
            ]

            stopped = True

        # DEATHROLL

        if channel_id in deathroll_games:

            del deathroll_games[
                channel_id
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

        await ctx.send(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        Stop(bot)
    )
