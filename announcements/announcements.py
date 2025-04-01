import discord
from redbot.core import commands, Config
import datetime

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_guild(announcement_channel=None)
        self.latest_announcement = {
            "username": "Red",
            "avatar": "https://api.hexios.top/static/avatar.png",
            "message": "Server is offline."
        }

    @commands.command()
    async def fivemstatus(self, ctx, *, status: str):
        """Update FiveM status."""
        self.latest_announcement = {
            "username": ctx.author.display_name,
            "avatar": ctx.author.avatar.url if ctx.author.avatar else "",
            "message": f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {status}"
        }
        await ctx.send(f"✅ Status updated: `{status}`")

        # Send the announcement to the configured channel
        channel_id = await self.config.guild(ctx.guild).announcement_channel()
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="📢 Server Announcement",
                    description=self.latest_announcement["message"],
                    color=discord.Color.blue()
                )
                embed.set_author(
                    name=self.latest_announcement["username"],
                    icon_url=self.latest_announcement["avatar"]
                )
                await channel.send(embed=embed)

    @commands.group()
    async def announcements(self, ctx):
        """Manage announcement settings."""
        pass

    @announcements.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Set the announcement channel."""
        await self.config.guild(ctx.guild).announcement_channel.set(channel.id)
        await ctx.send(f"✅ Announcement channel set to {channel.mention}.")

    @announcements.command()
    async def clearchannel(self, ctx):
        """Clear the announcement channel."""
        await self.config.guild(ctx.guild).announcement_channel.set(None)
        await ctx.send("✅ Announcement channel cleared.")

    def get_latest(self):
        # Ensure the data is in a format suitable for JavaScript
        return {
            "username": self.latest_announcement["username"],
            "avatar": self.latest_announcement["avatar"],
            "message": self.latest_announcement["message"],
            "timestamp": datetime.datetime.now().isoformat()
        }
