from .announcements import Announcements
from .api_server import run_api
import threading

async def setup(bot):
    cog = Announcements(bot)
    await bot.add_cog(cog)

    # Start Flask API
    thread = threading.Thread(target=run_api, args=(bot,))
    thread.daemon = True
    thread.start()

    return cog  
