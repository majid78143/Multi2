# Pixel — All-in-One Discord Bot + Website (Python/Flask)

Developed by Majid — HTML Force

## Files (flat structure, no sub-folders)

- `config.py` — All branding + credentials. **Logo link is here (`LOGO_URL`)** — replace this one line whenever you want to change the logo shown in `!help`, `!devinfo`, and every embed. `BANNER_URL` is empty for now — add your header/banner image link here later, it will show on the website home page.
- `storage.py` — JSON file based storage (`data.json`, auto-created, no database needed).
- `embeds.py` — Branded embed + YouTube subscribe button builder.
- `bot.py` — The entire Discord bot: all commands (moderation, automation, engagement, tickets, reaction roles, owner tools) and all events (welcome/leave, anti-raid, anti-nuke, automod, leveling, birthdays, sticky messages, AFK).
- `web.py` — The entire Flask website: home, commands list, status, login dashboard (per-server settings), owner panel, Discord OAuth2 login.
- `main.py` — Entry point. Runs the website and the Discord bot together in one process.
- `requirements.txt` — Python dependencies.
- `.env.example` — Copy this to `.env` and fill in your bot token/IDs.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in:
   - `BOT_TOKEN` — from the Discord Developer Portal
   - `CLIENT_ID` — your application ID
   - `CLIENT_SECRET` — only needed for website login dashboard
   - `REDIRECT_URI` — must match the redirect URL set in the Discord Developer Portal OAuth2 settings (e.g. `https://yourapp.onrender.com/auth/callback`)
   - `OWNER_IDS` — your Discord user ID(s), comma separated
3. Run:
   ```
   python main.py
   ```
   This starts the website (on `PORT`, default 3000) and logs the bot into Discord at the same time.

## Deploying to Render

1. Push this folder to a GitHub repository.
2. On Render, create a **Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Add the same environment variables from `.env` in Render's Environment tab.
6. In the Discord Developer Portal, set your OAuth2 redirect URL to `https://<your-render-domain>/auth/callback` and update `REDIRECT_URI` in Render to match.

Render's free web service may sleep when idle — if you need the bot online 24/7, use a paid instance/worker.

## Notes

- No database is used — all data is stored in `data.json`, created automatically on first run.
- Replace the logo any time by editing `LOGO_URL` in `config.py` — nothing else needs to change.
- Add your banner image later by setting `BANNER_URL` in `config.py`.
- `runtime.txt` pins Python to 3.11.9. Do not delete it — newer Python versions (3.13+) removed the `audioop` module that discord.py needs, which crashes the bot on some hosts.

## Slash commands (`/help`, `/ban`, etc.)

The bot registers both `!` text commands and `/` slash commands. Slash commands only appear in Discord after the bot has logged in at least once and Discord has synced them — this can take up to an hour globally the first time (usually much faster). If they still don't show up:
1. Confirm the bot is Online (check `/status` on the website).
2. Re-invite the bot with the `applications.commands` scope included (the invite link on the website home page already includes it).
3. Kick and re-add the bot to the server if it was invited before slash commands were added.

## Why does the bot sometimes go offline?

If you're on Render's **Free** plan, a Web Service is put to sleep after ~15 minutes with no incoming HTTP traffic — since the bot's Discord connection runs in the same process as the website, this kills the bot too. This is a hosting-plan limit, not a bug in the code. Fixes:
- Use an external uptime monitor (e.g. UptimeRobot, free) to ping your site's `/health` URL every 5 minutes, keeping the process alive, or
- Upgrade to a paid Render instance, which does not sleep.

## Why does the dashboard require login?

The website dashboard lets you change server settings and run moderation actions (purge, announcements, etc.) directly from the browser. Discord OAuth login is what proves you actually have permission in that server — without it, anyone with the link could control your server. Adding the bot to a server and logging into the dashboard are two separate steps by design (bot install = server-wide, login = proving who *you* are), so this can't be merged into one click. Once you log in with Discord, it stays logged in (session) until you log out.

## Website live actions

Inside a server's dashboard page (`/dashboard/<server>`) there is a "Live Actions" panel — purge messages or send an announcement directly, which runs instantly on Discord through the same running bot (no need to type a command in Discord). More actions can be added the same way in `web.py` following the `action_purge` / `action_announce` pattern.
