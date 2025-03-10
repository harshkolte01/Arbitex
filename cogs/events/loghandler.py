import logging
import discord
import aiohttp
import datetime
import sys
from discord.ext import commands

class LogHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_url = "https://discord.com/api/webhooks/1345680610122797120/tgo_I5Cpv_khtpv9Tk5GgrDr7vpxqG0v2X6aRzkjHxLHT3uFLnwMblKLmTFZ4rNhTpRc"  # Replace with your webhook URL
        self.session = aiohttp.ClientSession()

        # Set up custom logging to suppress console logs
        self.logger = logging.getLogger("discord")
        self.logger.setLevel(logging.INFO)  # Capture all logs (INFO, WARNING, ERROR, CRITICAL)
        self.logger.handlers = []  # Remove default handlers
        self.logger.addHandler(DiscordWebhookHandler(self.webhook_url, self.session))

        # Redirect stderr to suppress console errors
        sys.stderr = self  # Override sys.stderr to suppress errors

    def write(self, message):
        """Suppress all errors from appearing in the console."""
        pass  # Prevents console errors from showing up

    def flush(self):
        """Required for sys.stderr override (no effect)."""
        pass

    async def cog_unload(self):
        """Cleanup when the cog is unloaded"""
        await self.session.close()
        sys.stderr = sys.__stderr__  # Restore default error output on unload

class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url: str, session: aiohttp.ClientSession):
        super().__init__()
        self.webhook_url = webhook_url
        self.session = session

    def emit(self, record):
        """Send logs to the Discord Webhook and suppress console output"""
        log_message = self.format(record)
        formatted_message = f"```{log_message}```"

        embed = discord.Embed(
            title="Error Log" if record.levelname in ["ERROR", "CRITICAL"] else "ℹ️ Bot Log",
            description=formatted_message[:4000],  # Limit to 4000 characters
            color=discord.Color.red() if record.levelname in ["ERROR", "CRITICAL"] else discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )

        # Prevent blocking by sending logs asynchronously
        self.session.loop.create_task(self.send_to_webhook(embed))

    async def send_to_webhook(self, embed: discord.Embed):
        """Send log embeds to the Discord webhook (with anti-rate limit handling)"""
        try:
            async with self.session.post(self.webhook_url, json={"embeds": [embed.to_dict()]}) as response:
                if response.status not in [200, 204]:
                    pass  # Prevent console spam from errors
        except:
            pass  # Silently handle failures to avoid recursion issues

# Completely suppress logs from appearing in the console
logging.getLogger().handlers = []

async def setup(bot):
    await bot.add_cog(LogHandler(bot))
