import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
#  BRANDING CONFIG
# ------------------------------------------------------------
#  LOGO_URL   -> !help, !devinfo aur saare embeds ke thumbnail/
#                footer icon me yehi link use hota hai.
#                Replace karne ke liye sirf neeche wali
#                LOGO_URL line change karo.
#
#  BANNER_URL -> Abhi khali hai. Apna main header/banner image
#                ready hote hi uska link yaha daal dena. Yeh
#                website ke home page ke top banner me use
#                hoga.
# ============================================================

BOT_NAME = "Pixel"
BRAND = "HTML Force"
DEVELOPER = "Majid"

# 👉 LOGO LINK YAHA HAI
LOGO_URL = "https://cdn.postimage.me/2026/07/10/57704cc40aa8bb4822c15.png"

# 👉 BANNER LINK - abhi khali, baad me khud add karna
BANNER_URL = ""

YOUTUBE_URL = "https://youtube.com/@htmlforc01?si=OlmpQGgUGmFhYyEk"

COLOR_HEX = "#7C3AED"
COLOR_INT = 0x7C3AED

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

OWNER_IDS = [
    i.strip()
    for i in os.getenv("OWNER_IDS", "1464697383467356316").split(",")
    if i.strip()
]

PORT = int(os.getenv("PORT", "3000"))
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:3000/auth/callback")
SESSION_SECRET = os.getenv("SESSION_SECRET", "pixel_dev_secret_change_me")

DEFAULT_PREFIX = "!"
DISCORD_API = "https://discord.com/api"
