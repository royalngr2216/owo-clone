from discord.ext import commands
import discord

from utils.economy import (
can_afford,
remove_cash,
add_cash,
format_cash,
add_history
)

─────────────────────────

CONFIRM VIEW

─────────────────────────

class ConfirmTransferView(discord.ui.View):

def __init__(
    self,
    sender,
    receiver,
    amount
):

    super().__init__(timeout=30)

    self.sender = sender
    self.receiver = receiver
    self.amount = amount

# ─────────────────────────
# CONFIRM
# ─────────────────────────

@discord.ui.button(
    label="Confirm",
    style=discord.ButtonStyle.success
)
async def confirm(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if interaction.user != self.sender:

        return await interaction.response.send_message(
            "This is not your transfer.",
            ephemeral=True
        )

    # CHECK AGAIN

    if not can_afford(
        self.sender.id,
        self.amount
    ):

        embed = discord.Embed(
            description=(
                "❌ You no longer have enough cash."
            ),
            color=0xED4245
        )

        return await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    # TRANSFER

    remove_cash(
        self.sender.id,
        self.amount
    )

    add_cash(
        self.receiver.id,
        self.amount
    )

    # HISTORY

    add_history(
        self.sender.id,
        "transfer",
        "loss",
        self.amount,
        self.receiver.id
    )

    add_history(
        self.receiver.id,
        "transfer",
        "win",
        self.amount,
        self.sender.id
    )

    embed = discord.Embed(
        description=(
            f"✅ Transfer Successful\n\n"
            f"{self.sender.mention} sent "
            f"{format_cash(self.amount)}\n"
            f"to {self.receiver.mention}"
        ),
        color=0x57F287
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )

# ─────────────────────────
# CANCEL
# ─────────────────────────

@discord.ui.button(
    label="Cancel",
    style=discord.ButtonStyle.danger
)
async def cancel(
    self,
    interaction: discord.Interaction,
    button: discord.ui.Button
):

    if interaction.user != self.sender:

        return await interaction.response.send_message(
            "This is not your transfer.",
            ephemeral=True
        )

    embed = discord.Embed(
        description=(
            "❌ Transfer cancelled."
        ),
        color=0xED4245
    )

    await interaction.response.edit_message(
        embed=embed,
        view=None
    )

─────────────────────────

COG

─────────────────────────

class Give(commands.Cog):

def __init__(self, bot):

    self.bot = bot

@commands.command(name="give")
async def give(
    self,
    ctx,
    member: discord.Member = None,
    amount: int = None
):

    # ─────────────────────────
    # VALIDATION
    # ─────────────────────────

    if member is None or amount is None:

        return await ctx.send(
            "Use: `.give @user amount`"
        )

    if member.bot:

        return await ctx.send(
            "You cannot send cash to bots."
        )

    if member == ctx.author:

        return await ctx.send(
            "You cannot send cash to yourself."
        )

    if amount <= 0:

        return await ctx.send(
            "Invalid amount."
        )

    if not can_afford(
        ctx.author.id,
        amount
    ):

        return await ctx.send(
            "You don't have enough cash."
        )

    # ─────────────────────────
    # CONFIRMATION
    # ─────────────────────────

    embed = discord.Embed(
        description=(

            f"💸 Transfer Confirmation\n\n"

            f"Send {format_cash(amount)}\n"
            f"to {member.mention}?"

        ),
        color=0xFEE75C
    )

    view = ConfirmTransferView(
        ctx.author,
        member,
        amount
    )

    await ctx.send(
        embed=embed,
        view=view
    )

async def setup(bot):

await bot.add_cog(
    Give(bot)
)
