import logging
import discord
from discord.ext import tasks
from redbot.core import commands, Config
from collections import defaultdict
import time
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
        self.rate_limits = defaultdict(list)  # Tracks user requests: {user_id: [timestamps]}

        # Initialize configuration groups with correct syntax
        self.config.register_custom("thresholds", default={"cpu": 80, "memory": 80, "disk": 80})
        self.config.register_custom("api_keys", default={"ptero": None, "gpt": None})
        self.config.register_custom("intents", default={})  # Ensure intents are initialized
        self.config.register_custom("features", default={"resource_monitoring": False, "intent_handling": False})
        self.config.register_custom("rate_limit", default={"max_requests": 5, "time_window": 60})  # 5 requests per 60 seconds
        self.config.register_custom("fallback_phrases", default={
            "restart server": "The server is being restarted. Please wait a moment.",
            "check status": "The server status is being checked. Please hold on.",
            "hi": "Hello! How can I assist you today?",
            "hello": "Hi there! What can I do for you?",
            "how are you": "I'm just a bot, but I'm here to help! How can I assist you?",
            "default": "I'm sorry, I can't process that request right now."
        })
        self.config.register_guild(admin_ids=[], listening_channel=None)

        self.resource_monitor_loop.change_interval(minutes=self.resource_monitor_interval)
        self.resource_monitor_loop.start()
        log.info("NaturalAssistant cog initialized.")

    def cog_unload(self):
        self.resource_monitor_loop.cancel()
        log.info("NaturalAssistant cog unloaded.")

    async def get_features(self):
        """Safely retrieve the features configuration group."""
        try:
            return await self.config.custom("features").all()
        except ValueError:
            # Initialize the features group if it is not already initialized
            await self.config.custom("features").set({})
            return {"resource_monitoring": False, "intent_handling": False}

    @tasks.loop(minutes=5)
    async def resource_monitor_loop(self):
        try:
            features = await self.get_features()
            if not features.get("resource_monitoring", False):
                return  # Skip if resource monitoring is disabled

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

    @red.command(name="removechannel")
    async def removechannel(self, ctx):
        """Remove the listening channel."""
        await self.config.guild(ctx.guild).listening_channel.clear()
        await ctx.send("Listening channel removed.")
        log.info(f"Listening channel removed by {ctx.author}.")

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

    @red.command(name="enablefeature")
    async def enablefeature(self, ctx, feature: str):
        """Enable a specific feature (resource_monitoring or intent_handling)."""
        valid_features = ["resource_monitoring", "intent_handling"]
        if feature not in valid_features:
            await ctx.send(f"Invalid feature. Valid features are: {', '.join(valid_features)}.")
            return

        await self.config.custom("features").set_raw(feature, value=True)
        await ctx.send(f"Feature '{feature}' has been enabled.")
        log.info(f"Feature '{feature}' enabled by {ctx.author}.")

    @red.command(name="disablefeature")
    async def disablefeature(self, ctx, feature: str):
        """Disable a specific feature (resource_monitoring or intent_handling)."""
        valid_features = ["resource_monitoring", "intent_handling"]
        if feature not in valid_features:
            await ctx.send(f"Invalid feature. Valid features are: {', '.join(valid_features)}.")
            return

        await self.config.custom("features").set_raw(feature, value=False)
        await ctx.send(f"Feature '{feature}' has been disabled.")
        log.info(f"Feature '{feature}' disabled by {ctx.author}.")

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

    @red.command(name="setratelimit")
    async def setratelimit(self, ctx, max_requests: int, time_window: int):
        """Set the rate limit (max requests and time window in seconds)."""
        if max_requests < 1 or time_window < 1:
            await ctx.send("Both max requests and time window must be at least 1.")
            return

        await self.config.custom("rate_limit").set({"max_requests": max_requests, "time_window": time_window})
        await ctx.send(f"Rate limit set to {max_requests} requests per {time_window} seconds.")
        log.info(f"Rate limit updated to {max_requests} requests per {time_window} seconds by {ctx.author}.")

    async def is_rate_limited(self, user_id):
        """Check if a user is rate-limited."""
        rate_limit_config = await self.config.custom("rate_limit").all()
        max_requests = rate_limit_config["max_requests"]
        time_window = rate_limit_config["time_window"]

        now = time.time()
        timestamps = self.rate_limits[user_id]

        # Remove timestamps outside the time window
        self.rate_limits[user_id] = [t for t in timestamps if now - t <= time_window]

        # Check if the user exceeds the rate limit
        if len(self.rate_limits[user_id]) >= max_requests:
            return True

        # Add the current timestamp
        self.rate_limits[user_id].append(now)
        return False

    async def get_fallback_response(self, intent_phrase):
        """Get a fallback response for a given intent."""
        fallback_phrases = await self.config.custom("fallback_phrases").all()
        return fallback_phrases.get(intent_phrase.lower(), fallback_phrases.get("default", "I'm unable to respond right now."))

    async def save_learned_intent(self, phrase, action, server_id, roles):
        """Save a new intent learned from GPT responses."""
        await self.config_manager.add_intent(phrase, action, server_id, roles)
        log.info(f"Learned new intent: '{phrase}' with action '{action}' for server '{server_id}'.")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            features = await self.get_features()
            if not features.get("intent_handling", False):
                return  # Skip if intent handling is disabled

            if message.author.bot or not message.guild:
                return

            # Check if the user is an admin
            is_admin = message.author.guild_permissions.administrator

            # Apply rate limiting for non-admins
            if not is_admin and await self.is_rate_limited(message.author.id):
                await message.channel.send("You are being rate-limited. Please wait before making another request.")
                return

            # Check if the message matches an intent
            intent = await match_intent(message.content, self.config_manager)
            if intent:
                allowed_roles = intent.get("roles", [])
                if not await check_user_permission(message.author, allowed_roles):
                    await message.channel.send("Sorry, you don't have permission to do that.")
                    return

                action = intent["action"]
                server_id = intent["server_id"]
                try:
                    # Attempt to use GPT for the response
                    response = await self.ptero_api.handle_action(action, server_id)
                    formatted_response = await format_response_with_gpt(response)
                except Exception as e:
                    log.error(f"GPT error: {e}")
                    # Fallback to predefined phrases if GPT fails
                    formatted_response = await self.get_fallback_response(action)

                await message.channel.send(formatted_response)
            else:
                # If no intent matches, check for basic phrases
                try:
                    # Attempt to use GPT for unmatched messages
                    gpt_response = await format_response_with_gpt(message.content)
                    await message.channel.send(gpt_response)

                    # Save the learned intent if GPT response is successful
                    predicted_intent = await format_response_with_gpt(
                        f"Predict the intent of this message: '{message.content}'. "
                        "Return the action, server_id, and roles in JSON format."
                    )
                    learned_intent = eval(predicted_intent)  # Convert GPT's JSON-like response to a Python dictionary
                    if "action" in learned_intent and "server_id" in learned_intent:
                        await self.save_learned_intent(
                            phrase=message.content.lower(),
                            action=learned_intent["action"],
                            server_id=learned_intent["server_id"],
                            roles=learned_intent.get("roles", [])
                        )
                except Exception as e:
                    log.error(f"GPT error for unmatched message: {e}")
                    # Fallback to predefined phrases if GPT fails
                    fallback_response = await self.get_fallback_response(message.content)
                    await message.channel.send(fallback_response)
        except Exception as e:
            log.error(f"Error processing message: {e}")
            await message.channel.send("An error occurred while processing your request.")
