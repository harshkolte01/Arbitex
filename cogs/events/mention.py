import discord
import aiosqlite
import time
from discord.ext import commands
from utils import getConfig
from utils.Tools import get_ignore_data
from datetime import datetime, timedelta, timezone

class Mention(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x2F3136  # Dark theme color
        self.bot_name = "Arbitex"
        self.start_time = time.time()  # Bot start time for uptime

    async def is_blacklisted(self, message: discord.Message) -> bool:
        async with aiosqlite.connect("db/block.db") as db:
            async with db.execute("SELECT 1 FROM guild_blacklist WHERE guild_id = ?", (message.guild.id,)) as cursor:
                if await cursor.fetchone():
                    return True
                
            async with db.execute("SELECT 1 FROM user_blacklist WHERE user_id = ?", (message.author.id,)) as cursor:
                if await cursor.fetchone():
                    return True

        return False

    def get_bot_uptime(self) -> str:
        uptime_seconds = int(time.time() - self.start_time)
        return str(timedelta(seconds=uptime_seconds))  # Converts seconds to formatted time string

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if await self.is_blacklisted(message):
            return

        ignore_data = await get_ignore_data(message.guild.id)
        if str(message.author.id) in ignore_data["user"] or str(message.channel.id) in ignore_data["channel"]:
            return

        if message.reference and message.reference.resolved:
            if isinstance(message.reference.resolved, discord.Message):
                if message.reference.resolved.author.id == self.bot.user.id:
                    return

        guild_id = message.guild.id
        data = await getConfig(guild_id)
        prefix = data.get("prefix", "$")  # Default prefix if none is set

        if self.bot.user in message.mentions and len(message.content.strip().split()) == 1:
            latency = round(self.bot.latency * 1000, 2)  # Convert to ms
            total_guilds = len(self.bot.guilds)  # Total servers

            total_users = sum(g.member_count or 0 for g in self.bot.guilds)  # Total members (handling None values)
            total_bots = sum(len([m for m in g.members if m.bot]) for g in self.bot.guilds)  # Counting bots correctly
            total_humans = total_users - total_bots  # Total humans
            
            # Get active users
            online_users = sum(
                m.status in {discord.Status.online, discord.Status.idle, discord.Status.dnd} 
                for g in self.bot.guilds 
                for m in g.members if not m.bot
            )
            offline_users = total_humans - online_users
            
            # Find users created in the last 30 days (FIXED TIMEZONE ERROR)
            one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_users = [m for g in self.bot.guilds for m in g.members if m.created_at >= one_month_ago]

            embed = discord.Embed(
                color=self.color,
                description=(
                    f"> <:speed_autorespond:1278194799656304652> **Hey {message.author.mention},**\n\n"
                    f"> <:speed_server:1277892874620371009> My Prefix for this Server: `{prefix}`\n"
                    f"> <:speed_author:1277892998436229153> Use `{prefix}help` for Commands!\n\n"
                    f"> <:speed_ping:1277822753721810986> **Latency:** `{latency}ms`\n"
                    f"> <:speed_duration:1277892806760726570> **Uptime:** `{self.get_bot_uptime()}`\n"
                    f"> <:speed_welcome:1277893518282592318> **Servers:** `{total_guilds}`\n\n"
                    f"> <:speed_fun:1277893459562467389> **Total Users:** `{total_users}`\n"
                    f"> <:speed_online:1277892933491757140> **Online Users:** `{online_users}`\n"
                    f"> <:speed_offline:1277892857801211957> **Offline Users:** `{offline_users}`\n"
                    f"> <:speed_users:1277893558476472320> **Humans:** `{total_humans}`\n"
                    f"> <:speed_bot:1277823196271214624> **Bots:** `{total_bots}`\n\n"
                    f"> <:speed_team:1277892711327731817> **Tokens:** `{len(recent_users)}`"
                )
            )

            embed.set_author(name=self.bot_name, icon_url=self.bot.user.display_avatar.url)
            embed.set_footer(text="Developed by Arbitex Development", icon_url=self.bot.user.display_avatar.url)

            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Mention(bot))
