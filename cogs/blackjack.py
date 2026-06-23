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
# CUSTOM EMOJIS & CONFIG
# ─────────────────────────
SHUFFLE_EMOJI = "<a:14722:1519037409579499581>"
DEALER_THINKING = "<:dealer:1519037377769640140>"


# ─────────────────────────
# CARD HELPERS
# ─────────────────────────

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

SUIT_COLORS = {"♥": "❤️", "♦": "🔶", "♠": "🖤", "♣": "🍀"}

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
        return f"`{hand[0]}`  `🂠`"
    return "  ".join(f"`{c}`" for c in hand)

def hand_label(hand, hide_second=False):
    if hide_second:
        return f"? (showing {card_value(hand[0])})"
    t = hand_total(hand)
    if t > 21:
        return f"~~{t}~~ 💥 BUST"
    if t == 21:
        return "**21** 🌟"
    return str(t)

def score_bar(total):
    """Visual score bar for the hand total."""
    if total > 21:
        return "🔴🔴🔴🔴🔴 BUST"
    filled = round((total / 21) * 5)
    bar = "🟩" * filled + "⬛" * (5 - filled)
    if total >= 18:
        bar = "🟨" * filled + "⬛" * (5 - filled)
    if total == 21:
        bar = "🏆🏆🏆🏆🏆"
    return bar


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
                    title="🃏 Game Already Running",
                    description="You already have a blackjack game in progress!\nUse the **Hit**, **Stand**, or **Double** buttons to continue.",
                    color=0xED4245
                ).set_footer(text="One game at a time!")
            )
            return

        if amount is None:
            embed = discord.Embed(
                title="🃏 Blackjack",
                description=(
                    "Beat the dealer to **21** without going over!\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "**👊 Hit** — Draw another card\n"
                    "**✋ Stand** — Keep your hand, dealer plays\n"
                    "**💰 Double** — Double bet, one card only\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🎯 Dealer hits on **16 or below**, stands on **17+**\n"
                    "🌟 **Natural Blackjack** (21 in 2 cards) pays **1.5×**!\n\n"
                    "**Usage:** `.blackjack <amount>` or `.bj <amount>`"
                ),
                color=0x2B2D31
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1234567890.webp") # Keep your original thumbnail if desired
            embed.set_footer(text="Good luck! 🍀")
            await ctx.send(embed=embed)
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

        # --- ANIMATION: SHUFFLING ---
        shuffle_embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"{SHUFFLE_EMOJI} **Shuffling the deck and dealing cards...**",
            color=0x2B2D31
        )
        msg = await ctx.send(embed=shuffle_embed)
        bj_games[ctx.author.id]["msg"] = msg
        
        await asyncio.sleep(1.2) # Smooth delay for the shuffle animation

        # Instant natural blackjack check
        if hand_total(player) == 21:
            del bj_games[ctx.author.id]
            if hand_total(dealer) == 21:
                add_cash(ctx.author.id, bet)
                embed = discord.Embed(
                    title="🤝 Push — Both Got Blackjack!",
                    color=0xFEE75C
                )
                embed.add_field(
                    name="🧑 Your Hand",
                    value=f"{fmt_hand(player)}\n{score_bar(21)} `21`",
                    inline=True
                )
                embed.add_field(
                    name="🤖 Dealer Hand",
                    value=f"{fmt_hand(dealer)}\n{score_bar(21)} `21`",
                    inline=True
                )
                embed.add_field(
                    name="💫 Result",
                    value=f"Both drew Blackjack — your **{format_cash(bet)}** is returned.",
                    inline=False
                )
            else:
                payout = int(bet * 2.5)
                add_cash(ctx.author.id, payout)
                update_biggest_win(ctx.author.id, payout - bet)
                record_win(ctx.author.id, payout - bet)
                embed = discord.Embed(
                    title="🌟 BLACKJACK! Natural 21!",
                    color=0xFFD700
                )
                embed.add_field(
                    name="🧑 Your Hand",
                    value=f"{fmt_hand(player)}\n{score_bar(21)} `21`",
                    inline=True
                )
                embed.add_field(
                    name="🤖 Dealer Hand",
                    value=f"{fmt_hand(dealer)}\n{score_bar(hand_total(dealer))} `{hand_total(dealer)}`",
                    inline=True
                )
                embed.add_field(
                    name="💰 Winnings",
                    value=f"**+{format_cash(payout - bet)}** *(1.5× payout)*",
                    inline=False
                )
            embed.set_footer(text=f"Bet: {format_cash(bet)}")
            await msg.edit(embed=embed)
            await check_achievements(self.bot, ctx.author)
            return

        # Start standard game
        embed, view = self._build_embed_view(ctx.author.id)
        await msg.edit(embed=embed, view=view)

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
            color=0x2B2D31
        )
        embed.add_field(
            name=f"🧑 Your Hand — `{ptotal}`",
            value=f"{fmt_hand(player)}\n{score_bar(ptotal)}",
            inline=True
        )
        embed.add_field(
            name=f"🤖 Dealer — `? (showing {dealer_show})`",
            value=f"{fmt_hand(dealer, hide_second=True)}\n{'⬛' * 5}",
            inline=True
        )
        
        tip = (
            "🔴 Stand on 17+" if ptotal >= 17
            else "🟡 Consider hitting!" if ptotal <= 11
            else "🟠 Risky zone — your call!"
        )
        embed.add_field(
            name="💡 Status",
            value=f"> {tip}",
            inline=False
        )
        
        embed.set_footer(text=f"Current Bet: {format_cash(bet)}  •  Hit, Stand, or Double")

        cash = get_cash(user_id)
        can_double = cash >= bet

        view = BjView(user_id=user_id, can_double=can_double, cog=self)
        return embed, view

    def _build_reveal_embed(self, player, dealer, bet, status_text):
        """Builds a temporary embed for smooth dealer animations."""
        ptotal = hand_total(player)
        dtotal = hand_total(dealer)

        embed = discord.Embed(
            title=f"{DEALER_THINKING} {status_text}",
            color=0xFEE75C
        )
        embed.add_field(
            name=f"🧑 Your Hand — `{hand_label(player)}`",
            value=f"{fmt_hand(player)}\n{score_bar(ptotal)}",
            inline=True
        )
        embed.add_field(
            name=f"🤖 Dealer Hand — `{hand_label(dealer)}`",
            value=f"{fmt_hand(dealer)}\n{score_bar(dtotal)}",
            inline=True
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}")
        return embed

    # ─────────────────────────
    # HIT
    # ─────────────────────────

    async def do_hit(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return

        g = bj_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game found.", ephemeral=True)
            return

        if g.get("done"):
            try:
                await interaction.response.defer()
            except:
                pass
            return

        card = g["deck"].pop()
        g["player"].append(card)
        ptotal = hand_total(g["player"])

        if ptotal > 21:
            g["done"] = True
            await self._end_game(interaction, user_id, "bust")
        elif ptotal == 21:
            g["done"] = True
            await self._end_game(interaction, user_id, "stand")
        else:
            embed, view = self._build_embed_view(user_id)
            await interaction.response.edit_message(embed=embed, view=view)

    # ─────────────────────────
    # STAND
    # ─────────────────────────

    async def do_stand(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return

        g = bj_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game found.", ephemeral=True)
            return

        if g.get("done"):
            try:
                await interaction.response.defer()
            except:
                pass
            return

        g["done"] = True
        await self._end_game(interaction, user_id, "stand")

    # ─────────────────────────
    # DOUBLE
    # ─────────────────────────

    async def do_double(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return

        g = bj_games.get(user_id)
        if not g:
            await interaction.response.send_message("No active game found.", ephemeral=True)
            return

        if g.get("done"):
            try:
                await interaction.response.defer()
            except:
                pass
            return

        cash = get_cash(user_id)
        if cash < g["bet"]:
            await interaction.response.send_message("❌ Not enough cash to double down!", ephemeral=True)
            return

        remove_cash(user_id, g["bet"])
        add_stats(user_id, total_gambled=g["bet"])
        g["bet"] *= 2
        g["done"] = True

        card = g["deck"].pop()
        g["player"].append(card)

        await self._end_game(interaction, user_id, "double")

    # ─────────────────────────
    # END GAME WITH ANIMATIONS
    # ─────────────────────────

    async def _end_game(self, interaction, user_id, result_type):
        g = bj_games.pop(user_id, None)
        if not g:
            try:
                await interaction.response.defer()
            except Exception:
                pass
            return

        player = g["player"]
        dealer = g["dealer"]
        deck = g["deck"]
        bet = g["bet"]
        msg = g.get("msg")

        ptotal = hand_total(player)
        
        # If player doubled and busted on the 1 extra card, override to bust so dealer doesn't draw
        if result_type == "double" and ptotal > 21:
            result_type = "bust"

        # --- ANIMATION: DEALER REVEAL AND DRAW ---
        if result_type != "bust":
            # Initial Reveal
            reveal_embed = self._build_reveal_embed(player, dealer, bet, "Dealer is revealing cards...")
            try:
                if interaction:
                    await interaction.response.edit_message(embed=reveal_embed, view=None)
                elif msg:
                    await msg.edit(embed=reveal_embed, view=None)
            except Exception:
                pass

            # Drawing Loop
            while hand_total(dealer) < 17:
                await asyncio.sleep(1.2) # Smooth delay to prevent API rate limits
                dealer.append(deck.pop())
                draw_embed = self._build_reveal_embed(player, dealer, bet, "Dealer draws a card...")
                try:
                    if interaction:
                        await interaction.edit_original_response(embed=draw_embed)
                    elif msg:
                        await msg.edit(embed=draw_embed)
                except Exception:
                    pass
            
            # Brief pause before final outcome
            await asyncio.sleep(0.8)
        else:
            # If player busted, we skip dealer drawing but still acknowledge the interaction
            try:
                if interaction:
                    await interaction.response.defer()
            except Exception:
                pass

        # --- FINAL CALCULATION ---
        dtotal = hand_total(dealer)

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
            title = "✅ You Win!"
            result_line = f"💰 **+{format_cash(profit)}**"
            banner = "🎉 Nice hand!"
        elif outcome == "push":
            add_cash(user_id, bet)
            color = 0xFEE75C
            title = "🤝 Push!"
            result_line = f"↩️ Bet returned: **{format_cash(bet)}**"
            banner = "Equal hands — nobody wins."
        else:
            record_loss(user_id, bet)
            color = 0xED4245
            title = "❌ Dealer Wins"
            result_line = f"💸 **-{format_cash(bet)}**"
            banner = "Better luck next time!"

        final_embed = discord.Embed(title=f"🃏 Blackjack — {title}", color=color)
        final_embed.description = f"*{banner}*"
        final_embed.add_field(
            name=f"🧑 Your Hand — `{hand_label(player)}`",
            value=f"{fmt_hand(player)}\n{score_bar(ptotal)}",
            inline=True
        )
        final_embed.add_field(
            name=f"🤖 Dealer Hand — `{hand_label(dealer)}`",
            value=f"{fmt_hand(dealer)}\n{score_bar(dtotal)}",
            inline=True
        )
        final_embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━", value=result_line, inline=False)
        final_embed.set_footer(text=f"Total Bet: {format_cash(bet)}  •  Play again with .bj <amount>")

        try:
            if interaction:
                # If we deferred previously instead of editing (e.g., on bust), we must use edit_original_response
                await interaction.edit_original_response(embed=final_embed, view=None)
            elif msg:
                await msg.edit(embed=final_embed, view=None)
        except discord.errors.InteractionResponded:
            try:
                await interaction.edit_original_response(embed=final_embed, view=None)
            except Exception:
                pass
        except Exception:
            pass

        try:
            await check_achievements(self.bot, ctx_user=interaction.user if interaction else None)
        except Exception:
            pass


# ─────────────────────────
# VIEW (BUTTONS)
# ─────────────────────────

class BjView(discord.ui.View):

    def __init__(self, user_id, can_double, cog):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.cog = cog
        self._responding = False
        if not can_double:
            for item in self.children:
                if hasattr(item, "label") and item.label == "Double Down":
                    item.disabled = True

    async def _safe_respond(self, interaction, coro):
        """Prevents double-response 'Interaction already acknowledged' errors."""
        if self._responding:
            try:
                await interaction.response.defer()
            except Exception:
                pass
            return
        self._responding = True
        try:
            await coro
        except Exception:
            pass
        finally:
            self._responding = False

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green, emoji="👊")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._safe_respond(interaction, self.cog.do_hit(interaction, self.user_id))

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red, emoji="✋")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._safe_respond(interaction, self.cog.do_stand(interaction, self.user_id))

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.blurple, emoji="💰")
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._safe_respond(interaction, self.cog.do_double(interaction, self.user_id))

    async def on_timeout(self):
        g = bj_games.pop(self.user_id, None)
        if g:
            add_cash(self.user_id, g["bet"])
            try:
                msg = g.get("msg")
                if msg:
                    embed = discord.Embed(
                        title="🃏 Blackjack — Timed Out",
                        description=f"⏰ Game timed out. Your bet of **{format_cash(g['bet'])}** has been returned.",
                        color=0x808080
                    )
                    await msg.edit(embed=embed, view=None)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
