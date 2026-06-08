from discord.ext import commands
import discord

from utils.economy import (
    get_history,
    format_cash
)


class History(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="history")
    async def history(
        self,
        ctx,
        member: discord.Member = None
    ):

        if member is None:

            member = ctx.author

        data = get_history(member.id)

        if not data:

            embed = discord.Embed(

                description="❌ No history found.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        lines = []

        for entry in data:

            result = entry["result"]

            emoji = (
                "✅"
                if result == "WIN"
                else "❌"
            )

            game = entry["game"]

            amount = format_cash(
                entry["amount"]
            )

            lines.append(

                f"{emoji} "
                f"**{game}** • "
                f"{amount}"

            )

        embed = discord.Embed(

            title=f"📜 {member.display_name} History",

            description="\n".join(lines),

            color=0x5865F2
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        History(bot)
    )
