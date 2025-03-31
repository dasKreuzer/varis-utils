from .core import SevereWeatherShutdown

async def setup(bot):
    await bot.add_cog(SevereWeatherShutdown(bot))
