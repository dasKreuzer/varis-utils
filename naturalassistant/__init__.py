from .core import NaturalAssistant
import logging

log = logging.getLogger("red.naturalassistant")

async def setup(bot):
    try:
        await bot.add_cog(NaturalAssistant(bot))
        log.info("NaturalAssistant cog successfully loaded.")
    except Exception as e:
        log.error(f"Failed to load NaturalAssistant cog: {e}")