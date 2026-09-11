from discord.ext import commands
import discord
import random

from data.pokemon import POKEMON_LIST
from utils.stats import record_win, record_loss, get_profile
from utils.economy import create_account, get_cash, add_cash, remove_cash, format_cash, parse_amount
from cogs.system import update_roles
from utils.game_state import randoms_games

SPECIAL_PLAYERS = {1287545546231255092, 711959035238285443}
SPECIAL_POOL = [p for p in POKEMON_LIST if 450 <= p.total_stats <= 780]


class Randoms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="randoms")
    async def randoms(self, ctx, opponent: discord.Member = None, bo: int = 1, amount: str = None):
        if opponent is None:
            await ctx.send("❌ Usage: `.randoms @user 1/3/5/7/9 [amount]`\nExample: `.randoms @user 3 10k`")
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
        if ctx.channel.id in randoms_games:
            await ctx.send("❌ A randoms match is already active in this channel.")
            return

        create_account(ctx.author.id)
        create_account(opponent.id)
        bet = 0
        if amount is not None:
            bet = parse_amount(amount, get_cash(ctx.author.id))
            if bet is None or bet <= 0:
                await ctx.send("❌ Invalid wager. Use `1000`, `10k`, `1.5k`, or `1m`.")
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
        randoms_games[ctx.channel.id] = {
            "player1": ctx.author, "player2": opponent, "bo": bo,
            "wins_required": wins, "score1": 0, "score2": 0,
            "bet": bet, "picks": {},
        }
        await ctx.send(embed=discord.Embed(
            title="🐉 RANDOMS",
            description=f"{ctx.author.mention} ⚔️ {opponent.mention}\n\n💵 Wager: **{format_cash(bet)}**\n\n🏆 First to **{wins}** wins\n\n🎮 Both players use `.pick`",
            color=discord.Color.purple(),
        ))

    @commands.command(name="pick")
    async def pick(self, ctx):
        game = randoms_games.get(ctx.channel.id)
        if not game:
            await ctx.send("❌ No active randoms game.")
            return
        if ctx.author.id not in (game["player1"].id, game["player2"].id):
            await ctx.send("❌ You are not in this match.")
            return
        if ctx.author.id in {u.id for u in game["picks"]}:
            await ctx.send("❌ You already picked this round.")
            return

        if ctx.author.id in SPECIAL_PLAYERS:
            roll = random.randint(1, 100)
            if roll <= 20:
                pool = [p for p in POKEMON_LIST if 450 <= p.total_stats <= 500]
            elif roll <= 35:
                pool = [p for p in POKEMON_LIST if 500 < p.total_stats <= 530]
            elif roll <= 80:
                pool = [p for p in POKEMON_LIST if 530 < p.total_stats <= 580]
            elif roll <= 92:
                pool = [p for p in POKEMON_LIST if 570 < p.total_stats <= 680]
            else:
                pool = [p for p in POKEMON_LIST if 680 < p.total_stats <= 780]
            pokemon = random.choice(pool or SPECIAL_POOL)
        else:
            pokemon = random.choice(POKEMON_LIST)

        game["picks"][ctx.author] = pokemon
        clean_name = pokemon.name.lower().replace(" ", "").replace(".", "").replace("'", "").replace("-", "")
        embed_color = discord.Color.green() if pokemon.total_stats < 400 else discord.Color.blue() if pokemon.total_stats < 500 else discord.Color.red()
        embed = discord.Embed(description=f"🎴 {ctx.author.mention} picked\n# **{pokemon.name}**", color=embed_color)
        embed.set_image(url=f"https://play.pokemonshowdown.com/sprites/xyani/{clean_name}.gif")
        for name, value in (("❤️ HP", pokemon.hp), ("⚔️ Attack", pokemon.attack), ("🛡️ Defense", pokemon.defense), ("✨ Sp. Attack", pokemon.sp_attack), ("🔮 Sp. Defense", pokemon.sp_defense), ("⚡ Speed", pokemon.speed)):
            embed.add_field(name=name, value=f"**{value}**", inline=True)
        embed.add_field(name="💥 Total Power", value=f"# **{pokemon.total_stats}**", inline=False)
        await ctx.send(embed=embed)
        if len(game["picks"]) == 2:
            await self.resolve_round(ctx.channel.id)

    async def resolve_round(self, channel_id):
        game = randoms_games.get(channel_id)
        if not game or len(game["picks"]) != 2:
            return
        p1, p2 = game["player1"], game["player2"]
        poke1, poke2 = game["picks"][p1], game["picks"][p2]
        if poke1.total_stats > poke2.total_stats:
            game["score1"] += 1; winner = p1
        elif poke2.total_stats > poke1.total_stats:
            game["score2"] += 1; winner = p2
        else:
            winner = None
        channel = self.bot.get_channel(channel_id)
        if winner:
            await channel.send(embed=discord.Embed(description=f"🏆 {winner.mention} wins the round!\n\n📊 Score\n**{game['score1']} - {game['score2']}**", color=discord.Color.gold()))
        else:
            await channel.send(embed=discord.Embed(description=f"🤝 Round tied!\n\n📊 Score\n**{game['score1']} - {game['score2']}**", color=discord.Color.light_grey()))
        game["picks"] = {}
        if game["score1"] >= game["wins_required"] or game["score2"] >= game["wins_required"]:
            await self.end_match(channel_id)
        else:
            await channel.send(f"🎮 Next round! Both players use `.pick`. Current score: **{game['score1']} - {game['score2']}**")

    async def end_match(self, channel_id):
        game = randoms_games.get(channel_id)
        if not game:
            return
        winner, loser = (game["player1"], game["player2"]) if game["score1"] > game["score2"] else (game["player2"], game["player1"])
        bet = game["bet"]
        if bet > 0:
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
            prize = format_cash(bet) if bet else "No wager"
            await channel.send(embed=discord.Embed(title="🏆 RANDOMS RESULT", description=f"{winner.mention} wins the match!\n\n📊 Final Score\n**{game['score1']} - {game['score2']}**\n\n💵 Prize: **{prize}**", color=discord.Color.gold()))
        randoms_games.pop(channel_id, None)


async def setup(bot):
    await bot.add_cog(Randoms(bot))
