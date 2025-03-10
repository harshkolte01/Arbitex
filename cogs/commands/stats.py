import discord
import psutil
import sys
import os
import time
import aiosqlite
import platform
import pkg_resources
import datetime
import asyncio
from discord import Embed, ButtonStyle
from discord.ui import Button, View
from discord.ext import commands
import wavelink

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.total_songs_played = 0
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with aiosqlite.connect("db/stats.db") as db:
            await db.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
            await db.commit()
            async with db.execute("SELECT value FROM stats WHERE key = 'total_songs_played'") as cursor:
                row = await cursor.fetchone()
                self.total_songs_played = row[0] if row else 0

    async def update_total_songs_played(self):
        async with aiosqlite.connect("db/stats.db") as db:
            await db.execute("INSERT OR REPLACE INTO stats (key, value) VALUES ('total_songs_played', ?)",
                             (self.total_songs_played,))
            await db.commit()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        self.total_songs_played += 1
        await self.update_total_songs_played()

    def count_code_stats(self, file_path):
        total_lines = 0
        total_words = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith(('〇')):
                        total_lines += 1
                        total_words += len(stripped_line.split())
        except (UnicodeDecodeError, IOError):
            pass
        return total_lines, total_words

    def gather_file_stats(self, directory):
        total_files = 0
        total_lines = 0
        total_words = 0
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.py') and '.local' not in root:
                    total_files += 1
                    file_lines, file_words = self.count_code_stats(file_path)
                    total_lines += file_lines
                    total_words += file_words
        return total_files, total_lines, total_words

    @commands.hybrid_command(name="stats", aliases=["botinfo", "botstats", "bi", "statistics"], help="Shows the bot's information.")
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def stats(self, ctx):
        # Loading message in embed
        embed = Embed(title="Arbitex Statistics: Loading", color=0x000000)
        embed.add_field(name="<a:speed_loading:1277822539732750356> Please wait...", value="Gathering Arbitex information...", inline=False)
        message = await ctx.send(embed=embed)

        guild_count = len(self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds if g.member_count is not None)
        bot_count = sum(sum(1 for m in g.members if m.bot) for g in self.bot.guilds)
        human_count = user_count - bot_count
        channel_count = len(set(self.bot.get_all_channels()))
        blahh = human_count + bot_count
        text_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.TextChannel)])
        voice_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.VoiceChannel)])
        category_channel_count = len([c for c in self.bot.get_all_channels() if isinstance(c, discord.CategoryChannel)])
        slash_commands = len([cmd for cmd in self.bot.tree.get_commands()])
        commands_count = len(set(self.bot.walk_commands()))
        uptime_seconds = int(round(time.time() - self.start_time))
        uptime_timedelta = datetime.timedelta(seconds=uptime_seconds)
        uptime = f"{uptime_timedelta.days} days, {uptime_timedelta.seconds // 3600} hours, {(uptime_timedelta.seconds // 60) % 60} minutes, {uptime_timedelta.seconds % 60} seconds"

        total_files, total_lines, total_words = self.gather_file_stats('.')

        cpu_info = psutil.cpu_freq()
        memory_info = psutil.virtual_memory()

        total_libraries = sum(1 for _ in pkg_resources.working_set)
        channels_connected = sum(1 for vc in self.bot.voice_clients if vc)
        playing_tracks = sum(1 for vc in self.bot.voice_clients if vc.playing)

        embed = Embed(title="Arbitex Statistics: General", color=0x000000)  # Embed color is now red
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="<:emoji_12:1340884405060636804> Channels", value=f"Total: **{channel_count}**\nText: **{text_channel_count}** | Voice: **{voice_channel_count}** | Category: **{category_channel_count}**", inline=False)
        embed.add_field(name="<:emoji_12:1340884388078026886> Uptime", value=f"{uptime}", inline=False)
        embed.add_field(name="<:emoji_10:1340884364807897260> User Count", value=f"Humans: **{human_count}** | Bots: **{bot_count}**", inline=False)
        embed.add_field(name="<:emoji_16:1340938210120826890> Server Count", value=f"Total Servers: **{guild_count}**", inline=False)
        embed.add_field(name="<:emoji_17:1340938513801150525> Commands", value=f"Total: **{commands_count}** | Slash: **{slash_commands}**", inline=False)
        embed.add_field(name="<:emoji_8:1340884327692763166> Libraries Used", value=f"Discord.py: **[discord.py](https://discordpy.readthedocs.io/en/stable/)**\nTotal Libraries: **{total_libraries}**", inline=False)
        embed.add_field(name="<:emoji_8:1340884310265430069> Codebase Stats", value=f"Total Python Files: **{total_files}**\nTotal Lines: **{total_lines}**\nTotal Words: **{total_words}**", inline=False)
        embed.add_field(name="<:emoji_7:1340884284176728074> Music Stats", value=f"Connected Channels: **{channels_connected}**\nCurrently Playing: **{playing_tracks}**\nTotal Songs Played: **{self.total_songs_played}**", inline=False)
        embed.set_footer(text="Powered by Arbitex Development™", icon_url=self.bot.user.display_avatar.url)

        view = View()

        # Buttons for navigating between different categories
        general_button = Button(label="General", style=ButtonStyle.secondary, custom_id="stats_general")
        system_button = Button(label="System", style=ButtonStyle.secondary, custom_id="stats_system")
        team_button = Button(label="Team Info", style=ButtonStyle.secondary, custom_id="stats_team")
        ping_button = Button(label="Ping", style=ButtonStyle.secondary, custom_id="stats_ping")
        delete_button = Button(emoji="<:speed_bin:1277892670727127062>", style=ButtonStyle.danger, custom_id="stats_delete")  # Delete button with emoji

        async def button_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.user.send("You are not allowed to interact with these buttons. Only the command user can do that.")
                return

            if interaction.type == discord.InteractionType.component:  # Make sure the interaction is a component interaction
                custom_id = interaction.data['custom_id']  # Use data['custom_id'] for MessageComponentInteraction

                if custom_id == "stats_general":
                    await interaction.response.edit_message(embed=embed, view=view)
                elif custom_id == "stats_system":
                    system_embed = Embed(title="Arbitex Statistics: System", color=0x000000)
                    system_embed.add_field(name="<:emoji_5:1340884257194770432> System Info", value=f"• Discord.py: **{discord.__version__}**\n• Python: **{platform.python_version()}**\n• Architecture: **{platform.machine()}**\n• Platform: **{platform.system()}**", inline=False)
                    system_embed.add_field(name="<:emoji_4:1340884236898668574> RAM Info", value=f"• Total Memory: **{psutil.virtual_memory().total / (1024 ** 3):.2f} GB**\n• Memory Left: **{psutil.virtual_memory().available / (1024 ** 3):.2f} GB**", inline=False)
                    system_embed.add_field(name="<:emoji_4:1340884218040815818> CPU Info", value=f"• Physical Cores: **{psutil.cpu_count(logical=False)}**\n• Logical Cores (vCPU): **{psutil.cpu_count(logical=True)}**\n• CPU Usage: **{psutil.cpu_percent()}%**", inline=False)
                    system_embed.add_field(name="<:emoji_10:1340884346491506699> Disk Space", value=f"• Total Disk: **{psutil.disk_usage('/').total / (1024 ** 3):.2f} GB**\n• Disk Free: **{psutil.disk_usage('/').free / (1024 ** 3):.2f} GB**\n• Disk Used: **{psutil.disk_usage('/').used / (1024 ** 3):.2f} GB**\n• Usage: **{psutil.disk_usage('/').percent}%**", inline=False)
                    system_embed.set_footer(text="Powered by Arbitex Development™", icon_url=self.bot.user.display_avatar.url)
                    await interaction.response.edit_message(embed=system_embed, view=view)
                elif custom_id == "stats_team":
                    team_embed = Embed(title="Arbitex Team Info", color=0x000000)
                    team_embed.add_field(name="<:emoji_14:1340918591092035735> Owners", value="**[Marco](https://discord.com/users/936490998362685450)**", inline=False)
                    team_embed.add_field(name="<:emoji_14:1340918613191688282> Developers", value="**[Marco](https://discord.com/users/936490998362685450)**", inline=False)
                    team_embed.add_field(name="<:emoji_16:1340938210120826890> Partners", value="**[Natkhat](https://discord.gg/natkhat)**", inline=False)
                    team_embed.set_footer(text="Powered by Arbitex Development™", icon_url=self.bot.user.display_avatar.url)
                    await interaction.response.edit_message(embed=team_embed, view=view)
                elif custom_id == "stats_ping":
                    embed_ping = Embed(title="Arbitex Statistics: Ping", color=0x000000)
                    bot_latency = round(self.bot.latency * 1000)
                    database_latency = 0.08  # Example placeholder, replace with actual DB latency
                    rtt = 175.15  # Example placeholder, replace with actual RTT calculation
                    embed_ping.add_field(name="<:emoji_3:1340884191822479390> Bot Latency", value=f"**{bot_latency} ms**", inline=False)
                    embed_ping.add_field(name="<:emoji_1:1340884144418455634> Database Latency", value=f"**{database_latency} ms**", inline=False)
                    embed_ping.add_field(name="<:emoji_1:1340884162059698299> Round-Trip Time (RTT)", value=f"**{rtt} ms**", inline=False)
                    embed_ping.set_footer(text="Powered by Arbitex Development™", icon_url=self.bot.user.display_avatar.url)
                    await interaction.response.edit_message(embed=embed_ping, view=view)
                elif custom_id == "stats_delete":
                    await interaction.message.delete()

        general_button.callback = button_callback
        system_button.callback = button_callback
        team_button.callback = button_callback
        ping_button.callback = button_callback
        delete_button.callback = button_callback

        view.add_item(general_button)
        view.add_item(system_button)
        view.add_item(team_button)
        view.add_item(ping_button)
        view.add_item(delete_button)

        await ctx.reply(embed=embed, view=view)
        await message.delete()
