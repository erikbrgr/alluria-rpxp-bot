import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

os.chdir(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(".env")
TOKEN: str = os.getenv("TOKEN")
client = commands.Bot(command_prefix="$", intents=discord.Intents.all())

@client.event
async def on_ready():
    print("Bot has connected to Discord API")

async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")
            print(f"{filename[:-3]} has been loaded")

async def main():
    async with client:
        await load()
        await client.start(TOKEN)

asyncio.run(main())