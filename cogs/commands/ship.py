import os
import io
import random
import discord
import datetime
import requests
from discord.ext import commands
from discord.ext.commands import errors
from PIL import Image, ImageFont, ImageDraw
from utils.Tools import *

class Ship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.special_users = {936490998362685450, 1213846273254490134}
        self.template_path = "./data/ship/Template.png"
        self.fill_path = "./data/ship/Tmpl_fill.png"
        self.font_path = "./data/ship/font.ttf"
        self.tmp_image_path = "./data/ship/tmp_ship.png"

    @commands.hybrid_command(pass_context=True, help="Ship two users together.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ship(self, ctx, user1: discord.Member = None, user2: discord.Member = None):
        guild = ctx.guild
        if not user1:
            user1 = ctx.author
            user2 = random.choice([m for m in guild.members if not m.bot and m.id != ctx.author.id])
        elif not user2:
            user2 = user1
            user1 = ctx.author

        rate = 100 if {user1.id, user2.id} <= self.special_users else self.calculate_ship_rate(user1.id, user2.id)
        author_avatar = await self.get_avatar(user1)
        user_avatar = await self.get_avatar(user2)

        if author_avatar and user_avatar:
            self.generate_ship_image(author_avatar, user_avatar, user1.name, user2.name, rate)
            await self.send_ship_image(ctx, user1.mention, user2.mention, rate)
        else:
            await self.send_text_ship(ctx, user1.mention, user2.mention, rate)

    def calculate_ship_rate(self, user1_id, user2_id):
        now = datetime.datetime.now()
        seed = (user1_id + user2_id) / ((now.day + now.month + now.year) / 3)
        random.seed(seed)
        return random.randint(1, 99)

    async def send_ship_image(self, ctx, user1_mention, user2_mention, rate):
        progress_bar = self.create_progress_bar(rate)
        embed = discord.Embed(
            color=discord.Color(0xeb1818),
            title="Love Compatibility",
            description=f"**{user1_mention} & {user2_mention}**\n"
                        f"Love rate: `{progress_bar}` **{rate}%**"
        )
        embed.set_image(url="attachment://tmp_ship.png")  # Attach the image to embed

        try:
            file = discord.File(self.tmp_image_path, filename="tmp_ship.png")
            await ctx.send(embed=embed, file=file)
        except:
            await self.send_text_ship(ctx, user1_mention, user2_mention, rate)

    async def send_text_ship(self, ctx, user1_mention, user2_mention, rate):
        progress_bar = self.create_progress_bar(rate)
        embed = discord.Embed(
            color=discord.Color(0xeb1818),
            title="Love Compatibility",
            description=f"**{user1_mention} & {user2_mention}**\n"
                        f"Love rate: `{progress_bar}` **{rate}%**"
        )
        await ctx.send(embed=embed)

    def generate_ship_image(self, author_avatar, user_avatar, author_name, user_name, rate):
        tmpl = Image.open(self.template_path).convert('RGBA')
        fill = Image.open(self.fill_path).convert('RGBA')
        blank = Image.new('RGBA', tmpl.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(blank)
        font_small = ImageFont.truetype(self.font_path, 34)
        font_large = ImageFont.truetype(self.font_path, 80)

        author_avatar = author_avatar.resize((150, 150), Image.Resampling.LANCZOS)
        user_avatar = user_avatar.resize((150, 150), Image.Resampling.LANCZOS)

        tmpl.paste(author_avatar, (20, 50))
        tmpl.paste(user_avatar, (20, 312))

        fill = fill.crop((0, (100 - rate) * 2, fill.width, fill.height))
        blank.paste(fill, (tmpl.width - fill.width - 1, 154 + (100 - rate) * 2))

        draw.text((20, 10), author_name, font=font_small, fill=(191, 15, 0, 255))
        draw.text((20, 460), user_name, font=font_small, fill=(191, 15, 0, 255))
        draw.text((330, 192), f"{rate}%", font=font_large, fill=(255, 255, 255, 255))

        tmpl = Image.alpha_composite(tmpl, blank)
        tmpl.save(self.tmp_image_path, "PNG")

    def create_progress_bar(self, rate):
        return '█' * (rate // 5) + ' ' * (20 - (rate // 5))

    async def get_avatar(self, user):
        try:
            url = user.display_avatar.replace(format="png").url + "?size=256"
            response = requests.get(url, timeout=5)
            avatar = Image.open(io.BytesIO(response.content)).convert('RGBA')
            return Image.alpha_composite(Image.new('RGBA', avatar.size, (255, 255, 255, 255)), avatar)
        except:
            return None

def setup(bot):
    bot.add_cog(Ship(bot))
