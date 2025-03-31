from .core import SevereWeatherShutdown

async def setup(bot):
    """
    Load the SevereWeatherShutdown cog into the bot.
    """
    await bot.add_cog(SevereWeatherShutdown(bot))
