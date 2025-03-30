from flask import Flask, jsonify
from redbot.core.bot import Red
from cogs.announcements.announcements import Announcements

app = Flask(__name__)
bot: Red = None

@app.route("/announcements", methods=["GET"])
def get_announcements():
    cog: Announcements = bot.get_cog("Announcements")
    if cog:
        return jsonify([cog.get_latest()])
    return jsonify([])

def run_api(_bot):
    global bot
    bot = _bot
    app.run(host="0.0.0.0", port=8765)
