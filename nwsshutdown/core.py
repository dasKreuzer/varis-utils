import discord
import asyncio
import os  # Import the os module for system commands
import logging
from discord.ext import tasks
from redbot.core import commands
import aiohttp

from .config import get_config_schema
from .utils import fetch_alerts, fetch_current_conditions, fetch_mesoscale_discussions
from .embeds import build_admin_embed, build_announcement_embed

log = logging.getLogger("nwsshutdown")

class SevereWeatherShutdown(commands.Cog):
    """Automatically shuts down your server during severe weather alerts."""

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
        log.info(f"Alert detected for guild {guild.name}: {alert['properties']['event']}")
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

    async def execute_system_shutdown(self):
        """
        Execute a system shutdown command to turn off the machine.
        """
        try:
            log.warning("System shutdown initiated.")
            confirmation = input("Confirm shutdown (yes/no): ").strip().lower()
            if confirmation != "yes":
                log.info("Shutdown canceled by user.")
                return

            password = input("Enter the machine password to proceed with shutdown: ").strip()
            if os.name == "nt":  # Windows
                log.error("Password prompt is not supported for Windows shutdown.")
                return
            else:  # Unix-based systems (Linux, macOS)
                os.system(f"echo {password} | sudo -S shutdown now")
        except Exception as e:
            log.error(f"Failed to execute system shutdown: {e}")

    async def notify_admins(self, admins, embed, message):
        for admin in admins:
            try:
                await admin.send(embed=embed)
                await admin.send(message)
            except Exception as e:
                log.error(f"Failed to notify admin {admin.display_name}: {e}")

    async def start_shutdown_timer(self, guild, alert):
        admin_ids = await self.config.guild(guild).admin_ids()
        admins = [guild.get_member(uid) for uid in admin_ids if guild.get_member(uid)]

        embed = build_admin_embed(alert)

        for i in range(5):
            await asyncio.sleep(60)
            message = f"Server will shut down in {5-i} minutes. Respond with !wshutdown yes or !wshutdown no."
            await self.notify_admins(admins, embed, message)

        channel_id = await self.config.guild(guild).announcement_channel()
        channel = guild.get_channel(channel_id)

        if channel:
            embed = build_announcement_embed(alert)
            await channel.send(embed=embed)

        await asyncio.sleep(300)
        print("[!] Server shutdown triggered.")
        self.shutdown_pending = False

        # Trigger the system shutdown
        await self.execute_system_shutdown()

    @commands.command(name="wshutdown")
    async def storm_shutdown(self, ctx, decision: str):
        """
        Confirm or cancel a server shutdown due to severe weather.

        Use `!wshutdown yes` to confirm or `!wshutdown no` to cancel.
        """
        guild = ctx.guild
        if not guild:
            await ctx.send("This command can only be used in a server.")
            return

        admin_ids = await self.config.guild(guild).admin_ids()
        admins = [guild.get_member(uid) for uid in admin_ids if guild.get_member(uid)]

        if decision.lower() == "no":
            self.shutdown_pending = False
            if self.shutdown_timer_task:
                self.shutdown_timer_task.cancel()
            await ctx.send("Shutdown has been cancelled.")

            # Notify all listed admins about the cancellation
            for admin in admins:
                try:
                    await admin.send("The server shutdown has been canceled by an admin.")
                except Exception as e:
                    log.error(f"Failed to notify admin {admin.display_name}: {e}")

        elif decision.lower() == "yes":
            await ctx.send("Shutdown confirmed. Server will be shut down in 5 minutes.")
        else:
            await ctx.send("Please use `!wshutdown yes` or `!wshutdown no`.")

    @commands.group()
    async def weather(self, ctx):
        """Configure the weather alert system."""
        pass

    @weather.command()
    async def setlocation(self, ctx, lat: float, lon: float):
        """
        Set the latitude and longitude for weather alerts.

        Example: `!weather setlocation 40.7128 -74.0060`
        """
        await self.config.guild(ctx.guild).lat.set(lat)
        await self.config.guild(ctx.guild).lon.set(lon)
        await ctx.send(f"Location set to ({lat}, {lon}).")

    @weather.command()
    async def addadmin(self, ctx, user: discord.Member):
        """
        Add a user as a storm admin.

        Storm admins receive alerts and can manage shutdowns.
        """
        admins = await self.config.guild(ctx.guild).admin_ids()
        if user.id not in admins:
            admins.append(user.id)
            await self.config.guild(ctx.guild).admin_ids.set(admins)
            await ctx.send(f"✅ {user.display_name} added as a storm admin.")
        else:
            await ctx.send(f"{user.display_name} is already listed as a storm admin.")

    @weather.command()
    async def removeadmin(self, ctx, user: discord.Member):
        """
        Remove a user from the list of storm admins.
        """
        admins = await self.config.guild(ctx.guild).admin_ids()
        if user.id in admins:
            admins.remove(user.id)
            await self.config.guild(ctx.guild).admin_ids.set(admins)
            await ctx.send(f"❌ {user.display_name} removed from storm admins.")
        else:
            await ctx.send(f"{user.display_name} is not currently an admin.")

    @weather.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """
        Set the channel for shutdown announcements.

        Example: `!weather setchannel #announcements`
        """
        await self.config.guild(ctx.guild).announcement_channel.set(channel.id)
        await ctx.send(f"Announcement channel set to {channel.mention}.")

    @weather.command()
    async def toggle(self, ctx):
        """
        Enable or disable the weather alert system.
        """
        current = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not current)
        await ctx.send(f"Weather alerts {'enabled' if not current else 'disabled'}.")

    @weather.command()
    async def addalert(self, ctx, *, alert: str):
        """
        Add a new alert type to monitor.

        Example: `!weather addalert Flood Warning`
        """
        alerts = await self.config.guild(ctx.guild).alerts()
        if alert not in alerts:
            alerts.append(alert)
            await self.config.guild(ctx.guild).alerts.set(alerts)
            await ctx.send(f"Alert '{alert}' added.")
        else:
            await ctx.send("That alert type is already being tracked.")

    @weather.command()
    async def removealert(self, ctx, *, alert: str):
        """
        Remove an alert type from monitoring.

        Default alerts (Tornado Warning, Severe Thunderstorm Warning) cannot be removed.
        """
        alerts = await self.config.guild(ctx.guild).alerts()
        if alert in alerts and alert not in ["Tornado Warning", "Severe Thunderstorm Warning"]:
            alerts.remove(alert)
            await self.config.guild(ctx.guild).alerts.set(alerts)
            await ctx.send(f"Alert '{alert}' removed.")
        else:
            await ctx.send("You can't remove default alerts or it wasn't in the list.")

    @weather.command()
    async def status(self, ctx):
        """
        Display the current weather alert configuration.
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

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
        """
        Manually check for active weather alerts.
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

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
        """
        Send a test alert to simulate a Tornado Warning.
        """
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
        """
        Simulate a server shutdown due to a Tornado Warning.
        """
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

    @weather.command()
    async def currentweather(self, ctx):
        """
        Display the current weather conditions for the configured location.
        """
        lat = await self.config.guild(ctx.guild).lat()
        lon = await self.config.guild(ctx.guild).lon()
        if not lat or not lon:
            await ctx.send("Location not configured. Use `!weather setlocation` to set it.")
            return

        conditions = await fetch_current_conditions(lat, lon)
        if not conditions:
            await ctx.send("Failed to fetch current weather conditions. Please ensure the location is valid and try again.")
            return

        # Convert temperature from Celsius to Fahrenheit if available
        temp_celsius = conditions.get('temperature', {}).get('value')
        temp_fahrenheit = (temp_celsius * 9/5 + 32) if temp_celsius is not None else "N/A"

        embed = discord.Embed(
            title="Current Weather Conditions",
            color=discord.Color.blue()
        )
        embed.add_field(name="Temperature", value=f"{temp_fahrenheit}°F")
        embed.add_field(name="Wind Speed", value=f"{conditions.get('windSpeed', {}).get('value', 'N/A')} km/h")
        embed.add_field(name="Humidity", value=f"{conditions.get('relativeHumidity', {}).get('value', 'N/A')}%")
        embed.set_footer(text="Data provided by the National Weather Service")
        await ctx.send(embed=embed)

    @weather.command()
    async def mesoscale(self, ctx):
        """
        Display the latest mesoscale discussions from the SPC.
        """
        try:
            discussions = await fetch_mesoscale_discussions()
            if not discussions:
                await ctx.send("No mesoscale discussions available at the moment.")
                return

            embed = discord.Embed(
                title="Latest Mesoscale Discussions",
                color=discord.Color.green()
            )
            for discussion in discussions[:5]:  # Limit to the latest 5 discussions
                embed.add_field(
                    name=discussion["title"],
                    value=f"[Read more]({discussion['link']})",
                    inline=False
                )
            embed.set_footer(text="Data provided by the Storm Prediction Center (SPC)")
            await ctx.send(embed=embed)
        except Exception as e:
            log.error(f"Failed to fetch mesoscale discussions: {e}")
            await ctx.send("Failed to fetch mesoscale discussions. Please try again later.")