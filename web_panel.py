# web_panel.py

from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from requests_oauthlib import OAuth2Session
from datetime import timedelta
import os
import config

# ==================================================
# APP
# ==================================================

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# авторизация на 7 дней
app.permanent_session_lifetime = timedelta(days=7)

# ==================================================
# MONGODB
# ==================================================

cluster = MongoClient(config.MONGO_URL)
db = cluster["discord_bot_db"]

settings_collection = db["settings"]
bot_guilds_collection = db["bot_guilds"]

# ==================================================
# DISCORD OAUTH2
# ==================================================

API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = API_BASE_URL + "/oauth2/authorize"
TOKEN_URL = API_BASE_URL + "/oauth2/token"

SCOPES = ["identify", "guilds"]
BOT_ID = str(config.CLIENT_ID)


def get_discord_session(token=None, state=None):
    return OAuth2Session(
        client_id=config.CLIENT_ID,
        token=token,
        state=state,
        scope=SCOPES,
        redirect_uri=config.REDIRECT_URI
    )


# ==================================================
# HOME
# ==================================================

@app.route("/")
def index():
    if "oauth2_token" not in session:
        return render_template("login.html")

    try:
        discord = get_discord_session(token=session["oauth2_token"])

        user_resp = discord.get(API_BASE_URL + "/users/@me")
        if user_resp.status_code != 200:
            session.clear()
            return redirect(url_for("login"))

        guilds_resp = discord.get(API_BASE_URL + "/users/@me/guilds")
        if guilds_resp.status_code != 200:
            return "Ошибка получения серверов Discord"

        user = user_resp.json()
        guilds = guilds_resp.json()
        dashboard_guilds = []

        for g in guilds:
            permissions = int(g.get("permissions", 0))

            is_admin = (
                g.get("owner") or
                (permissions & 0x8)
            )

            if not is_admin:
                continue

            guild_id = int(g["id"])

            bot_data = bot_guilds_collection.find_one({
                "_id": guild_id
            })
            bot_added = bot_data is not None

            settings_data = settings_collection.find_one({
                "_id": guild_id
            })

            current_prefix = (
                settings_data.get("prefix", config.PREFIX)
                if settings_data else config.PREFIX
            )

            invite_url = (
                f"https://discord.com/oauth2/authorize"
                f"?client_id={BOT_ID}"
                f"&scope=bot%20applications.commands"
                f"&permissions=8"
                f"&guild_id={guild_id}"
                f"&disable_guild_select=true"
            )

            dashboard_guilds.append({
                "id": g["id"],
                "name": g["name"],
                "icon": g.get("icon"),
                "bot_added": bot_added,
                "current_prefix": current_prefix,
                "invite_url": invite_url
            })

        return render_template(
            "index.html",
            guilds=dashboard_guilds,
            user=user
        )

    except Exception as e:
        print("INDEX ERROR:", str(e))
        session.clear()
        return f"Ошибка авторизации: {str(e)}"


# ==================================================
# LOGIN
# ==================================================

@app.route("/login")
def login():
    session.clear()

    try:
        discord = get_discord_session()

        authorization_url, state = discord.authorization_url(
            AUTHORIZATION_BASE_URL
        )

        session["oauth2_state"] = state

        print("LOGIN STATE:", state)
        print("AUTH URL:", authorization_url)

        return redirect(authorization_url)

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return f"Ошибка login(): {str(e)}"


# ==================================================
# CALLBACK
# ==================================================

@app.route("/callback")
def callback():
    print("========== CALLBACK ==========")
    print("FULL URL:", request.url)
    print("ARGS:", request.args)

    if "error" in request.args:
        return f"OAuth ошибка: {request.args.get('error')}"

    saved_state = session.get("oauth2_state")
    returned_state = request.args.get("state")

    if not saved_state:
        return "State не найден в session"

    if saved_state != returned_state:
        return "State mismatch", 403

    code = request.args.get("code")
    if not code:
        return "Discord не вернул code"

    try:
        discord = get_discord_session(state=saved_state)

        token = discord.fetch_token(
            TOKEN_URL,
            client_secret=config.CLIENT_SECRET,
            authorization_response=request.url,
            include_client_id=True
        )

        if not token:
            return "Токен пустой"

        session.permanent = True
        session["oauth2_token"] = token

        print("TOKEN SAVED")

        return redirect("/")

    except Exception as e:
        print("TOKEN ERROR:", str(e))
        return f"Ошибка получения токена: {str(e)}"


# ==================================================
# UPDATE PREFIX
# ==================================================

@app.route("/update", methods=["POST"])
def update():
    if "oauth2_token" not in session:
        return redirect(url_for("login"))

    guild_id = request.form.get("guild_id")
    prefix = request.form.get("prefix")

    if not guild_id or not prefix:
        return "Ошибка данных"

    try:
        settings_collection.update_one(
            {"_id": int(guild_id)},
            {"$set": {"prefix": prefix}},
            upsert=True
        )

        return redirect(url_for("index"))

    except Exception as e:
        print("UPDATE ERROR:", str(e))
        return f"Ошибка MongoDB: {str(e)}"


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==================================================
# START
# ==================================================

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    print("START:")
    print("http://127.0.0.1:5000")
    print("REDIRECT_URI:", config.REDIRECT_URI)

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )