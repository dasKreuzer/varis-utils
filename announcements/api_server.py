from flask import Flask, jsonify, request
from redbot.core.bot import Red
from announcements import Announcements
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
bot: Red = None

@app.route("/announcements", methods=["GET"])
def get_announcements():
    cog: Announcements = bot.get_cog("Announcements")
    if cog:
        return jsonify([cog.get_latest()])
    return jsonify([])

@app.route("/announcements/update", methods=["POST"])
def update_announcement():
    cog: Announcements = bot.get_cog("Announcements")
    if not cog:
        return jsonify({"error": "Announcements cog not loaded."}), 500

    data = request.json
    if not data or "message" not in data:
        return jsonify({"error": "Invalid request. 'message' field is required."}), 400

    cog.latest_announcement = {
        "username": data.get("username", "System"),
        "avatar": data.get("avatar", ""),
        "message": data["message"]
    }
    return jsonify({"success": True, "message": "Announcement updated."})

def run_api(_bot):
    global bot
    bot = _bot
    app.run(host="127.0.0.1", port=8765)  # Ensure it binds to localhost only
