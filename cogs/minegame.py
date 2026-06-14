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


def calc_mult(mines, revealed):
    """Returns current multiplier based on mines count and tiles revealed."""
    mult = 1.0
    for i in range(revealed):
        remaining = GRID_SIZE * GRID_SIZE - i
        chance = (remaining - mines) / remaining
        mult /= chance
    return round(mult * 0.97, 2)  # 3% house edge


def danger_color(mines):
    """Color based on number of mines."""
    if mines <= 3:
        return 0x57F287   # green - easy
    elif mines <= 10:
        return 0xFEE75C   # yellow - medium
    else:
        return 0xED4245   # red - dangerous


def mines_risk_label(mines):
    if mines == 1:
        return "😌 Chill"
    elif mines <= 3:
        return "🟢 Easy"
    elif mines <= 5:
        return "🟡 Medium"
    elif mines <= 10:
        return "🟠 Hard"
    elif mines <= 15:
        return "🔴 Extreme"
    elif mines <= 20:
        return "💀 Insane"
    else:
        return "☠️ One tile left!"


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
    async def mines(self, ctx, amount: str = None, mines: str = None):
        """
        Classic mines game — pick safe tiles and cash out before hitting a bomb!
        Usage: .mines <amount> <mine_count>
        Example: .mines 1000 5
        """

        if ctx.author.id in mines_games:
            await ctx.send(embed=discord.Embed(
                title="💣 Game Already Running",
                description="You already have a mines game in progress!\nReveal tiles or press **💰 Cash Out** to end it.",
                color=0xED4245
            ))
            return

        if amount is None or mines is None:
            embed = discord.Embed(
                title="💣 Mines",
                description=(
                    "Navigate a **5×5** grid full of hidden bombs!\n"
                    "Reveal safe 💎 tiles to grow your multiplier.\n"
                    "**Cash out anytime** — or hit a 💣 and lose it all!\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "**⚡ More mines = higher risk = bigger rewards!**\n\n"
                    f"**Available mine counts:**\n"
                    f"`{' · '.join(str(m) for m in MINE_OPTIONS)}`\n\n"
                    "😌 `1` — Chill\n"
                    "🟢 `3` — Easy\n"
                    "🟡 `5` — Medium\n"
                    "🟠 `10` — Hard\n"
                    "🔴 `15` — Extreme\n"
                    "💀 `20` — Insane\n"
                    "☠️ `24` — One tile left!\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "**Usage:** `.mines <amount> <mines>`\n"
                    "**Example:** `.mines 1000 5`"
                ),
                color=0x2B2D31
            )
            embed.set_footer(text="How many mines can you survive? 💣")
            await ctx.send(embed=embed)
            return

        # Parse mine count
        try:
            mine_count = int(mines)
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="❌ Invalid Mine Count",
                description=f"Mine count must be a number.\nAvailable: `{', '.join(str(m) for m in MINE_OPTIONS)}`",
                color=0xED4245
            ))
            return

        if mine_count not in MINE_OPTIONS:
            await ctx.send(embed=discord.Embed(
                title="❌ Invalid Mine Count",
                description=f"Choose from: `{', '.join(str(m) for m in MINE_OPTIONS)}`",
                color=0xED4245
            ))
            return

        cash = get_cash(ctx.author.id)
        bet = parse_amount(amount, cash)

        if bet is None or bet <= 0:
            await ctx.send(embed=discord.Embed(
                title="❌ Invalid Amount",
                description="Please enter a valid bet amount.",
                color=0xED4245
            ))
            return
        if cash < bet:
            await ctx.send(embed=discord.Embed(
                title="❌ Insufficient Funds",
                description=f"You only have **{format_cash(cash)}**.",
                color=0xED4245
            ))
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
        total_safe = GRID_SIZE * GRID_SIZE - mines
        tiles_left = total_safe - safe
        risk_label = mines_risk_label(mines)

        # Next tile multiplier preview
        next_mult = calc_mult(mines, safe + 1) if tiles_left > 1 else None
        next_potential = int(bet * next_mult) if next_mult else None

        desc_parts = [
            f"**{risk_label}** · 💣 `{mines}` mines hidden\n",
            f"━━━━━━━━━━━━━━━━━━━━━",
            f"💎 Safe tiles found: **{safe}** / {total_safe}",
            f"📈 Multiplier: **{mult}×**",
            f"💰 Cash out now: **{format_cash(potential)}**",
        ]
        if next_potential and safe > 0:
            desc_parts.append(f"⬆️ Next tile: **{format_cash(next_potential)}** ({next_mult}×)")
        desc_parts.append("━━━━━━━━━━━━━━━━━━━━━")
        if safe == 0:
            desc_parts.append("*Click a tile to start! Cash out is unlocked after 1 safe tile.*")
        else:
            desc_parts.append("*Keep going or collect your winnings!*")

        embed = discord.Embed(
            title="💣 Mines",
            description="\n".join(desc_parts),
            color=danger_color(mines)
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}  •  {tiles_left} safe tiles remaining")
        return embed

    # ─────────────────────────
    # REVEAL TILE
    # ─────────────────────────

    async def reveal_tile(self, interaction, user_id, pos):
        if interaction.user.id != user_id:
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return

        g = mines_games.get(user_id)
        if not g or g["done"]:
            await interaction.response.defer()
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

            embed = discord.Embed(
                title="💥 BOOM! You Hit a Mine!",
                description=(
                    f"You found a **💣** after revealing **{g['safe_count']}** safe tile(s).\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💸 Lost: **{format_cash(bet)}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"*The board is revealed below.*"
                ),
                color=0xED4245
            )
            embed.set_footer(text=f"Bet: {format_cash(bet)}  •  Play again with .mines <amount> <mines>")
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
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return
        g = mines_games.get(user_id)
        if not g or g["safe_count"] == 0:
            await interaction.response.send_message(
                "❌ Reveal at least **one** safe tile before cashing out!", ephemeral=True
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

        if auto:
            title = "💣 Mines — BOARD CLEARED! 🎉"
            banner = "🏆 You revealed every safe tile! Incredible!"
            color = 0xFFD700
        else:
            title = "💣 Mines — Cashed Out!"
            banner = f"Smart move! You survived {safe} safe tile(s)."
            color = 0x57F287

        embed = discord.Embed(
            title=title,
            description=(
                f"*{banner}*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 Safe tiles: **{safe}**\n"
                f"📈 Multiplier: **{mult}×**\n"
                f"💰 Payout: **{format_cash(payout)}**\n"
                f"📊 Profit: **+{format_cash(profit)}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"*The board is revealed below.*"
            ),
            color=color
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}  •  Play again with .mines <amount> <mines>")
        final_view = FinalMinesView(mine_positions=g["mine_positions"], hit=None, revealed=g["revealed"])
        await interaction.response.edit_message(embed=embed, view=final_view)
        await check_achievements(self.bot, interaction.user)

    async def on_timeout_cleanup(self, user_id):
        g = mines_games.pop(user_id, None)
        if g:
            add_cash(user_id, g["bet"])
            try:
                msg = g.get("msg")
                if msg:
                    embed = discord.Embed(
                        title="💣 Mines — Timed Out",
                        description=f"⏰ Game timed out. Your bet of **{format_cash(g['bet'])}** has been returned.",
                        color=0x808080
                    )
                    await msg.edit(embed=embed, view=None)
            except Exception:
                pass


# ─────────────────────────
# GRID VIEW (BUTTONS)
# ─────────────────────────

class MinesView(discord.ui.View):

    def __init__(self, user_id, cog, game):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.cog = cog

        revealed = game["revealed"]

        # 25 tile buttons (5x5)
        for pos in range(GRID_SIZE * GRID_SIZE):
            is_revealed = pos in revealed
            emoji = "💎" if is_revealed else "⬜"
            btn = MineButton(pos=pos, emoji=emoji, disabled=is_revealed, user_id=user_id, cog=cog)
            self.add_item(btn)

        # Cashout button
        can_cashout = game["safe_count"] > 0
        bet = game["bet"]
        mines = game["mine_count"]
        safe = game["safe_count"]
        mult = calc_mult(mines, safe)
        potential = int(bet * mult)

        cashout_label = f"💰 Cash Out ({mult}×)" if can_cashout else "💰 Cash Out (reveal a tile first)"
        cashout_btn = discord.ui.Button(
            label=cashout_label,
            style=discord.ButtonStyle.green if can_cashout else discord.ButtonStyle.secondary,
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
                emoji = "⬜"
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
