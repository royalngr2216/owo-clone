from discord.ext import commands
import discord
import random
import asyncio
import math

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
# CRASH POINT GENERATION
# ─────────────────────────

def generate_crash_point():
    """
    Generates a fair crash point with exactly a 3% house edge.
    Most games will run, but the house always maintains its profit margin.
    """
    if random.random() < 0.03:
        return 1.00

    crash = 1.00 / (1.0 - random.random())
    return max(1.01, round(crash, 2))


def get_frames(crash_point):
    """Build animated multiplier frames up to crash."""
    frames = []
    mult = 1.0
    step = 0.05
    while mult < crash_point:
        frames.append(round(mult, 2))
        if mult < 2.0:
            step = 0.05
        elif mult < 5.0:
            step = 0.10
        elif mult < 10.0:
            step = 0.20
        else:
            step = 0.50
        mult = round(mult + step, 2)
    frames.append(crash_point)
    return frames


def rocket_bar(mult):
    """Visual progress bar for the multiplier."""
    capped = min(mult, 10.0)
    filled = round((capped / 10.0) * 8)
    bar = "🟩" * filled + "⬛" * (8 - filled)
    if mult >= 5:
        bar = "🟨" * filled + "⬛" * (8 - filled)
    if mult >= 10:
        bar = "🔴" * 8
    return bar


def mult_color(mult):
    if mult < 1.5:
        return 0x57F287   # green
    elif mult < 3.0:
        return 0xFEE75C   # yellow
    elif mult < 7.0:
        return 0xFF7700   # orange
    else:
        return 0xED4245   # red


# ─────────────────────────
# ACTIVE GAMES
# ─────────────────────────

crash_player_games = {}


class Crash(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["cr"])
    async def crash(self, ctx, amount: str = None, auto_cashout: str = None):
        """
        Bet on a rising multiplier — cash out before it crashes!
        """

        # Clean up stale finished games before blocking a new one
        existing = crash_player_games.get(ctx.author.id)
        if existing and existing.get("finished"):
            del crash_player_games[ctx.author.id]

        if ctx.author.id in crash_player_games:
            await ctx.send(embed=discord.Embed(
                title="🚀 Game Already Running",
                description="You already have a crash game in progress!\nPress **💰 Cash Out** to end it first.",
                color=0xED4245
            ))
            return

        if amount is None:
            embed = discord.Embed(
                title="🚀 Crash",
                description=(
                    "**cash out** before it crashes! <:bj:1492588515253551144>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "💰 **Manual** — press Cash Out whenever you want\n"
                    "🎯 **Auto** — set a target and cash out automatically\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "**Usage:**\n"
                    "`.crash <amount>` — manual cashout\n"
                    "`.crash <amount> <target×>` — auto cashout\n\n"
                    "**Example:** `.crash 1000 2.5` → auto cashes at **2.5×**\n\n"
                    "<:bj:1492588515253551144> The longer you wait, the higher the risk!"
                ),
                color=0x2B2D31
            )
            embed.set_footer(text="<:Pray:1509654308705145033>")
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

        # Parse optional auto cashout
        auto_target = None
        if auto_cashout is not None:
            try:
                auto_target = float(auto_cashout.replace("x", "").replace("X", ""))
                if auto_target <= 1.0:
                    await ctx.send(embed=discord.Embed(
                        title="❌ Invalid Target",
                        description="Auto cashout must be above **1.0×**.",
                        color=0xED4245
                    ))
                    return
            except ValueError:
                await ctx.send(embed=discord.Embed(
                    title="❌ Invalid Value",
                    description="Please enter a valid auto cashout multiplier, e.g. `2.5`",
                    color=0xED4245
                ))
                return

        remove_cash(ctx.author.id, bet)
        add_stats(ctx.author.id, games_played=1, total_gambled=bet)

        crash_point = generate_crash_point()
        frames = get_frames(crash_point)

        crash_player_games[ctx.author.id] = {
            "bet": bet,
            "crash_point": crash_point,
            "current_mult": 1.0,
            "cashed_out": False,
            "cashout_mult": None,
            "auto_target": auto_target,
            "finished": False,
        }

        # Build initial embed
        auto_str = f"🎯 Auto cashout at **{auto_target}×**" if auto_target else "💡 Press **Cash Out** manually"
        embed = discord.Embed(
            title="🚀 Crash — LIVE",
            description=(
                f"**Multiplier: `1.00×`** 🚀\n"
                f"{rocket_bar(1.0)}\n\n"
                f"{auto_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💸 Bet: **{format_cash(bet)}**\n"
                f"💰 Potential: **{format_cash(bet)}**"
            ),
            color=0x57F287
        )
        embed.set_footer(text="🚀 Launching...")

        view = CrashView(user_id=ctx.author.id, cog=self)
        msg = await ctx.send(embed=embed, view=view)
        crash_player_games[ctx.author.id]["msg"] = msg

        # ─── ANIMATE ───
        for frame_mult in frames:
            g = crash_player_games.get(ctx.author.id)
            if not g or g["cashed_out"] or g["finished"]:
                break

            g["current_mult"] = frame_mult

            # Auto cashout check
            if auto_target and frame_mult >= auto_target:
                await self._resolve_auto_cashout(ctx.author.id, auto_target, msg, bet, crash_point)
                return

            if frame_mult == crash_point:
                break

            # Update display
            potential = int(bet * frame_mult)
            color = mult_color(frame_mult)

            embed = discord.Embed(
                title="🚀 Crash — LIVE",
                description=(
                    f"**Multiplier: `{frame_mult}×`** 🚀\n"
                    f"{rocket_bar(frame_mult)}\n\n"
                    f"{auto_str}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💸 Bet: **{format_cash(bet)}**\n"
                    f"💰 Cash out now: **{format_cash(potential)}**"
                ),
                color=color
            )
            embed.set_footer(text=f"🚀 Multiplier climbing... Don't wait too long!")
            try:
                await msg.edit(embed=embed, view=view)
            except Exception:
                pass

            await asyncio.sleep(0.4)

        # Check if user already cashed out
        g = crash_player_games.get(ctx.author.id)
        if not g or g["cashed_out"] or g["finished"]:
            return

        # CRASHED — user didn't cash out
        crash_player_games[ctx.author.id]["finished"] = True
        del crash_player_games[ctx.author.id]
        record_loss(ctx.author.id, bet)

        embed = discord.Embed(
            title="💥 CRASHED!",
            description=(
                f"**Crashed at `{crash_point}×`** 💥\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💸 Lost: **{format_cash(bet)}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"*{_crash_quip(crash_point)}*"
            ),
            color=0xED4245
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}  •  Play again with .crash <amount>")
        try:
            await msg.edit(embed=embed, view=None)
        except Exception:
            pass
        await check_achievements(self.bot, ctx.author)

    # ─────────────────────────
    # AUTO CASHOUT RESOLVE
    # ─────────────────────────

    async def _resolve_auto_cashout(self, user_id, auto_target, msg, bet, crash_point):
        g = crash_player_games.get(user_id)
        if not g or g["cashed_out"] or g["finished"]:
            return

        g["cashed_out"] = True
        g["cashout_mult"] = auto_target
        g["finished"] = True
        del crash_player_games[user_id]

        payout = int(bet * auto_target)
        profit = payout - bet
        add_cash(user_id, payout)
        if profit > 0:
            update_biggest_win(user_id, profit)
            record_win(user_id, profit)
        else:
            record_loss(user_id, abs(profit))

        embed = discord.Embed(
            title="🎯 Auto Cashed Out!",
            description=(
                f"**Cashed out at `{auto_target}×`** ✅\n"
                f"Crashed at `{crash_point}×` — *just in time!*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 **+{format_cash(profit)}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Payout: **{format_cash(payout)}**"
            ),
            color=0x57F287
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}  •  Play again with .crash <amount>")
        try:
            await msg.edit(embed=embed, view=None)
        except Exception:
            pass
        # Can't use interaction here, so just check achievements via bot
        try:
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                member = guild.get_member(user_id)
                if member:
                    await check_achievements(self.bot, member)
        except Exception:
            pass

    # ─────────────────────────
    # MANUAL CASHOUT
    # ─────────────────────────

    async def cashout(self, interaction, user_id):
        if interaction.user.id != user_id:
            await interaction.response.send_message("🚫 This isn't your game!", ephemeral=True)
            return

        g = crash_player_games.get(user_id)
        if not g:
            await interaction.response.send_message("❌ No active game found.", ephemeral=True)
            return
        if g.get("cashed_out") or g.get("finished"):
            await interaction.response.send_message("You've already cashed out!", ephemeral=True)
            return

        current_mult = g.get("current_mult", 1.0)
        crash_point = g["crash_point"]
        bet = g["bet"]

        # Mark as done immediately to prevent double cashout
        g["cashed_out"] = True
        g["cashout_mult"] = current_mult
        g["finished"] = True
        del crash_player_games[user_id]

        payout = int(bet * current_mult)
        profit = payout - bet

        add_cash(user_id, payout)
        if profit > 0:
            update_biggest_win(user_id, profit)
            record_win(user_id, profit)
        else:
            record_loss(user_id, abs(profit))

        color = 0x57F287 if profit >= 0 else 0xED4245
        result = f"💰 **+{format_cash(profit)}**" if profit >= 0 else f"💸 **-{format_cash(abs(profit))}**"

        embed = discord.Embed(
            title="✅ Cashed Out!",
            description=(
                f"**Cashed out at `{current_mult}×`** ✅\n"
                f"Crashed at `{crash_point}×`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{result}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"Payout: **{format_cash(payout)}**"
            ),
            color=color
        )
        embed.set_footer(text=f"Bet: {format_cash(bet)}  •  Play again with .crash <amount>")
        await interaction.response.edit_message(embed=embed, view=None)
        await check_achievements(self.bot, interaction.user)


def _crash_quip(crash_point):
    if crash_point == 1.0:
        return "Instant crash. Brutal. 😬"
    elif crash_point < 1.5:
        return "Crashed way too early..."
    elif crash_point < 3.0:
        return "Could've cashed out if you were faster!"
    elif crash_point < 7.0:
        return "That was actually pretty high!"
    else:
        return f"It went to {crash_point}×! You should've cashed out! <:bj:1492588515253551144>"


class CrashView(discord.ui.View):

    def __init__(self, user_id, cog):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.cog = cog

    @discord.ui.button(label="Cash Out", style=discord.ButtonStyle.green, emoji="💰")
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.cashout(interaction, self.user_id)

    async def on_timeout(self):
        g = crash_player_games.pop(self.user_id, None)
        if g and not g.get("cashed_out") and not g.get("finished"):
            # Return bet on timeout
            add_cash(self.user_id, g["bet"])
            try:
                msg = g.get("msg")
                if msg:
                    embed = discord.Embed(
                        title="🚀 Crash — Timed Out",
                        description=f"⏰ Game timed out. Your bet of **{format_cash(g['bet'])}** has been returned.",
                        color=0x808080
                    )
                    await msg.edit(embed=embed, view=None)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Crash(bot))
        
