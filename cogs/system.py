from discord.ext import commands
import discord
from datetime import datetime

from utils.stats import get_profile
from utils.economy import (
    economy_collection,
    format_cash
)


# ─────────────────────────
# ROLE UPDATE
# ─────────────────────────

async def update_roles(member, matches):

    return


# ─────────────────────────
# HELP DROPDOWN
# ─────────────────────────

HELP_CATEGORIES = {

    "💰 Economy": (

        "**.cash [user]**\n"
        "View balances.\n\n"

        "**.daily**\n"
        "Claim daily reward.\n\n"

        "**.weekly**\n"
        "Claim weekly reward.\n\n"

        "**.monthly**\n"
        "Claim monthly reward.\n\n"

        "**.give @user amount**\n"
        "Transfer money.\n\n"

        "**.rob @user**\n"
        "Attempt a robbery."
    ),

    "🎒 Items": (

        "**.shop**\n"
        "Open the item shop.\n\n"

        "**.inventory**\n"
        "View collected items.\n\n"

        "**.sell item amount**\n"
        "Sell inventory items.\n\n"
        ".sell all all for sellimg all.\n\n"

        "**.padlock**\n"
        "View protection status."
    ),

    "⚒ Workers": (

        "**.workers**\n"
        "View all workers.\n\n"

        "**.claim**\n"
        "Claim worker earnings.\n\n"

        "**.upgrade worker-1**\n"
        "Upgrade a worker."
    ),

    "🌎 Activities": (

        "**.job**\n"
        "Work for money.\n\n"

        "**.fish**\n"
        "Go fishing for rewards.\n\n"

        "**.hunt**\n"
        "Go hunting for rewards."

        "**.mine**\n"
        "Go mining for very high rewards."
    ),

    "🎮 Games": (

        "**.randoms @user bo amount**\n"
        "Pokémon random battle.\n\n"

        "**.deathroll @user bo amount**\n"
        "Start a deathroll match.\n\n"

        "**.crack @user bo amount**\n"
        "Guess the hidden number."
    ),

    "🎲 Casino": (

    "**.dice up amount**\n"
    "Win on 8-12.\n\n"

    "**.dice down amount**\n"
    "Win on 2-6.\n\n"

    "**.dice 7 amount**\n"
    "Exact 7 payout.\n\n"
    "Get 7x on win.\n\n"

    "**.cf heads amount**\n"
    "Coinflip heads.\n\n"

    "**.cf tails amount**\n"
    "Coinflip tails.\n\n"

    "**.slots amount**\n"
    "Play the slot machine."
    ),  

    "📊 Profile": (

        "**.profile [user]**\n"
        "View player stats.\n\n"

        "**.leaderboard**\n"
        "View richest players."
    ),

    "⚙ Utility": (

        "**.ping**\n"
        "View bot latency.\n\n"

        "**.stop**\n"
        "Force stop active game."
    )
}


class HelpDropdown(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label=category,
                description=f"View {category} commands"
            )

            for category in HELP_CATEGORIES
        ]

        super().__init__(

            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        category = self.values[0]

        embed = discord.Embed(

            title=category,

            description=HELP_CATEGORIES[category],

            color=0x5865F2
        )

        embed.set_footer(
            text="ECHLEON Economy System"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


class HelpView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=180)

        self.add_item(
            HelpDropdown()
        )


# ─────────────────────────
# SYSTEM COG
# ─────────────────────────

class System(commands.Cog):

    def __init__(self, bot):

        self.bot = bot


    # ─────────────────────────
    # HELP
    # ─────────────────────────

    @commands.command(name="help")
    async def help(self, ctx):

        embed = discord.Embed(

            title="ECHLEON HELP",

            description=(

                "Modern economy system with games, "
                "workers, activities, inventory and more.\n\n"

                "Select a category below."

            ),

            color=0x5865F2
        )

        embed.set_footer(
            text="ECHLEON Economy System"
        )

        await ctx.send(

            embed=embed,
            view=HelpView()
        )


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


        stats = get_profile(member.id)

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


        user_data = economy_collection.find_one({

            "user_id": str(member.id)

        })


        if not user_data:

            user_data = {}


        padlock_until = user_data.get(
            "padlock_until",
            0
        )


        current_time = int(
            datetime.now().timestamp()
        )


        if padlock_until > current_time:

            remaining = (
                padlock_until - current_time
            ) // 86400

            protection = (
                f"🛡 Active ({remaining}d)"
            )

        else:

            protection = "❌ None"


        embed = discord.Embed(

            title="PROFILE",

            description=member.mention,

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
            inline=True
        )

        embed.add_field(
            name="Protection",
            value=protection,
            inline=True
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
                    "$gt": 0
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

                f"**#{index + 1}** {name}\n"
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


        if ctx.channel.id in randoms_games:

            del randoms_games[
                ctx.channel.id
            ]

            stopped = True


        if ctx.channel.id in deathroll_games:

            del deathroll_games[
                ctx.channel.id
            ]

            stopped = True


        if ctx.channel.id in crack_games:

            del crack_games[
                ctx.channel.id
            ]

            stopped = True


        if stopped:

            embed = discord.Embed(

                description="🛑 Active game stopped.",

                color=0xED4245
            )

        else:

            embed = discord.Embed(

                description="❌ No active game.",

                color=0xED4245
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
                f"🏓 Pong: **{latency}ms**"
            ),

            color=0x57F287
        )


        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        System(bot)
        )
