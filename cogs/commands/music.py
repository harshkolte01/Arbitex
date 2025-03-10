import random
import discord
from discord.ext import commands, tasks
import datetime
from discord.ui import Button, View
import wavelink
from wavelink.enums import TrackSource
from utils import Paginator, DescriptionEmbedPaginator
from core import Cog, Olympus, Context
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import aiohttp
from typing import cast
import asyncio
from utils.Tools import *
track_histories = {}
import base64
import asyncio
import re

SPOTIFY_TRACK_REGEX = r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"
SPOTIFY_PLAYLIST_REGEX = r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
SPOTIFY_ALBUM_REGEX = r"https?://open\.spotify\.com/album/([a-zA-Z0-9]+)"
WEBHOOK_URL = "https://discord.com/api/webhooks/1345215782753407056/JYqLTGdI-CMaClCXXZXspWyoXCZrL-czqy4zx66N46AzISFa26vcJZ3-bR1AsuWLjMXi"  # Replace with your actual webhook URL

class SpotifyAPI:
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None

    async def get_token(self):
        auth_url = "https://accounts.spotify.com/api/token"
        auth_value = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode('utf-8')
        headers = {"Authorization": f"Basic {auth_value}"}
        data = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as response:
                text = await response.text()
                if response.status != 200:
                    raise Exception(f"Failed to fetch token: {response.status}, response: {text}")
                self.token = (await response.json()).get("access_token")

    async def get(self, endpoint, params=None):
        retries = 2
        for attempt in range(retries):
            if not self.token or attempt > 0:
                await self.get_token()

            url = f"{self.BASE_URL}/{endpoint}"
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 401 and attempt < retries - 1:
                        continue
                    elif response.status != 200:
                        raise Exception(f"Failed to fetch data from Spotify: {response.status}")
                    return await response.json()
        raise Exception("Exceeded max retries to fetch Spotify data")

    
    async def get_track(self, track_id):
        return await self.get(f"tracks/{track_id}")

    async def get_playlist(self, playlist_id):
        return await self.get(f"playlists/{playlist_id}")

spotify_api = SpotifyAPI(client_id="369cc13e91db4fb8a952d47aa6484c29", client_secret="f81c4654c87941fab1bbd077f7122c78")

class PlatformSelectView(View):
    def __init__(self, ctx, query):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.query = query

        platforms = [
            ("YouTube", "ytsearch", discord.ButtonStyle.red),
            ("JioSaavn", "jssearch", discord.ButtonStyle.green),
            ("SoundCloud", "scsearch", discord.ButtonStyle.grey),
        ]

        for name, source, style in platforms:
            button = Button(label=name, style=style)
            button.callback = self.create_callback(source)
            self.add_item(button)

    def create_callback(self, source):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("Only the command author can select a platform.", ephemeral=True)
                return

            await interaction.response.send_message(f"Searching on {interaction.data['custom_id']}...", ephemeral=True)
            await self.perform_search(source)
            await interaction.message.delete()
        return callback

    async def perform_search(self, source):
        results = await wavelink.Playable.search(self.query, source=source)
        if not results:
            return await self.ctx.send(embed=discord.Embed(description="No results found.", color=0xFF0000))

        top_results = results[:5]
        embed = discord.Embed(
            title=f"Top 5 Results for '{self.query}' ({source})",
            color=0x1DB954
        )
        for i, track in enumerate(top_results, start=1):
            embed.add_field(name=f"{i}. {track.title}", value=f"Duration: {track.length // 1000 // 60}:{track.length // 1000 % 60} | [Link]({track.uri})", inline=False)

        await self.ctx.send(embed=embed, view=SearchResultView(self.ctx, top_results))

    

class SearchResultView(View):
    def __init__(self, ctx, results):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.results = results

        for i in range(5):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.primary)
            button.callback = self.create_callback(i)
            self.add_item(button)

    def create_callback(self, index):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("Only the command author can select a track.", ephemeral=True)
                return

            track = self.results[index]
            vc = self.ctx.voice_client or await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
            vc.ctx = self.ctx


            if not vc.playing:
                await vc.play(track)
                await interaction.response.send_message(f"Started playing `{track.title}`.")
                await self.ctx.cog.display_player_embed(vc, track, self.ctx)

            else:
                await vc.queue.put_wait(track)
                await interaction.response.send_message(f"Added `{track.title}` to the queue.")

        return callback



class MusicControlView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.ctx.voice_client or not self.player.playing:
            await interaction.response.send_message("I'm not currently playing this anymore.", ephemeral=True)
            return False
        if interaction.user in self.ctx.voice_client.channel.members:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(description="Only members in the same voice channel as me can control the player.", color=0x000000),
            ephemeral=True
        )
        return False

    @discord.ui.button(label="AUTOPLAY", style=discord.ButtonStyle.secondary)
    async def autoplay_button(self, interaction: discord.Interaction, button: Button):
        self.player.autoplay = (
            wavelink.AutoPlayMode.enabled if self.player.autoplay != wavelink.AutoPlayMode.enabled else wavelink.AutoPlayMode.disabled
        )
        await interaction.response.send_message(f"Autoplay {'enabled' if self.player.autoplay == wavelink.AutoPlayMode.enabled else 'disabled'} by **{interaction.user.display_name}**.")


    @discord.ui.button(label="PREVIOUS", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        guild_id = interaction.guild.id

        if guild_id in track_histories and len(track_histories[guild_id]) > 1:
            track_histories[guild_id].pop()
            previous_track = track_histories[guild_id][-1] 

            player = self.player 
            vc = self.ctx.voice_client

            if player.playing:
                await player.stop()

            await vc.queue.put_wait(previous_track)

            await interaction.response.send_message(f"Playing previous track: `{previous_track.title}`.")
        else:
            await interaction.response.send_message("No previous track available.", ephemeral=True)

    @discord.ui.button(label="PAUSE", style=discord.ButtonStyle.success)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        if self.player.paused:
            await self.player.pause(False)

            await self.player.channel.edit(status=f"Playing: {self.player.current.title}")
            button.label = "PAUSE" 
            await interaction.response.edit_message(view=self)

        elif self.player.playing:
            await self.player.pause(True)
            await self.player.channel.edit(status=f"Paused: {self.player.current.title}")
            button.label = "RESUME"
            await interaction.response.edit_message(view=self)


    @discord.ui.button(label="SKIP", style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        if self.player.autoplay == wavelink.AutoPlayMode.enabled:
            await self.player.stop()
            return await interaction.response.send_message(f"Skipped song by **{interaction.user.display_name}**.")
            #await self.player.play(await self.player.queue.get_next_track())

        if self.player and self.player.playing and not self.player.queue.is_empty:
            await self.player.stop()
            await interaction.response.send_message(f"Skipped song by **{interaction.user.display_name}**.")
        else:
            await interaction.response.send_message("No song in queue to skip.", ephemeral=True)


    @discord.ui.button(label="LOOP", style=discord.ButtonStyle.secondary)
    async def loop_button(self, interaction: discord.Interaction, button: Button):
        self.player.queue.mode = wavelink.QueueMode.loop if self.player.queue.mode != wavelink.QueueMode.loop else wavelink.QueueMode.normal
        await interaction.response.send_message(f"Loop {'enabled' if self.player.queue.mode == wavelink.QueueMode.loop else 'disabled'} by **{interaction.user.display_name}**.")


    @discord.ui.button(label="SHUFFLE", style=discord.ButtonStyle.secondary)
    async def shuffle_button(self, interaction: discord.Interaction, button: Button):
        if self.player.queue:
            random.shuffle(self.player.queue)
            await interaction.response.send_message(f"Queue shuffled by **{interaction.user.display_name}**.")
        else:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)


    @discord.ui.button(label="REWIND", style=discord.ButtonStyle.secondary)
    async def rewind_button(self, interaction: discord.Interaction, button: Button):
        if self.player.playing:
            new_position = max(self.player.position - 10000, 0)
            await self.player.seek(new_position)
            await interaction.response.send_message("Rewinded 10 seconds.", ephemeral=True)
        else:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)

    @discord.ui.button(label="STOP", style=discord.ButtonStyle.secondary)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        if self.player:
            voice_channel = self.player.channel
            if voice_channel:
                await voice_channel.edit(status=None)

            await self.player.disconnect()
            await interaction.response.send_message(f"Stopped and disconnected by **{interaction.user.display_name}**.")
        else:
            await interaction.response.send_message("Not connected.", ephemeral=True)

    @discord.ui.button(label="FORWARD", style=discord.ButtonStyle.secondary)
    async def forward_button(self, interaction: discord.Interaction, button: Button):
        if self.player.playing:
            new_position = min(self.player.position + 10000, self.player.current.length)
            await self.player.seek(new_position)
            await interaction.response.send_message("Forwarded 10 seconds.", ephemeral=True)
        else:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)

    @discord.ui.button(label="REPLAY", style=discord.ButtonStyle.secondary)
    async def replay_button(self, interaction: discord.Interaction, button: Button):
        if self.player.playing:
            await self.player.seek(0)
            await interaction.response.send_message("Replaying the current track.", ephemeral=True)
        else:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)



class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.inactivity_timeout = 120  # Inactivity timeout (seconds)
        self.client.loop.create_task(self.connect_nodes())
        self.client.loop.create_task(self.monitor_inactivity())

    async def connect_nodes(self) -> None:
        """Connects to Lavalink nodes."""
        try:
            nodes = [wavelink.Node(uri="37.114.37.78:8080", password="H@rsh1to10")]
            await wavelink.Pool.connect(nodes=nodes, client=self.client, cache_capacity=None)
        except Exception:
            pass  # Prevents console spam

    async def monitor_inactivity(self):
        """Monitors inactive voice channels and disconnects if necessary."""
        while True:
            try:
                for guild in self.client.guilds:
                    await self.check_inactivity(guild.id)
                await asyncio.sleep(60)
            except Exception:
                pass  # Prevents crashes

    async def check_inactivity(self, guild_id):
        """Checks if a voice channel is inactive and disconnects the bot if needed."""
        guild = self.client.get_guild(guild_id)
        if not guild:
            return

        player = wavelink.Pool.get_node().get_player(guild.id)  # Lavalink player retrieval
        if player and player.playing and player.channel and len(player.channel.members) == 1:
            await self.inactivity_timer(guild)

    async def inactivity_timer(self, guild):
        """Waits before disconnecting the bot due to inactivity."""
        await asyncio.sleep(self.inactivity_timeout)

        player = wavelink.Pool.get_node().get_player(guild.id)  # Recheck player
        if player and player.channel and len(player.channel.members) == 1:
            await player.disconnect(force=True)
            try:
                embed = discord.Embed(
                    description="Bot has been disconnected due to inactivity (idle for more than 2 minutes).",
                    color=0xFF0000
                )
                embed.set_author(name="Inactive Timeout", icon_url=self.client.user.avatar.url)
                embed.set_footer(text="Thanks for choosing Apolex!")

                support = Button(label='Support', style=discord.ButtonStyle.link, url='https://discord.gg/yV7HbDYKS5')
                vote = Button(label='Vote', style=discord.ButtonStyle.link, url='https://top.gg/bot/1144179659735572640/vote')

                view = View()
                view.add_item(support)
                view.add_item(vote)

                if player.ctx and player.ctx.channel:
                    await player.ctx.channel.send(embed=embed, view=view)
            except:
                pass  # Prevents errors if sending fails

    async def display_player_embed(self, player, track, ctx, autoplay=False):
        if track.artwork:
            template_path = 'data/pictures/player.png'
            font_path = 'utils/arial.ttf'
            font = ImageFont.truetype(font_path, 40) 

            base_img = Image.open(template_path).convert("RGBA")

            async with aiohttp.ClientSession() as session:
                async with session.get(track.artwork) as resp:
                    if resp.status == 200:
                        track_img_data = io.BytesIO(await resp.read())
                        track_img = Image.open(track_img_data).convert("RGBA")
                        track_img = ImageOps.fit(track_img, (220, 220), centering=(0.5, 0.5))

                        mask = Image.new('L', (220, 220), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, 220, 220), fill=255)
                        track_img.putalpha(mask)
                        base_img.paste(track_img, (15, 125 - 85), track_img) 

            draw = ImageDraw.Draw(base_img)
            draw.text((240, 50), track.title, font=font, fill="white")

            image_bytes = io.BytesIO()
            base_img.save(image_bytes, format="PNG")
            image_bytes.seek(0)

            file = discord.File(image_bytes, filename="player.png")
            sec = track.length // 1000
            duration= f"0{sec // 60}:{sec % 60}" if sec < 600 else f"{sec // 60}:{sec % 60}"
            embed = discord.Embed(title=f"**{track.title}**",
            color=0x1DB954 if "spotify" in track.source else 0x00E6A7 if "jiosaavn" in track.source else 0xFF0000 if "youtube" in track.source else 0xFF5500
            )
            #embed.set_author(name="Now Playing", icon_url="https://cdn.discordapp.com/emojis/1275556609958875218.gif")
            embed.add_field(name="Author", value=f"`{track.author}`")
            embed.add_field(name="Duration", value=f"`{duration}`")
            embed.add_field(name="Source", value=f"[Listen on Spotify]({track.uri})" if "spotify" in track.source else f"[Listen on JioSaavn]({track.uri})" if "jiosaavn" in track.source else f"[Listen on SoundCloud]({track.uri})" if "soundcloud" in track.source else f"[Listen on YouTube]({track.uri})")
            embed.set_image(url="attachment://player.png")
            embed.set_footer(text="Requested by " + (ctx.author.display_name if not autoplay else f"{ctx.author.display_name} (Autoplay Mode)"), icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

            await ctx.send(embed=embed, file=file, view=MusicControlView(player, ctx))
        else:
            await ctx.send(embed=discord.Embed(description="Track has no artwork."), ephemeral=True)


    async def on_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player.queue:
            if player.queue.mode == wavelink.QueueMode.loop:
                await player.play(payload.track)
                #await self.display_player_embed(player, payload.track, player.ctx)
            elif player.autoplay == wavelink.AutoPlayMode.enabled:

                await asyncio.sleep(5)

                if player.current:
                    await self.display_player_embed(player, player.current, player.ctx, autoplay=True)
                else:
                    player.ctx.send("No suitable track found for autoplay.")


            else:
                await player.disconnect()
                ended = discord.Embed(description="All tracks have been played, leaving the voice channel." , color=0xFF0000)
                ended.set_author(name="Queue Ended", icon_url=self.client.user.avatar.url)
                support = Button(label='Support',
                             style=discord.ButtonStyle.link,
                    url=f'https://discord.gg/yV7HbDYKS5')
                vote = Button(label='Vote',
                             style=discord.ButtonStyle.link,
                    url=f'https://top.gg/bot/1144179659735572640/vote')
                view = View()
                view.add_item(support)
                view.add_item(vote)
                await player.ctx.send(embed=ended, view=view)
        else:
            next_track = await player.queue.get_wait()
            await player.play(next_track)
            await self.display_player_embed(player, next_track, player.ctx)



    async def play_source(self, ctx, query):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="You need to be in a voice channel to use this command.", color=0x000000))
            return

        vc = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.ctx = ctx
        
        
        if vc.playing:
            if ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.send(embed=discord.Embed(description=f"You must be connected to {ctx.voice_client.channel.mention} to play.", color=0x000000))
                return
        vc.autoplay = wavelink.AutoPlayMode.disabled

        """if re.match(SPOTIFY_TRACK_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "track")
        elif re.match(SPOTIFY_PLAYLIST_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "playlist")
        elif re.match(SPOTIFY_ALBUM_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "album")
        
            return"""
            
        tracks = await wavelink.Playable.search(query)
        if not tracks:
            await ctx.send(embed=discord.Embed(description="No results found.", color=0x000000))
            return

        if isinstance(tracks, wavelink.Playlist):
            await vc.queue.put_wait(tracks.tracks)
            await ctx.send(embed=discord.Embed(description=f"Added playlist [{tracks.name}](https://discord.gg/yV7HbDYKS5) with **{len(tracks.tracks)} songs** to the queue.", color=0x000000))
            if not vc.playing:
                track = await vc.queue.get_wait()
                await vc.play(track)
                await self.display_player_embed(vc, track, ctx)
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)
            await ctx.send(embed=discord.Embed(description=f"Added [{track.title}](https://discord.gg/yV7HbDYKS5) to the queue.", color=0x000000))
            if not vc.playing:
                await vc.play(await vc.queue.get_wait())
                await self.display_player_embed(vc, track, ctx)
            self.client.loop.create_task(self.check_inactivity(ctx.guild.id))
           # await interaction.response.defer()


    
    async def handle_spotify_link(self, ctx, vc, link, type_):
        try:
            if type_ == "track":
                track_id = re.search(SPOTIFY_TRACK_REGEX, link).group(1)
                track_info = await spotify_api.get_track(track_id)

                
                title = track_info['name']
                author = ', '.join(artist['name'] for artist in track_info['artists'])

                
                search_query = f"{title} by {author}"
                search_results = await wavelink.Playable.search(search_query, source=wavelink.enums.TrackSource.YouTube)

                if not search_results:
                    await ctx.send("Can't play this track from Spotify, please try with another track.")
                    return

                track = search_results[0]
                await vc.queue.put_wait(track)
                await ctx.send(embed=discord.Embed(description=f"Added [{track.title}](https://discord.gg/yV7HbDYKS5) to the queue.", color=0x000000))
                if not vc.playing:
                    await vc.play(track)
                    await self.display_player_embed(vc, track, ctx)

                #await self.display_player_embed(vc, track, ctx)
                
            elif type_ == "playlist":
                lmao = await ctx.send("Processing to add tracks from the playlist, this may take a while...")
                
                playlist_id = re.search(SPOTIFY_PLAYLIST_REGEX, link).group(1)
                playlist_info = await spotify_api.get(f"playlists/{playlist_id}")
                tracks = playlist_info.get("tracks", {}).get("items", [])
                playlist_length = len(tracks)

                if not tracks:
                    await ctx.send("No tracks found in the playlist.")
                    return

                c = 0
                for track in tracks:
                    title = track['track']['name']
                    author = ', '.join(artist['name'] for artist in track['track']['artists'])
                    search_query = f"{title} {author}"

                    track_results = await wavelink.Playable.search(search_query, source=wavelink.enums.TrackSource.YouTube)
                    if track_results:
                        await vc.queue.put_wait(track_results[0])
                        c += 1
                        await ctx.message.add_reaction("<:speed_tick:1277893404805697558>")

                await ctx.send(embed=discord.Embed(description=f"Added **{c}** of **{playlist_length}** tracks from **playlist** **[{playlist_info['name']}](https://discord.gg/yV7HbDYKS5)** to the queue.", color=0x000000))
                await lmao.delete()
                
                if not vc.playing:
                    next_track = await vc.queue.get_wait()
                    await vc.play(next_track)
                    await self.display_player_embed(vc, next_track, ctx)


            elif type_ == "album":
                await ctx.message.add_reaction("<a:speed_loading:1277822539732750356>")
                album_id = re.search(SPOTIFY_ALBUM_REGEX, link).group(1)
                album_info = await spotify_api.get(f"albums/{album_id}")
                tracks = album_info.get("tracks", {}).get("items", [])

                if not tracks:
                    await ctx.send("No tracks found in the album.")
                    return

                for track in tracks:
                    title = track['name']
                    author = ', '.join(artist['name'] for artist in track['artists'])
                    search_query = f"{title} {author}"

                    track_results = await wavelink.Playable.search(search_query, source=wavelink.enums.TrackSource.YouTube)
                    if track_results:
                        await vc.queue.put_wait(track_results[0])

                await ctx.send(embed=discord.Embed(description=f"Added all tracks from album **[{album_info['name']}](https://discord.gg/yV7HbDYKS5)** to the queue.", color=0x000000))
                if not vc.playing:
                    next_track = await vc.queue.get_wait()
                    await vc.play(next_track)
                    await self.display_player_embed(vc, next_track, ctx)

                
        except Exception as e:
            await ctx.send(f"An error occurred while processing the Spotify link: {e}")



    def create_progress_bar(self, completed, total, length=10):
        filled_length = int(length * (completed / total))
        bar = '█' * filled_length + '░' * (length - filled_length)
        return bar

    @commands.hybrid_command(name="play", aliases=['p'], usage="play <query>", help="Plays a song or playlist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str):
        
        await self.play_source(ctx, query)


    @commands.hybrid_command(name="search", usage="search <query>", help="Searches music from multiple platforms.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def search2(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(description="You need to be in a voice channel to use this command.", color=0x000000))
            return

        embed = discord.Embed(
            title="Select a platform to search from:",
            description="Click a button below to choose.",
            color=0xff0000
        )
        await ctx.send(embed=embed, view=PlatformSelectView(ctx, query))


    @commands.hybrid_command(name="nowplaying", aliases=["nop"], usage="nowplaying", help="Shows the info about current playing song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def nowplaying(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        track = vc.current
        position = vc.position / 1000  
        length = track.length / 1000  

        progress_bar = self.create_progress_bar(position, length, length=10)
        position_str = f"{int(position // 60)}:{int(position % 60):02}"
        length_str = f"{int(length // 60)}:{int(length % 60):02}"


        queue_length = len(vc.queue) if vc.queue else 0


        if "spotify" in track.uri:
            source_name = "Spotify"
        elif "youtube" in track.uri:
            source_name = "YouTube"
        elif "soundcloud" in track.uri:
            source_name = "SoundCloud"
        elif "jiosaavn" in track.uri:
            source_name = "JioSaavn"
        else:
            source_name = "Unknown Source"


        embed = discord.Embed(
            title="Now Playing",
            color=0x1DB954 if source_name == "Spotify" else 0xFF0000
        )
        embed.add_field(name="Track", value=f"[{track.title}]({track.uri})", inline=False)
        embed.add_field(name="Song By", value=track.author, inline=False)
        embed.add_field(name="Progress", value=f"{position_str} [{progress_bar}] {length_str}", inline=False)
        embed.add_field(name="Duration", value=length_str, inline=False)
        embed.add_field(name="Queue Length", value=str(queue_length), inline=False)
        embed.add_field(name="Source", value=f"{source_name} - [Link]({track.uri})", inline=False)
        embed.set_thumbnail(url=track.artwork if track.artwork else "")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="autoplay", usage="autoplay", help="Toggles autoplay mode.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def autoplay(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc:
            vc.autoplay = (
                wavelink.AutoPlayMode.enabled if vc.autoplay != wavelink.AutoPlayMode.enabled else wavelink.AutoPlayMode.disabled
            )
            await ctx.send(embed=discord.Embed(description=f"Autoplay {'enabled' if vc.autoplay == wavelink.AutoPlayMode.enabled else 'disabled'} by {ctx.author.mention}.", color=0x000000))

    @commands.hybrid_command(name="loop", usage="loop", help="Toggles loop mode.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def loop(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc:
            vc.queue.mode = wavelink.QueueMode.loop if vc.queue.mode != wavelink.QueueMode.loop else wavelink.QueueMode.normal
            await ctx.send(embed=discord.Embed(description=f"Loop {'enabled' if vc.queue.mode == wavelink.QueueMode.loop else 'disabled'} by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="I'm not connected to a voice channel.", color=0xFF0000))


    @commands.hybrid_command(name="pause", usage="pause", help="Pauses the current song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pause(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and vc.playing and not vc.paused:
            await vc.pause(True)
            await vc.channel.edit(status=f"Paused: {vc.current.title}")
            await ctx.send(embed=discord.Embed(description=f"Paused by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="Nothing is playing or already paused.", color=0xFF0000))

    @commands.hybrid_command(name="resume", usage="resume", help="Resumes the paused song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def resume(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and vc.paused:
            await vc.pause(False)
            await vc.channel.edit(status=f"Playing: {vc.current.title}")
            await ctx.send(embed=discord.Embed(description=f"Resumed by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="Player is not paused.", color=0xFF0000))

    @commands.hybrid_command(name="skip", usage="skip", help="Skips the current song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def skip(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc.autoplay == wavelink.AutoPlayMode.enabled:
            await vc.stop()
            return await ctx.send(embed=discord.Embed(description=f"Skipped by {ctx.author.mention}.", color=0x000000))


        if vc and vc.playing and not vc.queue.is_empty:
            await vc.stop()
            await ctx.send(embed=discord.Embed(description=f"Skipped by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="No song is playing or in the queue to skip.", color=0xFF0000))

    @commands.hybrid_command(name="shuffle", usage="shuffle", help="Shuffles the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and vc.queue:
            random.shuffle(vc.queue)
            await ctx.send(embed=discord.Embed(description=f"Queue shuffled by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="Queue is empty.", color=0xFF0000))

    @commands.hybrid_command(name="stop", usage="stop", help="Stops the current song and clears the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and player:
            await vc.channel.edit(status=None)
            vc.queue.clear()
            await vc.disconnect(force=True)
            await ctx.send(embed=discord.Embed(description=f"Stopped and queue cleared by {ctx.author.mention}.", color=0x000000))
        else:
            await ctx.send(embed=discord.Embed(description="Nothing is playing to stop.", color=0xFF0000))

    @commands.hybrid_command(name="volume", aliases=["vol"], usage="volume <level>", help="Sets the volume of the player.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, level: int):
        vc = ctx.voice_client

        if not vc:
            await ctx.send(embed=discord.Embed(description="I'm not connected to a voice channel.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc:
            if 1 <= level <= 100:
                await vc.set_volume(level)
                await ctx.send(embed=discord.Embed(description=f"Volume set to {level}% by {ctx.author.mention}.", color=0x000000))
            else:
                await ctx.send(embed=discord.Embed(description="Volume must be between 1 and 100.", color=0xFF0000))
        else:
            await ctx.send(embed=discord.Embed(description="Bot is not connected to a voice channel.", color=0xFF0000))

    @commands.hybrid_command(name="queue", usage="queue", help="Shows the current queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def queue(self, ctx: commands.Context):
        vc = ctx.voice_client

        if not vc or not vc.queue or vc.queue.is_empty:
            await ctx.send(embed=discord.Embed(description="The queue is currently empty.", color=0x000000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return


        entries = [f"{index + 1}. [{track.title} - {track.author}]({track.uri})" for index, track in enumerate(vc.queue)]
        paginator = Paginator(source=DescriptionEmbedPaginator(
            entries=entries,
            title="Current Queue",
            description="List of upcoming songs.",
            per_page=10,
            color=0x000000),
            ctx=ctx)
        await paginator.paginate()

    @commands.hybrid_command(name="clearqueue", usage="clearqueue", help="Clears the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def clearqueue(self, ctx: commands.Context):
        vc = ctx.voice_client

        if not vc or not vc.queue or vc.queue.is_empty:
            await ctx.send(embed=discord.Embed(description="No Queue to clear.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and vc.queue:
            vc.queue.clear()
            await ctx.send(embed=discord.Embed(description="Queue has been cleared.", color=0x1DB954))
        else:
            await ctx.send(embed=discord.Embed(description="No queue to clear.", color=0xFF0000))

    @commands.hybrid_command(name="replay", usage="replay", help="Replays the current song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def replay(self, ctx: commands.Context):
        vc = ctx.voice_client

        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="I'm not connected to any voice channel.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc and vc.playing:
            await vc.seek(0)
            await ctx.send(embed=discord.Embed(description="Replaying the current track.", color=0x1DB954))
        else:
            await ctx.send(embed=discord.Embed(description="No track is currently playing.", color=0xFF0000))

    @commands.hybrid_command(name="join", aliases=["connect"], usage="join", help="Joins the voice channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        if ctx.author.voice:
            # Connect to the voice channel
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        
            # Self-Deafen the bot
            if ctx.guild.me.voice:
                try:
                    await ctx.guild.me.edit(deafen=True)
                except Exception as e:
                    pass

            await ctx.send(embed=discord.Embed(description="Joined the voice channel.", color=0x1DB954))
        else:
            await ctx.send(embed=discord.Embed(description="You need to join a voice channel first.", color=0xFF0000))


    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave"], usage="disconnect", help="Disconnects the bot from the voice channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disconnect(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc:
            await ctx.send(embed=discord.Embed(description="I'm not connected to any voice channel.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        if vc:
            await vc.disconnect()
            await ctx.send(embed=discord.Embed(description="Disconnected from the voice channel.", color=0x1DB954))
        else:
            await ctx.send(embed=discord.Embed(description="Bot is not connected to any voice channel.", color=0xFF0000))

    @commands.hybrid_command(name="seek", usage="seek <percentage>", help="Seeks to a specific percentage of the song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def seek(self, ctx: commands.Context, percentage: int):
        if not 1 <= percentage <= 100:
            await ctx.send(embed=discord.Embed(description="Please provide a percentage between 1 and 100.", color=0xFF0000))
            return

        vc = ctx.voice_client
        if not vc or not vc.playing:
            await ctx.send(embed=discord.Embed(description="No song is currently playing.", color=0xFF0000))
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            await ctx.send(embed=discord.Embed(description="You need to be in the same voice channel as me to use this command.", color=0xFF0000))
            return

        track = vc.current
        target_position = int(track.length * (percentage / 100))  
        await vc.seek(target_position)

        await ctx.send(embed=discord.Embed(description=f"Seeked to {percentage}% of the current track.", color=0x1DB954))

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not player or not player.current:
            return  # Prevents the error by skipping if player is None or has no track

        track = player.current
        guild = player.guild
        voice_channel = player.channel

        embed = discord.Embed(
            title="Track Started",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="**Guild**", value=f"{guild.name} (`{guild.id}`)", inline=False)
        embed.add_field(name="**Track**", value=f"{track.title}", inline=True)
        embed.add_field(name="**Artist**", value=f"{track.author}", inline=True)
        embed.add_field(name="**Duration**", value=f"{track.length // 1000} sec", inline=True)

        if voice_channel:
            # Ensure the bot has permissions before attempting to deafen
            me = guild.me
            if me and me.voice and me.guild_permissions.deafen_members:
                try:
                    await me.edit(deafen=True)
                except Exception as e:
                    pass

        # Send log to webhook
        await self.send_webhook_log(embed)

    async def send_webhook_log(self, embed: discord.Embed):
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            try:
                await webhook.send(embed=embed, username="Music Logs")
            except Exception as e:
                pass

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player

        # Ensure the player exists and is connected to a voice channel
        if not player or not player.channel:
            return  # Exit early if player or channel is None

        voice_channel = player.channel

        try:
            # Perform a dummy edit only if the channel still exists
            if voice_channel and voice_channel.guild and voice_channel.id in [vc.id for vc in voice_channel.guild.voice_channels]:
                await voice_channel.edit(name=voice_channel.name)  # Dummy edit to prevent potential errors
        except Exception as e:
            # Log the error in a webhook
            await self.send_webhook_log(f"**Error in `on_wavelink_track_end`**:\n```{e}```")

        # Call the track end event handler
        await self.on_track_end(payload)

    async def send_webhook_log(self, message: str):
        """ Sends an error log to the specified webhook """
        async with aiohttp.ClientSession() as session:
            webhook_data = {"content": message}
            try:
                async with session.post(WEBHOOK_URL, json=webhook_data) as response:
                    if response.status != 204:  # Discord webhooks return 204 No Content on success
                        print(f"Failed to send webhook log: {response.status}")
            except Exception as e:
                pass


    
"""
@Author: Sonu Jana
    + Discord: me.sonu
    + Community: https://discord.gg/yV7HbDYKS5 (Arbitex Development)
    + for any queries reach out Community or DM me.
"""