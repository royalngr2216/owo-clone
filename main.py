import discord
from discord.ext import commands

from flask import Flask
from threading import Thread

import traceback
import os

─────────────────────────

KEEP ALIVE

─────────────────────────

app = Flask(name)

@app.route("/")
def home():

return "Royal Economy Online"

def run_web():

port = int(
    os.environ.get(
        "PORT",
        10000
    )
)

app.run(
    host="0.0.0.0",
    port=port
)

def keep_alive():

t = Thread(
    target=run_web
)

t.start()

─────────────────────────

BOT

─────────────────────────

intents = discord.Intents.default()

intents.message_content = True
intents.members = True

class RoyalBot(commands.Bot):

def __init__(self):

    super().__init__(

        command_prefix=".",

        intents=intents,

        help_command=None

    )

    self.maintenance = False

# ─────────────────────────
# LOAD COGS
# ─────────────────────────

async def setup_hook(self):

    print("\n⚙️ Loading Cogs...\n")

    if os.path.exists("./cogs"):

        for file in os.listdir("./cogs"):

            if file.endswith(".py"):

                try:

                    await self.load_extension(
                        f"cogs.{file[:-3]}"
                    )

                    print(
                        f"✅ Loaded {file}"
                    )

                except Exception:

                    print(
                        f"\n❌ FAILED TO LOAD: {file}\n"
                    )

                    traceback.print_exc()

                    print("\n")

    print("\n✅ Cog loading finished.\n")

# ─────────────────────────
# COMMAND ERRORS
# ─────────────────────────

async def on_command_error(
    self,
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return

    print("\n❌ COMMAND ERROR ❌\n")

    traceback.print_exception(
        type(error),
        error,
        error.__traceback__
    )

    print("\n")

    embed = discord.Embed(

        description=(
            "❌ Command crashed.\n"
            "Check Render logs."
        ),

        color=0xED4245
    )

    try:

        await ctx.send(
            embed=embed
        )

    except:
        pass

bot = RoyalBot()

─────────────────────────

EVENTS

─────────────────────────

@bot.event
async def on_ready():

print("\n🚀 BOT ONLINE 🚀\n")

print(
    f"Logged in as: {bot.user}"
)

print(
    f"Servers: {len(bot.guilds)}"
)

print("\n")

─────────────────────────

START BOT

─────────────────────────

if name == "main":

print("\n🔄 Starting Royal Economy...\n")

keep_alive()

token = os.getenv("TOKEN")

if not token:

    print(
        "\n❌ TOKEN NOT FOUND ❌\n"
    )

else:

    bot.run(token)
