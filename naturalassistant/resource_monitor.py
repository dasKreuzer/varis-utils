import psutil
import logging
import time

log = logging.getLogger("red.naturalassistant")

async def check_system_resources(config_manager):
    warnings = []
    try:
        # Ensure thresholds are initialized with default values
        thresholds = await config_manager.config.custom("thresholds").all()
        cpu_threshold = thresholds.get("cpu", 80)
        memory_threshold = thresholds.get("memory", 80)
        disk_threshold = thresholds.get("disk", 80)

        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage("/").percent

        if cpu_usage > cpu_threshold:
            warnings.append(f"CPU usage is at {cpu_usage}% (Threshold: {cpu_threshold}%).")

        if memory_usage > memory_threshold:
            warnings.append(f"Memory usage is at {memory_usage}% (Threshold: {memory_threshold}%).")

        if disk_usage > disk_threshold:
            warnings.append(f"Disk usage is at {disk_usage}% (Threshold: {disk_threshold}%).")

    except Exception as e:
        log.error(f"Error checking system resources: {e}")
        warnings.append("An error occurred while checking system resources.")

    return warnings

async def send_warning_to_admins(bot, warnings):
    if not warnings:
        return

    cog = bot.get_cog("NaturalAssistant")
    if not cog:
        log.error("NaturalAssistant cog is not loaded. Cannot send warnings to admins.")
        return

    cooldowns = {}  # Track cooldowns for each guild
    for guild in bot.guilds:
        try:
            now = time.time()
            if guild.id in cooldowns and now - cooldowns[guild.id] < 300:  # 5-minute cooldown
                log.warning(f"Skipping warnings for guild {guild.id} due to cooldown.")
                continue
            cooldowns[guild.id] = now

            admin_ids = await cog.config.guild(guild).get_raw("admin_ids", default=[])
            for admin_id in admin_ids:
                admin = guild.get_member(admin_id)
                if admin:
                    await admin.send("\n".join(warnings))
        except Exception as e:
            log.error(f"Error sending warnings to admins in guild {guild.id}: {e}")
