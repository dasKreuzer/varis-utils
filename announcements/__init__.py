from .announcements import Announcements
from .api_server import run_api
import threading

def setup(bot):
    cog = Announcements(bot)
    bot.add_cog(cog)

    # Start Flask API in a separate thread
    thread = threading.Thread(target=run_api, args=(bot,))
    thread.daemon = True
    thread.start()