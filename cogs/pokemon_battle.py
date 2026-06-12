from discord.ext import commands
import discord
import asyncio
import random

from cogs.pokemon_team import get_team, fetch_pokemon_data
from utils.economy import get_cash, add_cash, remove_cash, format_cash

def gif_url(name: str) -> str:
    clean = name.lower().replace(" ", "").replace(".", "").replace("'", "")
    return f"https://play.pokemonshowdown.com/sprites/xyani/{clean}.gif"

# ─────────────────────────────────────────────────────────────────
# PRIORITY BRACKETS & TYPE CHART
# ─────────────────────────────────────────────────────────────────

# Common priority moves. Any move not listed defaults to 0 priority.
PRIORITIES = {
    "helping-hand": 5,
    "protect": 4, "detect": 4, "endure": 4, "kings-shield": 4, "spiky-shield": 4,
    "fake-out": 3, "wide-guard": 3, "quick-guard": 3,
    "extreme-speed": 2, "feint": 2, "first-impression": 2,
    "quick-attack": 1, "ice-shard": 1, "mach-punch": 1, "bullet-punch": 1, 
    "aqua-jet": 1, "sucker-punch": 1, "vacuum-wave": 1, "shadow-sneak": 1, 
    "water-shuriken": 1, "accelerock": 1, "bide": 1,
    "trick-room": -7,
    "roar": -6, "whirlwind": -6, "dragon-tail": -6, "circle-throw": -6,
    "counter": -5, "mirror-coat": -5,
    "avalanche": -4, "revenge": -4,
}

def get_priority(move_name: str) -> int:
    return PRIORITIES.get(move_name.lower().replace(" ", "-"), 0)

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
# STAT CALC & DAMAGE
# ─────────────────────────────────────────────────────────────────

def apply_level_100_stats(poke_data: dict) -> dict:
    """Converts raw API base stats into competitive Level 100 stats."""
    new_stats = {}
    for stat, base in poke_data["stats"].items():
        if stat == "hp":
            new_stats[stat] = 2 * base + 162  # Formula simulating standard EVs/IVs at Lvl 100
        else:
            new_stats[stat] = 2 * base + 57
    poke_data["stats"] = new_stats
    return poke_data

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
# BATTLE STATE (Simultaneous Actions)
# ─────────────────────────────────────────────────────────────────

class BattleState:
    def __init__(self, p0: discord.Member, p1: discord.Member,
                 poke0: dict, poke1: dict,
                 team0: list[dict], team1: list[dict],
                 bet: int):
        self.players  = [p0, p1]
        self.pokemon  = [poke0, poke1]          # active Pokémon
        self.teams    = [team0, team1]           # full teams
        self.max_hp   = [poke0["stats"]["hp"], poke1["stats"]["hp"]]
        self.cur_hp   = [poke0["stats"]["hp"], poke1["stats"]["hp"]]
        self.bet      = bet
        self.turn_num = 1
        self.log      = "The battle has begun! Both trainers must choose an action."
        self.actions  = {}  # user_id -> dict {"type": "move"/"switch", "data": dict}
        self.main_msg = None # Stores the embed message so it can be updated easily

    def deal(self, p_idx: int, dmg: int):
        self.cur_hp[p_idx] = max(0, self.cur_hp[p_idx] - dmg)

    def winner(self) -> int | None:
        if self.cur_hp[0] <= 0: return 1
        if self.cur_hp[1] <= 0: return 0
        return None

    def switch(self, player_idx: int, new_poke: dict):
        self.pokemon[player_idx]  = new_poke
        self.max_hp[player_idx]   = new_poke["stats"]["hp"]
        self.cur_hp[player_idx]   = new_poke["stats"]["hp"]

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
        embed.add_field(name="📢 Match Log", value=state.log, inline=False)

    if state.bet:
        embed.add_field(name="💰 Pot", value=f"🪙 {format_cash(state.bet * 2)}", inline=True)

    if not final:
        status = f"⏳ Turn {state.turn_num} — "
        if len(state.actions) == 0:
            status += "Waiting for both trainers..."
        elif len(state.actions) == 1:
            status += "Waiting for 1 trainer..."
        embed.set_footer(text=status)

    return embed

# ─────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────

class MainBattleView(discord.ui.View):
    """The public main menu attached to the battle embed."""
    def __init__(self, state: BattleState, cog):
        super().__init__(timeout=120)
        self.state = state
        self.cog   = cog

    @discord.ui.button(label="⚔️ Choose Action", style=discord.ButtonStyle.primary, row=0)
    async def btn_action(self, interaction: discord.Interaction, _):
        if interaction.user not in self.state.players:
            return await interaction.response.send_message("You are not in this battle!", ephemeral=True)
        
        if interaction.user.id in self.state.actions:
            return await interaction.response.send_message("You already locked in! Waiting for your opponent...", ephemeral=True)
            
        p_idx = 0 if interaction.user.id == self.state.players[0].id else 1
        
        # Opens an ephemeral private view so choices remain hidden
        view = ActionSelectView(self.state, self.cog, p_idx)
        await interaction.response.send_message("Choose your move or switch:", view=view, ephemeral=True)

    @discord.ui.button(label="🏳️ Surrender", style=discord.ButtonStyle.danger, row=0)
    async def btn_surrender(self, interaction: discord.Interaction, _):
        if interaction.user not in self.state.players:
            return await interaction.response.send_message("You are not in this battle!", ephemeral=True)
            
        self.stop()
        await interaction.response.defer()
        winner_idx = 1 if interaction.user.id == self.state.players[0].id else 0
        await self.cog.end_battle(self.state.main_msg, self.state, winner_idx, surrendered=True)


class ActionSelectView(discord.ui.View):
    """Hidden ephemeral view to pick a move or a switch."""
    def __init__(self, state: BattleState, cog, p_idx: int):
        super().__init__(timeout=60)
        self.state = state
        self.cog = cog
        self.p_idx = p_idx
        
        # Moves dropdown
        move_opts = []
        for m in state.pokemon[p_idx]["moves"]:
            prio = get_priority(m["name"])
            prio_str = f" | Prio: +{prio}" if prio > 0 else (f" | Prio: {prio}" if prio < 0 else "")
            pwr = f"⚡{m['power']}" if m["power"] else "Status"
            move_opts.append(discord.SelectOption(
                label=m["display"],
                description=f"{m['type'].title()} • {pwr}{prio_str}",
                value=f"move_{m['name']}"
            ))
            
        sel_move = discord.ui.Select(placeholder="⚔️ Select a Move...", options=move_opts)
        sel_move.callback = self.on_select
        self.add_item(sel_move)
        
        # Switch dropdown
        available_team = [pk for pk in state.teams[p_idx] if pk["name"] != state.pokemon[p_idx]["name"]]
        if available_team:
            switch_opts = [discord.SelectOption(label=pk["display"], value=f"switch_{pk['name']}") for pk in available_team]
            sel_switch = discord.ui.Select(placeholder="🔄 Switch Pokémon...", options=switch_opts)
            sel_switch.callback = self.on_select
            self.add_item(sel_switch)

    async def on_select(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        
        if val.startswith("move_"):
            m_name = val.split("_")[1]
            move = next(m for m in self.state.pokemon[self.p_idx]["moves"] if m["name"] == m_name)
            self.state.actions[interaction.user.id] = {"type": "move", "data": move}
            
        elif val.startswith("switch_"):
            p_name = val.split("_")[1]
            poke = next(p for p in self.state.teams[self.p_idx] if p["name"] == p_name)
            self.state.actions[interaction.user.id] = {"type": "switch", "data": poke}

        await interaction.response.edit_message(content="✅ Action locked in! Waiting for opponent...", view=None)
        
        # If both players have locked in, trigger resolution
        if len(self.state.actions) == 2:
            await self.cog.resolve_turn(self.state)


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
            custom_id=tag, # Use custom_id to enforce ownership
        )

        async def cb(interaction: discord.Interaction):
            val = interaction.data["values"][0]
            
            # Validation strictly checks who clicked which dropdown
            if interaction.custom_id == "ch":
                if interaction.user.id != self.challenger.id:
                    return await interaction.response.send_message("Use your own dropdown!", ephemeral=True)
                self.ch_pick = val
            elif interaction.custom_id == "op":
                if interaction.user.id != self.opponent.id:
                    return await interaction.response.send_message("Use your own dropdown!", ephemeral=True)
                self.op_pick = val
                
            await interaction.response.send_message(f"✅ Lead locked in!", ephemeral=True)
            
            if self.ch_pick and self.op_pick:
                self.stop()
                await self.cog.start_battle(
                    interaction.message, self.challenger, self.opponent,
                    self.ch_team, self.op_team,
                    self.ch_pick, self.op_pick, self.bet,
                )

        sel.callback = cb
        return sel

class ChallengeView(discord.ui.View):
    """Accept / Decline a battle challenge."""
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bet: int, cog):
        super().__init__(timeout=30)
        self.challenger = challenger
        self.opponent   = opponent
        self.bet        = bet
        self.cog        = cog

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _):
        if interaction.user != self.opponent:
            return await interaction.response.send_message("This isn't your challenge!", ephemeral=True)
        self.stop()
        await interaction.response.defer()
        await self.cog.on_accepted(interaction.message, self.challenger, self.opponent, self.bet)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, _):
        if interaction.user not in (self.opponent, self.challenger):
            return await interaction.response.send_message("Not your challenge!", ephemeral=True)
        self.stop()
        await interaction.message.edit(
            embed=discord.Embed(description=f"**{self.opponent.display_name}** declined the battle. 💨", color=0xED4245),
            view=None,
        )

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
            return await ctx.send(embed=discord.Embed(description="❌ Usage: `.battle @user <amount>`\nExample: `.battle @Ash 500k`", color=0xED4245))

        if opponent == ctx.author or opponent.bot:
            return await ctx.send(embed=discord.Embed(description="❌ Invalid opponent.", color=0xED4245))

        if ctx.channel.id in self.active:
            return await ctx.send(embed=discord.Embed(description="❌ A battle is already active in this channel!", color=0xED4245))

        from utils.economy import parse_amount as _pa
        bet = 0
        if amount:
            cash = get_cash(ctx.author.id)
            bet  = _pa(amount, cash)
            if bet is None or bet <= 0:
                return await ctx.send(embed=discord.Embed(description="❌ Invalid bet amount.", color=0xED4245))

        ch_team = get_team(str(ctx.author.id))
        op_team = get_team(str(opponent.id))
        if not ch_team:
            return await ctx.send(embed=discord.Embed(description=f"❌ **{ctx.author.display_name}** has no team set! Use `.team`", color=0xED4245))
        if not op_team:
            return await ctx.send(embed=discord.Embed(description=f"❌ **{opponent.display_name}** has no team set!", color=0xED4245))

        if bet > 0:
            if get_cash(ctx.author.id) < bet:
                return await ctx.send(embed=discord.Embed(description=f"❌ **{ctx.author.display_name}** can't afford that bet.", color=0xED4245))
            if get_cash(opponent.id) < bet:
                return await ctx.send(embed=discord.Embed(description=f"❌ **{opponent.display_name}** can't afford that bet.", color=0xED4245))

        bet_txt = f"🪙 **{format_cash(bet)}** each" if bet else "For glory (no bet)"

        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{ctx.author.mention} challenges {opponent.mention}!\n\n💰 Wager: {bet_txt}\n\n{opponent.mention}, do you accept?",
            color=0xF1C40F,
        )
        await ctx.send(embed=embed, view=ChallengeView(ctx.author, opponent, bet, self))

    # ── Challenge accepted ─────────────────────────────────────────

    async def on_accepted(self, msg: discord.Message, challenger: discord.Member, opponent: discord.Member, bet: int):
        ch_team = get_team(str(challenger.id))
        op_team = get_team(str(opponent.id))

        embed = discord.Embed(
            title="⚔️ Battle Starting!",
            description="Both trainers — pick your **lead Pokémon** from the dropdowns below!\n*(Your choice is hidden from your opponent 🤫)*",
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
        await msg.edit(embed=discord.Embed(description="⏳ Loading Pokémon data...", color=0x5865F2), view=None)

        async def load_team(names: list[str], uid: str) -> list[dict]:
            result = []
            for name in names:
                data = await fetch_pokemon_data(name, uid)
                if data:
                    data = apply_level_100_stats(data) # Scales stats for fair calculations
                    result.append(data)
            return result

        ch_full = await load_team(ch_team_names, str(challenger.id))
        op_full = await load_team(op_team_names, str(opponent.id))

        ch_poke = next((p for p in ch_full if p["name"] == ch_lead), ch_full[0] if ch_full else None)
        op_poke = next((p for p in op_full if p["name"] == op_lead), op_full[0] if op_full else None)

        if not ch_poke or not op_poke:
            return await msg.edit(embed=discord.Embed(description="❌ Failed to load Pokémon data. Try again.", color=0xED4245))

        if bet > 0:
            remove_cash(challenger.id, bet)
            remove_cash(opponent.id, bet)

        state = BattleState(challenger, opponent, ch_poke, op_poke, ch_full, op_full, bet)
        state.main_msg = msg
        self.active[msg.channel.id] = state

        state.log = f"**{challenger.display_name}** sent out **{ch_poke['display']}**!\n**{opponent.display_name}** sent out **{op_poke['display']}**!"
        
        await msg.edit(embed=battle_embed(state), view=MainBattleView(state, self))

    # ── Turn Resolution ───────────────────────────────────────────

    async def resolve_turn(self, state: BattleState):
        p0_id = state.players[0].id
        p1_id = state.players[1].id
        
        a0 = state.actions[p0_id]
        a1 = state.actions[p1_id]

        # Sorting key for who goes first: Switches > Priority > Speed > Random
        def get_speed_score(p_idx, action):
            if action["type"] == "switch":
                return 1000000 # Switches always go first
            prio = get_priority(action["data"]["name"])
            spd = state.pokemon[p_idx]["stats"]["speed"]
            return (prio * 10000) + spd
            
        score0 = get_speed_score(0, a0)
        score1 = get_speed_score(1, a1)
        
        if score0 > score1:
            order = [0, 1]
        elif score1 > score0:
            order = [1, 0]
        else:
            order = [0, 1] if random.random() > 0.5 else [1, 0]

        log_lines = []
        
        for p_idx in order:
            if state.cur_hp[p_idx] <= 0: continue # Fainted mons can't act
            
            action = state.actions[state.players[p_idx].id]
            other_idx = 1 - p_idx
            
            if action["type"] == "switch":
                new_poke = action["data"]
                state.switch(p_idx, new_poke)
                log_lines.append(f"🔄 **{state.players[p_idx].display_name}** withdrew and sent out **{new_poke['display']}**!")
                
            elif action["type"] == "move":
                move = action["data"]
                
                if state.cur_hp[other_idx] <= 0:
                    log_lines.append(f"💨 **{state.pokemon[p_idx]['display']}**'s attack missed because there's no target!")
                    continue
                    
                dmg, tm = calc_damage(state.pokemon[p_idx], move, state.pokemon[other_idx])
                state.deal(other_idx, dmg)
                
                eff = eff_text(tm)
                pwr_note = f" *(status)*" if move["power"] == 0 else f" for **{dmg} damage**!"
                log_lines.append(f"⚔️ **{state.pokemon[p_idx]['display']}** used **{move['display']}**{pwr_note}")
                if eff: log_lines.append(f"└ {eff}")
                
                if state.cur_hp[other_idx] <= 0:
                    log_lines.append(f"💀 **{state.pokemon[other_idx]['display']}** fainted!")

        state.log = "\n".join(log_lines)
        state.actions.clear()
        state.turn_num += 1

        w = state.winner()
        if w is not None:
            await self.end_battle(state.main_msg, state, w)
        else:
            await state.main_msg.edit(embed=battle_embed(state), view=MainBattleView(state, self))

    # ── End battle ────────────────────────────────────────────────

    async def end_battle(self, msg: discord.Message, state: BattleState, winner_idx: int, surrendered: bool = False):
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
            result_parts.append(f"💀 **{loser_poke['display']}** was defeated!")

        result_parts.append(f"🏆 **{winner.display_name}** wins!")

        if state.bet > 0:
            result_parts.append(f"💰 Prize: 🪙 **{format_cash(state.bet * 2)}**")

        embed.add_field(name="Result", value="\n".join(result_parts), inline=False)
        embed.set_image(url=gif_url(state.pokemon[winner_idx]["name"]))
        await msg.edit(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(PokemonBattle(bot))
