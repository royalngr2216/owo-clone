from discord.ext import commands
import discord
import random
import asyncio

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    parse_amount,
    format_cash
)
from utils.stats import (
    add_stats,
    update_biggest_win,
    record_win,
    record_loss
)
from utils.achievement_checker import check_achievements

# ─────────────────────────
# CONFIG
# ─────────────────────────

GRID_SIZE = 5  # 5x5 = 25 tiles
MINE_OPTIONS = [1, 3, 5, 10, 15, 20, 24]

# Multiplier table: mines -> [mult after 1 safe, 2 safe, ...]
# Uses the standard mines game formula (simplified)
def calc_mult(mines, revealed):
    """Returns current multiplier based on mines count and tiles revealed."""
    safe = GRID_SIZE * GRID_SIZE - mines
    mult = 1.0
    for i in range(revealed):
        remaining = GRID_SIZE * GRID_SIZE - i
        chance = (remaining - mines) / remaining
        mult /= chance
    return round(mult * 0.97, 2)  # 3% house edge

# ─────────────────────────
# ACTIVE GAMES
# ─────────────────────────

mines_games = {}


def build_grid_view(user_id, cog):
    g = mines_games[user_id]
    return MinesView(user_id=user_id, cog=cog, game=g)


class MinesGame(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="mines")
    async def mines(self, ctx, mines: str = None, amount: str = None):
        """Classic mines game — pick safe tiles and cash out before hitting a bomb!"""

        if ctx.author.id in mines_games:
            await ctx.send(embed=discord.Embed(
                description="❌ You already have a game running! Use the buttons.",
                color=0xED4245
            ))
            return

        if mines is None or amount is None:
            embed = discord.Embed(
                title="💣 Mines",
                description=(
                    "**How to play:**\n\n"
                    "Pick a 5×5 grid of tiles. Some hide **bombs** 💣.\n"
                    "Reveal safe tiles 💎 to multiply your bet.\n"
                    "**Cash out anytime** — or blow up and lose!\n\n"
                    "More mines = higher multipliers per tile!\n\n"
                    f"Available mine counts: `{', '.join(str(m) for m in MINE_OPTIONS)}`\n\n"
                    "Usage: `.mines <mines> <amount>`\n"
                    "Example: `.mines 5 1000`"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
            return

        try:
            mine_count = int(mines)
        except ValueError:
            await ctx.send(embed=discord.Embed(description="❌ Invalid mine count.", color=0xED4245))
            return

        if mine_count not in MINE_OPTIONS:
            await ctx.send(embed=discord.Embed(
                description=f"❌ Choose mine count from: `{', '.join(str(m) for m in MINE_OPTIONS)}`",
                color=0xED4245
            ))
            return

        cash = get_cash(ctx.author.id)
        bet = parse_amount(amount, cash)

        if bet is None or bet <= 0:
            await ctx.send(embed=discord.Embed(description="❌ Invalid amount.", color=0xED4245))
            return
        if cash < bet:
            await ctx.send(embed=discord.Embed(description="❌ Not enough cash.", color=0xED4245))
            return

        remove_cash(ctx.author.id, bet)
        add_stats(ctx.author.id, games_played=1, total_gambled=bet)

        # Place mines
        positions = list(range(GRID_SIZE * GRID_SIZE))
        mine_positions = set(random.sample(positions, mine_count))

        mines_games[ctx.author.id] = {
            "bet": bet,
            "mine_count": mine_count,
            "mine_positions": mine_positions,
            "revealed": set(),
            "safe_count": 0,
            "done": False,
        }

        embed = self._build_embed(ctx.author.id)
        view = build_grid_view(ctx.author.id, self)
        msg = await ctx.send(embed=embed, view=view)
        mines_games[ctx.author.id]["msg"] = msg

    # ─────────────────────────
    # EMBED
    # ─────────────────────────

    def _build_embed(self, user_id):
        g = mines_games[user_id]
        bet = g["bet"]
        safe = g["safe_count"]
        mines = g["mine_count"]
        mult = calc_mult(mines, safe)
        potential = int(bet * mult)

        desc = (
            f"💣 Mines: **{mines}** | 💎 Safe found: **{safe}**\n"
            f"Current multiplier: **{mult}×**\n"
            f"💰 Cash out now: **{format_cash(potential)}**\n\n"
            "Click a tile below!"
        )
        embed = discord.Embed(
            title="💣 Mines",
            description=desc,
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        return embed

    # ─────────────────────────
    # REVEAL TILE
    # ─────────────────────────

    async def reveal_tile(self, interaction, user_id, pos):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        g = mines_games.get(user_id)
        if not g or g["done"]:
            return

        if pos in g["revealed"]:
            await interaction.response.send_message("Already revealed!", ephemeral=True)
            return

        g["revealed"].add(pos)

        if pos in g["mine_positions"]:
            # Hit a mine
            g["done"] = True
            del mines_games[user_id]
            bet = g["bet"]
            record_loss(user_id, bet)

            # Build reveal showing all mines
            embed = discord.Embed(
                title="💣 Mines — BOOM! You hit a mine!",
                description=(
                    f"💣 Lost **{format_cash(bet)}**!\n"
                    f"You had found **{g['safe_count']}** safe tile(s)."
                ),
                color=0xED4245
            )
            embed.set_footer(text=f"Bet: {format_cash(bet)}")
            final_view = FinalMinesView(mine_positions=g["mine_positions"], hit=pos, revealed=g["revealed"])
            await interaction.response.edit_message(embed=embed, view=final_view)
            await check_achievements(self.bot, interaction.user)
        else:
            # Safe tile
            g["safe_count"] += 1
            total_safe = GRID_SIZE * GRID_SIZE - g["mine_count"]

            if g["safe_count"] >= total_safe:
                # Won all safe tiles — auto cashout
                await self._cashout(interaction, user_id, auto=True)
                return

            embed = self._build_embed(user_id)
            view = build_grid_view(user_id, self)
            await interaction.response.edit_message(embed=embed, view=view)

    # ─────────────────────────
    # CASH OUT
    # ─────────────────────────

    async def cashout(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        g = mines_games.get(user_id)
        if not g or g["safe_count"] == 0:
            await interaction.response.send_message(
                "❌ Reveal at least one tile before cashing out!", ephemeral=True
            )
            return
        await self._cashout(interaction, user_id)

    async def _cashout(self, interaction, user_id, auto=False):
        g = mines_games.pop(user_id, None)
        if not g:
            return

        bet = g["bet"]
        safe = g["safe_count"]
        mines = g["mine_count"]
        mult = calc_mult(mines, safe)
        payout = int(bet * mult)
        profit = payout - bet

        add_cash(user_id, payout)
        update_biggest_win(user_id, profit)
        record_win(user_id, profit)

        title = "💣 Mines — CLEARED! 🎉" if auto else "💣 Mines — Cashed Out!"
        embed = discord.Embed(
            title=title,
            description=(
                f"💎 Safe tiles found: **{safe}**\n"
                f"Multiplier: **{mult}×**\n"
                f"Payout: **{format_cash(payout)}**\n"
                f"Profit: **{format_cash(profit)}**"
            ),
            color=0x57F287
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        final_view = FinalMinesView(mine_positions=g["mine_positions"], hit=None, revealed=g["revealed"])
        await interaction.response.edit_message(embed=embed, view=final_view)
        await check_achievements(self.bot, interaction.user)

    async def on_timeout_cleanup(self, user_id):
        g = mines_games.pop(user_id, None)
        if g:
            add_cash(user_id, g["bet"])


# ─────────────────────────
# GRID VIEW (BUTTONS)
# ─────────────────────────

class MinesView(discord.ui.View):

    def __init__(self, user_id, cog, game):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.cog = cog

        revealed = game["revealed"]
        mines = game["mine_positions"]

        # 25 tile buttons (5x5)
        for pos in range(GRID_SIZE * GRID_SIZE):
            is_revealed = pos in revealed
            # Show gem for revealed safe tiles
            emoji = "💎" if is_revealed else "⬛"
            btn = MineButton(pos=pos, emoji=emoji, disabled=is_revealed, user_id=user_id, cog=cog)
            self.add_item(btn)

        # Cashout button
        can_cashout = game["safe_count"] > 0
        cashout_btn = discord.ui.Button(
            label=f"Cash Out",
            style=discord.ButtonStyle.green,
            emoji="💰",
            row=5,
            disabled=not can_cashout
        )
        cashout_btn.callback = self._cashout_cb
        self.add_item(cashout_btn)

    async def _cashout_cb(self, interaction: discord.Interaction):
        await self.cog.cashout(interaction, self.user_id)

    async def on_timeout(self):
        await self.cog.on_timeout_cleanup(self.user_id)


class MineButton(discord.ui.Button):

    def __init__(self, pos, emoji, disabled, user_id, cog):
        row = pos // GRID_SIZE
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            row=row,
            disabled=disabled
        )
        self.pos = pos
        self.user_id = user_id
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.reveal_tile(interaction, self.user_id, self.pos)


class FinalMinesView(discord.ui.View):
    """Disabled grid showing where mines were."""

    def __init__(self, mine_positions, hit, revealed):
        super().__init__(timeout=1)
        for pos in range(GRID_SIZE * GRID_SIZE):
            if pos == hit:
                emoji = "💥"
            elif pos in mine_positions:
                emoji = "💣"
            elif pos in revealed:
                emoji = "💎"
            else:
                emoji = "⬛"
            row = pos // GRID_SIZE
            btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                emoji=emoji,
                row=row,
                disabled=True
            )
            self.add_item(btn)


async def setup(bot):
    await bot.add_cog(MinesGame(bot))
