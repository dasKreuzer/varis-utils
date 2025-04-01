import logging
import discord
from discord.ext import tasks
from redbot.core import commands, Config
from .intent_handler import match_intent
from .permission_checker import check_user_permission
from .pterodactyl_api import PterodactylAPI
from .gpt_formatter import format_response_with_gpt
from .config_manager import ConfigManager
from .resource_monitor import check_system_resources, send_warning_to_admins

log = logging.getLogger("red.naturalassistant")

class NaturalAssistant(commands.Cog):
    """Red-powered assistant with Pterodactyl integration and resource monitoring."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210)
        self.config_manager = ConfigManager(self.config)
        self.ptero_api = PterodactylAPI(self.config_manager)
        self.resource_monitor_interval = 5  # Default interval in minutes

        # Initialize configuration groups with correct syntax
        self.config.register_custom("thresholds", default={"cpu": 80, "memory": 80, "disk": 80})
        self.config.register_custom("api_keys", default={"ptero": None, "gpt": None})
        self.config.register_custom("intents", default={})
        self.config.register_guild(admin_ids=[], listening_channel=None)

        self.resource_monitor_loop.change_interval(minutes=self.resource_monitor_interval)
        self.resource_monitor_loop.start()
        log.info("NaturalAssistant cog initialized.")

    def cog_unload(self):
        self.resource_monitor_loop.cancel()
        log.info("NaturalAssistant cog unloaded.")

    @tasks.loop(minutes=5)
    async def resource_monitor_loop(self):
        try:
            warnings = await check_system_resources(self.config_manager)
            if warnings:
                await send_warning_to_admins(self.bot, warnings)
        except Exception as e:
            log.error(f"Error in resource monitoring loop: {e}")

    @commands.group(name="red", invoke_without_command=True)
    async def red(self, ctx):
        """Configure the Red assistant."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @red.command(name="setchannel")
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel the Red assistant listens to."""
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send("I don't have permission to send messages in that channel.")
            return
        await self.config.guild(ctx.guild).listening_channel.set(channel.id)
        await ctx.send(f"Listening channel set to {channel.mention}.")
        log.info(f"Listening channel set to {channel.name} by {ctx.author}.")

    @red.command(name="addintent")
    async def addintent(self, ctx, phrase: str, action: str, server_id: str, *roles: discord.Role):
        """Add a new intent mapping."""
        await self.config_manager.add_intent(phrase, action, server_id, [role.id for role in roles])
        await ctx.send(f"Intent '{phrase}' added.")
        log.info(f"Intent '{phrase}' added by {ctx.author}.")

    @red.command(name="removeintent")
    async def removeintent(self, ctx, phrase: str):
        """Remove an intent mapping."""
        await self.config_manager.remove_intent(phrase)
        await ctx.send(f"Intent '{phrase}' removed.")
        log.info(f"Intent '{phrase}' removed by {ctx.author}.")

    @red.command(name="listintents")
    async def listintents(self, ctx):
        """List all mapped intents."""
        intents = await self.config_manager.list_intents()
        if not intents:
            await ctx.send("No intents configured.")
            return
        embed = discord.Embed(title="Configured Intents", color=discord.Color.blue())
        for phrase, intent in intents.items():
            embed.add_field(name=phrase, value=f"Action: {intent['action']}, Server: {intent['server_id']}", inline=False)
        await ctx.send(embed=embed)

    @red.command(name="setapikey")
    async def setapikey(self, ctx, api_key: str):
        """Set the Pterodactyl API key."""
        await self.config_manager.set_ptero_api_key(api_key)
        await ctx.send("Pterodactyl API key set.")
        log.info(f"Pterodactyl API key set by {ctx.author}.")

    @red.command(name="setgptkey")
    async def setgptkey(self, ctx, api_key: str):
        """Set the OpenAI GPT API key."""
        await self.config_manager.set_gpt_api_key(api_key)
        await ctx.send("OpenAI GPT API key set.")
        log.info(f"OpenAI GPT API key set by {ctx.author}.")

    @commands.command(name="setmonitorinterval")
    async def setmonitorinterval(self, ctx, minutes: int):
        """Set the interval (in minutes) for resource monitoring."""
        if minutes < 1:
            await ctx.send("Interval must be at least 1 minute.")
            return
        self.resource_monitor_interval = minutes
        self.resource_monitor_loop.change_interval(minutes=minutes)
        await ctx.send(f"Resource monitoring interval set to {minutes} minutes.")
        log.info(f"Resource monitoring interval updated to {minutes} minutes by {ctx.author}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        try:
            # Check if the message matches an intent
            intent = await match_intent(message.content, self.config_manager)
            if intent:
                allowed_roles = intent.get("roles", [])
                if not await check_user_permission(message.author, allowed_roles):
                    await message.channel.send("Sorry, you don't have permission to do that.")
                    return

                action = intent["action"]
                server_id = intent["server_id"]
                response = await self.ptero_api.handle_action(action, server_id)
                formatted_response = await format_response_with_gpt(response)
                await message.channel.send(formatted_response)
        except Exception as e:
            log.error(f"Error processing message: {e}")
            await message.channel.send("An error occurred while processing your request.")
