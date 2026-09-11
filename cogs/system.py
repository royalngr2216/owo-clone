from discord.ext import commands
import discord

from utils.economy import economy_collection, format_cash
from utils.titles import get_equipped
from utils.leaderboard_render import render_leaderboard

HELP_CATEGORIES = {
    "💰 Economy": (
        "**.cash [user]**\nView your balance.\n\n"
        "**.daily** · **.weekly** · **.monthly**\nClaim rewards.\n\n"
        "**.give @user amount**\nTransfer cash.\n\n"
        "**.donate @user amount**\nDonate cash.\n\n"
        "**.rob @user**\nAttempt a robbery.\n\n"
        "**.steal @user**\nAttempt a steal."
    ),
    "🎒 Items": (
        "**.shop**\nOpen the item shop / Poké Mart.\n\n"
        "**.inventory**\nView your inventory.\n\n"
        "**.sell item amount**\nSell items.\n\n"
        "**.padlock**\nView your protection status."
    ),
    "⚒ Workers": (
        "**.workers**\nView your workers.\n\n"
        "**.claim**\nClaim worker earnings.\n\n"
        "**.upgrade worker-1**\nUpgrade a worker."
    ),
    "🌎 Activities": (
        "**.job**\nWork for cash.\n\n"
        "**.fish**\nGo fishing.\n\n"
        "**.hunt**\nGo hunting.\n\n"
        "**.mine**\nGo mining."
    ),
    "🎮 Games": (
        "**.randoms @user bo amount**\nPokémon random battle.\n\n"
        "**.deathroll @user bo amount**\nPlay Deathroll.\n\n"
        "**.crack @user bo amount**\nCrack the hidden number."
    ),
    "🎲 Casino": (
        "**.cf h/t amount**\nCoinflip.\n\n"
        "**.blackjack amount** / **.bj amount**\nPlay Blackjack.\n\n"
        "**.crash amount**\nPlay Crash.\n\n"
        "**.guessnumber amount**\nGuess the number.\n\n"
        "**.mines amount**\nPlay Mines.\n\n"
        "**.highlow amount**\nPlay High/Low.\n\n"
        "**.lottery amount**\nEnter the lottery.\n\n"
        "**.slots amount**\nPlay Slots."
    ),
    "🐉 Pokémon": (
        "**.spawn**\nView Pokémon spawn status.\n\n"
        "**.catch pokeball**\nCatch with a Poké Ball.\n\n"
        "**.catch ultraball**\nCatch with an Ultra Ball.\n\n"
        "**.catch masterball**\nCatch with a Master Ball.\n\n"
        "**.balls [user]**\nView Poké Balls.\n\n"
        "**.pokemons**\nView your full Pokémon collection with images, rarity and pagination.\n\n"
        "**.dex** / **.pokedex**\nView your unique Pokédex, sorted by Pokédex number.\n\n"
        "**.pokemart**\nBrowse the Pokémon marketplace.\n\n"
        "**.pokecheck @user**\nView a trainer's listings.\n\n"
        "**.pokemon sell <pokemon> <price>**\nList a Pokémon for sale.\n\n"
        "**.pokemon buy @user <pokemon>**\nBuy a listed Pokémon.\n\n"
        "**.neel** / **.neel sell <pokemon>**\nView Neel or sell a Pokémon."
    ),
    "📊 Profile": (
        "**.profile [user]**\nView player stats.\n\n"
        "**.leaderboard**\nView the richest players.\n\n"
        "**.quests**\nView quests and achievements.\n\n"
        "**.titles**\nBrowse your cosmetic titles.\n\n"
        "**.titles buy <name>**\nBuy a title.\n\n"
        "**.titles equip <name>**\nEquip a title.\n\n"
        "**.titles unequip**\nUnequip your title."
    ),
    "🛡️ Admin": (
        "**.spawn set #channel**\nEnable Pokémon spawns in a channel.\n\n"
        "**.spawn disable**\nDisable Pokémon spawns.\n\n"
        "**.forcespawn**\nForce a new Pokémon spawn even if one is already active."
    ),
    "⚙ Utility": (
        "**.ping**\nView bot latency.\n\n"
        "**.stop**\nStop an active supported game."
    ),
}


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=category, description=f"View {category} commands")
            for category in HELP_CATEGORIES
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(title=category, description=HELP_CATEGORIES[category], color=0x5865F2)
        embed.set_footer(text="SARKARI ADDA Economy System")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown())


class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(title="SARKARI ADDA HELP", description="Economy, activities, games, casino and Pokémon commands.\n\nSelect a category below.", color=0x5865F2)
        embed.set_footer(text="SARKARI ADDA Economy System")
        await ctx.send(embed=embed, view=HelpView())

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        async with ctx.typing():
            top_docs = list(economy_collection.find({"cash": {"$gt": 0}}).sort("cash", -1).limit(10))
            top_entries = []
            top_ids = set()
            for index, user in enumerate(top_docs):
                try:
                    user_id = int(user["user_id"])
                except (TypeError, ValueError, KeyError):
                    continue
                top_ids.add(user_id)
                cash = user.get("cash", 0)
                try:
                    fetched_user = await self.bot.fetch_user(user_id)
                    name = getattr(fetched_user, "display_name", fetched_user.name)
                    avatar_url = str(fetched_user.display_avatar.url)
                except Exception:
                    name = f"User {user_id}"
                    avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
                top_entries.append({"rank": index + 1, "name": name, "cash": cash, "user_id": user_id, "avatar_url": avatar_url, "title_key": get_equipped(user_id)})
            if not top_entries:
                await ctx.send(embed=discord.Embed(description="❌ No one has any cash yet.", color=0xED4245))
                return
            requester_entry = None
            if ctx.author.id not in top_ids:
                my_doc = economy_collection.find_one({"user_id": str(ctx.author.id)})
                my_cash = my_doc.get("cash", 0) if my_doc else 0
                if my_cash > 0:
                    my_rank = economy_collection.count_documents({"cash": {"$gt": my_cash}}) + 1
                    requester_entry = {"rank": my_rank, "name": ctx.author.display_name, "cash": my_cash, "user_id": ctx.author.id, "avatar_url": str(ctx.author.display_avatar.url), "title_key": get_equipped(ctx.author.id)}
            try:
                buf = await render_leaderboard(top_entries, requester_entry, format_cash)
                await ctx.send(file=discord.File(buf, filename="leaderboard.png"))
            except Exception:
                embed = discord.Embed(title="LEADERBOARD", color=0xF1C40F)
                embed.description = "\n\n".join(f"**#{entry['rank']} {entry['name']}**\n{format_cash(entry['cash'])}" for entry in top_entries)
                await ctx.send(embed=embed)

    @commands.command(name="stop")
    async def stop(self, ctx):
        from utils.game_state import randoms_games, deathroll_games, crack_games
        stopped = False
        for games in (randoms_games, deathroll_games, crack_games):
            if ctx.channel.id in games:
                del games[ctx.channel.id]
                stopped = True
        embed = discord.Embed(description="🛑 Active game stopped." if stopped else "❌ No active game.", color=0xED4245)
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(embed=discord.Embed(description=f"🏓 Pong: **{latency}ms**", color=0x57F287))


async def setup(bot):
    await bot.add_cog(System(bot))
