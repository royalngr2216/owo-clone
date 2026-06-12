from discord.ext import commands
import discord
import asyncio
import sqlite3

# ─────────────────────────────────────────────────────────────────
# ROLE UPDATER  (used by randoms.py and other cogs)
# ─────────────────────────────────────────────────────────────────

RANK_ROLES = {
    10:  "Rookie",
    25:  "Challenger",
    50:  "Veteran",
    100: "Elite",
    200: "Champion",
    500: "Legend",
}

async def update_roles(member: discord.Member, matches: int):
    """Grant the highest rank role the member qualifies for."""
    if not member.guild:
        return
    guild      = member.guild
    earned     = [name for threshold, name in RANK_ROLES.items() if matches >= threshold]
    if not earned:
        return
    role_name  = earned[-1]
    role       = discord.utils.get(guild.roles, name=role_name)
    if role and role not in member.roles:
        try:
            await member.add_roles(role, reason="Rank update")
        except discord.Forbidden:
            pass


# ─────────────────────────────────────────────────────────────────
# HELP DATA  — every category with its commands
# ─────────────────────────────────────────────────────────────────

CATEGORIES = [
    {
        "name":  "💰 Economy",
        "emoji": "💰",
        "color": 0xF1C40F,
        "desc":  "Earn, manage and grow your money.",
        "commands": [
            (".daily",          "",                     "Claim your daily reward"),
            (".weekly",         "",                     "Claim your weekly reward"),
            (".monthly",        "",                     "Claim your monthly reward"),
            (".cash",           "[@user]",              "Check your or someone's balance"),
            (".give",           "@user <amount>",       "Give money to someone"),
            (".donate",         "@user <amount>",       "Donate money (alias: .dn)"),
            (".job",            "",                     "Work your job for coins"),
            (".hunt",           "",                     "Hunt for loot"),
            (".fish",           "",                     "Go fishing for items"),
            (".mine",           "",                     "Mine for ores and gems"),
            (".inventory",      "",                     "View your inventory"),
            (".sell",           "<item> <amount>",      "Sell items from your inventory"),
            (".shop",           "",                     "Browse the item shop"),
            (".padlock",        "",                     "Buy a padlock to protect your cash"),
            (".lottery",        "[amount]",             "Buy lottery tickets"),
        ],
    },
    {
        "name":  "🎰 Gambling",
        "emoji": "🎰",
        "color": 0xE74C3C,
        "desc":  "Test your luck. Win big or go broke.",
        "commands": [
            (".slots",          "<amount>",             "Spin the slot machine (alias: .s)"),
            (".coinflip",       "<heads/tails> <amount>","Flip a coin (alias: .cf)"),
            (".dice",           "<4/6/8/12/20> <amount>","Roll a dice"),
        ],
    },
    {
        "name":  "⚔️ PvP Games",
        "emoji": "⚔️",
        "color": 0x9B59B6,
        "desc":  "Challenge other players head-to-head.",
        "commands": [
            (".randoms",        "@user <bo> [amount]",  "Random Pokémon battle (BO1/3/5/7/9)"),
            (".pick",           "",                     "Pick your Pokémon in a randoms match"),
            (".deathroll",      "@user <bo> <amount>",  "Deathroll dice game"),
            (".roll",           "",                     "Roll in an active deathroll game"),
            (".crack",          "@user <bo> <amount>",  "Number guessing game"),
            (".guess",          "<number>",             "Guess in an active crack game"),
        ],
    },
    {
        "name":  "🎮 Pokémon",
        "emoji": "🎮",
        "color": 0xE67E22,
        "desc":  "Catch, train and battle Pokémon.",
        "commands": [
            (".catch",          "<name>",               "Catch the wild Pokémon in the channel"),
            (".pokemon",        "[@user]",              "View your Pokémon collection"),
            (".team",           "[p1, p2, ...]",        "View or set your active team (up to 6)"),
            (".moves",          "<pokémon> <m1, m2...>","Teach a Pokémon its moveset"),
            (".moveset",        "<pokémon> [@user]",    "View a Pokémon's current moves"),
            (".battle",         "@user [amount]",       "Challenge someone to a Pokémon battle"),
            (".setspawnchannel","",                     "Admin: set the Pokémon spawn channel"),
            (".spawntest",      "",                     "Admin: force a Pokémon spawn now"),
        ],
    },
    {
        "name":  "🛡 Protection",
        "emoji": "🛡",
        "color": 0x3498DB,
        "desc":  "Defend your coins from thieves.",
        "commands": [
            (".rob",            "@user",                "Attempt to rob someone"),
            (".padlock",        "",                     "Buy a padlock to block robs"),
        ],
    },
    {
        "name":  "📋 Profile",
        "emoji": "📋",
        "color": 0x2ECC71,
        "desc":  "Stats, quests and achievements.",
        "commands": [
            (".quests",         "",                     "View your active quests (alias: .quest)"),
        ],
    },
]

# ─────────────────────────────────────────────────────────────────
# HOME EMBED  (overview of all categories)
# ─────────────────────────────────────────────────────────────────

def home_embed(bot: commands.Bot) -> discord.Embed:
    embed = discord.Embed(
        title="📖  Echelon Help",
        description=(
            "Use the buttons below to browse commands by category.\n"
            "Or type `.help <command>` for details on a specific command.\n\u200b"
        ),
        color=0x5865F2,
    )
    for cat in CATEGORIES:
        count = len(cat["commands"])
        embed.add_field(
            name=f"{cat['emoji']}  {cat['name'].split(' ', 1)[1]}",
            value=f"`{count} commands`",
            inline=True,
        )
    embed.set_footer(text=f"Prefix: .  •  {sum(len(c['commands']) for c in CATEGORIES)} total commands")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    return embed


# ─────────────────────────────────────────────────────────────────
# CATEGORY EMBED
# ─────────────────────────────────────────────────────────────────

def category_embed(cat: dict, bot: commands.Bot) -> discord.Embed:
    embed = discord.Embed(
        title=f"{cat['emoji']}  {cat['name'].split(' ', 1)[1]}",
        description=cat["desc"] + "\n\u200b",
        color=cat["color"],
    )
    lines = []
    for cmd, args, desc in cat["commands"]:
        arg_part = f" `{args}`" if args else ""
        lines.append(f"**{cmd}**{arg_part}\n╰ {desc}")
    embed.add_field(name="Commands", value="\n".join(lines), inline=False)
    embed.set_footer(
        text=f"Echelon  •  {len(cat['commands'])} commands in this category",
        icon_url=bot.user.display_avatar.url,
    )
    return embed


# ─────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────

class HelpView(discord.ui.View):
    """
    Persistent help menu.
    Home button always returns to the overview.
    Each category button shows that category's commands.
    """

    def __init__(self, bot: commands.Bot, author: discord.Member):
        super().__init__(timeout=120)
        self.bot    = bot
        self.author = author
        self._build_buttons()

    def _build_buttons(self):
        # Home button
        home = discord.ui.Button(
            label="🏠 Home",
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        home.callback = self._home_cb
        self.add_item(home)

        # One button per category, spread across rows
        for i, cat in enumerate(CATEGORIES):
            row = 1 + (i // 4)
            btn = discord.ui.Button(
                label=cat["name"],
                style=discord.ButtonStyle.primary,
                row=row,
            )
            btn.callback = self._make_cat_cb(cat)
            self.add_item(btn)

    def _make_cat_cb(self, cat: dict):
        async def cb(interaction: discord.Interaction):
            if interaction.user != self.author:
                await interaction.response.send_message(
                    "Open your own `.help` menu!", ephemeral=True
                )
                return
            await interaction.response.edit_message(
                embed=category_embed(cat, self.bot), view=self
            )
        return cb

    async def _home_cb(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "Open your own `.help` menu!", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            embed=home_embed(self.bot), view=self
        )

    async def on_timeout(self):
        # Disable all buttons when the menu expires
        for item in self.children:
            item.disabled = True


# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class System(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ── .help ─────────────────────────────────────────────────────

    @commands.command(name="help", aliases=["h", "commands"])
    async def help(self, ctx, *, query: str = None):

        # .help <command>  — specific command lookup
        if query:
            query_low = query.lower().lstrip(".")
            for cat in CATEGORIES:
                for cmd, args, desc in cat["commands"]:
                    if query_low == cmd.lstrip("."):
                        embed = discord.Embed(
                            title=f"📖  {cmd}",
                            color=cat["color"],
                        )
                        embed.add_field(
                            name="Usage",
                            value=f"`{cmd} {args}`".strip() if args else f"`{cmd}`",
                            inline=False,
                        )
                        embed.add_field(name="Description", value=desc, inline=False)
                        embed.add_field(name="Category",    value=cat["name"], inline=True)
                        await ctx.send(embed=embed)
                        return
            await ctx.send(embed=discord.Embed(
                description=f"❌ No command named `{query}` found.",
                color=0xED4245,
            ))
            return

        # Main interactive menu
        view = HelpView(self.bot, ctx.author)
        await ctx.send(embed=home_embed(self.bot), view=view)

    # ── .ping ─────────────────────────────────────────────────────

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        color   = 0x57F287 if latency < 100 else (0xF1C40F if latency < 200 else 0xED4245)
        embed   = discord.Embed(
            title="🏓 Pong!",
            description=f"**{latency}ms**",
            color=color,
        )
        await ctx.send(embed=embed)

    # ── .stats ────────────────────────────────────────────────────

    @commands.command(name="stats", aliases=["botinfo", "info"])
    async def stats(self, ctx):
        guilds  = len(self.bot.guilds)
        users   = sum(g.member_count for g in self.bot.guilds)
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(title="📊  Bot Info", color=0x5865F2)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="🏓 Latency",  value=f"{latency}ms",  inline=True)
        embed.add_field(name="🏠 Servers",  value=str(guilds),     inline=True)
        embed.add_field(name="👥 Users",    value=str(users),      inline=True)
        embed.add_field(name="⚙️ Prefix",   value="`.`",           inline=True)
        embed.add_field(
            name="📖 Commands",
            value=str(sum(len(c["commands"]) for c in CATEGORIES)),
            inline=True,
        )
        embed.set_footer(text="Echelon Bot")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(System(bot))
               
