import discord
from core import Olympus, Cog
from discord.ext import commands
import aiosqlite
import traceback
from datetime import datetime, timedelta
import asyncio

WEBHOOK_URL = "https://discord.com/api/webhooks/1344840785807544340/XvqnmWzNHQ6XKVTtyjOe2owA6r0CNDS7ICduTARP9js1s_d06mkkD3k_0S4T2b06Ys9M"

class AutoBlacklist(Cog):
    def __init__(self, client: Olympus):
        self.client = client
        self.spam_cd_mapping = commands.CooldownMapping.from_cooldown(5, 5, commands.BucketType.member)
        self.spam_command_mapping = commands.CooldownMapping.from_cooldown(6, 10, commands.BucketType.member)
        self.spam_threshold = 5
        self.spam_window = timedelta(minutes=10)
        self.db_path = 'db/block.db'
        self.whitelist_db_path = 'db/blwhitelist.db'
        self.guild_command_tracking = {}

    async def send_webhook_log(self, title, description, color=0x000000):
        """Send logs/errors to the webhook instead of the console."""
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
        try:
            async with self.client.session.post(WEBHOOK_URL, json={"embeds": [embed.to_dict()]}) as response:
                return response.status == 204
        except Exception as e:
            return  # Ignore webhook failures

    async def is_whitelisted(self, user_id=None, guild_id=None):
        """Check if a user or guild is whitelisted."""
        try:
            async with aiosqlite.connect(self.whitelist_db_path) as db:
                if user_id:
                    async with db.execute("SELECT user_id FROM user_whitelist WHERE user_id = ?", (user_id,)) as cursor:
                        if await cursor.fetchone():
                            return True
                if guild_id:
                    async with db.execute("SELECT guild_id FROM guild_whitelist WHERE guild_id = ?", (guild_id,)) as cursor:
                        if await cursor.fetchone():
                            return True
        except Exception as e:
            await self.send_webhook_log("Database Error", f"Error: `{e}`", color=0xFF0000)
        return False

    async def add_to_blacklist(self, user_id=None, guild_id=None, channel=None):
        """Blacklist a user or guild if not whitelisted."""
        if await self.is_whitelisted(user_id=user_id, guild_id=guild_id):
            return  # Skip whitelisted users/guilds

        try:
            async with aiosqlite.connect(self.db_path) as db:
                timestamp = datetime.utcnow()

                if guild_id:
                    await db.execute("CREATE TABLE IF NOT EXISTS guild_blacklist (guild_id INTEGER PRIMARY KEY, timestamp TEXT)")
                    await db.execute("INSERT OR IGNORE INTO guild_blacklist (guild_id, timestamp) VALUES (?, ?)", (guild_id, timestamp))

                    await self.send_webhook_log("Guild Blacklisted", f"**Guild ID:** `{guild_id}`\nReason: Spam detected.", color=0xFF0000)

                elif user_id:
                    await db.execute("CREATE TABLE IF NOT EXISTS user_blacklist (user_id INTEGER PRIMARY KEY, timestamp TEXT)")
                    await db.execute("INSERT OR IGNORE INTO user_blacklist (user_id, timestamp) VALUES (?, ?)", (user_id, timestamp))

                    await self.send_webhook_log("User Blacklisted", f"**User ID:** `{user_id}`\nReason: Spam detected.", color=0xFF0000)

                await db.commit()
        except Exception as e:
            await self.send_webhook_log("Database Error", f"Error: `{e}`", color=0xFF0000)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor spam in messages and blacklist if necessary."""
        if message.author.bot or await self.is_whitelisted(user_id=message.author.id, guild_id=message.guild.id if message.guild else None):
            return

        guild_id = message.guild.id if message.guild else None
        if guild_id:
            self.guild_command_tracking.setdefault(guild_id, []).append(datetime.utcnow())

            self.guild_command_tracking[guild_id] = [
                t for t in self.guild_command_tracking[guild_id] if t >= datetime.utcnow() - timedelta(seconds=2)
            ]

            if len(self.guild_command_tracking[guild_id]) > 8:
                await self.add_to_blacklist(guild_id=guild_id, channel=message.channel)
                return

        bucket = self.spam_cd_mapping.get_bucket(message)
        retry = bucket.update_rate_limit()

        if retry:
            self.client.loop.create_task(self.track_spam(message.author.id))

    async def track_spam(self, user_id):
        """Track spam occurrences and blacklist users if necessary."""
        now = datetime.utcnow()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS spam_tracking (user_id INTEGER, timestamp TEXT)")
            await db.execute("INSERT INTO spam_tracking (user_id, timestamp) VALUES (?, ?)", (user_id, now))
            await db.commit()

            async with db.execute("SELECT COUNT(*) FROM spam_tracking WHERE user_id = ? AND timestamp > ?", (user_id, now - self.spam_window)) as cursor:
                spam_count = (await cursor.fetchone())[0]

            if spam_count >= self.spam_threshold:
                await self.add_to_blacklist(user_id=user_id)

            # Clean up old records
            await db.execute("DELETE FROM spam_tracking WHERE timestamp < ?", (now - self.spam_window,))
            await db.commit()
            
def setup(client):
    client.add_cog(AutoBlacklist(client))
