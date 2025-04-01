import psutil
import logging

log = logging.getLogger("red.naturalassistant")

async def check_system_resources(config_manager):
    warnings = []
    try:
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

    for guild in bot.guilds:
        try:
            admin_ids = await bot.get_cog("NaturalAssistant").config.guild(guild).admin_ids()
            for admin_id in admin_ids:
                admin = guild.get_member(admin_id)
                if admin:
                    await admin.send("\n".join(warnings))
        except Exception as e:
            log.error(f"Error sending warnings to admins in guild {guild.id}: {e}")
