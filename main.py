import asyncio
import threading

import config
from bot import bot, start_bot
from web import app


def run_web():
    app.config["BOT_INSTANCE"] = bot
    app.run(host="0.0.0.0", port=config.PORT, debug=False, use_reloader=False)


def main():
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print(f"[Pixel] Website running on port {config.PORT}")
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
