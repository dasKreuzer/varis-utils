import discord

def build_admin_embed(alert):
    props = alert["properties"]
    description = props['description'][:500] + "..." if len(props['description']) > 500 else props['description']
    return discord.Embed(
        title="\u26a0\ufe0f Severe Weather Alert Detected",
        description=f"**Type:** {props['event']}\n**Area:** {props['areaDesc']}\n"
                    f"**Issued By:** {props['senderName']}\n\n{description}",
        color=discord.Color.red()
    ).add_field(name="Expires", value=props.get("expires", "Unknown"), inline=False) \
     .set_footer(text="Reply with !wshutdown yes or !wshutdown no")

def build_announcement_embed(alert):
    props = alert["properties"]
    return discord.Embed(
        title="\ud83c\udf29\ufe0f SERVER SHUTDOWN NOTICE",
        description=f"Due to active severe weather in the area, the servers will be shut down shortly for safety reasons.\n\n"
                    f"**Type:** {props['event']}\nStay safe and follow local safety instructions.",
        color=discord.Color.orange()
    ).set_footer(text="Shutdown in 5 minutes.")
