import discord
from discord.ext import commands
import aiosqlite
import os
import time
import traceback
import aiohttp
from typing import Optional
from utils.Tools import *

black1 = 0
black2 = 0
black3 = 0

DB_PATH = "db/afk.db"
ERROR_WEBHOOK_URL = "https://discord.com/api/webhooks/1345676006937329695/80lhIc2ymfgtYHiv23jGaxVur7HePTQx2WcNMrXXmYtOzaq31jzF_pFo1g0BW49q3BwX"  # Replace with your actual error log webhook URL

async def log_error_to_webhook(error: str):
    """Logs errors to a webhook instead of the console."""
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(ERROR_WEBHOOK_URL, session=session)
        embed = discord.Embed(title="AFK System Error", description=f"```py\n{error}\n```", color=0xff0000)
        await webhook.send(embed=embed)

class BasicView(discord.ui.View):
    def __init__(self, ctx: commands.Context, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Only **{self.ctx.author}** can use this command. Use {self.ctx.prefix}**{self.ctx.command}** to run the command",
                    color=self.ctx.author.color
                ),
                ephemeral=True
            )
            return False
        return True

class OnOrOff(BasicView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx, timeout=None)
        self.value = None

    @discord.ui.button(label="DM me", emoji="<:speed_tick:1277893404805697558>", custom_id='Yes', style=discord.ButtonStyle.gray)
    async def dare(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = 'Yes'
        self.stop()

    @discord.ui.button(label="Don't DM", emoji="<:speed_cross:1277893420735791130>", custom_id='No', style=discord.ButtonStyle.gray)
    async def truth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = 'No'
        self.stop()

class afk(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    user_id INTEGER PRIMARY KEY,
                    AFK TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    mentions INTEGER NOT NULL,
                    dm TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk_guild (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.commit()

    async def cog_after_invoke(self, ctx):
        ctx.command.reset_cooldown(ctx)

    async def update_data(self, user, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO afk (user_id, AFK, reason, time, mentions, dm) VALUES (?, 'False', 'None', 0, 0, 'False')", 
                (user.id,)
            )
            if guild_id:
                await db.execute("INSERT OR IGNORE INTO afk_guild (user_id, guild_id) VALUES (?, ?)", (user.id, guild_id))
            await db.commit()

    async def time_formatter(self, seconds: float):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds".strip(", ")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT AFK, time, mentions, reason FROM afk WHERE user_id = ?", (message.author.id,))
                afk_data = await cursor.fetchone()
                await cursor.close()

                if afk_data and afk_data[0] == 'True' and message.guild:
                    cursor = await db.execute("SELECT guild_id FROM afk_guild WHERE user_id = ?", (message.author.id,))
                    guild_ids = [row[0] for row in await cursor.fetchall()]
                    await cursor.close()

                    if message.guild.id in guild_ids:
                        been_afk_for = await self.time_formatter(time.time() - int(afk_data[1]))
                        mention_count = afk_data[2]

                        await db.execute("UPDATE afk SET AFK = 'False', reason = 'None' WHERE user_id = ?", (message.author.id,))
                        await db.execute("DELETE FROM afk_guild WHERE user_id = ? AND guild_id = ?", (message.author.id, message.guild.id))
                        await db.commit()

                        embed = discord.Embed(
                            title=f'{message.author.display_name} Welcome Back!',
                            description=f'I removed your AFK\nTotal Mentions: **{mention_count}**\nAFK Time: **{been_afk_for}**',
                            color=0x0c0606
                        )
                        try:
                            await message.reply(embed=embed)
                        except discord.Forbidden:
                            pass

            await self.update_data(message.author, message.guild.id if message.guild else None)

        except Exception as e:
            await log_error_to_webhook(traceback.format_exc())

    @commands.hybrid_command(description="Set yourself as AFK with a reason")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def afk(self, ctx, *, reason=None):
        await ctx.defer()

        reason = reason or "I am AFK :)"
        if any(invite in reason.lower() for invite in ['discord.gg', 'gg/']):
            return await ctx.send(embed=discord.Embed(
                description="<:speed_cross:1277893420735791130> | You can't advertise server invites in the AFK reason",
                color=0x0c0606
            ))

        view = OnOrOff(ctx)
        embed = discord.Embed(description="Should I DM you on mentions?", color=0x000000)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        msg = await ctx.reply(embed=embed, view=view)
        await view.wait()

        if not view.value:
            return await msg.edit(content="Timed out, please try again.", view=None)

        dm_status = 'True' if view.value == 'Yes' else 'False'
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO afk VALUES (?, 'True', ?, ?, 0, ?)", (ctx.author.id, reason, int(time.time()), dm_status))
            await db.commit()

        await ctx.reply(embed=discord.Embed(title="Success", description=f'{ctx.author.mention}, You are now AFK: **{reason}**', color=0x000000))
