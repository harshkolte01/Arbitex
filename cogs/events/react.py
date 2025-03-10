import discord
from discord.ext import commands
import asyncio

class React(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        for owner in self.bot.owner_ids:
            if f"<@{owner}>" in message.content:
                try:
                    if owner == 936490998362685450:
                        
                        emojis = [
                            "<:speed_owner:1277823286356475955>"
                        ]
                        for emoji in emojis:
                            await message.add_reaction(emoji)
                    else:
                        
                        await message.add_reaction("<:speed_owner:1277823286356475955>")
                except discord.errors.RateLimited as e:
                    await asyncio.sleep(e.retry_after)
                    await message.add_reaction("<:speed_owner:1277823286356475955>")
                except Exception as e:
                    print(f"An unexpected error occurred Auto react owner mention: {e}")
