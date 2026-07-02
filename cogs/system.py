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
from utils.titles import get_equipped
from utils.leaderboard_render import render_leaderboard

# ─────────────────────────
# ROLE UPDATE
# ─────────────────────────

async def update_roles(member, matches):
    return


# ─────────────────────────
# HELP CATEGORIES
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
        "Transfer money but has limits.\n\n"
        "**.donate @user amount**\n"
        "Donates money.\n\n"
        "**.rob @user**\n"
        "Attempt a robbery."
    ),

    "🎒 Items": (
        "**.shop**\n"
        "Open the item shop, including the 🎾 Poké Mart for buying balls.\n\n"
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
        "**.cf h/t amount**\n"
        "Coinflip heads or tails.\n\n"
        "**.blackjack amount**\n"
        "Play a blackjack game with hit/stand/double.\n\n"
        "**.crash amount**\n"
        "Play a plane crash game, higher risk = higher payout.\n\n"
        "**.guessnumber amount**\n"
        "The faster you guess, the better rewards.\n\n"
        "**.mines amount**\n"
        "Play Original Mines Game, has better rewards.\n\n"
        "**.highlow amount**\n"
        "Bet by guessing higher or lower number next turn.\n\n"
        "**.lottery amount**\n"
        "Takes part in the lottery, higher amount = more chances of winning.\n\n"
        "**.slots amount**\n"
        "Play the slot machine." 
    ),

        "🐉 Pokemon": (
        "**.catch <pb/ub/mb> <name>**\n"
        "Catch the wild Pokémon currently in the channel using a Poké/Ultra/Master Ball.\n\n"
        "**.balls [user]**\n"
        "View your (or another trainer's) Poké Ball inventory.\n\n"
        "**.pokemons [user]**\n"
        "View your (or another trainer's) Pokémon collection.\n\n"
        "**.team [p1, p2, ...]**\n"
        "View or set your active battle team (up to 6 Pokémon).\n\n"
        "**.moves <pokémon> <m1, m2...>**\n"
        "Teach a Pokémon up to 4 moves from its official learnset.\n\n"
        "**.moveset <pokémon> [user]**\n"
        "View a Pokémon's current assigned moveset.\n\n"
        "**.battle @user [amount]**\n"
        "Challenge a trainer to a Pokémon battle (with an optional cash wager).\n\n"
        "**.pokemart**\n"
        "Browse the global Pokémon marketplace for active listings.\n\n"
        "**.pokecheck @user**\n"
        "View all market listings posted by a specific trainer.\n\n"
        "**.pokemon sell <pokemon> <price>**\n"
        "List one of your Pokémon for sale in the market.\n\n"
        "**.pokemon buy @user <pokemon>**\n"
        "Buy a listed Pokémon from another trainer.\n\n"
        "**.emiel**\n"
        "View Emiel's global activity feed (recent steals and sales).\n\n"
        "**.emiel sell <pokemon>**\n"
        "Instantly sell a Pokémon to Emiel for a rarity-based payout.\n\n"
        "**.setspawnchannel**\n"
        "Admin: Set the current channel for automatic 10-minute Pokémon spawns.\n\n"
        "**.spawntest**\n"
        "Admin: Force a wild Pokémon to spawn immediately."
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
    ),
}


# ─────────────────────────
# HELP DROPDOWN
# ─────────────────────────

class HelpDropdown(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(
                label=category,
                description=f"View {category} commands",
            )
            for category in HELP_CATEGORIES
        ]
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(
            title=category,
            description=HELP_CATEGORIES[category],
            color=0x5865F2,
        )
        embed.set_footer(text="ECHLEON Economy System")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())


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
            color=0x5865F2,
        )
        embed.set_footer(text="ECHLEON Economy System")
        await ctx.send(embed=embed, view=HelpView())


    # ─────────────────────────
    # PROFILE
    # ─────────────────────────

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):

        if member is None:
            member = ctx.author

        stats   = get_profile(member.id)
        wins    = stats["wins"]
        losses  = stats["losses"]
        matches = stats["matches"]

        winrate = round((wins / matches) * 100, 1) if matches > 0 else 0

        user_data = economy_collection.find_one({"user_id": str(member.id)}) or {}

        # ── Cash ──────────────────────────────────────────────────
        cash = user_data.get("cash", 0)

        # ── Profile stats ─────────────────────────────────────────
        games_played  = stats.get("games_played",  0)
        total_gambled = stats.get("total_gambled",  0)
        biggest_win   = stats.get("biggest_win",    0)
        total_mines   = stats.get("total_mines",    0)
        total_fishes  = stats.get("total_fishes",   0)
        total_hunts   = stats.get("total_hunts",    0)
        total_jobs    = stats.get("total_jobs",     0)

        # ── Inventory value ───────────────────────────────────────
        inventory       = user_data.get("inventory", {})
        inventory_value = sum(
            ALL_ITEMS[item]["price"] * amt
            for item, amt in inventory.items()
            if item in ALL_ITEMS
        )

        # ── Workers ───────────────────────────────────────────────
        workers        = user_data.get("workers", {})
        workers_owned  = len(workers)
        worker_income  = 0
        workers_value  = 0

        for worker in workers.values():
            level          = worker.get("level", 1)
            worker_income += WORKER_LEVELS[level]["income"]
            workers_value += WORKER_VALUES[level]

        # ── Shop value ────────────────────────────────────────────
        shop_value = 0
        if user_data.get("shovel"):        shop_value += 3_000_000
        if user_data.get("lock_and_key"):  shop_value += 2_500_000

        # ── Net worth ─────────────────────────────────────────────
        networth = cash + inventory_value + workers_value + shop_value

        # ── Padlock ───────────────────────────────────────────────
        padlock_until = user_data.get("padlock_until", 0)
        current_time  = int(datetime.now().timestamp())

        if padlock_until > current_time:
            remaining  = (padlock_until - current_time) // 86400
            protection = f"🛡 Active ({remaining}d)"
        else:
            protection = "❌ None"

        # ── Embed ─────────────────────────────────────────────────
        embed = discord.Embed(
            title=f"{member.name.upper()}'S PROFILE",
            description=member.mention,
            color=0x2B2D31,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="💰 Cash",            value=f"**{format_cash(cash)}**",            inline=False)
        embed.add_field(name="📦 Inventory Value", value=f"**{format_cash(inventory_value)}**", inline=False)
        embed.add_field(name="💎 Net Worth",       value=f"**{format_cash(networth)}**",        inline=False)

        embed.add_field(
            name="🎰 Gambling",
            value=(
                f"🎮 Games: **{games_played}**\n"
                f"💸 Gambled: **{format_cash(total_gambled)}**\n"
                f"🏆 Biggest Win: **{format_cash(biggest_win)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚒ Workers",
            value=(
                f"👷 Owned: **{workers_owned}**\n"
                f"💰 Value: **{format_cash(workers_value)}**\n"
                f"💵 Income/Day: **{format_cash(worker_income)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="🌎 Activities",
            value=(
                f"⛏ **{total_mines}**  "
                f"🎣 **{total_fishes}**  "
                f"🏹 **{total_hunts}**  "
                f"💼 **{total_jobs}**"
            ),
            inline=False,
        )

        # ── Achievements ──────────────────────────────────────────
        claimed          = user_data.get("claimed_achievements", [])
        achievement_text = ""

        for achievement_id in claimed:
            if achievement_id in LEGENDARY_ACHIEVEMENTS:
                achievement_text += f"🟡 {LEGENDARY_ACHIEVEMENTS[achievement_id]['name']}\n"
            elif achievement_id in RARE_ACHIEVEMENTS:
                achievement_text += f"🟣 {RARE_ACHIEVEMENTS[achievement_id]['name']}\n"
            elif achievement_id in COMMON_ACHIEVEMENTS:
                achievement_text += f"⚪ {COMMON_ACHIEVEMENTS[achievement_id]['name']}\n"

        embed.add_field(
            name="🏆 Completed Achievements",
            value=achievement_text or "❌ None",
            inline=False,
        )

        embed.add_field(name="🛡 Protection", value=protection, inline=False)

        await ctx.send(embed=embed)


    # ─────────────────────────
    # LEADERBOARD
    # ─────────────────────────

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):

        async with ctx.typing():

            # Efficient: sort + limit at the DB level instead of pulling
            # every account with cash > 0 into memory and sorting in Python.
            top_docs = list(
                economy_collection.find({"cash": {"$gt": 0}})
                .sort("cash", -1)
                .limit(10)
            )

            top_entries = []
            top_ids = set()

            for index, user in enumerate(top_docs):
                user_id = int(user["user_id"])
                top_ids.add(user_id)
                cash = user.get("cash", 0)

                try:
                    fetched_user = await self.bot.fetch_user(user_id)
                    name = fetched_user.display_name if hasattr(fetched_user, "display_name") else fetched_user.name
                    avatar_url = str(fetched_user.display_avatar.url)
                except Exception:
                    name = f"User {user_id}"
                    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

                top_entries.append({
                    "rank": index + 1,
                    "name": name,
                    "cash": cash,
                    "user_id": user_id,
                    "avatar_url": avatar_url,
                    "title_key": get_equipped(user_id),
                })

            if not top_entries:
                embed = discord.Embed(
                    description="❌ No one has any cash yet.",
                    color=0xED4245,
                )
                await ctx.send(embed=embed)
                return

            # Pin the requester's own rank at the bottom if they're not
            # already visible in the top 10.
            requester_entry = None
            if ctx.author.id not in top_ids:
                my_doc = economy_collection.find_one({"user_id": str(ctx.author.id)})
                my_cash = my_doc.get("cash", 0) if my_doc else 0

                if my_cash > 0:
                    my_rank = economy_collection.count_documents({"cash": {"$gt": my_cash}}) + 1
                    requester_entry = {
                        "rank": my_rank,
                        "name": ctx.author.display_name,
                        "cash": my_cash,
                        "user_id": ctx.author.id,
                        "avatar_url": str(ctx.author.display_avatar.url),
                        "title_key": get_equipped(ctx.author.id),
                    }

            try:
                buf = await render_leaderboard(top_entries, requester_entry, format_cash)
                file = discord.File(buf, filename="leaderboard.png")
                await ctx.send(file=file)
            except Exception:
                # Fallback to the plain text embed if image rendering fails
                # for any reason (missing fonts, network hiccup fetching an
                # avatar, etc.) so the command never just breaks.
                embed = discord.Embed(title="LEADERBOARD", color=0xF1C40F)
                text = ""
                for entry in top_entries:
                    text += f"**#{entry['rank']} {entry['name']}**\n{format_cash(entry['cash'])}\n\n"
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
            crack_games,
        )

        stopped = False

        if ctx.channel.id in randoms_games:
            del randoms_games[ctx.channel.id]
            stopped = True

        if ctx.channel.id in deathroll_games:
            del deathroll_games[ctx.channel.id]
            stopped = True

        if ctx.channel.id in crack_games:
            del crack_games[ctx.channel.id]
            stopped = True

        # Also stop active Pokémon battles
        try:
            from cogs.pokemon_battle import PokemonBattle
            cog = self.bot.get_cog("PokemonBattle")
            if cog and ctx.channel.id in cog.active:
                del cog.active[ctx.channel.id]
                stopped = True
        except Exception:
            pass

        embed = discord.Embed(
            description="🛑 Active game stopped." if stopped else "❌ No active game.",
            color=0xED4245,
        )
        await ctx.send(embed=embed)


    # ─────────────────────────
    # PING
    # ─────────────────────────

    @commands.command(name="ping")
    async def ping(self, ctx):

        latency = round(self.bot.latency * 1000)
        embed   = discord.Embed(
            description=f"🏓 Pong: **{latency}ms**",
            color=0x57F287,
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(System(bot))
        
