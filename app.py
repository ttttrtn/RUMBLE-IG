from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import requests
import instaloader
import threading
import time
import os
import json

app = Flask(__name__, static_folder="public")
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- CONFIG ----------------
RUMBLE_KEY = os.environ.get("RUMBLE_KEY")
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")

RUMBLE_URL = f"https://rumble.com/-livestream-api/get-data?key={RUMBLE_KEY}"

CACHE_FILE = "ig_cache.json"

# ---------------- INSTALOADER ----------------
L = instaloader.Instaloader()

try:
    L.login(IG_USERNAME, IG_PASSWORD)
except:
    print("Instagram login failed")

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
last_rumble_follow = None
last_rumble_sub = None

def rumble_loop():
    global last_rumble_follow, last_rumble_sub

    while True:
        try:
            data = requests.get(RUMBLE_URL).json()

            follower = data["followers"]["latest_follower"]["username"]
            sub = data["subscribers"]["latest_subscriber"]["username"]

            if follower and follower != last_rumble_follow:
                last_rumble_follow = follower

                socketio.emit("alert", {
                    "text": f"🔥 On Rumble: {follower} followed"
                })

            if sub and sub != last_rumble_sub:
                last_rumble_sub = sub

                socketio.emit("alert", {
                    "text": f"💎 On Rumble: {sub} subscribed"
                })

        except Exception as e:
            print("Rumble error:", e)

        time.sleep(2)

# ---------------- INSTAGRAM ----------------
def get_recent(profile, limit=150):
    return set(
        list(f.username for i, f in enumerate(profile.get_followers()) if i < limit)
    )

def instagram_loop():
    global ig_followers

    while True:
        try:
            profile = instaloader.Profile.from_username(L.context, IG_USERNAME)
            current = get_recent(profile)

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

# ---------------- RECOVERY ----------------
def recovery_loop():
    while True:
        try:
            L.login(IG_USERNAME, IG_PASSWORD)
        except:
            pass

        time.sleep(600)

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/<path:path>")
def static(path):
    return send_from_directory("public", path)

# ---------------- START ----------------
threading.Thread(target=rumble_loop, daemon=True).start()
threading.Thread(target=instagram_loop, daemon=True).start()
threading.Thread(target=recovery_loop, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
