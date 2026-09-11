from discord.ext import commands
import discord
import random

from utils.economy import create_account, get_cash, add_cash, remove_cash, format_cash, parse_amount
from utils.stats import record_win, record_loss, get_profile
from cogs.system import update_roles
from utils.game_state import crack_games


class Crack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="crack")
    async def crack(self, ctx, opponent: discord.Member = None, bo: int = 1, amount: str = None):
        if opponent is None or amount is None:
            await ctx.send("❌ Usage: `.crack @user 1/3/5/7/9 amount`\nExample: `.crack @user 3 10k`")
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
        if ctx.channel.id in crack_games:
            await ctx.send("❌ A crack match is already active in this channel.")
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
        crack_games[ctx.channel.id] = {
            "player1": ctx.author, "player2": opponent, "bet": bet,
            "bo": bo, "wins_required": wins, "score1": 0, "score2": 0,
            "secret": random.randint(1, 100), "turn": ctx.author,
        }
        await ctx.send(embed=discord.Embed(
            title="💥 CRACK",
            description=f"{ctx.author.mention} ⚔️ {opponent.mention}\n\n💵 Wager: **{format_cash(bet)}**\n\n🏆 First to **{wins}** wins\n\n🎯 Guess a number between **1 and 100**\n\n🎮 {ctx.author.mention} goes first\n\nUse `.guess number`",
            color=discord.Color.orange(),
        ))

    @commands.command(name="guess")
    async def guess(self, ctx, number: int = None):
        game = crack_games.get(ctx.channel.id)
        if not game:
            await ctx.send("❌ No active crack game.")
            return
        if number is None:
            await ctx.send("❌ Use `.guess <number>` (1–100).")
            return
        if ctx.author.id != game["turn"].id:
            await ctx.send(f"❌ It is {game['turn'].mention}'s turn.")
            return
        if not 1 <= number <= 100:
            await ctx.send("❌ Guess a number between 1 and 100.")
            return

        secret = game["secret"]
        p1, p2 = game["player1"], game["player2"]
        if number == secret:
            winner = ctx.author
            loser = p2 if winner.id == p1.id else p1
            if winner.id == p1.id:
                game["score1"] += 1
            else:
                game["score2"] += 1
            await ctx.send(embed=discord.Embed(
                title="🏆 ROUND WON",
                description=f"🎯 Secret Number: **{secret}**\n\n{winner.mention} cracked it.\n\n📊 Score\n**{game['score1']} - {game['score2']}**",
                color=discord.Color.green(),
            ))
            if game["score1"] >= game["wins_required"] or game["score2"] >= game["wins_required"]:
                await self.end_match(ctx.channel.id)
                return
            game["secret"] = random.randint(1, 100)
            game["turn"] = loser
            await ctx.send(f"🎯 New round started.\n🎮 {loser.mention} goes first")
            return

        game["turn"] = p2 if game["turn"].id == p1.id else p1
        hint = "📈 Higher" if number < secret else "📉 Lower"
        await ctx.send(embed=discord.Embed(
            description=f"{hint}\n\n🎮 Turn:\n{game['turn'].mention}",
            color=discord.Color.red(),
        ))

    async def end_match(self, channel_id):
        game = crack_games.get(channel_id)
        if not game:
            return
        if game["score1"] > game["score2"]:
            winner, loser = game["player1"], game["player2"]
        else:
            winner, loser = game["player2"], game["player1"]
        bet = game["bet"]
        remove_cash(loser.id, bet)
        add_cash(winner.id, bet)
        record_win(winner.id, bet)
        record_loss(loser.id, bet)
        try:
            await update_roles(winner, get_profile(winner.id)["matches"])
            await update_roles(loser, get_profile(loser.id)["matches"])
        except Exception:
            pass
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=discord.Embed(
                title="🏆 CRACK RESULT",
                description=f"{winner.mention} wins the match!\n\n📊 Final Score\n**{game['score1']} - {game['score2']}**\n\n💵 Prize: **{format_cash(bet)}**",
                color=discord.Color.gold(),
            ))
        crack_games.pop(channel_id, None)


async def setup(bot):
    await bot.add_cog(Crack(bot))
