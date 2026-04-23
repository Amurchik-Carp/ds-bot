import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GIGACHAD_CREDENTIALS = os.getenv("GIGACHAD_CREDENTIALS")
PREFIX = os.getenv("PREFIX", "!")
BOT_ID = os.getenv("BOT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
API_BASE_URL = os.getenv("API_BASE_URL", "https://discord.com")
MONGO_URL = os.getenv("MONGO_URL")
SECRET_KEY = os.getenv("SECRET_KEY")