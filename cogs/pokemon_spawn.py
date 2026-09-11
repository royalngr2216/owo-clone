from discord.ext import commands, tasks
import discord
import random
import asyncio
import aiohttp
import datetime
import io
import math

from PIL import Image, ImageDraw, ImageFont

from utils.pokemon_db import (
    db,
    get_balls,
    remove_ball,
    log_emiel_event,
)


# ─────────────────────────────────────────────────────────────────────
# URL HELPERS
# ─────────────────────────────────────────────────────────────────────

def _clean(name: str) -> str:
    return name.lower().replace(" ", "").replace(".", "").replace("'", "")

def gif_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/xyani/{_clean(name)}.gif"

def sprite_url(name: str) -> str:
    return f"https://play.pokemonshowdown.com/sprites/gen5/{_clean(name)}.png"

BALLS = {
    "pb": {"name": "Poké Ball", "db": "pokeball"},
    "ub": {"name": "Ultra Ball", "db": "ultraball"},
    "mb": {"name": "Master Ball", "db": "masterball"}
}

BALL_EMOJI = {
    "pb": "<:pb:1517998351227031632>",
    "ub": "<:ub:1517997681564324114>",
    "mb": "<a:mb:1517997721288704111>",
}

CATCH_RATES = {
    "pb": {"common": 35, "pseudo": 15, "ultra_beast": 15, "legendary": 7, "mythical": 3},
    "ub": {"common": 60, "pseudo": 30, "ultra_beast": 30, "legendary": 15, "mythical": 6},
    "mb": {"common": 100, "pseudo": 100, "ultra_beast": 100, "legendary": 100, "mythical": 100}
}

EMIEL_STEAL_CHANCE = 0.20

FAILURE_FLAVOR_TEXT = [
    "The Pokémon escaped!", "It broke free at the last second!", "That was close!",
    "The ball shattered open!", "So close!",
]

MYTHICAL_IDS: frozenset[int] = frozenset({151, 251, 385, 386, 489, 490, 491, 492, 493, 494, 647, 648, 649, 719, 720, 721, 801, 802, 807, 808, 809, 893})
LEGENDARY_IDS: frozenset[int] = frozenset({144,145,146,150,243,244,245,249,250,377,378,379,380,381,382,383,384,480,481,482,483,484,485,486,487,488,638,639,640,641,642,643,644,645,646,716,717,718,785,786,787,788,789,790,791,792,800,888,889,890,891,892,894,895,896,897,898})
ULTRA_BEAST_IDS: frozenset[int] = frozenset({793,794,795,796,797,798,799,803,804,805,806})
PSEUDO_LEGENDARY_IDS: frozenset[int] = frozenset({149,248,373,376,445,635,706,784,887})

def get_rarity(pokedex_id: int) -> str:
    if pokedex_id in MYTHICAL_IDS: return "mythical"
    if pokedex_id in LEGENDARY_IDS: return "legendary"
    if pokedex_id in ULTRA_BEAST_IDS: return "ultra_beast"
    if pokedex_id in PSEUDO_LEGENDARY_IDS: return "pseudo"
    return "common"

RARITY_ORDER = {"mythical":0,"legendary":1,"ultra_beast":2,"pseudo":3,"common":4}
RARITY_COLORS = {"mythical":(255,215,0),"legendary":(163,73,232),"ultra_beast":(32,210,210),"pseudo":(232,100,32),"common":(88,101,242)}
RARITY_LABELS = {"mythical":"✨ Mythical","legendary":"👑 Legendary","ultra_beast":"🔮 Ultra Beast","pseudo":"🔥 Pseudo","common":"Common"}
RARITY_EMBED_COLORS = {"mythical":0xFFD700,"legendary":0xA349E8,"ultra_beast":0x20D2D2,"pseudo":0xE86420,"common":0x57F287}
RARITY_SPAWN_EXTRA = {"mythical":"\n\n✨ **A MYTHICAL Pokémon has appeared — incredibly rare!** ✨","legendary":"\n\n👑 **A LEGENDARY Pokémon has appeared!** 👑","ultra_beast":"\n\n🔮 **An ULTRA BEAST has appeared!** 🔮","pseudo":"\n\n🔥 **A powerful Pseudo-Legendary has appeared!** 🔥","common":""}

COLS=3; CELL_W=112; CELL_H=162; PAD=14; GAP=10; SPRITE_SZ=84
BG_COLOR=(32,34,37); CARD_COLOR=(47,49,54); SHADOW_CLR=(22,23,25); WHITE=(255,255,255); SUBTEXT=(148,155,164)

def _load_font(size: int, bold: bool=False) -> ImageFont.ImageFont:
    suffix="-Bold" if bold else ""
    candidates=[f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",f"/usr/share/fonts/truetype/liberation/LiberationSans{suffix}.ttf",f"/usr/share/fonts/truetype/freefont/FreeSans{'Bold' if bold else ''}.ttf",f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf","/System/Library/Fonts/Helvetica.ttc"]
    for path in candidates:
        try: return ImageFont.truetype(path,size)
        except Exception: continue
    return ImageFont.load_default()

def _draw_centered(draw,cx,y,text,font,fill):
    bbox=draw.textbbox((0,0),text,font=font); tw=bbox[2]-bbox[0]; draw.text((cx-tw//2,y),text,fill=fill,font=font)

async def _fetch_sprite(session,name):
    try:
        async with session.get(sprite_url(name),timeout=aiohttp.ClientTimeout(total=6)) as r:
            if r.status != 200: return None
            return Image.open(io.BytesIO(await r.read())).convert("RGBA")
    except Exception: return None

async def build_dex_image(rows:list) -> io.BytesIO:
    n=len(rows); n_rows=math.ceil(n/COLS)
    iw=PAD+COLS*CELL_W+(COLS-1)*GAP+PAD; ih=PAD+n_rows*CELL_H+(n_rows-1)*GAP+PAD
    img=Image.new("RGBA",(iw,ih),BG_COLOR); draw=ImageDraw.Draw(img)
    font_name=_load_font(12,True); font_id=_load_font(11); font_unk=_load_font(30,True); font_rarity=_load_font(9)
    async with aiohttp.ClientSession() as sess: sprites=await asyncio.gather(*[_fetch_sprite(sess,r["name"]) for r in rows])
    for i,(row,spr) in enumerate(zip(rows,sprites)):
        col=i%COLS; ri=i//COLS; x=PAD+col*(CELL_W+GAP); y=PAD+ri*(CELL_H+GAP); rarity=get_rarity(row["pokedex_id"]); accent_clr=RARITY_COLORS[rarity]
        draw.rounded_rectangle([x+3,y+3,x+CELL_W+3,y+CELL_H+3],radius=12,fill=SHADOW_CLR); draw.rounded_rectangle([x,y,x+CELL_W,y+CELL_H],radius=12,fill=CARD_COLOR); draw.rounded_rectangle([x+8,y+5,x+CELL_W-8,y+9],radius=4,fill=accent_clr)
        sprite_top=y+16
        if spr:
            spr.thumbnail((SPRITE_SZ,SPRITE_SZ),Image.LANCZOS); sw,sh=spr.size; img.paste(spr,(x+(CELL_W-sw)//2,sprite_top+(SPRITE_SZ-sh)//2),spr)
        else: _draw_centered(draw,x+CELL_W//2,sprite_top+SPRITE_SZ//2-18,"?",font_unk,SUBTEXT)
        ty=sprite_top+SPRITE_SZ+7; cx=x+CELL_W//2; label=row["display"]; label=label[:12]+"…" if len(label)>13 else label
        _draw_centered(draw,cx,ty,label,font_name,WHITE); _draw_centered(draw,cx,ty+17,f"#{row['pokedex_id']:03}",font_id,SUBTEXT)
        if rarity!="common": _draw_centered(draw,cx,ty+31,RARITY_LABELS[rarity],font_rarity,accent_clr)
    buf=io.BytesIO(); img.save(buf,"PNG"); buf.seek(0); return buf

def sort_rows(rows:list,mode:str)->list:
    if mode=="rarity": return sorted(rows,key=lambda r:(RARITY_ORDER[get_rarity(r["pokedex_id"])],r["pokedex_id"]))
    return sorted(rows,key=lambda r:r["pokedex_id"])

_SORT_DEFS=[("dex","🔢 Dex #"),("rarity","⭐ Rarity")]; _SORT_DISPLAY={k:v for k,v in _SORT_DEFS}

class DexView(discord.ui.View):
    def __init__(self,rows:list,target:discord.Member):
        super().__init__(timeout=120); self._all_rows=rows; self.target=target; self.sort_mode="dex"; self.page=0; self.msg=None; self._apply_sort(); self._rebuild_buttons()
    def _apply_sort(self): self.rows=sort_rows(self._all_rows,self.sort_mode); self.pages=[self.rows[i:i+9] for i in range(0,len(self.rows),9)]; self.page=min(self.page,max(0,len(self.pages)-1))
    def _rebuild_buttons(self):
        self.clear_items()
        prev=discord.ui.Button(emoji="⬅️",style=discord.ButtonStyle.secondary,row=0,disabled=self.page==0); prev.callback=self._prev; self.add_item(prev)
        nxt=discord.ui.Button(emoji="➡️",style=discord.ButtonStyle.secondary,row=0,disabled=self.page>=len(self.pages)-1); nxt.callback=self._next; self.add_item(nxt)
        sort=discord.ui.Select(placeholder=f"Sort: {_SORT_DISPLAY[self.sort_mode]}",options=[discord.SelectOption(label=v,value=k,default=k==self.sort_mode) for k,v in _SORT_DEFS],row=1); sort.callback=self._sort; self.add_item(sort)
    async def _prev(self,interaction): self.page-=1; self._rebuild_buttons(); await self._refresh(interaction)
    async def _next(self,interaction): self.page+=1; self._rebuild_buttons(); await self._refresh(interaction)
    async def _sort(self,interaction): self.sort_mode=interaction.data["values"][0]; self.page=0; self._apply_sort(); self._rebuild_buttons(); await self._refresh(interaction)
    async def _refresh(self,interaction):
        embed=discord.Embed(title=f"📖 {self.target.display_name}'s Pokédex",description=f"Page {self.page+1}/{max(1,len(self.pages))}",color=0x5865F2); file=discord.File(await build_dex_image(self.pages[self.page]) if self.pages else io.BytesIO(),filename="dex.png"); embed.set_image(url="attachment://dex.png"); await interaction.response.edit_message(embed=embed,view=self,attachments=[file])
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.target.id: await interaction.response.send_message("❌ This isn't your Pokédex.",ephemeral=True); return False
        return True

class PokemonSpawn(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.command(name="dex",aliases=["pokedex"])
    async def dex(self,ctx,member:discord.Member=None):
        target=member or ctx.author; rows=list(db.pokemon_collection.find({"user_id":str(target.id)})); rows=[{"name":r.get("name","").lower(),"display":r.get("display",r.get("name","Unknown")),"pokedex_id":r.get("pokedex_id",0)} for r in rows]
        view=DexView(rows,target); embed=discord.Embed(title=f"📖 {target.display_name}'s Pokédex",description=f"Page 1/{max(1,len(view.pages))}",color=0x5865F2)
        if view.pages:
            file=discord.File(await build_dex_image(view.pages[0]),filename="dex.png"); embed.set_image(url="attachment://dex.png"); msg=await ctx.send(embed=embed,file=file,view=view); view.msg=msg
        else: await ctx.send(embed=embed)

    @tasks.loop(minutes=30)
    async def spawn_loop(self): pass

async def setup(bot): await bot.add_cog(PokemonSpawn(bot))
