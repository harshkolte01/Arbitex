import discord
from discord.ext import commands
import aiosqlite
from utils import Paginator, DescriptionEmbedPaginator

class Block(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.set_db())

    async def set_db(self):
        async with aiosqlite.connect('db/block.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_blacklist (
                    user_id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_blacklist (
                    guild_id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()

        async with aiosqlite.connect('db/blwhitelist.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_whitelist (
                    user_id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS guild_whitelist (
                    guild_id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()

    @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True)
    @commands.is_owner()
    async def blacklist(self, ctx):
        emb = discord.Embed(
            title="__Blacklist System__",
            color=0x000000
        )
        emb.add_field(
            name="Setup Commands",
            value=(
                "`→ blacklist user [add|remove|show]`\n"
                "`→ blacklist guild [add|remove|show]`\n"
                "`→ blacklist safe1 user [add|remove|show]`\n"
                "`→ blacklist safe2 guild [add|remove|show]`"
            ),
            inline=False
        )
        emb.set_footer(text="Use the above commands to manage blacklist and whitelist.")
        await ctx.send(embed=emb)

    # ======== Blacklist Commands ======== #
    @blacklist.group(name="user", invoke_without_command=True)
    @commands.is_owner()
    async def user(self, ctx):
        await ctx.send_help(ctx.command)

    @user.command(name="add")
    @commands.is_owner()
    async def add_user(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_blacklist WHERE user_id = ?', (user.id,))
            if await cursor.fetchone():
                embed = discord.Embed(
                    title="User Already Blacklisted",
                    description=f"{user.mention} is already blacklisted.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                await db.execute('INSERT INTO user_blacklist (user_id) VALUES (?)', (user.id,))
                await db.commit()
                embed = discord.Embed(
                    title="User Blacklisted",
                    description=f"{user.mention} has been added to the blacklist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

    @user.command(name="remove")
    @commands.is_owner()
    async def remove_user(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_blacklist WHERE user_id = ?', (user.id,))
            if not await cursor.fetchone():
                embed = discord.Embed(
                    title="User Not Blacklisted",
                    description=f"{user.mention} is not in the blacklist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                await db.execute('DELETE FROM user_blacklist WHERE user_id = ?', (user.id,))
                await db.commit()
                embed = discord.Embed(
                    title="User Unblacklisted",
                    description=f"{user.mention} has been removed from the blacklist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

    @user.command(name="show")
    @commands.is_owner()
    async def show_users(self, ctx):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_blacklist')
            rows = await cursor.fetchall()

        blacklist = [f"<@{row[0]}> ({row[0]})" for row in rows] if rows else ["No blacklisted users."]
        embed = discord.Embed(
            title="Blacklisted Users",
            description="\n".join(blacklist),
            color=0x000000
        )
        await ctx.reply(embed=embed)
        
    # ========== Blacklist Commands ========== #
    @blacklist.group(name="guild", invoke_without_command=True)
    @commands.is_owner()
    async def guild(self, ctx):
        await ctx.send_help(ctx.command)

    @guild.command(name="add")
    @commands.is_owner()
    async def add_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
            if await cursor.fetchone():
                embed = discord.Embed(
                    title="Guild Already Blacklisted",
                    description=f"Guild `{guild_id}` is already blacklisted.",
                    color=0x000000
                )
            else:
                await db.execute('INSERT INTO guild_blacklist (guild_id) VALUES (?)', (guild_id,))
                await db.commit()
                embed = discord.Embed(
                    title="Guild Blacklisted",
                    description=f"Guild `{guild_id}` has been added to the blacklist.",
                    color=0x000000
                )
            await ctx.reply(embed=embed)

    @guild.command(name="remove")
    @commands.is_owner()
    async def remove_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
            if not await cursor.fetchone():
                embed = discord.Embed(
                    title="Guild Not Blacklisted",
                    description=f"Guild `{guild_id}` is not in the blacklist.",
                    color=0x000000
                )
            else:
                await db.execute('DELETE FROM guild_blacklist WHERE guild_id = ?', (guild_id,))
                await db.commit()
                embed = discord.Embed(
                    title="Guild Unblacklisted",
                    description=f"Guild `{guild_id}` has been removed from the blacklist.",
                    color=0x000000
                )
            await ctx.reply(embed=embed)

    @guild.command(name="show")
    @commands.is_owner()
    async def show_guilds(self, ctx):
        async with aiosqlite.connect('db/block.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_blacklist')
            rows = await cursor.fetchall()

        blacklist = [f"`{row[0]}`" for row in rows] if rows else ["No blacklisted guilds."]
        embed = discord.Embed(
            title="Blacklisted Guilds",
            description="\n".join(blacklist),
            color=0x000000
        )
        await ctx.reply(embed=embed)

    # ======== Whitelist Commands ======== #
    @blacklist.group(name="safe1", invoke_without_command=True)
    @commands.is_owner()
    async def safe1(self, ctx):
        await ctx.send_help(ctx.command)

    @safe1.group(name="user", invoke_without_command=True)
    @commands.is_owner()
    async def safe1_user(self, ctx):
        await ctx.send_help(ctx.command)

    @safe1_user.command(name="add")
    @commands.is_owner()
    async def add_safe1_user(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_whitelist WHERE user_id = ?', (user.id,))
            if await cursor.fetchone():
                embed = discord.Embed(
                    title="User Already Whitelisted",
                    description=f"{user.mention} is already whitelisted.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                await db.execute('INSERT INTO user_whitelist (user_id) VALUES (?)', (user.id,))
                await db.commit()
                embed = discord.Embed(
                    title="User Whitelisted",
                    description=f"{user.mention} has been added to the whitelist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

    @safe1_user.command(name="remove")
    @commands.is_owner()
    async def remove_safe1_user(self, ctx, user: discord.User):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_whitelist WHERE user_id = ?', (user.id,))
            if not await cursor.fetchone():
                embed = discord.Embed(
                    title="User Not Whitelisted",
                    description=f"{user.mention} is not in the whitelist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
            else:
                await db.execute('DELETE FROM user_whitelist WHERE user_id = ?', (user.id,))
                await db.commit()
                embed = discord.Embed(
                    title="User Unwhitelisted",
                    description=f"{user.mention} has been removed from the whitelist.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)

    @safe1_user.command(name="show")
    @commands.is_owner()
    async def show_safe1_users(self, ctx):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT user_id FROM user_whitelist')
            rows = await cursor.fetchall()

        whitelist = [f"<@{row[0]}> ({row[0]})" for row in rows] if rows else ["No whitelisted users."]
        embed = discord.Embed(
            title="Whitelisted Users",
            description="\n".join(whitelist),
            color=0x000000
        )
        await ctx.reply(embed=embed)
        
    # ========== Whitelist Commands ========== #
    @blacklist.group(name="safe2", invoke_without_command=True)
    @commands.is_owner()
    async def safe2(self, ctx):
        await ctx.send_help(ctx.command)

    @safe2.group(name="guild", invoke_without_command=True)
    @commands.is_owner()
    async def safe2_guild(self, ctx):
        await ctx.send_help(ctx.command)

    @safe2_guild.command(name="add")
    @commands.is_owner()
    async def add_safe2_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_whitelist WHERE guild_id = ?', (guild_id,))
            if await cursor.fetchone():
                embed = discord.Embed(
                    title="Guild Already Whitelisted",
                    description=f"Guild `{guild_id}` is already whitelisted.",
                    color=0x000000
                )
            else:
                await db.execute('INSERT INTO guild_whitelist (guild_id) VALUES (?)', (guild_id,))
                await db.commit()
                embed = discord.Embed(
                    title="Guild Whitelisted",
                    description=f"Guild `{guild_id}` has been added to the whitelist.",
                    color=0x000000
                )
            await ctx.reply(embed=embed)

    @safe2_guild.command(name="remove")
    @commands.is_owner()
    async def remove_safe2_guild(self, ctx, guild_id: int):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_whitelist WHERE guild_id = ?', (guild_id,))
            if not await cursor.fetchone():
                embed = discord.Embed(
                    title="Guild Not Whitelisted",
                    description=f"Guild `{guild_id}` is not in the whitelist.",
                    color=0x000000
                )
            else:
                await db.execute('DELETE FROM guild_whitelist WHERE guild_id = ?', (guild_id,))
                await db.commit()
                embed = discord.Embed(
                    title="Guild Unwhitelisted",
                    description=f"Guild `{guild_id}` has been removed from the whitelist.",
                    color=0x000000
                )
            await ctx.reply(embed=embed)

    @safe2_guild.command(name="show")
    @commands.is_owner()
    async def show_safe2_guilds(self, ctx):
        async with aiosqlite.connect('db/blwhitelist.db') as db:
            cursor = await db.execute('SELECT guild_id FROM guild_whitelist')
            rows = await cursor.fetchall()

        whitelist = [f"`{row[0]}`" for row in rows] if rows else ["No whitelisted guilds."]
        embed = discord.Embed(
            title="Whitelisted Guilds",
            description="\n".join(whitelist),
            color=0x000000
        )
        await ctx.reply(embed=embed)

