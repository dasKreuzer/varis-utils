import discord
from redbot.core import commands
import datetime

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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

    def get_latest(self):
        # Ensure the data is in a format suitable for JavaScript
        return {
            "username": self.latest_announcement["username"],
            "avatar": self.latest_announcement["avatar"],
            "message": self.latest_announcement["message"],
            "timestamp": datetime.datetime.now().isoformat()
        }
