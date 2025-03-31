import discord
import asyncio
from discord.ext import tasks
from redbot.core import commands
import aiohttp

from .config import get_config_schema
from .utils import fetch_alerts
from .embeds import build_admin_embed, build_announcement_embed

class SevereWeatherShutdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = get_config_schema(self)
        self.shutdown_pending = False
        self.shutdown_timer_task = None
        self.alert_check_loop.start()

    def cog_unload(self):
        self.alert_check_loop.cancel()

    @tasks.loop(hours=1)
    async def alert_check_loop(self):
        for guild in self.bot.guilds:
            enabled = await self.config.guild(guild).enabled()
            if not enabled:
                continue

            lat = await self.config.guild(guild).lat()
            lon = await self.config.guild(guild).lon()
            if not lat or not lon:
                continue

            alerts = await fetch_alerts(lat, lon)
            if not alerts:
                continue

            valid_alerts = await self.config.guild(guild).alerts()
            matches = [a for a in alerts if a['properties']['event'] in valid_alerts]

            if matches and not self.shutdown_pending:
                self.shutdown_pending = True
                await self.handle_alert(guild, matches[0])

    async def get_county_from_latlon(self, lat, lon):
        url = f"https://geo.fcc.gov/api/census/block/find?latitude={lat}&longitude={lon}&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("County", {}).get("name", "Unknown County")
        return "Unknown County"

    async def handle_alert(self, guild, alert):
        admin_ids = await self.config.guild(guild).admin_ids()
        admins = [guild.get_member(uid) for uid in admin_ids if guild.get_member(uid)]
        if not admins:
            self.shutdown_pending = False
            return

        embed = build_admin_embed(alert)
        for admin in admins:
            try:
                await admin.send(embed=embed)
            except:
                continue

        self.shutdown_timer_task = self.bot.loop.create_task(self.start_shutdown_timer(guild, alert))

    async def start_shutdown_timer(self, guild, alert):
        admin_ids = await self.config.guild(guild).admin_ids()
        admins = [guild.get_member(uid) for uid in admin_ids if guild.get_member(uid)]

        embed = build_admin_embed(alert)

        for i in range(5):
            await asyncio.sleep(60)
            for admin in admins:
                try:
                    await admin.send(embed=embed)
                    await admin.send(f"@{admin.display_name}, please respond with !wshutdown yes or !wshutdown no. Server will shut down in {5-i} minutes.")
                except:
                    continue

        channel_id = await self.config.guild(guild).announcement_channel()
        channel = guild.get_channel(channel_id)

        if channel:
            embed = build_announcement_embed(alert)
            await channel.send(embed=embed)

        await asyncio.sleep(300)
        print("[!] Server shutdown triggered.")
        self.shutdown_pending = False

    @commands.command(name="wshutdown")
    async def storm_shutdown(self, ctx, decision: str):
        if decision.lower() == "no":
            self.shutdown_pending = False
            if self.shutdown_timer_task:
                self.shutdown_timer_task.cancel()
            await ctx.send("Shutdown has been cancelled.")
        elif decision.lower() == "yes":
            await ctx.send("Shutdown confirmed. Server will be shut down in 5 minutes.")
        else:
            await ctx.send("Please use `!wshutdown yes` or `!wshutdown no`.")

    # ... (other unchanged commands omitted for brevity) ...

    @weather.command()
    async def testalert(self, ctx):
        lat = await self.config.guild(ctx.guild).lat()
        lon = await self.config.guild(ctx.guild).lon()
        county = await self.get_county_from_latlon(lat, lon)

        fake_alert = {
            "properties": {
                "event": "Tornado Warning",
                "areaDesc": county,
                "senderName": "NWS Test",
                "description": "This is a simulated tornado warning for testing purposes."
            }
        }
        await self.handle_alert(ctx.guild, fake_alert)

    @weather.command()
    async def testshutdown(self, ctx):
        lat = await self.config.guild(ctx.guild).lat()
        lon = await self.config.guild(ctx.guild).lon()
        county = await self.get_county_from_latlon(lat, lon)

        fake_alert = {
            "properties": {
                "event": "Tornado Warning",
                "areaDesc": county,
                "senderName": "NWS Test",
                "description": "This is a simulated tornado warning for shutdown testing."
            }
        }
        self.shutdown_pending = False
        await self.handle_alert(ctx.guild, fake_alert)
