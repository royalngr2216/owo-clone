from discord.ext import commands
import discord
from datetime import datetime

from utils.stats import get_profile
from utils.economy import (
    economy_collection,
    format_cash
)
from utils.items import ALL_ITEMS

from utils.workers import (
    WORKER_LEVELS,
    WORKER_VALUES
)
from utils.achievements import (
    COMMON_ACHIEVEMENTS,
    RARE_ACHIEVEMENTS,
    LEGENDARY_ACHIEVEMENTS
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
        ".sell all all for selling all.\n\n"

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
        "Go hunting for rewards.\n\n"

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
        "View richest players.\n\n"

         "**.quests**\n"
        "View all quests and rewards."
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


        # ─────────────────────────
        # CASH
        # ─────────────────────────

        cash = user_data.get(
            "cash",
            0
        )


        # ─────────────────────────
        # PROFILE STATS
        # ─────────────────────────

        games_played = stats.get(
            "games_played",
            0
        )

        total_gambled = stats.get(
            "total_gambled",
            0
        )

        biggest_win = stats.get(
            "biggest_win",
            0
        )

        total_mines = stats.get(
            "total_mines",
            0
        )

        total_fishes = stats.get(
            "total_fishes",
            0
        )

        total_hunts = stats.get(
            "total_hunts",
            0
        )

        total_jobs = stats.get(
            "total_jobs",
            0
        )


        # ─────────────────────────
        # INVENTORY VALUE
        # ─────────────────────────

        inventory = user_data.get(
            "inventory",
            {}
        )

        inventory_value = 0


        for item_name, amount in inventory.items():

            if item_name in ALL_ITEMS:

                inventory_value += (

                    ALL_ITEMS[item_name]["price"]

                    * amount
                )


        # ─────────────────────────
        # WORKERS
        # ─────────────────────────

        workers = user_data.get(
            "workers",
            {}
        )

        workers_owned = len(workers)

        worker_income = 0
        workers_value = 0


        for worker in workers.values():

            level = worker.get(
                "level",
                1
            )

            worker_income += (

                WORKER_LEVELS[level]["income"]

            )

            workers_value += (

                WORKER_VALUES[level]

            )


        # ─────────────────────────
        # SHOP VALUE
        # ─────────────────────────

        shop_value = 0


        if user_data.get("shovel"):

            shop_value += 3_000_000


        if user_data.get("lock_and_key"):

            shop_value += 2_500_000


        # ─────────────────────────
        # NET WORTH
        # ─────────────────────────

        networth = (

            cash

            + inventory_value

            + workers_value

            + shop_value
        )


        # ─────────────────────────
        # PADLOCK
        # ─────────────────────────

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


        # ─────────────────────────
        # EMBED
        # ─────────────────────────

        embed = discord.Embed(

            title=f"{member.name.upper()}'S PROFILE",

            description=member.mention,

            color=0x2B2D31
        )


        embed.set_thumbnail(
            url=member.display_avatar.url
        )


        # CASH

        embed.add_field(

            name="💰 Cash",

            value=f"**{format_cash(cash)}**",

            inline=False
        )


        # INVENTORY

        embed.add_field(

            name="📦 Inventory Value",

            value=f"**{format_cash(inventory_value)}**",

            inline=False
        )


        # NET WORTH

        embed.add_field(

            name="💎 Net Worth",

            value=f"**{format_cash(networth)}**",

            inline=False
        )


        # GAMBLING

        embed.add_field(

            name="🎰 Gambling",

            value=(

                f"🎮 Games: **{games_played}**\n"
                f"💸 Gambled: **{format_cash(total_gambled)}**\n"
                f"🏆 Biggest Win: "
                f"**{format_cash(biggest_win)}**"

            ),

            inline=False
        )


        # WORKERS

        embed.add_field(

            name="⚒ Workers",

            value=(

                f"👷 Owned: **{workers_owned}**\n"
                f"💰 Value: "
                f"**{format_cash(workers_value)}**\n"
                f"💵 Income/Day: "
                f"**{format_cash(worker_income)}**"

            ),

            inline=False
        )


        # ACTIVITIES

        embed.add_field(

            name="🌎 Activities",

            value=(

                f"⛏ **{total_mines}**  "
                f"🎣 **{total_fishes}**  "
                f"🏹 **{total_hunts}**  "
                f"💼 **{total_jobs}**"

            ),

            inline=False
        )
        # ─────────────────────────
        # COMPLETED ACHIEVEMENTS
        # ─────────────────────────

        claimed = user_data.get(
            "claimed_achievements",
            []
        )

        achievement_text = ""


        for achievement_id in claimed:

            if achievement_id in LEGENDARY_ACHIEVEMENTS:

                achievement_text += (

                    f"🟡 "
                    f"{LEGENDARY_ACHIEVEMENTS[achievement_id]['name']}\n"

                )

            elif achievement_id in RARE_ACHIEVEMENTS:

                achievement_text += (

                    f"🟣 "
                    f"{RARE_ACHIEVEMENTS[achievement_id]['name']}\n"

                )

            elif achievement_id in COMMON_ACHIEVEMENTS:

                achievement_text += (

                    f"⚪ "
                    f"{COMMON_ACHIEVEMENTS[achievement_id]['name']}\n"

                )


        if achievement_text == "":

            achievement_text = "❌ None"


        embed.add_field(

            name="🏆 Completed Achievements",

            value=achievement_text,

            inline=False
        )
        # PROTECTION

        embed.add_field(

            name="🛡 Protection",

            value=protection,

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

                f"**#{index + 1} {name}**\n"
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
