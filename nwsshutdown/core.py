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

    @commands.group()
    async def weather(self, ctx):
        """Configure weather alert system."""
        pass

    @weather.command()
    async def setlocation(self, ctx, lat: float, lon: float):
        await self.config.guild(ctx.guild).lat.set(lat)
        await self.config.guild(ctx.guild).lon.set(lon)
        await ctx.send(f"Location set to ({lat}, {lon}).")

    @weather.command()
    async def addadmin(self, ctx, user: discord.Member):
        admins = await self.config.guild(ctx.guild).admin_ids()
        if user.id not in admins:
            admins.append(user.id)
            await self.config.guild(ctx.guild).admin_ids.set(admins)
            await ctx.send(f"✅ {user.display_name} added as a storm admin.")
        else:
            await ctx.send(f"{user.display_name} is already listed as a storm admin.")

    @weather.command()
    async def removeadmin(self, ctx, user: discord.Member):
        admins = await self.config.guild(ctx.guild).admin_ids()
        if user.id in admins:
            admins.remove(user.id)
            await self.config.guild(ctx.guild).admin_ids.set(admins)
            await ctx.send(f"❌ {user.display_name} removed from storm admins.")
        else:
            await ctx.send(f"{user.display_name} is not currently an admin.")

    @weather.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).announcement_channel.set(channel.id)
        await ctx.send(f"Announcement channel set to {channel.mention}.")

    @weather.command()
    async def toggle(self, ctx):
        current = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not current)
        await ctx.send(f"Weather alerts {'enabled' if not current else 'disabled'}.")

    @weather.command()
    async def addalert(self, ctx, *, alert: str):
        alerts = await self.config.guild(ctx.guild).alerts()
        if alert not in alerts:
            alerts.append(alert)
            await self.config.guild(ctx.guild).alerts.set(alerts)
            await ctx.send(f"Alert '{alert}' added.")
        else:
            await ctx.send("That alert type is already being tracked.")

    @weather.command()
    async def removealert(self, ctx, *, alert: str):
        alerts = await self.config.guild(ctx.guild).alerts()
        if alert in alerts and alert not in ["Tornado Warning", "Severe Thunderstorm Warning"]:
            alerts.remove(alert)
            await self.config.guild(ctx.guild).alerts.set(alerts)
            await ctx.send(f"Alert '{alert}' removed.")
        else:
            await ctx.send("You can't remove default alerts or it wasn't in the list.")

    @weather.command()
    async def status(self, ctx):
        config = await self.config.guild(ctx.guild).all()
        embed = discord.Embed(title="Weather Alert Configuration", color=discord.Color.blue())
        embed.add_field(name="Enabled", value=str(config['enabled']))
        embed.add_field(name="Latitude", value=str(config['lat']))
        embed.add_field(name="Longitude", value=str(config['lon']))
        embed.add_field(name="Alerts", value=", ".join(config['alerts']) or "None")

        admin_mentions = []
        for uid in config['admin_ids']:
            member = ctx.guild.get_member(uid)
            if member:
                admin_mentions.append(member.display_name)

        channel = ctx.guild.get_channel(config['announcement_channel']) if config['announcement_channel'] else None
        embed.add_field(name="Admins", value=", ".join(admin_mentions) or "None")
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set")
        await ctx.send(embed=embed)

    @weather.command()
    async def checknow(self, ctx):
        lat = await self.config.guild(ctx.guild).lat()
        lon = await self.config.guild(ctx.guild).lon()
        if not lat or not lon:
            await ctx.send("Location not configured.")
            return

        alerts = await fetch_alerts(lat, lon)
        if not alerts:
            await ctx.send("No active alerts found.")
            return

        valid_alerts = await self.config.guild(ctx.guild).alerts()
        matches = [a for a in alerts if a['properties']['event'] in valid_alerts]
        if matches:
            await ctx.send(f"Matching alert detected: {matches[0]['properties']['event']}")
        else:
            await ctx.send("No relevant alerts at this time.")

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