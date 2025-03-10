import discord
import aiohttp
from discord.ext import commands

# Webhook URL (Replace this with your actual webhook URL)
WEBHOOK_URL = "https://discord.com/api/webhooks/1344174920820850798/n8c4JERJt-UJkFWPnUMlIexmB4wMtcAQ6ExgYJjcN2CpxVWkSowVAtQofn3llv2FPxlS"

class GuildMemberAdd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            # Skip for bots
            if member.bot:
                return

            # Create welcome embed
            embed = discord.Embed(
                title=f"Welcome {member.global_name or member.name}!",
                description=(
                    f"- Thanks for joining **{member.guild.name}**! I'm **Arbitex**, a multipurpose bot. "
                    f"You can add me to your server [click here](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands)."
                ),
                color=0x2A2B30
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(
                text=f"You are the {member.guild.member_count}th member in this server!",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )

            # Create buttons
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Support", url="https://discord.gg/yV7HbDYKS5"))
            view.add_item(discord.ui.Button(label="Invite", url=f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"))

            # Send DM (Ignore failures)
            try:
                await member.send(embed=embed, view=view, content="[Arbitex](https://discord.gg/yV7HbDYKS5)")
            except discord.Forbidden:
                pass  # Ignore DM errors if the user has DMs closed

            # Send log to webhook
            log_embed = discord.Embed(
                title="New Member Joined",
                description=f"**User:** {member.mention} (`{member.id}`)\n**Account Created:** <t:{int(member.created_at.timestamp())}:R>\n**Joined Server:** <t:{int(member.joined_at.timestamp())}:R>",
                color=0x2A2B30,
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_thumbnail(url=member.display_avatar.url)
            log_embed.set_footer(text=f"Member Count: {member.guild.member_count}", icon_url=member.guild.icon.url if member.guild.icon else None)

            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(embed=log_embed, username="Arbitex Logs", avatar_url=self.bot.user.display_avatar.url)

        except Exception as e:
            print(f"Error in on_member_join for {member}: {e}")

async def setup(bot):
    await bot.add_cog(GuildMemberAdd(bot))