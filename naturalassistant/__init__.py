from .core import NaturalAssistant

async def setup(bot):
    bot.add_cog(NaturalAssistant(bot))
