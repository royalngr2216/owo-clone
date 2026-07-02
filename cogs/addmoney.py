import discord
from discord.ext import commands

# 1. CHANGE THIS NAME (e.g., from Economy to AdminMoney)
class AdminMoney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addmoney")
    @commands.is_owner()
    async def add_money(self, ctx, member: discord.Member, amount: int):
        """Adds money to a user's account without deducting from the owner."""
        
        if amount <= 0:
            await ctx.send("Please specify an amount greater than 0.")
            return

        # ---------------------------------------------------------
        # YOUR DATABASE LOGIC GOES HERE
        # (Don't forget to update this part later so the money actually saves!)
        # ---------------------------------------------------------

        await ctx.send(f"✅ Successfully added **{amount}** coins to {member.mention}'s account!")

    @add_money.error
    async def add_money_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ You do not have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("**Usage:** `.addmoney @user <amount>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid user or amount specified. Make sure you are pinging a valid user and providing a number.")

async def setup(bot):
    # 2. CHANGE THIS NAME TO MATCH THE CLASS ABOVE
    await bot.add_cog(AdminMoney(bot))
  
