from redbot.core import Config

def get_config_schema(cog):
    config = Config.get_conf(cog, identifier=1456789012345)
    config.register_guild(
        lat=None,
        lon=None,
        alerts=["Tornado Warning", "Severe Thunderstorm Warning"],
        admin_ids=[],  # ✅ Now a list of user IDs
        announcement_channel=None,
        enabled=False
    )
    return config
