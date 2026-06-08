from discord.ext import commands
import discord
import random

from data.pokemon import POKEMON_LIST

from utils.game_state import (
    randoms_games
)

from utils.economy import (
    get_cash,
    remove_cash,
    add_cash,
    format_cash,
    add_history
)

from utils.stats import (
    record_win,
    record_loss
)


class Randoms(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="randoms")
    async def randoms(
        self,
        ctx,
        opponent: discord.Member,
        bo: int,
        amount: int
    ):

        if opponent.bot:

            return

        if opponent == ctx.author:

            return

        if bo not in [1, 3, 5]:

            embed = discord.Embed(

                description=(
                    "Use:\n"
                    "`.randoms @user 1/3/5 amount`"
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if ctx.channel.id in randoms_games:

            embed = discord.Embed(

                description="❌ Game already active.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        cash1 = get_cash(ctx.author.id)
        cash2 = get_cash(opponent.id)

        if cash1 < amount:

            embed = discord.Embed(

                description=(
                    f"{ctx.author.mention} "
                    f"doesn't have enough cash."
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        if cash2 < amount:

            embed = discord.Embed(

                description=(
                    f"{opponent.mention} "
                    f"doesn't have enough cash."
                ),

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        wins_required = (
            bo // 2
        ) + 1

        randoms_games[ctx.channel.id] = {

            "player1": ctx.author,
            "player2": opponent,

            "amount": amount,

            "wins_required": wins_required,

            "score1": 0,
            "score2": 0
        }

        embed = discord.Embed(

            title="🐉 RANDOMS",

            description=(

                f"{ctx.author.mention} ⚔️ "
                f"{opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(amount)}**\n\n"

                f"🏆 First to "
                f"**{wins_required}** wins\n\n"

                f"Both players use `.pick`"

            ),

            color=0x5865F2
        )

        await ctx.send(embed=embed)

    @commands.command(name="pick")
    async def pick(self, ctx):

        if ctx.channel.id not in randoms_games:

            return

        game = randoms_games[ctx.channel.id]

        if ctx.author not in [

            game["player1"],
            game["player2"]

        ]:

            return

        if "picks" not in game:

            game["picks"] = {}

        if ctx.author.id in game["picks"]:

            return

        pokemon = random.choice(
            POKEMON_LIST
        )

        game["picks"][ctx.author.id] = pokemon

        embed = discord.Embed(

            title=f"{pokemon.name}",

            description=(
                f"💥 Total Power\n"
                f"## {pokemon.total_stats}"
            ),

            color=0x5865F2
        )

        clean_name = (
            pokemon.name.lower()
            .replace(" ", "")
            .replace(".", "")
            .replace("'", "")
        )

        gif = (
            "https://play.pokemonshowdown.com/"
            f"sprites/xyani/{clean_name}.gif"
        )

        embed.set_image(url=gif)

        await ctx.send(
            f"{ctx.author.mention}",
            embed=embed
        )

        if len(game["picks"]) == 2:

            await self.resolve_game(
                ctx.channel.id
            )

    async def resolve_game(
        self,
        channel_id
    ):

        game = randoms_games[channel_id]

        p1 = game["player1"]
        p2 = game["player2"]

        poke1 = game["picks"][p1.id]
        poke2 = game["picks"][p2.id]

        if poke1.total_stats > poke2.total_stats:

            winner = p1
            loser = p2

            game["score1"] += 1

        elif poke2.total_stats > poke1.total_stats:

            winner = p2
            loser = p1

            game["score2"] += 1

        else:

            embed = discord.Embed(

                description="🤝 Round tied.",

                color=0xFEE75C
            )

            channel = self.bot.get_channel(
                channel_id
            )

            await channel.send(embed=embed)

            game["picks"] = {}

            return

        embed = discord.Embed(

            title="🏆 ROUND WINNER",

            description=(

                f"{winner.mention}\n\n"

                f"📊 Score\n"
                f"**{game['score1']} - "
                f"{game['score2']}**"

            ),

            color=0x57F287
        )

        channel = self.bot.get_channel(
            channel_id
        )

        await channel.send(embed=embed)

        game["picks"] = {}

        if (
            game["score1"]
            >= game["wins_required"]
            or
            game["score2"]
            >= game["wins_required"]
        ):

            await self.end_match(
                channel_id,
                winner,
                loser
            )

    async def end_match(
        self,
        channel_id,
        winner,
        loser
    ):

        game = randoms_games[channel_id]

        amount = game["amount"]

        remove_cash(
            loser.id,
            amount
        )

        add_cash(
            winner.id,
            amount
        )

        record_win(
            winner.id,
            amount
        )

        record_loss(
            loser.id,
            amount
        )

        add_history(
            winner.id,
            "Randoms",
            "WIN",
            amount,
            loser.id
        )

        add_history(
            loser.id,
            "Randoms",
            "LOSS",
            amount,
            winner.id
        )

        embed = discord.Embed(

            title="👑 MATCH WINNER",

            description=(

                f"{winner.mention}\n\n"

                f"💵 Won "
                f"**{format_cash(amount)}**"

            ),

            color=0xFEE75C
        )

        channel = self.bot.get_channel(
            channel_id
        )

        await channel.send(embed=embed)

        del randoms_games[channel_id]


async def setup(bot):

    await bot.add_cog(
        Randoms(bot)
    )
