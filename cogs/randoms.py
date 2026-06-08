from discord.ext import commands
import random
import discord

from data.pokemon import POKEMON_LIST

from utils.stats import (
    record_win,
    record_loss,
    get_profile
)

from cogs.system import update_roles

from utils.game_state import (
    randoms_games
)


SPECIAL_PLAYERS = {

    1287545546231255092,
    711959035238285443
}


SPECIAL_POOL = [

    p for p in POKEMON_LIST
    if 450 <= p.total_stats <= 780
]


# ─────────────────────────
# CONFIRM VIEW
# ─────────────────────────

class RandomsConfirmView(
    discord.ui.View
):

    def __init__(
        self,
        ctx,
        opponent,
        bo
    ):

        super().__init__(timeout=30)

        self.ctx = ctx
        self.opponent = opponent
        self.bo = bo

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user != self.opponent:

            await interaction.response.send_message(
                "❌ This is not for you.",
                ephemeral=True
            )

            return

        if self.ctx.channel.id in randoms_games:

            await interaction.response.send_message(
                "❌ Match already active.",
                ephemeral=True
            )

            return

        wins_required = (
            self.bo // 2
        ) + 1

        randoms_games[
            self.ctx.channel.id
        ] = {

            "player1": self.ctx.author,
            "player2": self.opponent,

            "bo": self.bo,

            "wins_required": wins_required,

            "score1": 0,
            "score2": 0,

            "picks": {}
        }

        embed = discord.Embed(

            title="🐉 RANDOMS",

            description=(

                f"{self.ctx.author.mention} ⚔️ "
                f"{self.opponent.mention}\n\n"

                f"🏆 First to "
                f"**{wins_required}** wins\n\n"

                f"🎮 Use `.pick`"

            ),

            color=discord.Color.purple()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @discord.ui.button(
        label="Decline",
        style=discord.ButtonStyle.danger
    )
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user != self.opponent:

            await interaction.response.send_message(
                "❌ This is not for you.",
                ephemeral=True
            )

            return

        embed = discord.Embed(

            description="❌ Challenge declined.",

            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )


# ─────────────────────────
# RANDOMS
# ─────────────────────────

class Randoms(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ─────────────────────────
    # START GAME
    # ─────────────────────────

    @commands.command(name="randoms")
    async def randoms(
        self,
        ctx,
        opponent: discord.Member,
        bo: int = 1
    ):

        if opponent == ctx.author:

            await ctx.send(
                "You cannot play yourself."
            )

            return

        if opponent.bot:

            await ctx.send(
                "You cannot challenge bots."
            )

            return

        if bo not in [1, 3, 5, 7, 9]:

            await ctx.send(
                "Use: `.randoms @user 1/3/5/7/9`"
            )

            return

        if ctx.channel.id in randoms_games:

            await ctx.send(
                "A randoms game is already active."
            )

            return

        embed = discord.Embed(

            title="🐉 RANDOMS CHALLENGE",

            description=(

                f"{ctx.author.mention} challenged "
                f"{opponent.mention}\n\n"

                f"🏆 Best Of "
                f"**{bo}**"

            ),

            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="Waiting for opponent..."
        )

        await ctx.send(

            embed=embed,

            view=RandomsConfirmView(
                ctx,
                opponent,
                bo
            )
        )

    # ─────────────────────────
    # PICK COMMAND
    # ─────────────────────────

    @commands.command(name="pick")
    async def pick(self, ctx):

        if ctx.channel.id not in randoms_games:

            await ctx.send(
                "No active randoms game."
            )

            return

        game = randoms_games[
            ctx.channel.id
        ]

        if ctx.author not in [

            game["player1"],
            game["player2"]

        ]:

            await ctx.send(
                "You are not in this match."
            )

            return

        if ctx.author in game["picks"]:

            await ctx.send(
                "You already picked."
            )

            return

        # ─────────────────────────
        # SPECIAL PLAYER LUCK
        # ─────────────────────────

        if ctx.author.id in SPECIAL_PLAYERS:

            roll = random.randint(1, 100)

            if roll <= 20:

                pool = [

                    p for p in POKEMON_LIST
                    if 450 <= p.total_stats <= 500
                ]

            elif roll <= 35:

                pool = [

                    p for p in POKEMON_LIST
                    if 500 < p.total_stats <= 530
                ]

            elif roll <= 80:

                pool = [

                    p for p in POKEMON_LIST
                    if 530 < p.total_stats <= 580
                ]

            elif roll <= 92:

                pool = [

                    p for p in POKEMON_LIST
                    if 570 < p.total_stats <= 680
                ]

            else:

                pool = [

                    p for p in POKEMON_LIST
                    if 680 < p.total_stats <= 780
                ]

            if not pool:

                pool = SPECIAL_POOL

            pokemon = random.choice(pool)

        else:

            pokemon = random.choice(
                POKEMON_LIST
            )

        game["picks"][
            ctx.author
        ] = pokemon

        clean_name = (

            pokemon.name.lower()
            .replace(" ", "")
            .replace(".", "")
            .replace("'", "")
        )

        gif_url = (

            "https://play.pokemonshowdown.com/"
            f"sprites/xyani/{clean_name}.gif"
        )

        # ─────────────────────────
        # EMBED COLOR
        # ─────────────────────────

        if pokemon.total_stats < 400:

            embed_color = discord.Color.green()

        elif pokemon.total_stats < 500:

            embed_color = discord.Color.blue()

        else:

            embed_color = discord.Color.red()

        # ─────────────────────────
        # CLEAN POKEMON EMBED
        # ─────────────────────────

        embed = discord.Embed(

            description=(

                f"🎴 {ctx.author.mention} picked\n"
                f"# **{pokemon.name}**\n\n"

                f"💥 Total Power\n"
                f"# **{pokemon.total_stats}**"

            ),

            color=embed_color
        )

        embed.set_image(
            url=gif_url
        )

        await ctx.send(
            embed=embed
        )

        # ─────────────────────────
        # BOTH PICKED
        # ─────────────────────────

        if len(game["picks"]) == 2:

            await self.resolve_round(
                ctx.channel.id
            )

    # ─────────────────────────
    # ROUND RESULT
    # ─────────────────────────

    async def resolve_round(
        self,
        channel_id
    ):

        game = randoms_games[
            channel_id
        ]

        p1 = game["player1"]
        p2 = game["player2"]

        poke1 = game["picks"][p1]
        poke2 = game["picks"][p2]

        channel = self.bot.get_channel(
            channel_id
        )

        if poke1.total_stats > poke2.total_stats:

            game["score1"] += 1

            winner = p1

        elif poke2.total_stats > poke1.total_stats:

            game["score2"] += 1

            winner = p2

        else:

            winner = None

        # ─────────────────────────
        # ROUND RESULT
        # ─────────────────────────

        if winner:

            embed = discord.Embed(

                description=(

                    f"🏆 {winner.mention} "
                    f"wins the round!\n\n"

                    f"📊 Score\n"
                    f"# {game['score1']} - "
                    f"{game['score2']}"

                ),

                color=discord.Color.gold()
            )

        else:

            embed = discord.Embed(

                description="🤝 Round tied!",

                color=discord.Color.light_grey()
            )

        await channel.send(
            embed=embed
        )

        game["picks"] = {}

        # ─────────────────────────
        # MATCH END
        # ─────────────────────────

        if (

            game["score1"]
            == game["wins_required"]

            or

            game["score2"]
            == game["wins_required"]
        ):

            await self.end_match(
                channel_id
            )

    # ─────────────────────────
    # END MATCH
    # ─────────────────────────

    async def end_match(
        self,
        channel_id
    ):

        game = randoms_games[
            channel_id
        ]

        if game["score1"] > game["score2"]:

            winner = game["player1"]
            loser = game["player2"]

        else:

            winner = game["player2"]
            loser = game["player1"]

        # ─────────────────────────
        # SAVE STATS
        # ─────────────────────────

        record_win(
            winner.id,
            0
        )

        record_loss(
            loser.id,
            0
        )

        winner_stats = get_profile(
            winner.id
        )

        loser_stats = get_profile(
            loser.id
        )

        await update_roles(
            winner,
            winner_stats["matches"]
        )

        await update_roles(
            loser,
            loser_stats["matches"]
        )

        # ─────────────────────────
        # RESULT EMBED
        # ─────────────────────────

        embed = discord.Embed(

            description=(

                f"🏆 {winner.mention} "
                f"wins the match!\n\n"

                f"📊 Final Score\n"
                f"# {game['score1']} - "
                f"{game['score2']}"

            ),

            color=discord.Color.gold()
        )

        channel = self.bot.get_channel(
            channel_id
        )

        await channel.send(
            embed=embed
        )

        del randoms_games[
            channel_id
        ]


async def setup(bot):

    await bot.add_cog(
        Randoms(bot)
    )
