from discord.ext import commands
from core import Olympus, Cog
import discord
import logging
from discord.ui import View, Button, Select

logging.basicConfig(
    level=logging.INFO,
    format="\x1b[38;5;197m[\x1b[0m%(asctime)s\x1b[38;5;197m]\x1b[0m -> \x1b[38;5;197m%(message)s\x1b[0m",
    datefmt="%H:%M:%S",
)

client = Olympus()

class Guild(Cog):
    def __init__(self, client: Olympus):
        self.client = client

    @client.event
    @commands.Cog.listener(name="on_guild_join")
    async def on_guild_add(self, guild):
        try:
            
            rope = [inv for inv in await guild.invites() if inv.max_age == 0 and inv.max_uses == 0]
            ch = 1344001906082713740  
            me = self.client.get_channel(ch)
            if me is None:
                logging.error(f"Channel with ID {ch} not found.")
                return

            channels = len(set(self.client.get_all_channels()))
            embed = discord.Embed(title=f"{guild.name}'s Information", color=0x000000)
            
            embed.set_author(name="Guild Joined")
            embed.set_footer(text=f"Added in {guild.name}")

            embed.add_field(
                name="**__About__**",
                value=f"**Name : ** {guild.name}\n**ID :** {guild.id}\n**Owner <:speed_owner:1277823286356475955> :** {guild.owner} (<@{guild.owner_id}>)\n**Created At : **{guild.created_at.month}/{guild.created_at.day}/{guild.created_at.year}\n**Members :** {len(guild.members)}",
                inline=False
            )
            embed.add_field(
                name="**__Description__**",
                value=f"""{guild.description}""",
                inline=False
            )
            embed.add_field(
                name="**__Members__**",
                value=f"""<:speed_users:1277893558476472320> Members : {len(guild.members)}\n<:speed_sponsor:1277892049814949908> Humans : {len(list(filter(lambda m: not m.bot, guild.members)))}\n<:speed_bot:1277823196271214624> Bots : {len(list(filter(lambda m: m.bot, guild.members)))}
                """,
                inline=False
            )
            embed.add_field(
                name="**__Channels__**",
                value=f"""
Categories : {len(guild.categories)}
Text Channels : {len(guild.text_channels)}
Voice Channels : {len(guild.voice_channels)}
Threads : {len(guild.threads)}
                """,
                inline=False
            )  
            embed.add_field(name="__Bot Stats:__", 
            value=f"Servers: `{len(self.client.guilds)}`\nUsers: `{len(self.client.users)}`\nChannels: `{channels}`", inline=False)  

            if guild.icon is not None:
                embed.set_thumbnail(url=guild.icon.url)

            embed.timestamp = discord.utils.utcnow()
            await me.send(f"{rope[0]}" if rope else "No Pre-Made Invite Found", embed=embed)

            if not guild.chunked:
                await guild.chunk()

            embed = discord.Embed(description="<:speed_ArrowRed:1278191483840761909> Prefix For This Server is `$`\n<:speed_ArrowRed:1278191483840761909> Get Started with `$help`\n<:speed_ArrowRed:1278191483840761909> For detailed guides, FAQ & information, visit our **[Support Server](https://discord.gg/yV7HbDYKS5)**",
    color=0xff0000)
            embed.set_author(name="Thanks for adding me!", icon_url=guild.me.display_avatar.url)
            embed.set_footer(text="Powered by Arbitex Development™", icon_url="https://cdn.discordapp.com/icons/699587669059174461/f689b4366447d5a23eda8d0ec749c1ba.png")
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            support = Button(label='Support',
                             style=discord.ButtonStyle.link,
                    url=f'https://discord.gg/yV7HbDYKS5')
            web = Button(label='Website',
                             style=discord.ButtonStyle.link,
                    url=f'https://discord.gg/yV7HbDYKS5')
            view = View()
            view.add_item(support)
            view.add_item(web)
            channel = discord.utils.get(guild.text_channels, name="general")
            if not channel:
                channels = [channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages]
                if channels:
                    channel = channels[0]
                else:
                    logging.error(f"No channel found with send permissions in guild: {guild.name}")
                    return

            await channel.send(embed=embed, view=view)

        except Exception as e:
            logging.error(f"Error in on_guild_join: {e}")

    @client.event
    @commands.Cog.listener(name="on_guild_remove")
    async def on_guild_remove(self, guild):
        try:
            ch = 1344001798444290122  
            idk = self.client.get_channel(ch)
            if idk is None:
                logging.error(f"Channel with ID {ch} not found.")
                return

            channels = len(set(self.client.get_all_channels()))
            embed = discord.Embed(title=f"{guild.name}'s Information", color=0x000000)
        
            embed.set_author(name="Guild Removed")
            embed.set_footer(text=f"{guild.name}")

            embed.add_field(
                name="**__About__**",
                value=f"**Name : ** {guild.name}\n**ID :** {guild.id}\n**Owner <:speed_owner:1277823286356475955> :** {guild.owner} (<@{guild.owner_id}>)\n**Created At : **{guild.created_at.month}/{guild.created_at.day}/{guild.created_at.year}\n**Members :** {len(guild.members)}",
                inline=False
            )
            embed.add_field(
                name="**__Description__**",
                value=f"""{guild.description}""",
                inline=False
            )
            
                
            embed.add_field(
                name="**__Members__**",
                value=f"""
Members : {len(guild.members)}
Humans : {len(list(filter(lambda m: not m.bot, guild.members)))}
Bots : {len(list(filter(lambda m: m.bot, guild.members)))}
                """,
                inline=False
            )
            embed.add_field(
                name="**__Channels__**",
                value=f"""
Categories : {len(guild.categories)}
Text Channels : {len(guild.text_channels)}
Voice Channels : {len(guild.voice_channels)}
Threads : {len(guild.threads)}
                """,
                inline=False
            )   
            embed.add_field(name="__Bot Stats:__", 
            value=f"Servers: `{len(self.client.guilds)}`\nUsers: `{len(self.client.users)}`\nChannels: `{channels}`", inline=False)

            if guild.icon is not None:
                embed.set_thumbnail(url=guild.icon.url)

            embed.timestamp = discord.utils.utcnow()
            await idk.send(embed=embed)
        except Exception as e:
            logging.error(f"Error in on_guild_remove: {e}")

#client.add_cog(Guild(client))