import discord
import asyncio
from discord.ext import tasks
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

    async def handle_alert(self, guild, alert):
        admin_id = await self.config.guild(guild).admin_id()
        admin = guild.get_member(admin_id)
        if not admin:
            self.shutdown_pending = False
            return

        embed = build_admin_embed(alert)
        try:
            await admin.send(embed=embed)
        except:
            pass

        self.shutdown_timer_task = self.bot.loop.create_task(self.start_shutdown_timer(guild, alert))

    async def start_shutdown_timer(self, guild, alert):
        admin_id = await self.config.guild(guild).admin_id()
        admin = guild.get_member(admin_id)

        for i in range(5):
            await asyncio.sleep(60)
            try:
                await admin.send(f"@{admin.display_name}, please respond with !shutdown yes or !shutdown no. Server will shut down in {5-i} minutes.")
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

    @commands.command()
    async def shutdown(self, ctx, decision: str):
        if decision.lower() == "no":
            self.shutdown_pending = False
            if self.shutdown_timer_task:
                self.shutdown_timer_task.cancel()
            await ctx.send("Shutdown has been cancelled.")
        elif decision.lower() == "yes":
            await ctx.send("Shutdown confirmed. Server will be shut down in 5 minutes.")
        else:
            await ctx.send("Please use `!shutdown yes` or `!shutdown no`.")

    @commands.group()
    async def weather(self, ctx):
        "Configure weather alert system."
        pass

    @weather.command()
    async def setlocation(self, ctx, lat: float, lon: float):
        await self.config.guild(ctx.guild).lat.set(lat)
        await self.config.guild(ctx.guild).lon.set(lon)
        await ctx.send(f"Location set to ({lat}, {lon}).")

    @weather.command()
    async def setadmin(self, ctx, user: discord.Member):
        await self.config.guild(ctx.guild).admin_id.set(user.id)
        await ctx.send(f"Admin set to {user.display_name}.")

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
        admin = ctx.guild.get_member(config['admin_id']) if config['admin_id'] else None
        channel = ctx.guild.get_channel(config['announcement_channel']) if config['announcement_channel'] else None
        embed.add_field(name="Admin", value=admin.display_name if admin else "Not set")
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
        fake_alert = {
            "properties": {
                "event": "Tornado Warning",
                "areaDesc": "Fake County",
                "senderName": "NWS Test",
                "description": "This is a simulated tornado warning for testing purposes."
            }
        }
        await self.handle_alert(ctx.guild, fake_alert)

    @weather.command()
    async def testshutdown(self, ctx):
        fake_alert = {
            "properties": {
                "event": "Tornado Warning",
                "areaDesc": "Fake County",
                "senderName": "NWS Test",
                "description": "This is a simulated tornado warning for shutdown testing."
            }
        }
        await self.start_shutdown_timer(ctx.guild, fake_alert)
