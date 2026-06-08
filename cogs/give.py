from discord.ext import commands
import discord

from utils.economy import (
    get_cash,
    add_cash,
    remove_cash,
    format_cash
)


class GiveView(discord.ui.View):

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

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user != self.sender:

            await interaction.response.send_message(
                "❌ Not for you.",
                ephemeral=True
            )

            return

        cash = get_cash(self.sender.id)

        if cash < self.amount:

            embed = discord.Embed(

                description="❌ Not enough cash.",

                color=0xED4245
            )

            await interaction.response.edit_message(
                embed=embed,
                view=None
            )

            return

        remove_cash(
            self.sender.id,
            self.amount
        )

        add_cash(
            self.receiver.id,
            self.amount
        )

        embed = discord.Embed(

            title="💸 CASH SENT",

            description=(

                f"{self.sender.mention} sent\n"
                f"**{format_cash(self.amount)}**\n"
                f"to {self.receiver.mention}"

            ),

            color=0x57F287
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

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

            await interaction.response.send_message(
                "❌ Not for you.",
                ephemeral=True
            )

            return

        embed = discord.Embed(

            description="❌ Transfer cancelled.",

            color=0xED4245
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )


class Give(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.command(name="give")
    async def give(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):

        if member.bot:

            return

        if member == ctx.author:

            return

        if amount <= 0:

            return

        cash = get_cash(ctx.author.id)

        if cash < amount:

            embed = discord.Embed(

                description="❌ Not enough cash.",

                color=0xED4245
            )

            await ctx.send(embed=embed)

            return

        embed = discord.Embed(

            title="💸 Confirm Transfer",

            description=(

                f"Send "
                f"**{format_cash(amount)}**\n"
                f"to {member.mention}?"

            ),

            color=0x5865F2
        )

        view = GiveView(
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
