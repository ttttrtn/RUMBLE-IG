from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import requests
import instaloader
import threading
import time
import os
import json

# ---------------- APP ----------------
app = Flask(__name__, static_folder="public")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# ---------------- CONFIG ----------------
RUMBLE_KEY = os.environ.get("RUMBLE_KEY")
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")

RUMBLE_URL = f"https://rumble.com/-livestream-api/get-data?key={RUMBLE_KEY}"

CACHE_FILE = "ig_cache.json"

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()

def ig_login():
    try:
        if IG_USERNAME and IG_PASSWORD:
            L.login(IG_USERNAME, IG_PASSWORD)
            print("Instagram login success")
    except Exception as e:
        print("Instagram login failed:", e)

ig_login()

# ---------------- CACHE ----------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        return set(json.load(open(CACHE_FILE)))
    return set()

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(list(data), f)

ig_followers = load_cache()

# ---------------- RUMBLE ----------------
last_follow = None
last_sub = None

def rumble_loop():
    global last_follow, last_sub

    while True:
        try:
            data = requests.get(RUMBLE_URL, timeout=10).json()

            follower = data.get("followers", {}).get("latest_follower", {}).get("username")
            sub = data.get("subscribers", {}).get("latest_subscriber", {}).get("username")

            if follower and follower != last_follow:
                last_follow = follower
                socketio.emit("alert", {
                    "text": f"🔥 On Rumble: {follower} followed"
                })

            if sub and sub != last_sub:
                last_sub = sub
                socketio.emit("alert", {
                    "text": f"💎 On Rumble: {sub} subscribed"
                })

        except Exception as e:
            print("Rumble error:", e)

        time.sleep(3)

# ---------------- INSTAGRAM ----------------
def get_followers(profile, limit=120):
    users = set()

    try:
        for i, f in enumerate(profile.get_followers()):
            users.add(f.username)
            if i >= limit:
                break
    except:
        pass

    return users


def instagram_loop():
    global ig_followers

    while True:
        try:
            profile = instaloader.Profile.from_username(L.context, IG_USERNAME)
            current = get_followers(profile)

            new = current - ig_followers

            for user in new:
                socketio.emit("alert", {
                    "text": f"📸 On Instagram: {user} followed"
                })

            if new:
                ig_followers = current
                save_cache(ig_followers)

        except Exception as e:
            print("IG error:", e)

        time.sleep(60)

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("public", path)

# ---------------- START THREADS ----------------
threading.Thread(target=rumble_loop, daemon=True).start()
threading.Thread(target=instagram_loop, daemon=True).start()

# ---------------- RUN ----------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
