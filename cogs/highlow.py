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
# CARD HELPERS
# ─────────────────────────

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUES = {r: i + 2 for i, r in enumerate(RANKS)}  # 2=2, A=14

def random_card():
    return random.choice(RANKS), random.choice(SUITS)

def card_str(rank, suit):
    return f"`{rank}{suit}`"

# Multiplier increases with each correct guess
MULTIPLIERS = [1.5, 2.0, 2.75, 3.75, 5.0, 7.0, 10.0]


# ─────────────────────────
# ACTIVE GAMES
# ─────────────────────────

hl_games = {}


class HigherLower(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["hl"])
    async def highlow(self, ctx, amount: str = None):
        """Guess if the next card is higher or lower! Chain wins to multiply."""

        if ctx.author.id in hl_games:
            await ctx.send(embed=discord.Embed(
                description="❌ You already have a game running! Use the buttons.",
                color=0xED4245
            ))
            return

        if amount is None:
            embed = discord.Embed(
                title="🎴 Higher or Lower",
                description=(
                    "**How to play:**\n\n"
                    "A card is shown. Guess if the **next card** is higher or lower.\n"
                    "Each correct guess multiplies your winnings:\n\n"
                    "• Round 1 → **1.5×**\n"
                    "• Round 2 → **2×**\n"
                    "• Round 3 → **2.75×**\n"
                    "• Round 4 → **3.75×**\n"
                    "• Round 5 → **5×**\n"
                    "• Round 6 → **7×**\n"
                    "• Round 7 → **10×** 🎉\n\n"
                    "Cash out anytime with **Collect**!\n"
                    "Tie = neutral (no win/loss for that round)\n\n"
                    "Usage: `.highlow <amount>` or `.hl <amount>`"
                ),
                color=0x5865F2
            )
            await ctx.send(embed=embed)
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

        rank, suit = random_card()
        hl_games[ctx.author.id] = {
            "bet": bet,
            "current_rank": rank,
            "current_suit": suit,
            "round": 0,
        }

        embed, view = self._build(ctx.author.id)
        msg = await ctx.send(embed=embed, view=view)
        hl_games[ctx.author.id]["msg"] = msg

    # ─────────────────────────
    # BUILD EMBED
    # ─────────────────────────

    def _build(self, user_id):
        g = hl_games[user_id]
        bet = g["bet"]
        rnd = g["round"]
        mult = MULTIPLIERS[rnd]
        potential = int(bet * mult)

        next_mult = MULTIPLIERS[rnd + 1] if rnd + 1 < len(MULTIPLIERS) else None

        desc = (
            f"**Current card:** {card_str(g['current_rank'], g['current_suit'])} "
            f"(value **{RANK_VALUES[g['current_rank']]}**)\n\n"
            f"🎯 Round **{rnd + 1}** of {len(MULTIPLIERS)}\n"
            f"💰 Collect now: **{format_cash(potential)}**"
        )
        if next_mult:
            desc += f"\n⬆️ Keep going: **{format_cash(int(bet * next_mult))}** if correct"

        embed = discord.Embed(
            title="🎴 Higher or Lower",
            description=desc,
            color=0x5865F2
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")

        is_last = (rnd >= len(MULTIPLIERS) - 1)
        view = HlView(user_id=user_id, cog=self, collect_only=is_last)
        return embed, view

    # ─────────────────────────
    # GUESS
    # ─────────────────────────

    async def do_guess(self, interaction, user_id, direction):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        g = hl_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        old_rank = g["current_rank"]
        old_val = RANK_VALUES[old_rank]
        new_rank, new_suit = random_card()
        new_val = RANK_VALUES[new_rank]

        if new_val == old_val:
            # Tie — redraw, neutral outcome
            g["current_rank"] = new_rank
            g["current_suit"] = new_suit
            embed, view = self._build(user_id)
            extra = f"\n\n🤝 **Tie!** ({card_str(new_rank, new_suit)}) — redraw, no change."
            embed.description += extra
            await interaction.response.edit_message(embed=embed, view=view)
            return

        correct = (
            (direction == "higher" and new_val > old_val) or
            (direction == "lower" and new_val < old_val)
        )

        g["current_rank"] = new_rank
        g["current_suit"] = new_suit
        g["round"] += 1

        if correct:
            if g["round"] >= len(MULTIPLIERS):
                # Max rounds reached — auto collect
                await self._collect(interaction, user_id, forced=True, last_card=card_str(new_rank, new_suit))
            else:
                embed, view = self._build(user_id)
                embed.description = f"✅ Correct! Next: {card_str(new_rank, new_suit)} (value **{new_val}**)\n\n" + embed.description
                embed.color = 0x57F287
                await interaction.response.edit_message(embed=embed, view=view)
        else:
            # Lost
            del hl_games[user_id]
            bet = g["bet"]
            record_loss(user_id, bet)
            embed = discord.Embed(
                title="🎴 Higher or Lower — WRONG!",
                description=(
                    f"The next card was {card_str(new_rank, new_suit)} (value **{new_val}**)\n"
                    f"You guessed **{direction}** — wrong!\n\n"
                    f"❌ Lost **{format_cash(bet)}**"
                ),
                color=0xED4245
            )
            embed.set_footer(text=f"Bet: {format_cash(bet)}")
            await interaction.response.edit_message(embed=embed, view=None)
            await check_achievements(self.bot, interaction.user)

    # ─────────────────────────
    # COLLECT
    # ─────────────────────────

    async def do_collect(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        await self._collect(interaction, user_id)

    async def _collect(self, interaction, user_id, forced=False, last_card=None):
        g = hl_games.pop(user_id, None)
        if not g:
            return

        bet = g["bet"]
        rnd = g["round"]
        mult = MULTIPLIERS[min(rnd, len(MULTIPLIERS) - 1)]
        payout = int(bet * mult)
        profit = payout - bet

        add_cash(user_id, payout)
        update_biggest_win(user_id, profit)
        record_win(user_id, profit)

        title = "🎴 Higher or Lower — MAX WIN! 🎉" if forced else "🎴 Higher or Lower — Cashed Out!"
        desc = f"💰 You cashed out after **{rnd}** correct guess(es)!\n\n"
        if last_card:
            desc += f"Final card: {last_card}\n\n"
        desc += (
            f"Multiplier: **{mult}×**\n"
            f"Payout: **{format_cash(payout)}**\n"
            f"Profit: **{format_cash(profit)}**"
        )

        embed = discord.Embed(title=title, description=desc, color=0x57F287)
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        await interaction.response.edit_message(embed=embed, view=None)
        await check_achievements(self.bot, interaction.user)

    async def on_timeout_cleanup(self, user_id):
        g = hl_games.pop(user_id, None)
        if g:
            add_cash(user_id, g["bet"])


# ─────────────────────────
# VIEW
# ─────────────────────────

class HlView(discord.ui.View):

    def __init__(self, user_id, cog, collect_only=False):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog
        if collect_only:
            for item in self.children:
                if hasattr(item, "label") and item.label in ["Higher", "Lower"]:
                    item.disabled = True

    @discord.ui.button(label="Higher", style=discord.ButtonStyle.green, emoji="⬆️")
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_guess(interaction, self.user_id, "higher")

    @discord.ui.button(label="Lower", style=discord.ButtonStyle.red, emoji="⬇️")
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_guess(interaction, self.user_id, "lower")

    @discord.ui.button(label="Collect", style=discord.ButtonStyle.blurple, emoji="💰")
    async def collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_collect(interaction, self.user_id)

    async def on_timeout(self):
        await self.cog.on_timeout_cleanup(self.user_id)


async def setup(bot):
    await bot.add_cog(HigherLower(bot))
