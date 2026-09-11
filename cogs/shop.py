from discord.ext import commands
import discord
from datetime import datetime
from utils.pokemon_db import add_ball, get_balls
from utils.economy import economy_collection, get_cash, remove_cash, format_cash, create_account

PADLOCK_PRICE = 250000
WORKER_PRICE = 5000000
LOCK_AND_KEY_PRICE = 2500000
SHOVEL_PRICE = 3000000

POKE_MART_ITEMS = {
    "pb": {"name": "Poké Ball", "emoji": "<:pb:1517998351227031632>", "db": "pokeball", "price": 1_000},
    "ub": {"name": "Ultra Ball", "emoji": "<:ub:1517997681564324114>", "db": "ultraball", "price": 10_000},
    "mb": {"name": "Master Ball", "emoji": "<a:mb:1517997721288704111>", "db": "masterball", "price": 50_000},
}
BALL_QUANTITIES = [1, 5, 10, 25, 50]


class ShopView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

        self.item_select = discord.ui.Select(
            placeholder="Choose an item to purchase",
            options=[
                discord.SelectOption(label="Padlock", description="250K NGR • 1 day protection", emoji="🛡"),
                discord.SelectOption(label="Worker", description="5M NGR • Passive income worker", emoji="⚒"),
                discord.SelectOption(label="Lock and Key", description="2.5M NGR • 20 rob attempts", emoji="🔐"),
                discord.SelectOption(label="Shovel", description="3M NGR • Unlock mining", emoji="⛏"),
            ],
        )
        self.item_select.callback = self.select_callback
        self.add_item(self.item_select)

        self.ball_select = discord.ui.Select(
            placeholder="Pokemart — Buy Pokeballs",
            options=[
                discord.SelectOption(label="Poké Ball", description="1K NGR each", emoji="<:pb:1517998351227031632>", value="pb"),
                discord.SelectOption(label="Ultra Ball", description="10K NGR each", emoji="<:ub:1517997681564324114>", value="ub"),
                discord.SelectOption(label="Master Ball", description="50K NGR each", emoji="<a:mb:1517997721288704111>", value="mb"),
            ],
        )
        self.ball_select.callback = self.pokemart_callback
        self.add_item(self.ball_select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This menu is not for you.", ephemeral=True)
            return

        choice = self.item_select.values[0]
        create_account(interaction.user.id)
        user_data = economy_collection.find_one({"user_id": str(interaction.user.id)}) or {}
        workers = user_data.get("workers", {})

        if choice == "Padlock":
            price = PADLOCK_PRICE
            if get_cash(interaction.user.id) < price:
                await interaction.response.send_message(embed=_not_enough(price), ephemeral=True)
                return
            remove_cash(interaction.user.id, price)
            now = int(datetime.now().timestamp())
            current = max(user_data.get("padlock_until", 0), now)
            new_time = current + 86400
            economy_collection.update_one({"user_id": str(interaction.user.id)}, {"$set": {"padlock_until": new_time}})
            days = (new_time - now) // 86400
            await interaction.response.send_message(embed=discord.Embed(
                title="🛡 PADLOCK PURCHASED",
                description=f"Your account is now protected from robbing.\n\n⏰ Total Protection:\n**{days} Days**",
                color=0x5865F2,
            ))
            return

        if choice == "Worker":
            if len(workers) >= 5:
                await interaction.response.send_message(embed=discord.Embed(description="❌ You already own the maximum number of workers.", color=0xED4245), ephemeral=True)
                return
            if get_cash(interaction.user.id) < WORKER_PRICE:
                await interaction.response.send_message(embed=_not_enough(WORKER_PRICE), ephemeral=True)
                return
            remove_cash(interaction.user.id, WORKER_PRICE)
            worker_name = f"worker-{len(workers) + 1}"
            workers[worker_name] = {"level": 1, "stored": 0, "total_earned": 0, "last_claim": int(datetime.now().timestamp())}
            economy_collection.update_one({"user_id": str(interaction.user.id)}, {"$set": {"workers": workers}})
            await interaction.response.send_message(embed=discord.Embed(
                title="⚒ WORKER PURCHASED",
                description=f"Purchased **{worker_name}**\n\n💰 Income:\n**200K NGR / Day**\n\n📈 Upgradeable up to Level 5",
                color=0x57F287,
            ))
            return

        if choice == "Lock and Key":
            if user_data.get("lock_and_key"):
                await interaction.response.send_message(embed=discord.Embed(description="❌ You already own **Lock and Key**.", color=0xED4245), ephemeral=True)
                return
            if get_cash(interaction.user.id) < LOCK_AND_KEY_PRICE:
                await interaction.response.send_message(embed=_not_enough(LOCK_AND_KEY_PRICE), ephemeral=True)
                return
            remove_cash(interaction.user.id, LOCK_AND_KEY_PRICE)
            economy_collection.update_one({"user_id": str(interaction.user.id)}, {"$set": {"lock_and_key": True}})
            await interaction.response.send_message(embed=discord.Embed(
                title="🔐 LOCK AND KEY PURCHASED",
                description="Your rob attempts have increased.\n\n📈 Rob Attempts:\n**10 → 20**",
                color=0x57F287,
            ))
            return

        if choice == "Shovel":
            if user_data.get("shovel", False):
                await interaction.response.send_message(embed=discord.Embed(description="❌ You already own a shovel.", color=0xED4245), ephemeral=True)
                return
            if get_cash(interaction.user.id) < SHOVEL_PRICE:
                await interaction.response.send_message(embed=_not_enough(SHOVEL_PRICE), ephemeral=True)
                return
            remove_cash(interaction.user.id, SHOVEL_PRICE)
            economy_collection.update_one({"user_id": str(interaction.user.id)}, {"$set": {"shovel": True}})
            await interaction.response.send_message(embed=discord.Embed(
                title="⛏ SHOVEL PURCHASED",
                description="You purchased a shovel.\n\n⛏ You can now use `.mine`",
                color=0x57F287,
            ))

    async def pokemart_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This menu is not for you.", ephemeral=True)
            return
        ball_key = self.ball_select.values[0]
        item = POKE_MART_ITEMS[ball_key]
        embed = discord.Embed(
            title=f"{item['emoji']} {item['name']}",
            description=f"Select a quantity to purchase.\n\n💵 Price per ball:\n**{format_cash(item['price'])}**",
            color=0x5865F2,
        )
        embed.set_footer(text="Prices scale automatically with quantity")
        await interaction.response.send_message(embed=embed, view=BallQuantityView(self.ctx, ball_key), ephemeral=True)


class BallQuantityView(discord.ui.View):
    def __init__(self, ctx, ball_key):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.ball_key = ball_key
        item = POKE_MART_ITEMS[ball_key]
        for qty in BALL_QUANTITIES:
            button = discord.ui.Button(
                label=f"×{qty} — {format_cash(item['price'] * qty)}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"ball_{ball_key}_{qty}",
            )
            button.callback = self._make_callback(qty)
            self.add_item(button)

    def _make_callback(self, qty):
        async def callback(interaction: discord.Interaction):
            await self._purchase(interaction, qty)
        return callback

    async def _purchase(self, interaction: discord.Interaction, qty: int):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This menu is not for you.", ephemeral=True)
            return
        item = POKE_MART_ITEMS[self.ball_key]
        total_price = item["price"] * qty
        create_account(interaction.user.id)
        cash = get_cash(interaction.user.id)
        if cash < total_price:
            await interaction.response.send_message(embed=_not_enough(total_price, cash), ephemeral=True)
            return
        remove_cash(interaction.user.id, total_price)
        add_ball(interaction.user.id, item["db"], qty)
        remaining = get_cash(interaction.user.id)
        balls = get_balls(interaction.user.id)
        embed = discord.Embed(
            title="<a:mb:1517997721288704111> PURCHASE COMPLETE",
            description=(
                f"{item['emoji']} **{item['name']} ×{qty}**\n\n"
                f"💵 Cost:\n**{format_cash(total_price)}**\n\n"
                f"💰 Remaining Balance:\n**{format_cash(remaining)}**"
            ),
            color=0x57F287,
        )
        embed.add_field(
            name="🎒 Your Balls",
            value=(
                f"Poké Ball: **{balls.get('pokeball', 0)}**\n"
                f"Ultra Ball: **{balls.get('ultraball', 0)}**\n"
                f"Master Ball: **{balls.get('masterball', 0)}**"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


def _not_enough(required, current=None):
    text = f"❌ You don't have enough cash.\n\nRequired: **{format_cash(required)}**"
    if current is not None:
        text += f"\nYou have: **{format_cash(current)}**"
    return discord.Embed(description=text, color=0xED4245)


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shop")
    async def shop(self, ctx):
        embed = discord.Embed(
            title="🛒 SHOP",
            description=(
                "Buy items to improve your account.\n\n"
                "🛡 **Padlock** — 250K NGR\n"
                "⚒ **Worker** — 5M NGR\n"
                "🔐 **Lock and Key** — 2.5M NGR\n"
                "⛏ **Shovel** — 3M NGR\n\n"
                "🎯 **Pokemart** — Buy Poké Balls"
            ),
            color=0x5865F2,
        )
        await ctx.send(embed=embed, view=ShopView(ctx))


async def setup(bot):
    await bot.add_cog(Shop(bot))
