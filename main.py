import discord
from discord.ext import commands

from flask import Flask

from threading import Thread

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

    print("⚙️ Loading Cogs...")

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

                except Exception as e:

                    print(
                        f"❌ Failed {file}: {e}"
                    )

# ─────────────────────────
# GLOBAL CHECK
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

    print(error)

bot = RoyalBot()

─────────────────────────

EVENTS

─────────────────────────

@bot.event
async def on_ready():

print(
    f"🚀 Logged in as {bot.user}"
)

print(
    f"🌍 Connected to "
    f"{len(bot.guilds)} servers"
)

─────────────────────────

START

─────────────────────────

if name == "main":

print("🔄 Starting Royal Economy...")

keep_alive()

token = os.getenv("TOKEN")

if not token:

    print("❌ TOKEN NOT FOUND")

else:

    bot.run(token)
