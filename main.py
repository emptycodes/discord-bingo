import discord
from discord.ext import commands

from dotenv import load_dotenv
from os import getenv

from cogs.bingo_game import BingoGame

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)


@bot.event
async def on_ready():
    await bot.add_cog(BingoGame(bot))
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

load_dotenv()
bot.run(getenv("DISCORD_TOKEN"))
