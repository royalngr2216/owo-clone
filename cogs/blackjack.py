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
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def make_deck():
    return [f"{r}{s}" for s in SUITS for r in RANKS]

def card_value(card):
    rank = card[:-1]
    if rank in ["J", "Q", "K"]:
        return 10
    if rank == "A":
        return 11
    return int(rank)

def hand_total(hand):
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def fmt_hand(hand, hide_second=False):
    if hide_second and len(hand) >= 2:
        return f"`{hand[0]}`  `??`"
    return "  ".join(f"`{c}`" for c in hand)

def hand_label(hand, hide_second=False):
    if hide_second:
        return f"? (showing {card_value(hand[0])})"
    t = hand_total(hand)
    if t > 21:
        return f"~~{t}~~ BUST"
    return str(t)


# ─────────────────────────
# ACTIVE GAMES
# ─────────────────────────

bj_games = {}


class Blackjack(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────
    # COMMAND
    # ─────────────────────────

    @commands.command(aliases=["bj"])
    async def blackjack(self, ctx, amount: str = None):

        if ctx.author.id in bj_games:
            await ctx.send(
                embed=discord.Embed(
                    description="❌ You already have a game running! Use the buttons to play.",
                    color=0xED4245
                )
            )
            return

        if amount is None:
            embed = discord.Embed(
                title="🃏 Blackjack",
                description=(
                    "**How to play:**\n\n"
                    "Get closer to **21** than the dealer without going over.\n\n"
                    "• **Hit** — draw another card\n"
                    "• **Stand** — keep your hand\n"
                    "• **Double** — double your bet and draw exactly one card\n\n"
                    "Dealer must hit on 16 or below, stand on 17+.\n"
                    "**Blackjack** (21 with 2 cards) pays **1.5×**!\n\n"
                    "Usage: `.blackjack <amount>` or `.bj <amount>`"
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

        deck = make_deck()
        random.shuffle(deck)

        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        bj_games[ctx.author.id] = {
            "player": player,
            "dealer": dealer,
            "deck": deck,
            "bet": bet,
            "done": False
        }

        # Instant natural blackjack check
        if hand_total(player) == 21:
            del bj_games[ctx.author.id]
            if hand_total(dealer) == 21:
                # Push
                add_cash(ctx.author.id, bet)
                embed = discord.Embed(
                    title="🃏 Blackjack — PUSH",
                    description=(
                        f"**Your hand:** {fmt_hand(player)} — **{hand_total(player)}**\n"
                        f"**Dealer hand:** {fmt_hand(dealer)} — **{hand_total(dealer)}**\n\n"
                        f"Both got Blackjack! Your **{format_cash(bet)}** is returned."
                    ),
                    color=0xFEE75C
                )
            else:
                payout = int(bet * 2.5)
                add_cash(ctx.author.id, payout)
                update_biggest_win(ctx.author.id, payout - bet)
                record_win(ctx.author.id, payout - bet)
                embed = discord.Embed(
                    title="🃏 Blackjack — BLACKJACK! 🎉",
                    description=(
                        f"**Your hand:** {fmt_hand(player)} — **21**\n"
                        f"**Dealer hand:** {fmt_hand(dealer)} — **{hand_total(dealer)}**\n\n"
                        f"Natural Blackjack! You won **{format_cash(payout - bet)}**!"
                    ),
                    color=0x57F287
                )
            await ctx.send(embed=embed)
            await check_achievements(self.bot, ctx.author)
            return

        embed, view = self._build_embed_view(ctx.author.id)
        msg = await ctx.send(embed=embed, view=view)
        bj_games[ctx.author.id]["msg"] = msg

    # ─────────────────────────
    # BUILD EMBED + VIEW
    # ─────────────────────────

    def _build_embed_view(self, user_id):
        g = bj_games[user_id]
        player = g["player"]
        dealer = g["dealer"]
        bet = g["bet"]

        ptotal = hand_total(player)
        dealer_show = card_value(dealer[0])

        embed = discord.Embed(
            title="🃏 Blackjack",
            color=0x5865F2
        )
        embed.add_field(
            name=f"🧑 Your Hand — {ptotal}",
            value=fmt_hand(player),
            inline=False
        )
        embed.add_field(
            name=f"🤖 Dealer Hand — ? (showing {dealer_show})",
            value=fmt_hand(dealer, hide_second=True),
            inline=False
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")

        cash = get_cash(user_id)
        can_double = cash >= bet

        view = BjView(user_id=user_id, can_double=can_double, cog=self)
        return embed, view

    # ─────────────────────────
    # HIT
    # ─────────────────────────

    async def do_hit(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        g = bj_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        card = g["deck"].pop()
        g["player"].append(card)
        ptotal = hand_total(g["player"])

        if ptotal > 21:
            # Bust
            await self._end_game(interaction, user_id, "bust")
        elif ptotal == 21:
            # Auto-stand on 21
            await self._end_game(interaction, user_id, "stand")
        else:
            embed, view = self._build_embed_view(user_id)
            await interaction.response.edit_message(embed=embed, view=view)

    # ─────────────────────────
    # STAND
    # ─────────────────────────

    async def do_stand(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        await self._end_game(interaction, user_id, "stand")

    # ─────────────────────────
    # DOUBLE
    # ─────────────────────────

    async def do_double(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return

        g = bj_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return

        cash = get_cash(user_id)
        if cash < g["bet"]:
            await interaction.response.send_message("❌ Not enough cash to double!", ephemeral=True)
            return

        remove_cash(user_id, g["bet"])
        add_stats(user_id, total_gambled=g["bet"])
        g["bet"] *= 2

        card = g["deck"].pop()
        g["player"].append(card)

        await self._end_game(interaction, user_id, "stand")

    # ─────────────────────────
    # END GAME
    # ─────────────────────────

    async def _end_game(self, interaction, user_id, result_type):
        g = bj_games.pop(user_id, None)
        if not g:
            return

        player = g["player"]
        dealer = g["dealer"]
        deck = g["deck"]
        bet = g["bet"]

        ptotal = hand_total(player)

        # Dealer draws
        if result_type != "bust":
            while hand_total(dealer) < 17:
                dealer.append(deck.pop())

        dtotal = hand_total(dealer)

        # Determine outcome
        if ptotal > 21:
            outcome = "bust"
        elif dtotal > 21:
            outcome = "win"
        elif ptotal > dtotal:
            outcome = "win"
        elif ptotal == dtotal:
            outcome = "push"
        else:
            outcome = "loss"

        if outcome == "win":
            payout = bet * 2
            profit = bet
            add_cash(user_id, payout)
            update_biggest_win(user_id, profit)
            record_win(user_id, profit)
            color = 0x57F287
            title = "🃏 Blackjack — YOU WIN! 🎉"
            result_line = f"✅ Won **{format_cash(profit)}**!"
        elif outcome == "push":
            add_cash(user_id, bet)
            color = 0xFEE75C
            title = "🃏 Blackjack — PUSH"
            result_line = f"🤝 Bet returned: **{format_cash(bet)}**"
        else:
            record_loss(user_id, bet)
            color = 0xED4245
            title = "🃏 Blackjack — YOU LOSE"
            result_line = f"❌ Lost **{format_cash(bet)}**"

        embed = discord.Embed(title=title, color=color)
        embed.add_field(
            name=f"🧑 Your Hand — {hand_label(player)}",
            value=fmt_hand(player),
            inline=False
        )
        embed.add_field(
            name=f"🤖 Dealer Hand — {hand_label(dealer)}",
            value=fmt_hand(dealer),
            inline=False
        )
        embed.add_field(name="Result", value=result_line, inline=False)
        embed.set_footer(text=f"Bet: {format_cash(bet)}")

        await interaction.response.edit_message(embed=embed, view=None)
        ctx_user = interaction.user
        await check_achievements(self.bot, ctx_user)


# ─────────────────────────
# VIEW (BUTTONS)
# ─────────────────────────

class BjView(discord.ui.View):

    def __init__(self, user_id, can_double, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog
        if not can_double:
            for item in self.children:
                if hasattr(item, "label") and item.label == "Double":
                    item.disabled = True

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green, emoji="👊")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_hit(interaction, self.user_id)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red, emoji="✋")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_stand(interaction, self.user_id)

    @discord.ui.button(label="Double", style=discord.ButtonStyle.blurple, emoji="💰")
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.do_double(interaction, self.user_id)

    async def on_timeout(self):
        g = bj_games.pop(self.user_id, None)
        if g:
            add_cash(self.user_id, g["bet"])


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
