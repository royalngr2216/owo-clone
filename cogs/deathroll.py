from discord.ext import commands
import discord
import random

from utils.economy import (
    create_account,
    get_cash,
    add_cash,
    remove_cash,
    format_cash
)

from utils.stats import (
    record_win,
    record_loss
)

from utils.game_state import (
    deathroll_games
)


# ─────────────────────────
# CONFIRM VIEW
# ─────────────────────────

class DeathrollConfirmView(
    discord.ui.View
):

    def __init__(
        self,
        ctx,
        opponent,
        amount
    ):

        super().__init__(
            timeout=60
        )

        self.ctx = ctx

        self.opponent = opponent

        self.amount = amount


    # ─────────────────────────
    # ACCEPT
    # ─────────────────────────

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.opponent.id:

            await interaction.response.send_message(

                "You are not the challenged user.",

                ephemeral=True
            )

            return


        if self.ctx.channel.id in deathroll_games:

            await interaction.response.send_message(

                "A deathroll game is already active.",

                ephemeral=True
            )

            return


        deathroll_games[
            self.ctx.channel.id
        ] = {

            "player1": self.ctx.author,

            "player2": self.opponent,

            "turn": self.ctx.author,

            "current": 100,

            "bet": self.amount
        }


        embed = discord.Embed(

            title="💀 DEATHROLL",

            description=(

                f"{self.ctx.author.mention} ⚔️ "
                f"{self.opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(self.amount)}**\n\n"

                f"🎲 Starting Number: "
                f"**100**\n\n"

                f"🎮 Use `.roll`"

            ),

            color=discord.Color.red()
        )


        await interaction.response.edit_message(

            embed=embed,

            view=None
        )


    # ─────────────────────────
    # DECLINE
    # ─────────────────────────

    @discord.ui.button(
        label="Decline",
        style=discord.ButtonStyle.red,
        emoji="❌"
    )
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.opponent.id:

            await interaction.response.send_message(

                "You are not the challenged user.",

                ephemeral=True
            )

            return


        embed = discord.Embed(

            description=(

                f"{self.opponent.mention} "
                f"declined the challenge."

            ),

            color=discord.Color.red()
        )


        await interaction.response.edit_message(

            embed=embed,

            view=None
        )


    # ─────────────────────────
    # TIMEOUT
    # ─────────────────────────

    async def on_timeout(self):

        for item in self.children:

            item.disabled = True

        try:

            await self.message.edit(
                view=self
            )

        except:

            pass


# ─────────────────────────
# DEATHROLL COG
# ─────────────────────────

class Deathroll(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ─────────────────────────
    # DEATHROLL
    # ─────────────────────────

    @commands.command(name="deathroll")
    async def deathroll(
        self,
        ctx,
        opponent: discord.Member,
        amount: str
    ):

        if opponent == ctx.author:

            await ctx.send(
                "You cannot play yourself."
            )

            return


        if ctx.channel.id in deathroll_games:

            await ctx.send(
                "A deathroll game is already active."
            )

            return


        amount = amount.lower()

        if amount.endswith("k"):

            amount = int(
                float(amount[:-1]) * 1000
            )

        elif amount.endswith("m"):

            amount = int(
                float(amount[:-1]) * 1000000
            )

        else:

            amount = int(amount)


        if amount <= 0:

            await ctx.send(
                "Amount must be greater than 0."
            )

            return


        create_account(ctx.author.id)
        create_account(opponent.id)


        if get_cash(ctx.author.id) < amount:

            await ctx.send(
                f"{ctx.author.mention} does not have enough cash."
            )

            return


        if get_cash(opponent.id) < amount:

            await ctx.send(
                f"{opponent.mention} does not have enough cash."
            )

            return


        # ─────────────────────────
        # CONFIRM EMBED
        # ─────────────────────────

        embed = discord.Embed(

            title="💀 DEATHROLL CHALLENGE",

            description=(

                f"{ctx.author.mention} "
                f"challenged "
                f"{opponent.mention}\n\n"

                f"💵 Wager: "
                f"**{format_cash(amount)}**\n\n"

                f"Do you accept?"

            ),

            color=discord.Color.red()
        )


        view = DeathrollConfirmView(

            ctx,
            opponent,
            amount
        )


        message = await ctx.send(

            embed=embed,

            view=view
        )


        view.message = message


    # ─────────────────────────
    # ROLL
    # ─────────────────────────

    @commands.command(name="roll")
    async def roll(self, ctx):

        if ctx.channel.id not in deathroll_games:

            await ctx.send(
                "No active deathroll game."
            )

            return


        game = deathroll_games[
            ctx.channel.id
        ]


        if ctx.author != game["turn"]:

            await ctx.send(
                "It is not your turn."
            )

            return


        rolled = random.randint(
            1,
            game["current"]
        )


        embed = discord.Embed(

            description=(

                f"🎲 {ctx.author.mention} rolled\n"
                f"# **{rolled}**"

            ),

            color=discord.Color.orange()
        )


        await ctx.send(embed=embed)


        # ─────────────────────────
        # PLAYER LOSES
        # ─────────────────────────

        if rolled == 1:

            loser = ctx.author


            if loser == game["player1"]:

                winner = game["player2"]

            else:

                winner = game["player1"]


            amount = game["bet"]


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


            end_embed = discord.Embed(

                title="☠️ DEATHROLL OVER",

                description=(

                    f"{loser.mention} rolled "
                    f"**1**\n\n"

                    f"🏆 Winner: "
                    f"{winner.mention}\n"

                    f"💵 Won: "
                    f"**{format_cash(amount)}**"

                ),

                color=discord.Color.dark_red()
            )


            await ctx.send(
                embed=end_embed
            )


            del deathroll_games[
                ctx.channel.id
            ]

            return


        # ─────────────────────────
        # NEXT TURN
        # ─────────────────────────

        game["current"] = rolled


        if game["turn"] == game["player1"]:

            game["turn"] = game["player2"]

        else:

            game["turn"] = game["player1"]


async def setup(bot):

    await bot.add_cog(
        Deathroll(bot)
    )
