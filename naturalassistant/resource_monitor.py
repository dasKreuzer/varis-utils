import psutil

async def check_system_resources(config_manager):
    warnings = []
    cpu_threshold = await config_manager.config.custom("thresholds").cpu()
    memory_threshold = await config_manager.config.custom("thresholds").memory()
    disk_threshold = await config_manager.config.custom("thresholds").disk()

    if psutil.cpu_percent() > cpu_threshold:
        warnings.append(f"CPU usage is at {psutil.cpu_percent()}%.")

    if psutil.virtual_memory().percent > memory_threshold:
        warnings.append(f"Memory usage is at {psutil.virtual_memory().percent}%.")

    if psutil.disk_usage("/").percent > disk_threshold:
        warnings.append(f"Disk usage is at {psutil.disk_usage('/').percent}%.")

    return warnings

async def send_warning_to_admins(bot, warnings):
    for guild in bot.guilds:
        admin_ids = await bot.get_cog("NaturalAssistant").config.guild(guild).admin_ids()
        for admin_id in admin_ids:
            admin = guild.get_member(admin_id)
            if admin:
                await admin.send("\n".join(warnings))
