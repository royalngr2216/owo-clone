from discord.ext import commands
import discord

from utils.economy import (
ensure_account,
economy_collection,
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

    user = ensure_account(
        member.id
    )

    history = user.get(
        "history",
        []
    )

    if not history:

        embed = discord.Embed(
            description=(
                "📜 No history found."
            ),
            color=0x2B2D31
        )

        return await ctx.send(
            embed=embed
        )

    embed = discord.Embed(
        title="📜 Match History",
        description=member.display_name,
        color=0x2B2D31
    )

    lines = []

    game_icons = {

        "coinflip": "🪙",
        "dice": "🎲",
        "deathroll": "💀",
        "crack": "🎯",
        "randoms": "🐉",
        "average": "📊",
        "jackpot": "🎰"
    }

    for entry in history[:10]:

        game = entry["game"]

        icon = game_icons.get(
            game,
            "🎮"
        )

        result = entry["result"]

        amount = format_cash(
            entry["amount"]
        )

        opponent = entry["opponent"]

        if result == "win":

            line = (
                f"{icon} **{game.title()}**\n"
                f"✅ Won {amount}\n"
                f"vs <@{opponent}>"
            )

        else:

            line = (
                f"{icon} **{game.title()}**\n"
                f"❌ Lost {amount}\n"
                f"vs <@{opponent}>"
            )

        lines.append(line)

    embed.description = "\n\n".join(
        lines
    )

    embed.set_footer(
        text=f"Showing {min(len(history), 10)} recent matches"
    )

    await ctx.send(embed=embed)

async def setup(bot):

await bot.add_cog(
    History(bot)
)
