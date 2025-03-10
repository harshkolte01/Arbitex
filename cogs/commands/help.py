import discord
from discord.ext import commands
from discord import app_commands
from difflib import get_close_matches
from contextlib import suppress
from core import Context
from core.Olympus import Olympus
from core.Cog import Cog
from utils.Tools import getConfig
from itertools import chain
import json
from utils import help as vhelp
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
import asyncio
from utils.config import serverLink
from utils.Tools import *

# Define Colors
color = 0x2B2D42  # Dark futuristic blue
accent_color = 0x8D99AE  # Light futuristic accent color
client = Olympus()

class HelpCommand(commands.HelpCommand):
    
    async def send_bot_help(self, mapping):
        ctx = self.context
        check_ignore = await ignore_check().predicate(ctx)
        check_blacklist = await blacklist_check().predicate(ctx)

        if not check_blacklist:
            return
        if not check_ignore:
            await self.send_ignore_message(ctx, "command")
            return
        
        loading_embed = discord.Embed(
            description="<a:speed_loading:1277822539732750356> **Loading Arbitex Help Module...**",
            color=color
        )
        ok = await ctx.reply(embed=loading_embed)
        
        data = await getConfig(ctx.guild.id)
        prefix = data["prefix"]
        slash_commands_count = len([cmd for cmd in ctx.bot.tree.get_commands() if isinstance(cmd, app_commands.Command)])
        total_commands = len(set(ctx.bot.walk_commands()))

        # **Improved UI Design with Dividers & Icons**
        embed = discord.Embed(
            title="__Arbitex Help Panel__",
            description=(
                "Welcome to the **Arbitex Help System!**\n"
                "Use the selectmenu below to navigate through different help categories."
            ),
            color=color
        )
        
        embed.add_field(
            name="**__General Info:__**",
            value=(
                f"> <:speed_reddot:1278193273575440445> **Server Prefix:** `{prefix}`\n"
                f"> <:speed_reddot:1278193273575440445> **Total Commands:** `{total_commands}`\n"
                f"> <:speed_reddot:1278193273575440445> **Slash Commands:** `{slash_commands_count}`\n"
                f"> <:speed_reddot:1278193273575440445> **[Invite Me](https://discord.com/oauth2/authorize?client_id=1344939913061208074&permissions=8&integration_type=0&scope=bot+applications.commands)** | "
                f"**[Support Server](https://discord.gg/AWttaUGM84)**"
            ),
            inline=False
        )

        embed.add_field(
            name="**__How to Use Me?__**",
            value=(
                f"> <:speed_reddot:1278193273575440445> **Command Help:** `{prefix}help <command>`\n"
                f"> <:speed_reddot:1278193273575440445> **Module Help:** Use the menu below to explore categories"
            ),
            inline=False
        )

        embed.add_field(
            name="**__Features & Modules__**",
            value=(
                "> <:speed_security:1277892984360403026> **Antinuke**\n"
                "> <:speed_automode:1277893548519198751> **Automod**\n"
                "> <:speed_server:1277892874620371009> **Server**\n"
                "> <:speed_utility:1277893544735936593> **Utility**\n"
                "> <:speed_general:1277892911689764924> **General**\n"
                "> <:speed_mod:1277893508459397133> **Moderation**\n"
                "> <:speed_giveaways:1277893483629252630> **Giveaway**\n"
                "> <:speed_fun:1277893459562467389> **Fun**\n"
                "> <:speed_ignore:1277892788624691271> **Ignore**\n"
                "> <:speed_mic:1277893554412195840> **Voice**\n"
                "> <:speed_welcome:1277893518282592318> **Welcomer**"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Requested by {ctx.author}", 
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )

        # **Help View with Interactive Buttons**
        view = vhelp.View(mapping=mapping, ctx=ctx, homeembed=embed, ui=2)
        await asyncio.sleep(0.5)
        await ok.edit(embed=embed, view=view)

    async def send_command_help(self, command):
        ctx = self.context
        check_ignore = await ignore_check().predicate(ctx)
        check_blacklist = await blacklist_check().predicate(ctx)

        if not check_blacklist:
            return
        if not check_ignore:
            await self.send_ignore_message(ctx, "command")
            return

        # **Improved Command-Specific Help UI**
        embed = discord.Embed(
            title=f"💡 __{command.qualified_name.title()} Command__",
            description=f"```xml\n<[] = optional | ‹› = required\n(Don't type these while using commands)>```\n"
                        f">>> {command.help if command.help else 'No additional details provided.'}",
            color=color
        )

        alias = ' | '.join(command.aliases) if command.aliases else "No Aliases"
        embed.add_field(name="📝 **Aliases**", value=alias, inline=False)
        embed.add_field(name="🔧 **Usage**", value=f"`{ctx.prefix}{command.signature}`", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_thumbnail(url=ctx.bot.user.avatar.url)

        await ctx.reply(embed=embed, mention_author=False)

class Help(Cog, name="help"):
    def __init__(self, client: Olympus):
        self._original_help_command = client.help_command
        attributes = {
            'name': "help",
            'aliases': ['h'],
            'cooldown': commands.CooldownMapping.from_cooldown(1, 5, commands.BucketType.user),
            'help': 'Shows help about the bot, a command, or a category'
        }
        client.help_command = HelpCommand(command_attrs=attributes)
        client.help_command.cog = self

    async def cog_unload(self):
        self.help_command = self._original_help_command
