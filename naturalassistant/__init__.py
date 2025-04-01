from .core import NaturalAssistant

async def setup(bot):
    try:
        await bot.add_cog(NaturalAssistant(bot))
        bot.log.info("NaturalAssistant cog successfully loaded.")
    except Exception as e:
        bot.log.error(f"Failed to load NaturalAssistant cog: {e}")
