from discord.ext import commands
import discord
import asyncio
import random
import sqlite3

from cogs.pokemon_team import get_team, fetch_pokemon_data
from utils.economy import get_cash, add_cash, remove_cash, format_cash

DB_PATH = "pokemon.db"

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

# ─────────────────────────────────────────────────────────────────
# TYPE CHART  (Gen 6+)
# ─────────────────────────────────────────────────────────────────

TYPE_CHART: dict[str, dict[str, float]] = {
    "normal":   {"rock":0.5,"ghost":0,"steel":0.5},
    "fire":     {"fire":0.5,"water":0.5,"rock":0.5,"dragon":0.5,"grass":2,"ice":2,"bug":2,"steel":2},
    "water":    {"water":0.5,"grass":0.5,"dragon":0.5,"fire":2,"ground":2,"rock":2},
    "grass":    {"fire":0.5,"grass":0.5,"poison":0.5,"flying":0.5,"bug":0.5,"dragon":0.5,"steel":0.5,"water":2,"ground":2,"rock":2},
    "electric": {"grass":0.5,"electric":0.5,"dragon":0.5,"ground":0,"flying":2,"water":2},
    "ice":      {"water":0.5,"ice":0.5,"steel":0.5,"fire":0.5,"grass":2,"ground":2,"flying":2,"dragon":2},
    "fighting": {"poison":0.5,"bug":0.5,"psychic":0.5,"flying":0.5,"fairy":0.5,"ghost":0,"normal":2,"ice":2,"rock":2,"dark":2,"steel":2},
    "poison":   {"poison":0.5,"ground":0.5,"rock":0.5,"ghost":0.5,"steel":0,"grass":2,"fairy":2},
    "ground":   {"grass":0.5,"bug":0.5,"electric":0,"flying":0,"fire":2,"poison":2,"rock":2,"steel":2},
    "flying":   {"electric":0.5,"rock":0.5,"steel":0.5,"ground":0,"grass":2,"fighting":2,"bug":2},
    "psychic":  {"psychic":0.5,"steel":0.5,"dark":0,"fighting":2,"poison":2},
    "bug":      {"fire":0.5,"fighting":0.5,"flying":0.5,"ghost":0.5,"steel":0.5,"fairy":0.5,"grass":2,"psychic":2,"dark":2},
    "rock":     {"fighting":0.5,"ground":0.5,"steel":0.5,"fire":2,"ice":2,"flying":2,"bug":2},
    "ghost":    {"normal":0,"dark":0.5,"psychic":2,"ghost":2},
    "dragon":   {"steel":0.5,"fairy":0,"dragon":2},
    "dark":     {"fighting":0.5,"dark":0.5,"fairy":0.5,"ghost":2,"psychic":2},
    "steel":    {"fire":0.5,"water":0.5,"electric":0.5,"steel":0.5,"ice":2,"rock":2,"fairy":2},
    "fairy":    {"fire":0.5,"poison":0.5,"steel":0.5,"fighting":2,"dragon":2,"dark":2},
}

def type_mult(move_type: str, def_types: list[str]) -> float:
    chart = TYPE_CHART.get(move_type, {})
    mult = 1.0
    for t in def_types:
        mult *= chart.get(t, 1.0)
    return mult

def eff_text(mult: float) -> str:
    if mult == 0:  return "It had no effect... 😶"
    if mult >= 4:  return "It's super effective!! 💥💥"
    if mult >= 2:  return "It's super effective! 💥"
    if mult < 1:   return "It's not very effective... 😬"
    return ""

# ─────────────────────────────────────────────────────────────────
# DAMAGE  (Gen 5+ formula, level 100)
# ─────────────────────────────────────────────────────────────────

def calc_damage(atk_poke: dict, move: dict, def_poke: dict) -> tuple[int, float]:
    if move["power"] == 0:
        return 0, 1.0
    if move["category"] == "special":
        A = atk_poke["stats"].get("special-attack", 80)
        D = def_poke["stats"].get("special-defense", 80)
    else:
        A = atk_poke["stats"].get("attack", 80)
        D = def_poke["stats"].get("defense", 80)

    stab  = 1.5 if move["type"] in atk_poke["types"] else 1.0
    tm    = type_mult(move["type"], def_poke["types"])
    rand  = random.uniform(0.85, 1.0)
    raw   = ((2 * 100 / 5 + 2) * move["power"] * A / D / 50 + 2)
    dmg   = int(raw * stab * tm * rand)
    return max(1, dmg), tm

# ─────────────────────────────────────────────────────────────────
# HP BAR
# ─────────────────────────────────────────────────────────────────

def hp_bar(cur: int, mx: int, length: int = 10) -> str:
    ratio  = max(0.0, cur / mx)
    filled = round(ratio * length)
    bar    = "█" * filled + "░" * (length - filled)
    pct    = round(ratio * 100)
    icon   = "🟩" if pct > 50 else ("🟨" if pct > 20 else "🟥")
    return f"{icon} `{bar}` **{cur}/{mx}**"

# ─────────────────────────────────────────────────────────────────
# BATTLE STATE
# ─────────────────────────────────────────────────────────────────

class BattleState:
    def __init__(self, p0: discord.Member, p1: discord.Member,
                 poke0: dict, poke1: dict,
                 team0: list[dict], team1: list[dict],
                 bet: int):
        self.players  = [p0, p1]
        self.pokemon  = [poke0, poke1]          # active Pokémon
        self.teams    = [team0, team1]           # full teams (list of dicts)
        self.max_hp   = [poke0["stats"]["hp"], poke1["stats"]["hp"]]
        self.cur_hp   = [poke0["stats"]["hp"], poke1["stats"]["hp"]]
        self.bet      = bet
        self.turn     = 0
        self.log      = ""

    @property
    def atker(self)      : return self.players[self.turn]
    @property
    def defer(self)      : return self.players[1 - self.turn]
    @property
    def atk_poke(self)   : return self.pokemon[self.turn]
    @property
    def def_poke(self)   : return self.pokemon[1 - self.turn]

    def deal(self, dmg: int):
        self.cur_hp[1 - self.turn] = max(0, self.cur_hp[1 - self.turn] - dmg)

    def winner(self) -> int | None:
        if self.cur_hp[0] <= 0: return 1
        if self.cur_hp[1] <= 0: return 0
        return None

    def switch(self, player_idx: int, new_poke: dict):
        """Switch the active Pokémon for player_idx."""
        self.pokemon[player_idx]  = new_poke
        self.max_hp[player_idx]   = new_poke["stats"]["hp"]
        self.cur_hp[player_idx]   = new_poke["stats"]["hp"]

    def next_turn(self):
        self.turn = 1 - self.turn

# ─────────────────────────────────────────────────────────────────
# EMBED BUILDER
# ─────────────────────────────────────────────────────────────────

def battle_embed(state: BattleState, *, title="⚔️ Pokémon Battle",
                 color=0x5865F2, final=False) -> discord.Embed:
    p0, p1   = state.players
    pk0, pk1 = state.pokemon
    h0, h1   = state.cur_hp
    m0, m1   = state.max_hp

    embed = discord.Embed(title=title, color=color)

    embed.add_field(
        name=f"{p0.display_name}  —  {pk0['display']}",
        value=hp_bar(h0, m0),
        inline=False,
    )
    embed.add_field(
        name=f"{p1.display_name}  —  {pk1['display']}",
        value=hp_bar(h1, m1),
        inline=False,
    )

    if state.log:
        embed.add_field(name="📢 Last action", value=state.log, inline=False)

    if state.bet:
        embed.add_field(name="💰 Pot", value=f"🪙 {format_cash(state.bet * 2)}", inline=True)

    if not final:
        embed.set_footer(text=f"🎮 {state.atker.display_name}'s turn")

    # GIF of the current attacker's Pokémon
    embed.set_image(url=gif_url(state.atk_poke["name"]))
    return embed

# ─────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────

class MainBattleView(discord.ui.View):
    """
    Three buttons: Move, Pokémon, Surrender
    Only the current attacker can press them.
    """

    def __init__(self, state: BattleState, cog):
        super().__init__(timeout=90)
        self.state = state
        self.cog   = cog

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.state.atker:
            await interaction.response.send_message(
                "It's not your turn!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⚔️ Move", style=discord.ButtonStyle.primary, row=0)
    async def btn_move(self, interaction: discord.Interaction, _):
        if not await self._check(interaction): return
        view = MoveSelectView(self.state, self.cog)
        await interaction.response.edit_message(
            embed=battle_embed(self.state), view=view
        )

    @discord.ui.button(label="🔄 Pokémon", style=discord.ButtonStyle.secondary, row=0)
    async def btn_pokemon(self, interaction: discord.Interaction, _):
        if not await self._check(interaction): return
        idx   = self.state.turn
        team  = self.state.teams[idx]
        # Filter out fainted / already active
        available = [
            pk for pk in team
            if pk["name"] != self.state.atk_poke["name"]
        ]
        if not available:
            await interaction.response.send_message(
                "No other Pokémon to switch to!", ephemeral=True
            )
            return
        view = SwitchSelectView(self.state, self.cog, available)
        await interaction.response.edit_message(
            embed=battle_embed(self.state), view=view
        )

    @discord.ui.button(label="🏳️ Surrender", style=discord.ButtonStyle.danger, row=0)
    async def btn_surrender(self, interaction: discord.Interaction, _):
        if not await self._check(interaction): return
        self.stop()
        await interaction.response.defer()
        winner_idx = 1 - self.state.turn
        await self.cog.end_battle(interaction.message, self.state, winner_idx, surrendered=True)

    async def on_timeout(self):
        # Auto-forfeit on inactivity
        self.stop()


class MoveSelectView(discord.ui.View):
    """Dropdown with this Pokémon's 4 moves."""

    def __init__(self, state: BattleState, cog):
        super().__init__(timeout=60)
        self.state = state
        self.cog   = cog

        options = []
        for m in state.atk_poke["moves"]:
            pwr = f"⚡{m['power']}" if m["power"] else "Status"
            options.append(discord.SelectOption(
                label=m["display"],
                description=f"{m['type'].title()}  •  {pwr}  •  {m['category'].title()}",
                value=m["name"],
            ))

        select = discord.ui.Select(
            placeholder="Choose a move...",
            options=options,
        )
        select.callback = self.on_select
        self.add_item(select)

        # Back button
        back = discord.ui.Button(label="↩ Back", style=discord.ButtonStyle.secondary)
        back.callback = self.on_back
        self.add_item(back)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user != self.state.atker:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        chosen_name = interaction.data["values"][0]
        move = next(m for m in self.state.atk_poke["moves"] if m["name"] == chosen_name)
        self.stop()
        await interaction.response.defer()
        await self.cog.process_move(interaction.message, self.state, move)

    async def on_back(self, interaction: discord.Interaction):
        if interaction.user != self.state.atker:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        view = MainBattleView(self.state, self.cog)
        await interaction.response.edit_message(embed=battle_embed(self.state), view=view)


class SwitchSelectView(discord.ui.View):
    """Dropdown to switch active Pokémon."""

    def __init__(self, state: BattleState, cog, available: list[dict]):
        super().__init__(timeout=60)
        self.state = state
        self.cog   = cog

        options = [
            discord.SelectOption(label=pk["display"], value=pk["name"])
            for pk in available
        ]
        select = discord.ui.Select(placeholder="Switch to...", options=options)
        select.callback = self.on_select
        self.add_item(select)

        back = discord.ui.Button(label="↩ Back", style=discord.ButtonStyle.secondary)
        back.callback = self.on_back
        self.add_item(back)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user != self.state.atker:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        chosen = interaction.data["values"][0]
        new_poke = next(pk for pk in self.state.teams[self.state.turn] if pk["name"] == chosen)
        self.state.switch(self.state.turn, new_poke)
        self.state.log = (
            f"**{self.state.atker.display_name}** switched to **{new_poke['display']}**! 🔄"
        )
        self.stop()
        await interaction.response.defer()
        self.state.next_turn()
        view = MainBattleView(self.state, self.cog)
        await interaction.message.edit(embed=battle_embed(self.state), view=view)

    async def on_back(self, interaction: discord.Interaction):
        if interaction.user != self.state.atker:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        view = MainBattleView(self.state, self.cog)
        await interaction.response.edit_message(embed=battle_embed(self.state), view=view)


class ChallengeView(discord.ui.View):
    """Accept / Decline a battle challenge."""

    def __init__(self, challenger: discord.Member, opponent: discord.Member,
                 bet: int, cog):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent   = opponent
        self.bet        = bet
        self.cog        = cog

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _):
        if interaction.user != self.opponent:
            await interaction.response.send_message("This isn't your challenge!", ephemeral=True)
            return
        self.stop()
        await interaction.response.defer()
        await self.cog.on_accepted(interaction.message, self.challenger, self.opponent, self.bet)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, _):
        if interaction.user not in (self.opponent, self.challenger):
            await interaction.response.send_message("Not your challenge!", ephemeral=True)
            return
        self.stop()
        await interaction.message.edit(
            embed=discord.Embed(
                description=f"**{self.opponent.display_name}** declined the battle. 💨",
                color=0xED4245,
            ),
            view=None,
        )

    async def on_timeout(self):
        pass


class PokemonPickView(discord.ui.View):
    """Both trainers pick their lead Pokémon via dropdowns."""

    def __init__(self, challenger: discord.Member, opponent: discord.Member,
                 ch_team: list[str], op_team: list[str], bet: int, cog):
        super().__init__(timeout=60)
        self.challenger  = challenger
        self.opponent    = opponent
        self.ch_team     = ch_team
        self.op_team     = op_team
        self.bet         = bet
        self.cog         = cog
        self.ch_pick: str | None = None
        self.op_pick: str | None = None

        self.add_item(self._make_select(challenger, ch_team, "ch"))
        self.add_item(self._make_select(opponent,   op_team, "op"))

    def _make_select(self, player, team, tag):
        opts = [discord.SelectOption(label=n.title(), value=n) for n in team]
        sel  = discord.ui.Select(
            placeholder=f"{player.display_name}: pick your lead Pokémon",
            options=opts,
            custom_id=tag,
        )

        async def cb(interaction: discord.Interaction):
            val = interaction.data["values"][0]
            if interaction.user.id == self.challenger.id:
                self.ch_pick = val
            elif interaction.user.id == self.opponent.id:
                self.op_pick = val
            else:
                await interaction.response.send_message("Not your battle!", ephemeral=True)
                return
            await interaction.response.send_message(
                f"✅ You chose **{val.title()}**!", ephemeral=True
            )
            if self.ch_pick and self.op_pick:
                self.stop()
                await self.cog.start_battle(
                    interaction.message, self.challenger, self.opponent,
                    self.ch_team, self.op_team,
                    self.ch_pick, self.op_pick, self.bet,
                )

        sel.callback = cb
        return sel

# ─────────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────────

class PokemonBattle(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.active: dict[int, BattleState] = {}   # channel_id → state

    # ── .battle @user <amount> ────────────────────────────────────

    @commands.command(name="battle")
    async def battle(self, ctx, opponent: discord.Member = None, amount: str = None):

        if opponent is None:
            await ctx.send(embed=discord.Embed(
                description="❌ Usage: `.battle @user <amount>`\nExample: `.battle @Ash 500k`",
                color=0xED4245,
            ))
            return

        if opponent == ctx.author or opponent.bot:
            await ctx.send(embed=discord.Embed(
                description="❌ Invalid opponent.",
                color=0xED4245,
            ))
            return

        if ctx.channel.id in self.active:
            await ctx.send(embed=discord.Embed(
                description="❌ A battle is already active in this channel!",
                color=0xED4245,
            ))
            return

        # Parse bet
        from utils.economy import parse_amount as _pa
        bet = 0
        if amount:
            cash = get_cash(ctx.author.id)
            bet  = _pa(amount, cash)
            if bet is None or bet <= 0:
                await ctx.send(embed=discord.Embed(
                    description="❌ Invalid bet amount.", color=0xED4245
                ))
                return

        # Check teams
        ch_team = get_team(str(ctx.author.id))
        op_team = get_team(str(opponent.id))
        if not ch_team:
            await ctx.send(embed=discord.Embed(
                description=f"❌ **{ctx.author.display_name}** has no team set! Use `.team`",
                color=0xED4245,
            ))
            return
        if not op_team:
            await ctx.send(embed=discord.Embed(
                description=f"❌ **{opponent.display_name}** has no team set!",
                color=0xED4245,
            ))
            return

        # Check balances
        if bet > 0:
            if get_cash(ctx.author.id) < bet:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ **{ctx.author.display_name}** can't afford that bet.",
                    color=0xED4245,
                ))
                return
            if get_cash(opponent.id) < bet:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ **{opponent.display_name}** can't afford that bet.",
                    color=0xED4245,
                ))
                return

        bet_txt = f"🪙 **{format_cash(bet)}** each" if bet else "For glory (no bet)"

        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=(
                f"{ctx.author.mention} challenges {opponent.mention}!\n\n"
                f"💰 Wager: {bet_txt}\n\n"
                f"{opponent.mention}, do you accept?"
            ),
            color=0xF1C40F,
        )
        embed.set_footer(text="You have 30 seconds to respond.")
        await ctx.send(
            embed=embed,
            view=ChallengeView(ctx.author, opponent, bet, self),
        )

    # ── Challenge accepted ─────────────────────────────────────────

    async def on_accepted(self, msg: discord.Message,
                          challenger: discord.Member, opponent: discord.Member,
                          bet: int):
        ch_team = get_team(str(challenger.id))
        op_team = get_team(str(opponent.id))

        embed = discord.Embed(
            title="⚔️ Battle Starting!",
            description=(
                "Both trainers — pick your **lead Pokémon** from the dropdowns below!\n"
                "*(Your choice is hidden from your opponent 🤫)*"
            ),
            color=0x5865F2,
        )
        view = PokemonPickView(challenger, opponent, ch_team, op_team, bet, self)
        await msg.edit(embed=embed, view=view)

    # ── Both picked → fetch & start ───────────────────────────────

    async def start_battle(
        self, msg: discord.Message,
        challenger: discord.Member, opponent: discord.Member,
        ch_team_names: list[str], op_team_names: list[str],
        ch_lead: str, op_lead: str, bet: int,
    ):
        await msg.edit(embed=discord.Embed(
            description="⏳ Loading Pokémon data...", color=0x5865F2
        ), view=None)

        # Fetch full data for all team members
        async def load_team(names: list[str], uid: str) -> list[dict]:
            result = []
            for name in names:
                data = await fetch_pokemon_data(name, uid)
                if data:
                    result.append(data)
            return result

        ch_full = await load_team(ch_team_names, str(challenger.id))
        op_full = await load_team(op_team_names, str(opponent.id))

        ch_poke = next((p for p in ch_full if p["name"] == ch_lead), ch_full[0] if ch_full else None)
        op_poke = next((p for p in op_full if p["name"] == op_lead), op_full[0] if op_full else None)

        if not ch_poke or not op_poke:
            await msg.edit(embed=discord.Embed(
                description="❌ Failed to load Pokémon data. Try again.",
                color=0xED4245,
            ))
            return

        # Deduct bets
        if bet > 0:
            remove_cash(challenger.id, bet)
            remove_cash(opponent.id, bet)

        state = BattleState(challenger, opponent, ch_poke, op_poke, ch_full, op_full, bet)
        self.active[msg.channel.id] = state

        state.log = (
            f"**{challenger.display_name}** sent out **{ch_poke['display']}**!\n"
            f"**{opponent.display_name}** sent out **{op_poke['display']}**!"
        )
        view = MainBattleView(state, self)
        await msg.edit(embed=battle_embed(state), view=view)

    # ── Process a move ────────────────────────────────────────────

    async def process_move(self, msg: discord.Message, state: BattleState, move: dict):
        dmg, tm = calc_damage(state.atk_poke, move, state.def_poke)
        state.deal(dmg)

        eff  = eff_text(tm)
        pwr_note = f" *(status)*" if move["power"] == 0 else f" for **{dmg} damage**"
        state.log = (
            f"**{state.atker.display_name}**'s **{state.atk_poke['display']}** "
            f"used **{move['display']}**{pwr_note}!"
            + (f"\n{eff}" if eff else "")
        )

        w = state.winner()
        if w is not None:
            await self.end_battle(msg, state, w)
            return

        state.next_turn()
        view = MainBattleView(state, self)
        await msg.edit(embed=battle_embed(state), view=view)

    # ── End battle ────────────────────────────────────────────────

    async def end_battle(self, msg: discord.Message, state: BattleState,
                         winner_idx: int, surrendered: bool = False):
        self.active.pop(msg.channel.id, None)

        winner = state.players[winner_idx]
        loser  = state.players[1 - winner_idx]

        if state.bet > 0:
            total = state.bet * 2
            add_cash(winner.id, total)

        embed = battle_embed(state, title="🏆 Battle Over!", color=0xF1C40F, final=True)

        result_parts = []
        if surrendered:
            result_parts.append(f"🏳️ **{loser.display_name}** surrendered!")
        else:
            loser_poke = state.pokemon[1 - winner_idx]
            result_parts.append(f"💀 **{loser_poke['display']}** fainted!")

        result_parts.append(f"🏆 **{winner.display_name}** wins!")

        if state.bet > 0:
            result_parts.append(f"💰 Prize: 🪙 **{format_cash(state.bet * 2)}**")

        embed.add_field(name="Result", value="\n".join(result_parts), inline=False)
        embed.set_image(url=gif_url(state.pokemon[winner_idx]["name"]))
        await msg.edit(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(PokemonBattle(bot))
