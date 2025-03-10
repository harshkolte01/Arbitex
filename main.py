import os
import asyncio
import traceback
from threading import Thread
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands

from core import Context
from core.Cog import Cog
from core.Olympus import Olympus
from utils.Tools import *
from utils.config import *

import jishaku

# Configuring Jishaku behavior
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "False"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

client = Olympus()
tree = client.tree

WEBHOOK_URL = "https://discord.com/api/webhooks/1340638746713784350/q3AN4moJUzHaVPWXBKK9oIqx7k6-JKdl6g_eo6-X0IYHdMXQM5O4gQsalOBSERUMQ3Yd"  # Replace with your actual webhook URL

@client.event
async def on_ready():
    await client.wait_until_ready()
    print("Bot Loaded & Online!")
    print(f"Logged in as: {client.user} ({client.user.id})")
    print(f"Connected to: {len(client.guilds)} guilds")
    print(f"Connected to: {len(client.users)} users")
    
    try:
        synced = await client.tree.sync()
        print(f"Synced Total {len(client.commands)} Client Commands and {len(synced)} Slash Commands")
    except Exception as e:
        pass

@client.event
async def on_command_completion(context: Context):
    executed_command = context.command.qualified_name
    embed = discord.Embed(color=0x2f3136)
    embed.set_author(name=f"Executed {executed_command} Command By: {context.author}", icon_url=context.author.avatar.url if context.author.avatar else None)
    embed.set_thumbnail(url=context.author.avatar.url if context.author.avatar else None)
    embed.add_field(name="Command Name:", value=executed_command, inline=False)
    embed.add_field(name="Executed By:", value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})", inline=False)
    if context.guild:
        embed.add_field(name="Executed In:", value=f"{context.guild.name} | ID: {context.guild.id}", inline=False)
        embed.add_field(name="Channel:", value=f"{context.channel.name} | ID: {context.channel.id}", inline=False)
    embed.set_footer(text="Powered By Arbitex Development™", icon_url=client.user.display_avatar.url if client.user.display_avatar else None)
    
    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            await webhook.send(embed=embed)
    except Exception as e:
        pass

from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Arbitex Development 2025"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()

keep_alive()

async def main():
    async with client:
        os.system("clear")
        await client.load_extension("jishaku")
        try:
            await client.start("MTMzMzc3OTE4MDYxNzIwMzgyMg.GbnlZh.6gWqbM8gSQodHygZyTs8t_q-JX7ZsBcyPBeOuo")  # Replace with your actual bot token
        except Exception as e:
            print(f"Bot failed to start: {e}")

if __name__ == "__main__":
    asyncio.run(main())
