from discord.ext import commands
import discord
import random

from utils.economy import create_account, get_cash, add_cash, remove_cash, format_cash, parse_amount
from utils.stats import record_win, record_loss, get_profile
from cogs.system import update_roles
from utils.game_state import deathroll_games


class Deathroll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="deathroll")
    async def deathroll(self, ctx, opponent: discord.Member = None, bo: int = 1, amount: str = None):
        if opponent is None or amount is None:
            await ctx.send("❌ Usage: `.deathroll @user 1/3/5/7/9 amount`\nExample: `.deathroll @user 3 10k`")
            return
        if opponent == ctx.author:
            await ctx.send("❌ You cannot play yourself.")
            return
        if opponent.bot:
            await ctx.send("❌ You cannot challenge bots.")
            return
        if bo not in (1, 3, 5, 7, 9):
            await ctx.send("❌ Best-of must be 1, 3, 5, 7, or 9.")
            return
        if ctx.channel.id in deathroll_games:
            await ctx.send("❌ A deathroll game is already active in this channel.")
            return

        create_account(ctx.author.id)
        create_account(opponent.id)
        bet = parse_amount(amount, get_cash(ctx.author.id))
        if bet is None or bet <= 0:
            await ctx.send("❌ Invalid wager. Use amounts like `1000`, `10k`, `1.5k`, or `1m`.")
            return
        if bet > 100_000:
            await ctx.send("❌ Maximum wager is **100,000 NGR**.")
            return
        if get_cash(ctx.author.id) < bet:
            await ctx.send(f"❌ {ctx.author.mention} does not have enough cash.")
            return
        if get_cash(opponent.id) < bet:
            await ctx.send(f"❌ {opponent.mention} does not have enough cash.")
            return

        wins = bo // 2 + 1
        deathroll_games[ctx.channel.id] = {
            "player1": ctx.author, "player2": opponent, "turn": ctx.author,
            "current": 100, "bet": bet, "bo": bo, "wins_required": wins,
            "score1": 0, "score2": 0,
        }
        await ctx.send(embed=discord.Embed(
            title="💀 DEATHROLL",
            description=f"{ctx.author.mention} ⚔️ {opponent.mention}\n\n💵 Wager: **{format_cash(bet)}**\n\n🏆 First to **{wins}** wins\n\n🎲 Starting Number: **100**\n\nUse `.roll`",
            color=discord.Color.red(),
        ))

    @commands.command(name="roll")
    async def roll(self, ctx):
        game = deathroll_games.get(ctx.channel.id)
        if not game:
            await ctx.send("❌ No active deathroll game.")
            return
        if ctx.author.id != game["turn"].id:
            await ctx.send(f"❌ It is {game['turn'].mention}'s turn.")
            return

        rolled = random.randint(1, game["current"])
        await ctx.send(embed=discord.Embed(
            description=f"🎲 {ctx.author.mention} rolled\n# **{rolled}**",
            color=discord.Color.orange(),
        ))

        if rolled != 1:
            game["current"] = rolled
            game["turn"] = game["player2"] if game["turn"].id == game["player1"].id else game["player1"]
            await ctx.send(f"🎲 Next roll: **1–{rolled}**\n🎮 Turn: {game['turn'].mention}")
            return

        loser = ctx.author
        winner = game["player2"] if loser.id == game["player1"].id else game["player1"]
        if winner.id == game["player1"].id:
            game["score1"] += 1
        else:
            game["score2"] += 1
        await ctx.send(embed=discord.Embed(
            title="🏆 ROUND WON",
            description=f"{loser.mention} rolled **1**\n\n{winner.mention} wins the round.\n\n📊 Score\n**{game['score1']} - {game['score2']}**",
            color=discord.Color.green(),
        ))

        if game["score1"] >= game["wins_required"] or game["score2"] >= game["wins_required"]:
            await self.end_match(ctx.channel.id)
            return
        game["current"] = 100
        game["turn"] = loser
        await ctx.send(f"🎲 New round started.\n🎮 {loser.mention} goes first\nStarting Number: **100**")

    async def end_match(self, channel_id):
        game = deathroll_games.get(channel_id)
        if not game:
            return
        if game["score1"] > game["score2"]:
            winner, loser = game["player1"], game["player2"]
        else:
            winner, loser = game["player2"], game["player1"]
        amount = game["bet"]
        remove_cash(loser.id, amount)
        add_cash(winner.id, amount)
        record_win(winner.id, amount)
        record_loss(loser.id, amount)
        try:
            await update_roles(winner, get_profile(winner.id)["matches"])
            await update_roles(loser, get_profile(loser.id)["matches"])
        except Exception:
            pass
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=discord.Embed(
                title="☠️ DEATHROLL RESULT",
                description=f"{winner.mention} wins the match!\n\n📊 Final Score\n**{game['score1']} - {game['score2']}**\n\n💵 Prize: **{format_cash(amount)}**",
                color=discord.Color.dark_red(),
            ))
        deathroll_games.pop(channel_id, None)


async def setup(bot):
    await bot.add_cog(Deathroll(bot))
