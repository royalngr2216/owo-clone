from discord.ext import commands
import discord
import random
import asyncio

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    parse_amount,
    format_cash,
    MAX_BET
)
from utils.stats import (
    add_stats,
    update_biggest_win,
    record_win,
    record_loss
)
from utils.achievement_checker import check_achievements
from utils.crash_render import render_crash


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
# RECENT RESULTS TICKER
# ─────────────────────────

recent_crashes = []  # rolling history of last crash points, for flavor on the intro embed


def _push_recent(point):
    recent_crashes.append(point)
    if len(recent_crashes) > 10:
        recent_crashes.pop(0)


def _recent_ticker():
    if not recent_crashes:
        return "No recent games yet — be the first! 🚀"
    parts = []
    for p in recent_crashes[-10:]:
        if p < 1.5:
            parts.append(f"`{p:.2f}×`")
        elif p < 3.0:
            parts.append(f"**{p:.2f}×**")
        else:
            parts.append(f"🔥`{p:.2f}×`")
    return "  ".join(parts)


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
                    "**Cash out** before it crashes! 📈\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "💰 **Manual** — press Cash Out whenever you want\n"
                    "🎯 **Auto** — set a target and cash out automatically\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "**Usage:**\n"
                    "`.crash <amount>` — manual cashout\n"
                    "`.crash <amount> <target×>` — auto cashout\n\n"
                    "**Example:** `.crash 1000 2.5` → auto cashes at **2.5×**\n\n"
                    "The longer you wait, the higher the risk!"
                ),
                color=0x2B2D31
            )
            embed.add_field(name="Recent Games", value=_recent_ticker(), inline=False)
            embed.set_footer(text="Average crash ~1.03×  •  3% house edge")
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
        if bet > MAX_BET:
            await ctx.send(embed=discord.Embed(
                title="❌ Bet Too High",
                description=f"Max bet is **{format_cash(MAX_BET)}**.",
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
            "history": [1.0],
            "cashed_out": False,
            "cashout_mult": None,
            "auto_target": auto_target,
            "finished": False,
        }

        # Build initial embed + graph image
        auto_str = f"🎯 Auto cashout target: **{auto_target}×**" if auto_target else "💡 Press **Cash Out** whenever you like"
        embed = discord.Embed(
            title="🚀 Crash — LIVE",
            description=auto_str,
            color=0x57F287
        )
        img = render_crash([1.0], "live", bet, bet, format_cash)
        file = discord.File(img, filename="crash.png")
        embed.set_image(url="attachment://crash.png")
        embed.set_footer(text="Multiplier climbing... don't wait too long!")

        view = CrashView(user_id=ctx.author.id, cog=self)
        msg = await ctx.send(embed=embed, file=file, view=view)
        crash_player_games[ctx.author.id]["msg"] = msg

        # ─── ANIMATE ───
        for frame_mult in frames:
            g = crash_player_games.get(ctx.author.id)
            if not g or g["cashed_out"] or g["finished"]:
                break

            g["current_mult"] = frame_mult
            g["history"].append(frame_mult)

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
                description=auto_str,
                color=color
            )
            img = render_crash(g["history"], "live", bet, potential, format_cash)
            file = discord.File(img, filename="crash.png")
            embed.set_image(url="attachment://crash.png")
            embed.set_footer(text="Multiplier climbing... don't wait too long!")
            try:
                await msg.edit(embed=embed, attachments=[file], view=view)
            except Exception:
                pass

            await asyncio.sleep(0.45)

        # Check if user already cashed out
        g = crash_player_games.get(ctx.author.id)
        if not g or g["cashed_out"] or g["finished"]:
            return

        # CRASHED — user didn't cash out
        crash_player_games[ctx.author.id]["finished"] = True
        del crash_player_games[ctx.author.id]
        record_loss(ctx.author.id, bet)
        _push_recent(crash_point)

        embed = discord.Embed(
            title="💥 CRASHED!",
            description=f"*{_crash_quip(crash_point)}*",
            color=0xED4245
        )
        img = render_crash(g["history"], "crashed", bet, 0, format_cash, crash_point=crash_point)
        file = discord.File(img, filename="crash.png")
        embed.set_image(url="attachment://crash.png")
        embed.set_footer(text=f"Lost {format_cash(bet)}  •  Play again with .crash <amount>")
        try:
            await msg.edit(embed=embed, attachments=[file], view=None)
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
        _push_recent(crash_point)

        payout = int(bet * auto_target)
        profit = payout - bet
        add_cash(user_id, payout)
        if profit > 0:
            update_biggest_win(user_id, profit)
            record_win(user_id, profit)
        else:
            record_loss(user_id, abs(profit))

        # Build the "ghost" continuation so the player can see the full run
        ghost = get_frames(crash_point)
        ghost = [m for m in ghost if m > auto_target]

        embed = discord.Embed(
            title="🎯 Auto Cashed Out!",
            description=f"Crashed at `{crash_point}×` — **+{format_cash(profit)}** locked in.",
            color=0x57F287
        )
        img = render_crash(
            g["history"], "cashed", bet, payout, format_cash,
            cashout_mult=auto_target, ghost_history=ghost, crash_point=crash_point
        )
        file = discord.File(img, filename="crash.png")
        embed.set_image(url="attachment://crash.png")
        embed.set_footer(text=f"Payout {format_cash(payout)}  •  Play again with .crash <amount>")
        try:
            await msg.edit(embed=embed, attachments=[file], view=None)
        except Exception:
            pass
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
        _push_recent(crash_point)

        payout = int(bet * current_mult)
        profit = payout - bet

        add_cash(user_id, payout)
        if profit > 0:
            update_biggest_win(user_id, profit)
            record_win(user_id, profit)
        else:
            record_loss(user_id, abs(profit))

        color = 0x57F287 if profit >= 0 else 0xED4245
        result = f"**+{format_cash(profit)}**" if profit >= 0 else f"**-{format_cash(abs(profit))}**"

        ghost = get_frames(crash_point)
        ghost = [m for m in ghost if m > current_mult]

        embed = discord.Embed(
            title="✅ Cashed Out!",
            description=f"Crashed at `{crash_point}×` — {result} locked in.",
            color=color
        )
        img = render_crash(
            g["history"], "cashed", bet, payout, format_cash,
            cashout_mult=current_mult, ghost_history=ghost, crash_point=crash_point
        )
        file = discord.File(img, filename="crash.png")
        embed.set_image(url="attachment://crash.png")
        embed.set_footer(text=f"Payout {format_cash(payout)}  •  Play again with .crash <amount>")
        await interaction.response.edit_message(embed=embed, attachments=[file], view=None)
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
        return f"It went to {crash_point}×! You should've cashed out! 🔥"


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
