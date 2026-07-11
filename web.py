import time
import json as _json
import asyncio
import requests
from flask import Flask, request, redirect, session, jsonify, render_template_string

import config
from storage import get_guild_data, save_guild_data, get_global_data, save_global_data
from embeds import build_embed_from_template
from bot import post_ticket_panel, build_role_menu_view

app = Flask(__name__)
app.secret_key = config.SESSION_SECRET
START_TIME = time.time()

# ================= SVG ICON SET (premium, outline style, no emojis anywhere) =================

ICON = {
    "home": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 11.5 12 4l9 7.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M5.5 10v9a1 1 0 0 0 1 1H10v-5.5a2 2 0 0 1 4 0V20h3.5a1 1 0 0 0 1-1v-9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "commands": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 9l-4 3 4 3M16 9l4 3-4 3M13.5 6.5l-3 11" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "status": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 17l4-6 4 3 5-8 5 5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "dashboard": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="3.5" width="7" height="7" rx="1.3"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.3"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.3"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.3"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M22 8.7c0-2-1.5-3.6-3.4-3.8C15.7 4.6 12 4.6 12 4.6s-3.7 0-6.6.3C3.5 5.1 2 6.8 2 8.7 1.8 10.5 1.8 12 1.8 12s0 1.5.2 3.3c0 2 1.5 3.6 3.4 3.8 2.9.3 6.6.3 6.6.3s3.7 0 6.6-.3c1.9-.2 3.4-1.8 3.4-3.8.2-1.8.2-3.3.2-3.3s0-1.5-.2-3.3z"/><path d="M9.8 15.3V8.7L15.6 12l-5.8 3.3z" fill="#0f0b1e"/></svg>',
    "discord": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.3 5.3A16.6 16.6 0 0 0 15 4l-.3.6a12.9 12.9 0 0 1 3.7 1.5 14.6 14.6 0 0 0-12.8 0A12.9 12.9 0 0 1 9.3 4.6L9 4a16.6 16.6 0 0 0-4.3 1.3C2.2 9 1.5 12.6 1.8 16.1a16.7 16.7 0 0 0 5 2.6l.8-1.3a10.8 10.8 0 0 1-1.6-.8l.4-.3a12 12 0 0 0 10.2 0l.4.3a10.8 10.8 0 0 1-1.6.8l.8 1.3a16.6 16.6 0 0 0 5-2.6c.4-4-.6-7.6-2.9-10.8zM8.7 14c-.8 0-1.4-.7-1.4-1.6s.6-1.6 1.4-1.6 1.5.7 1.4 1.6c0 .9-.6 1.6-1.4 1.6zm6.6 0c-.8 0-1.4-.7-1.4-1.6s.6-1.6 1.4-1.6 1.4.7 1.4 1.6-.6 1.6-1.4 1.6z"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3.5 5 6v5.5c0 4.6 3 7.9 7 9 4-1.1 7-4.4 7-9V6l-7-2.5z" stroke-linejoin="round"/><path d="M9 12.2l2 2 4-4.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "gear": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 13.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V20a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H4a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3H10a1.7 1.7 0 0 0 1-1.6V4a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9V10a1.7 1.7 0 0 0 1.6 1H20a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1.5z" stroke-linejoin="round"/></svg>',
    "users": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="3.2"/><path d="M2.8 19c.6-3 3-5 6.2-5s5.6 2 6.2 5" stroke-linecap="round"/><path d="M16 8.2a3 3 0 1 1 3.6 3M21.2 19c-.4-2.1-1.7-3.7-3.6-4.5" stroke-linecap="round"/></svg>',
    "server": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="4" width="17" height="6" rx="1.5"/><rect x="3.5" y="14" width="17" height="6" rx="1.5"/><circle cx="7" cy="7" r=".8" fill="currentColor" stroke="none"/><circle cx="7" cy="17" r=".8" fill="currentColor" stroke="none"/></svg>',
    "chart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M11 20V4M18 20v-7" stroke-linecap="round"/></svg>',
    "logout": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M16 15l4-3-4-3M20 12H9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "login": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M8 15l-4-3 4-3M4 12h11" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "coin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v9M9.3 15.3c.5.9 1.5 1.4 2.7 1.4 1.7 0 2.9-.9 2.9-2.2 0-3-5.6-1.6-5.6-4.6 0-1.3 1.2-2.2 2.9-2.2 1.1 0 2.1.5 2.6 1.4" stroke-linecap="round"/></svg>',
    "gift": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="9" width="17" height="4" rx="1"/><rect x="4.5" y="13" width="15" height="7.5" rx="1"/><path d="M12 9v11.5M12 9c-1.4 0-3.4-1-3.4-3S10 3 12 5.5C14 3 15.8 4 15.4 6c0 2-2 3-3.4 3z" stroke-linejoin="round"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M4 6.5l8 6.5 8-6.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "ticket": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 8.5A1.5 1.5 0 0 0 5.5 10a1.5 1.5 0 0 1 0 3A1.5 1.5 0 0 0 4 14.5V17a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2.5A1.5 1.5 0 0 0 18.5 13a1.5 1.5 0 0 1 0-3A1.5 1.5 0 0 0 20 8.5V6a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1z" stroke-linejoin="round"/><path d="M10 6v13" stroke-dasharray="2 2"/></svg>',
    "role": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3.5 5 6v5.5c0 4.6 3 7.9 7 9 4-1.1 7-4.4 7-9V6l-7-2.5z" stroke-linejoin="round"/></svg>',
    "trash": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4.5 7h15M9.5 7V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2M7 7l1 12.5a1.5 1.5 0 0 0 1.5 1.4h5a1.5 1.5 0 0 0 1.5-1.4L17 7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "megaphone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10v4a1 1 0 0 0 1 1h2l6.5 4.5V4.5L6 9H4a1 1 0 0 0-1 1z" stroke-linejoin="round"/><path d="M17.5 9a4 4 0 0 1 0 6M20 6.5a7.5 7.5 0 0 1 0 11" stroke-linecap="round"/></svg>',
    "power": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3.5v8" stroke-linecap="round"/><path d="M7 6.3a8 8 0 1 0 10 0" stroke-linecap="round"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6.5h16M4 12h16M4 17.5h16" stroke-linecap="round"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5l14 14M19 5L5 19" stroke-linecap="round"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12.5l5.5 5.5L20 6.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "bolt": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 3 4 14h6l-1 7 9-11h-6l1-7z" stroke-linejoin="round"/></svg>',
    "reply": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 8 4 12l5 4M4 12h9a6 6 0 0 1 6 6v1" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}


def icon(name, size=20):
    return f'<span class="icon" style="width:{size}px;height:{size}px;display:inline-flex;">{ICON.get(name, "")}</span>'


# ================= mobile-first CSS =================

BASE_CSS = """
:root{--bg:#0b0817;--bg2:#120e24;--card:#191333;--card2:#1f1940;--accent:#7C3AED;--accent2:#a78bfa;--text:#f1edff;--muted:#9d92c4;--border:#2a2350;}
*{box-sizing:border-box;}
html{-webkit-tap-highlight-color:transparent;}
body{margin:0;font-family:'Segoe UI',Arial,sans-serif;background:radial-gradient(circle at top,var(--bg2),var(--bg) 60%);color:var(--text);min-height:100vh;}
.icon svg{width:100%;height:100%;}
a{color:inherit;}
header{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;background:rgba(18,14,36,.85);backdrop-filter:blur(10px);position:sticky;top:0;z-index:50;border-bottom:1px solid var(--border);}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:18px;letter-spacing:.3px;}
.brand img{width:34px;height:34px;border-radius:9px;box-shadow:0 0 0 2px var(--accent);}
nav.desktop-nav{display:flex;align-items:center;gap:6px;}
nav.desktop-nav a{display:flex;align-items:center;gap:7px;color:var(--muted);text-decoration:none;font-weight:600;font-size:14px;padding:9px 14px;border-radius:10px;transition:.15s;}
nav.desktop-nav a:hover,nav.desktop-nav a.active{color:var(--text);background:var(--card);}
.menu-btn{display:none;background:none;border:none;color:var(--text);width:26px;height:26px;cursor:pointer;padding:0;}
.mobile-nav{display:none;flex-direction:column;gap:4px;padding:10px 14px 16px;background:var(--bg2);border-bottom:1px solid var(--border);}
.mobile-nav a{display:flex;align-items:center;gap:10px;color:var(--muted);text-decoration:none;font-weight:600;padding:12px 10px;border-radius:10px;font-size:15px;}
.mobile-nav a:active{background:var(--card);}
.mobile-nav.open{display:flex;}
.container{max-width:1000px;margin:0 auto;padding:36px 18px 60px;}
.hero{text-align:center;padding:50px 16px 30px;}
.hero h1{font-size:clamp(26px,6vw,46px);margin:0 0 10px;line-height:1.15;}
.hero p{color:var(--muted);font-size:clamp(14px,3vw,18px);max-width:520px;margin:0 auto;}
.btn{display:inline-flex;align-items:center;gap:9px;padding:13px 22px;border-radius:12px;font-weight:700;text-decoration:none;margin:6px;font-size:14px;border:none;cursor:pointer;transition:.15s;}
.btn-primary{background:linear-gradient(135deg,var(--accent),#5b21b6);color:#fff;box-shadow:0 6px 22px rgba(124,58,237,.4);}
.btn-primary:hover{transform:translateY(-1px);}
.btn-yt{background:#FF0000;color:#fff;}
.btn-ghost{background:var(--card);color:var(--text);border:1px solid var(--border);}
.btn-danger{background:#3a1030;color:#ff8fb3;border:1px solid #5c1a3f;}
.btn-sm{padding:8px 14px;font-size:13px;margin:3px;}
.actions-row{display:flex;flex-wrap:wrap;justify-content:center;}
.stats{display:flex;gap:16px;justify-content:center;margin-top:34px;flex-wrap:wrap;}
.stat{background:var(--card);padding:20px 28px;border-radius:16px;text-align:center;min-width:120px;border:1px solid var(--border);}
.stat .icon{color:var(--accent2);margin:0 auto 6px;}
.stat b{font-size:26px;display:block;}
.stat span.label{color:var(--muted);font-size:13px;}
.card{background:var(--card);padding:22px;border-radius:16px;margin-bottom:16px;border:1px solid var(--border);}
.card h3{display:flex;align-items:center;gap:10px;margin-top:0;}
.card h3 .icon{color:var(--accent2);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;}
.tabs a{padding:8px 14px;border-radius:9px;background:var(--card2);color:var(--muted);text-decoration:none;font-size:13px;font-weight:600;border:1px solid var(--border);}
.tabs a.active{background:var(--accent);color:#fff;border-color:var(--accent);}
input,select,textarea{width:100%;padding:11px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);margin-top:6px;font-size:15px;}
label{font-weight:600;color:var(--muted);font-size:13px;display:flex;align-items:center;gap:6px;}
footer{text-align:center;padding:34px 16px;color:var(--muted);border-top:1px solid var(--border);margin-top:50px;font-size:13px;}
h2{display:flex;align-items:center;gap:10px;border-left:3px solid var(--accent);padding-left:12px;}
h2 .icon{color:var(--accent2);}
.cmd-tag{display:inline-flex;align-items:center;gap:6px;background:var(--card2);padding:8px 13px;border-radius:9px;margin:4px;font-size:13px;border:1px solid var(--border);}
.role-pill{display:inline-flex;align-items:center;gap:6px;background:var(--card2);padding:6px 12px;border-radius:20px;margin:3px;font-size:13px;border:1px solid var(--border);}
.role-pill .icon{width:14px;height:14px;color:var(--accent2);}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:20px;font-size:12px;font-weight:700;}
.badge-on{background:#123322;color:#5ee89a;}
.badge-off{background:#3a1a1a;color:#f28c8c;}
.login-wrap{min-height:70vh;display:flex;align-items:center;justify-content:center;padding:20px;}
.login-card{background:var(--card);border:1px solid var(--border);border-radius:22px;padding:44px 30px;text-align:center;max-width:380px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,.4);}
.login-card img{width:70px;height:70px;border-radius:18px;margin-bottom:16px;box-shadow:0 0 0 3px var(--accent);}
.login-card h2{justify-content:center;border:none;padding:0;font-size:22px;}
.login-card p{color:var(--muted);font-size:14px;margin-bottom:24px;}
.chip-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;}
.chip{background:var(--card2);border:1px solid var(--border);border-radius:20px;padding:5px 12px;font-size:12px;display:flex;align-items:center;gap:6px;}
.chip button{background:none;border:none;color:#ff8fb3;cursor:pointer;font-weight:800;}
@media (max-width:720px){
  nav.desktop-nav{display:none;}
  .menu-btn{display:flex;align-items:center;justify-content:center;}
  .container{padding:24px 14px 50px;}
  .stats{gap:10px;}
  .stat{padding:16px 18px;min-width:100px;}
  .grid{grid-template-columns:1fr;}
}
"""

HEADER_HTML = """
<header>
  <div class="brand"><img src="{{ logo }}" alt="logo"> {{ bot_name }}</div>
  <nav class="desktop-nav">
    <a href="/">""" + icon("home", 17) + """ Home</a>
    <a href="/commands">""" + icon("commands", 17) + """ Commands</a>
    <a href="/status">""" + icon("status", 17) + """ Status</a>
    <a href="/dashboard">""" + icon("dashboard", 17) + """ Dashboard</a>
  </nav>
  <button class="menu-btn" onclick="document.getElementById('mnav').classList.toggle('open')">""" + icon("menu", 24) + """</button>
</header>
<div class="mobile-nav" id="mnav">
  <a href="/">""" + icon("home", 18) + """ Home</a>
  <a href="/commands">""" + icon("commands", 18) + """ Commands</a>
  <a href="/status">""" + icon("status", 18) + """ Status</a>
  <a href="/dashboard">""" + icon("dashboard", 18) + """ Dashboard</a>
</div>
"""

FOOTER_HTML = """
<footer>
  <a class="btn btn-yt" href="{{ youtube }}" target="_blank">""" + icon("youtube", 18) + """ Subscribe on YouTube</a><br>
  Developed by {{ developer }} — {{ brand }}
</footer>
"""

PAGE_WRAP = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'><title>{{ title }}</title><style>" + BASE_CSS + "</style></head><body>" + HEADER_HTML + "{{ body|safe }}" + FOOTER_HTML + "</body></html>"


def render(title, body_html, **ctx):
    return render_template_string(
        PAGE_WRAP,
        title=title,
        body=render_template_string(body_html, icon=icon, **ctx),
        logo=config.LOGO_URL,
        bot_name=config.BOT_NAME,
        youtube=config.YOUTUBE_URL,
        developer=config.DEVELOPER,
        brand=config.BRAND,
    )


COMMANDS_LIST = {
    "General": ("home", ["help", "devinfo", "ping", "userinfo", "serverinfo", "avatar", "afk"]),
    "Moderation": ("shield", ["ban", "kick", "mute", "unmute", "warn", "warnings", "clearwarnings", "purge", "lock", "unlock", "verify"]),
    "Server Setup": ("gear", ["setprefix", "setwelcome", "setleave", "setautorole", "automod", "setlogchannel", "setmodlog", "setverification", "setsuggestionchannel", "setsticky", "removesticky", "togglecommand"]),
    "Engagement": ("coin", ["rank", "leaderboard", "balance", "daily", "pay", "shop", "buy", "setbirthday", "birthdays", "suggest", "poll", "remind", "translate", "giveaway"]),
    "Tickets & Roles": ("ticket", ["ticket", "closeticket", "reactionrole", "rolemenu"]),
    "Owner Only": ("shield", ["eval", "blacklist", "maintenance", "broadcast", "setstatus", "forceleave", "servers"]),
}

TEMPLATE_TYPES = {
    "welcome": "Welcome",
    "leave": "Leave",
    "boost": "Server Boost",
    "levelup": "Level Up",
    "ticket": "Ticket Welcome",
    "autoresponder": "Auto-Responder",
    "custom": "Custom / Announcement",
}


# ---------------- helper: run bot coroutine from sync Flask thread ----------------

def run_on_bot(coro, timeout=10):
    bot_instance = app.config.get("BOT_INSTANCE")
    if not bot_instance or not bot_instance.is_ready():
        raise RuntimeError("Bot is not online right now.")
    future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
    return future.result(timeout=timeout)


# ---------------- pages ----------------

@app.route("/")
def home():
    bot_instance = app.config.get("BOT_INSTANCE")
    servers = len(bot_instance.guilds) if bot_instance and bot_instance.is_ready() else 0
    users = sum(g.member_count or 0 for g in bot_instance.guilds) if bot_instance and bot_instance.is_ready() else 0
    invite = f"https://discord.com/oauth2/authorize?client_id={config.CLIENT_ID}&permissions=8&scope=bot%20applications.commands"
    body = """
    <div class="hero">
      {% if banner %}<img src="{{ banner }}" style="max-width:100%;border-radius:18px;margin-bottom:22px;">{% endif %}
      <h1>{{ bot_name }} — All-in-One Discord Bot</h1>
      <p>Moderation, automation, engagement and full server control in one place — controllable from Discord or from this dashboard.</p>
      <div class="actions-row">
        <a class="btn btn-primary" href="{{ invite }}" target="_blank">""" + icon("discord", 18) + """ Add to Server</a>
        <a class="btn btn-yt" href="{{ youtube }}" target="_blank">""" + icon("youtube", 18) + """ Subscribe on YouTube</a>
      </div>
      <div class="stats">
        <div class="stat">""" + icon("server", 22) + """<b>{{ servers }}</b><span class="label">Servers</span></div>
        <div class="stat">""" + icon("users", 22) + """<b>{{ users }}</b><span class="label">Users</span></div>
        <div class="stat">""" + icon("commands", 22) + """<b>{{ cmd_count }}</b><span class="label">Commands</span></div>
      </div>
    </div>
    """
    return render("Home", body, banner=config.BANNER_URL, invite=invite, servers=servers, users=users,
                  cmd_count=sum(len(v[1]) for v in COMMANDS_LIST.values()))


@app.route("/commands")
def commands_page():
    body = """
    <div class="container">
      <h2>""" + icon("commands", 22) + """ Commands</h2>
      <p style="color:var(--muted);font-size:13px;margin-top:-10px;">Every command works with the prefix (e.g. {{ prefix }}help) and as a / slash command.</p>
      <input id="search" placeholder="Search commands..." onkeyup="filterCmds()">
      {% for cat, data in commands.items() %}
      <div class="card cat-block">
        <h3>{{ icon(data[0], 18)|safe }} {{ cat }}</h3>
        <div>{% for c in data[1] %}<span class="cmd-tag">""" + icon("commands", 14) + """ /{{ c }}</span>{% endfor %}</div>
      </div>
      {% endfor %}
    </div>
    <script>
    function filterCmds(){
      var q = document.getElementById('search').value.toLowerCase();
      document.querySelectorAll('.cat-block').forEach(function(block){
        var tags = block.querySelectorAll('.cmd-tag');
        var visible = 0;
        tags.forEach(function(t){
          var show = t.innerText.toLowerCase().includes(q);
          t.style.display = show ? 'inline-flex' : 'none';
          if(show) visible++;
        });
        block.style.display = visible > 0 ? 'block' : 'none';
      });
    }
    </script>
    """
    return render("Commands", body, commands=COMMANDS_LIST, prefix=config.DEFAULT_PREFIX)


@app.route("/status")
def status_page():
    bot_instance = app.config.get("BOT_INSTANCE")
    ready = bool(bot_instance and bot_instance.is_ready())
    latency = round(bot_instance.latency * 1000) if ready else 0
    uptime = int(time.time() - START_TIME)
    body = """
    <div class="container">
      <h2>""" + icon("status", 22) + """ Bot Status</h2>
      <div class="card">
        <p>Status: <span class="badge {{ 'badge-on' if ready else 'badge-off' }}">""" + icon("power", 14) + """ {{ 'Online' if ready else 'Offline' }}</span></p>
        <p>Latency: <b>{{ latency }}ms</b></p>
        <p>Website Uptime: <b>{{ uptime }} seconds</b></p>
        {% if not ready %}<p style="color:var(--muted);font-size:13px;">If this stays Offline, your hosting plan may be putting the process to sleep — see README for the fix.</p>{% endif %}
      </div>
    </div>
    """
    return render("Status", body, ready=ready, latency=latency, uptime=uptime)


@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        body = """
        <div class="login-wrap">
          <div class="login-card">
            <img src="{{ logo }}" alt="logo">
            <h2>Dashboard Login</h2>
            <p>Sign in with your Discord account to manage the servers where you have permissions.</p>
            <a class="btn btn-primary" href="/auth/login" style="width:100%;justify-content:center;">""" + icon("discord", 18) + """ Continue with Discord</a>
          </div>
        </div>
        """
        return render("Dashboard Login", body, logo=config.LOGO_URL)
    bot_instance = app.config.get("BOT_INSTANCE")
    mutual = []
    if bot_instance and bot_instance.is_ready():
        for g in bot_instance.guilds:
            member = g.get_member(int(user["id"]))
            if member and (member.guild_permissions.manage_guild or str(member.id) in config.OWNER_IDS):
                mutual.append(g)
    body = """
    <div class="container">
      <h2>""" + icon("dashboard", 22) + """ Your Servers</h2>
      <p style="color:var(--muted);">Logged in as <b style="color:var(--text);">{{ user['username'] }}</b> — <a href="/auth/logout" style="color:var(--accent2);">Logout</a></p>
      <div class="grid">
      {% for g in guilds %}
        <div class="card"><b>{{ g.name }}</b><br><br><a class="btn btn-primary" href="/dashboard/{{ g.id }}">""" + icon("gear", 16) + """ Manage</a></div>
      {% else %}
        <p>No manageable mutual servers found. Add the bot to a server first, then refresh.</p>
      {% endfor %}
      </div>
      {% if is_owner %}<p style="margin-top:20px;"><a class="btn btn-ghost" href="/owner">""" + icon("shield", 16) + """ Owner Panel</a></p>{% endif %}
    </div>
    """
    return render("Dashboard", body, user=user, guilds=mutual, is_owner=str(user["id"]) in config.OWNER_IDS)


def _require_guild_manager(guild_id):
    """Returns (guild, member) or (None, None) on failure -- shared auth pattern."""
    user = session.get("user")
    if not user:
        return None, None
    bot_instance = app.config.get("BOT_INSTANCE")
    guild = bot_instance.get_guild(int(guild_id)) if bot_instance else None
    if not guild:
        return None, None
    member = guild.get_member(int(user["id"]))
    if not member or not (member.guild_permissions.manage_guild or str(member.id) in config.OWNER_IDS):
        return None, None
    return guild, member


DASH_TABS = [
    ("", "Overview", "gear"),
    ("/automod", "Auto-Mod", "shield"),
    ("/embeds", "Templates", "bolt"),
    ("/autoresponders", "Auto-Responders", "reply"),
    ("/rolemenus", "Role Menus", "role"),
    ("/tickets", "Tickets", "ticket"),
    ("/commands", "Commands", "commands"),
    ("/analytics", "Analytics", "chart"),
]


def _tabs_html(guild_id, active):
    parts = []
    for suffix, label, ic in DASH_TABS:
        cls = "active" if suffix == active else ""
        parts.append(f'<a class="{cls}" href="/dashboard/{guild_id}{suffix}">{icon(ic,14)} {label}</a>')
    return '<div class="tabs">' + "".join(parts) + "</div>"


@app.route("/dashboard/<guild_id>", methods=["GET", "POST"])
def dashboard_guild(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")

    data = get_guild_data(guild_id)
    notice = None
    if request.method == "POST":
        data["prefix"] = request.form.get("prefix", data["prefix"])
        data["automod"]["enabled"] = request.form.get("automod") == "on"
        data["welcome"]["enabled"] = request.form.get("welcome_enabled") == "on"
        data["welcome"]["channel_id"] = request.form.get("welcome_channel") or None
        data["welcome"]["message"] = request.form.get("welcome_message", data["welcome"]["message"])
        data["welcome"]["dm_enabled"] = request.form.get("welcome_dm") == "on"
        data["leave"]["enabled"] = request.form.get("leave_enabled") == "on"
        data["leave"]["channel_id"] = request.form.get("leave_channel") or None
        data["leave"]["message"] = request.form.get("leave_message", data["leave"]["message"])
        data["boost"]["enabled"] = request.form.get("boost_enabled") == "on"
        data["boost"]["channel_id"] = request.form.get("boost_channel") or None
        data["levelup"]["enabled"] = request.form.get("levelup_enabled") == "on"
        data["levelup"]["channel_id"] = request.form.get("levelup_channel") or None
        save_guild_data(guild_id, data)
        notice = "Settings saved."

    roles = sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)[:15]
    text_channels = [c for c in guild.text_channels][:25]
    templates = data.get("embed_templates", {})

    def tpl_options(section_key):
        current = data.get(section_key, {}).get("template")
        opts = ['<option value="">No template (use plain text below)</option>']
        for name in templates.keys():
            sel = "selected" if name == current else ""
            opts.append(f'<option value="{name}" {sel}>{name}</option>')
        return "".join(opts)

    def chan_options(current):
        opts = ['<option value="">Select channel</option>']
        for c in text_channels:
            sel = "selected" if str(c.id) == str(current) else ""
            opts.append(f'<option value="{c.id}" {sel}>#{c.name}</option>')
        return "".join(opts)

    body = """
    <div class="container">
      <h2>""" + icon("gear", 22) + """ Settings — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "") + """
      {% if notice %}<div class="card" style="border-color:#2b6e46;color:#5ee89a;">""" + icon("check", 16) + """ {{ notice }}</div>{% endif %}

      <form method="POST" class="card">
        <label>""" + icon("gear", 14) + """ Prefix</label>
        <input name="prefix" value="{{ data['prefix'] }}">

        <h3 style="margin-top:22px;">""" + icon("mail", 18) + """ Welcome</h3>
        <label><input type="checkbox" name="welcome_enabled" {{ 'checked' if data['welcome']['enabled'] else '' }} style="width:auto;display:inline;"> Enabled</label>
        <label style="margin-top:10px;">Channel</label>
        <select name="welcome_channel">{{ welcome_chan_opts|safe }}</select>
        <label style="margin-top:10px;">Rich embed template (from Templates tab, supports GIF)</label>
        <p style="color:var(--muted);font-size:12px;margin:4px 0 0;">Configured on the <a href="/dashboard/{{ guild.id }}/embeds" style="color:var(--accent2);">Templates tab</a> — set a template's type to "Welcome" and link it there.</p>
        <label style="margin-top:10px;">Plain-text fallback message ({user}, {server} supported)</label>
        <textarea name="welcome_message" id="welcomeBox">{{ data['welcome']['message'] }}</textarea>
        <label style="margin-top:10px;"><input type="checkbox" name="welcome_dm" {{ 'checked' if data['welcome'].get('dm_enabled') else '' }} style="width:auto;display:inline;"> Also DM the new member</label>

        <h3 style="margin-top:22px;">""" + icon("mail", 18) + """ Leave</h3>
        <label><input type="checkbox" name="leave_enabled" {{ 'checked' if data['leave']['enabled'] else '' }} style="width:auto;display:inline;"> Enabled</label>
        <label style="margin-top:10px;">Channel</label>
        <select name="leave_channel">{{ leave_chan_opts|safe }}</select>
        <label style="margin-top:10px;">Plain-text fallback message</label>
        <textarea name="leave_message" id="leaveBox">{{ data['leave']['message'] }}</textarea>

        <h3 style="margin-top:22px;">""" + icon("gift", 18) + """ Server Boost</h3>
        <label><input type="checkbox" name="boost_enabled" {{ 'checked' if data['boost']['enabled'] else '' }} style="width:auto;display:inline;"> Enabled</label>
        <label style="margin-top:10px;">Channel</label>
        <select name="boost_channel">{{ boost_chan_opts|safe }}</select>

        <h3 style="margin-top:22px;">""" + icon("chart", 18) + """ Level Up</h3>
        <label><input type="checkbox" name="levelup_enabled" {{ 'checked' if data['levelup']['enabled'] else '' }} style="width:auto;display:inline;"> Post level-up announcements in a fixed channel (otherwise posts in the channel the user leveled up in)</label>
        <label style="margin-top:10px;">Channel</label>
        <select name="levelup_channel">{{ levelup_chan_opts|safe }}</select>
        <p style="color:var(--muted);font-size:12px;">Set level role rewards from the Templates tab is not needed — use the Auto-Mod tab's companion "Level Roles" card below.</p>

        <label style="margin-top:14px;">
          <input type="checkbox" name="automod" {{ 'checked' if data['automod']['enabled'] else '' }} style="width:auto;display:inline;">
          """ + icon("shield", 14) + """ Auto-Moderation Enabled (fine-tune on the Auto-Mod tab)
        </label>
        <button class="btn btn-primary" type="submit" style="margin-top:16px;">""" + icon("check", 16) + """ Save Settings</button>
      </form>

      <div class="card">
        <h3>""" + icon("chart", 18) + """ Level-Up Role Rewards</h3>
        <form method="POST" action="/dashboard/{{ guild.id }}/levelrewards">
          <div class="grid">
            <div><label>Level</label><input name="level" type="number" min="1" value="5"></div>
            <div><label>Role</label><select name="role_id">{% for r in roles %}<option value="{{ r.id }}">{{ r.name }}</option>{% endfor %}</select></div>
          </div>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("check", 16) + """ Add Reward</button>
        </form>
        <div class="chip-list">
        {% for lvl, rid in data.get('levelup',{}).get('role_rewards',{}).items() %}
          <span class="chip">Level {{ lvl }} → {{ role_name(rid) }}
            <form method="POST" action="/dashboard/{{ guild.id }}/levelrewards/delete" style="display:inline;"><input type="hidden" name="level" value="{{ lvl }}"><button type="submit">×</button></form>
          </span>
        {% endfor %}
        </div>
      </div>

      <div class="card">
        <h3>""" + icon("role", 18) + """ Server Roles</h3>
        <div>{% for r in roles %}<span class="role-pill">""" + icon("role", 14) + """ {{ r.name }}</span>{% endfor %}</div>
      </div>

      <div class="card">
        <h3>""" + icon("power", 18) + """ Live Actions (run instantly on Discord, same as a bot command)</h3>

        <form method="POST" action="/dashboard/{{ guild.id }}/action/purge" style="margin-bottom:18px;">
          <label>""" + icon("trash", 14) + """ Purge messages — channel + amount</label>
          <select name="channel_id">{% for c in text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
          <input name="amount" type="number" value="10" min="1" max="100" style="margin-top:8px;">
          <button class="btn btn-danger" type="submit" style="margin-top:10px;">""" + icon("trash", 16) + """ Purge Now</button>
        </form>

        <form method="POST" action="/dashboard/{{ guild.id }}/action/announce">
          <label>""" + icon("megaphone", 14) + """ Send announcement — channel + message</label>
          <select name="channel_id">{% for c in text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
          <textarea name="message" id="announceBox" placeholder="Message to send (@role, @user, #channel supported)" style="margin-top:8px;"></textarea>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("megaphone", 16) + """ Send Now</button>
        </form>
      </div>

      <p><a href="/dashboard" style="color:var(--accent2);">← Back to servers</a></p>
    </div>
    """ + MENTION_PICKER_JS + """
    <script>
    fetch('/dashboard/""" + str(guild_id) + """/mentionables').then(r=>r.json()).then(d=>{ window.__mentionData = d; }).catch(()=>{});
    attachMentionPicker('welcomeBox');
    attachMentionPicker('leaveBox');
    attachMentionPicker('announceBox');
    </script>
    """
    role_map = {str(r.id): r.name for r in guild.roles}
    return render(
        f"Settings - {guild.name}", body, guild=guild, data=data, roles=roles, text_channels=text_channels,
        notice=notice,
        welcome_chan_opts=chan_options(data["welcome"].get("channel_id")),
        leave_chan_opts=chan_options(data["leave"].get("channel_id")),
        boost_chan_opts=chan_options(data["boost"].get("channel_id")),
        levelup_chan_opts=chan_options(data["levelup"].get("channel_id")),
        role_name=lambda rid: role_map.get(str(rid), f"role {rid}"),
    )


@app.route("/dashboard/<guild_id>/levelrewards", methods=["POST"])
def levelrewards_add(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    level = request.form.get("level")
    role_id = request.form.get("role_id")
    if level and role_id:
        data["levelup"].setdefault("role_rewards", {})[level] = role_id
        save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}")


@app.route("/dashboard/<guild_id>/levelrewards/delete", methods=["POST"])
def levelrewards_delete(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    level = request.form.get("level")
    data["levelup"].get("role_rewards", {}).pop(level, None)
    save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}")


# ---------------- Auto-Mod tab ----------------

@app.route("/dashboard/<guild_id>/automod", methods=["GET", "POST"])
def automod_page(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    am = data["automod"]
    notice = None
    if request.method == "POST":
        am["enabled"] = request.form.get("enabled") == "on"
        am["block_invites"] = request.form.get("block_invites") == "on"
        am["block_mass_mentions"] = request.form.get("block_mass_mentions") == "on"
        am["mass_mention_limit"] = int(request.form.get("mass_mention_limit") or 5)
        am["block_spam"] = request.form.get("block_spam") == "on"
        am["spam_message_limit"] = int(request.form.get("spam_message_limit") or 5)
        am["spam_window_seconds"] = int(request.form.get("spam_window_seconds") or 7)
        am["block_caps"] = request.form.get("block_caps") == "on"
        am["caps_percent_limit"] = int(request.form.get("caps_percent_limit") or 70)
        am["strike_action_at"] = int(request.form.get("strike_action_at") or 3)
        am["strike_action"] = request.form.get("strike_action") or "mute"
        am["strike_mute_minutes"] = int(request.form.get("strike_mute_minutes") or 30)
        words_raw = request.form.get("banned_words", "")
        am["banned_words"] = [w.strip().lower() for w in words_raw.split(",") if w.strip()]
        domains_raw = request.form.get("whitelisted_domains", "")
        am["whitelisted_domains"] = [d.strip().lower() for d in domains_raw.split(",") if d.strip()]
        save_guild_data(guild_id, data)
        notice = "Auto-mod settings saved."

    body = """
    <div class="container">
      <h2>""" + icon("shield", 22) + """ Auto-Mod — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/automod") + """
      {% if notice %}<div class="card" style="border-color:#2b6e46;color:#5ee89a;">""" + icon("check", 16) + """ {{ notice }}</div>{% endif %}
      <form method="POST" class="card">
        <label><input type="checkbox" name="enabled" {{ 'checked' if am['enabled'] else '' }} style="width:auto;display:inline;"> Auto-Moderation Enabled</label>

        <label style="margin-top:14px;">Banned words (comma separated)</label>
        <textarea name="banned_words">{{ am.get('banned_words',[])|join(', ') }}</textarea>

        <label style="margin-top:14px;"><input type="checkbox" name="block_invites" {{ 'checked' if am.get('block_invites') else '' }} style="width:auto;display:inline;"> Block Discord invite links</label>
        <label style="margin-top:8px;">Whitelisted domains (comma separated, e.g. discord.gg/yourserver)</label>
        <input name="whitelisted_domains" value="{{ am.get('whitelisted_domains',[])|join(', ') }}">

        <label style="margin-top:14px;"><input type="checkbox" name="block_mass_mentions" {{ 'checked' if am.get('block_mass_mentions') else '' }} style="width:auto;display:inline;"> Block mass mentions</label>
        <label style="margin-top:8px;">Mass mention limit</label>
        <input name="mass_mention_limit" type="number" value="{{ am.get('mass_mention_limit',5) }}">

        <label style="margin-top:14px;"><input type="checkbox" name="block_spam" {{ 'checked' if am.get('block_spam') else '' }} style="width:auto;display:inline;"> Block spam (rapid repeated messages)</label>
        <div class="grid">
          <div><label>Messages</label><input name="spam_message_limit" type="number" value="{{ am.get('spam_message_limit',5) }}"></div>
          <div><label>Within seconds</label><input name="spam_window_seconds" type="number" value="{{ am.get('spam_window_seconds',7) }}"></div>
        </div>

        <label style="margin-top:14px;"><input type="checkbox" name="block_caps" {{ 'checked' if am.get('block_caps') else '' }} style="width:auto;display:inline;"> Block excessive CAPS LOCK</label>
        <label style="margin-top:8px;">Caps % threshold</label>
        <input name="caps_percent_limit" type="number" value="{{ am.get('caps_percent_limit',70) }}">

        <h3 style="margin-top:22px;">""" + icon("bolt", 18) + """ Strike System</h3>
        <div class="grid">
          <div><label>Strikes before action</label><input name="strike_action_at" type="number" value="{{ am.get('strike_action_at',3) }}"></div>
          <div><label>Action</label>
            <select name="strike_action">
              <option value="mute" {{ 'selected' if am.get('strike_action')=='mute' else '' }}>Mute (timeout)</option>
              <option value="kick" {{ 'selected' if am.get('strike_action')=='kick' else '' }}>Kick</option>
              <option value="ban" {{ 'selected' if am.get('strike_action')=='ban' else '' }}>Ban</option>
            </select>
          </div>
          <div><label>Mute minutes (if mute)</label><input name="strike_mute_minutes" type="number" value="{{ am.get('strike_mute_minutes',30) }}"></div>
        </div>

        <button class="btn btn-primary" type="submit" style="margin-top:16px;">""" + icon("check", 16) + """ Save Auto-Mod Settings</button>
      </form>
      <p><a href="/dashboard/{{ guild.id }}" style="color:var(--accent2);">← Back to overview</a></p>
    </div>
    """
    return render(f"Auto-Mod - {guild.name}", body, guild=guild, am=am, notice=notice)


# ---------------- shared helpers for template builder ----------------

@app.route("/dashboard/<guild_id>/mentionables")
def mentionables(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "members": [{"id": str(m.id), "name": m.display_name} for m in guild.members if not m.bot][:500],
        "roles": [{"id": str(r.id), "name": r.name} for r in guild.roles if r.name != "@everyone"],
        "channels": [{"id": str(c.id), "name": c.name} for c in guild.text_channels],
    })


MENTION_PICKER_JS = """
<script>
function attachMentionPicker(textareaId){
  const ta = document.getElementById(textareaId);
  if(!ta) return;
  let box = document.createElement('div');
  box.style.cssText = 'position:absolute;background:#191333;border:1px solid #2a2350;border-radius:10px;max-height:200px;overflow:auto;z-index:99;display:none;min-width:220px;box-shadow:0 10px 30px rgba(0,0,0,.5);';
  document.body.appendChild(box);
  let triggerStart = -1, triggerChar = '';
  function hide(){ box.style.display='none'; }
  function show(items, insertFn){
    box.innerHTML='';
    if(!items.length){ hide(); return; }
    items.slice(0,25).forEach(it=>{
      const row = document.createElement('div');
      row.textContent = it.label;
      row.style.cssText='padding:9px 12px;cursor:pointer;font-size:14px;';
      row.onmouseenter=()=>row.style.background='#2a2350';
      row.onmouseleave=()=>row.style.background='transparent';
      row.onmousedown=(e)=>{ e.preventDefault(); insertFn(it); hide(); };
      box.appendChild(row);
    });
    const rect = ta.getBoundingClientRect();
    box.style.left = (rect.left + window.scrollX) + 'px';
    box.style.top = (rect.bottom + window.scrollY + 4) + 'px';
    box.style.display='block';
  }
  ta.addEventListener('input', function(){
    const pos = ta.selectionStart;
    const text = ta.value.slice(0, pos);
    const m = text.match(/([@#])([a-zA-Z0-9_-]*)$/);
    if(!m){ hide(); return; }
    triggerChar = m[1];
    triggerStart = pos - m[0].length;
    const query = m[2].toLowerCase();
    const data = window.__mentionData || {members:[],roles:[],channels:[]};
    let items = [];
    if(triggerChar === '#'){
      items = data.channels.filter(c=>c.name.toLowerCase().includes(query)).map(c=>({label:'#'+c.name, insert:'<#'+c.id+'>'}));
    } else {
      items = data.roles.filter(r=>r.name.toLowerCase().includes(query)).map(r=>({label:'@'+r.name+' (role)', insert:'<@&'+r.id+'>'}))
        .concat(data.members.filter(u=>u.name.toLowerCase().includes(query)).map(u=>({label:'@'+u.name, insert:'<@'+u.id+'>'})));
    }
    show(items, (it)=>{
      const before = ta.value.slice(0, triggerStart);
      const after = ta.value.slice(pos);
      ta.value = before + it.insert + ' ' + after;
      ta.focus();
      const newPos = (before + it.insert + ' ').length;
      ta.setSelectionRange(newPos, newPos);
    });
  });
  ta.addEventListener('blur', ()=> setTimeout(hide, 150));
}
</script>
"""


@app.route("/dashboard/<guild_id>/action/purge", methods=["POST"])
def action_purge(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    channel_id = int(request.form.get("channel_id"))
    amount = min(int(request.form.get("amount", 10)), 100)
    channel = guild.get_channel(channel_id)
    try:
        run_on_bot(channel.purge(limit=amount))
    except Exception as e:
        return f"Action failed: {e}", 500
    return redirect(f"/dashboard/{guild_id}")


@app.route("/dashboard/<guild_id>/action/announce", methods=["POST"])
def action_announce(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    channel_id = int(request.form.get("channel_id"))
    message = request.form.get("message", "").strip()
    channel = guild.get_channel(channel_id)
    if channel and message:
        try:
            run_on_bot(channel.send(message))
        except Exception as e:
            return f"Action failed: {e}", 500
    return redirect(f"/dashboard/{guild_id}")


# ---------------- universal template builder ----------------

def _embed_form_body(guild, template, text_channels, name_locked=False, action_url=None):
    return """
    <div class="container">
      <h2>""" + icon("bolt", 22) + """ Template Builder — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/embeds") + """
      <form method="POST" action=\"""" + (action_url or "") + """\" class="card" id="embedForm">
        <label>Template name</label>
        <input name="name" value="{{ template.get('name','') }}" """ + ("readonly" if name_locked else "") + """ required>

        <label style="margin-top:14px;">Template type — determines where this can be used (Welcome, Leave, Boost, Level Up, Ticket, Auto-Responder, or a free-standing Custom/Announcement embed)</label>
        <select name="type">
        {% for key, label in template_types.items() %}
          <option value="{{ key }}" {{ 'selected' if template.get('type','custom')==key else '' }}>{{ label }}</option>
        {% endfor %}
        </select>

        <label style="margin-top:14px;">Author name</label>
        <input name="author_name" value="{{ template.get('author_name','') }}">
        <label style="margin-top:10px;">Author icon URL</label>
        <input name="author_icon" value="{{ template.get('author_icon','') }}">

        <label style="margin-top:14px;">Title</label>
        <input name="title" value="{{ template.get('title','') }}">

        <label style="margin-top:14px;">Description (type @ for user/role, # for channel — suggestions appear. Placeholders: {user} {user.mention} {user.name} {server} {membercount} {level})</label>
        <textarea name="description" id="descBox" rows="5">{{ template.get('description','') }}</textarea>

        <label style="margin-top:14px;">Color (hex)</label>
        <input name="color" type="color" value="#{{ (template.get('color') or '7C3AED') }}" style="height:46px;padding:4px;">

        <label style="margin-top:14px;">Image URL (banner / GIF — paste any .gif link, plays automatically in Discord)</label>
        <input name="image_url" id="imgUrl" value="{{ template.get('image_url','') }}">
        <img id="imgPreview" src="{{ template.get('image_url','') }}" style="max-width:100%;border-radius:10px;margin-top:8px;display:{{ 'block' if template.get('image_url') else 'none' }};" onerror="this.style.display='none'">

        <label style="margin-top:14px;">Thumbnail URL (also supports GIF)</label>
        <input name="thumbnail_url" id="thumbUrl" value="{{ template.get('thumbnail_url','') }}">
        <img id="thumbPreview" src="{{ template.get('thumbnail_url','') }}" style="max-width:80px;border-radius:8px;margin-top:8px;display:{{ 'block' if template.get('thumbnail_url') else 'none' }};" onerror="this.style.display='none'">

        <label style="margin-top:14px;">Footer text</label>
        <input name="footer_text" value="{{ template.get('footer_text','') }}">
        <label style="margin-top:10px;">Footer icon URL</label>
        <input name="footer_icon" value="{{ template.get('footer_icon','') }}">

        <label style="margin-top:14px;">""" + icon("chart", 14) + """ Fields</label>
        <div id="fieldsWrap"></div>
        <button type="button" class="btn btn-ghost" onclick="addField()" style="margin-top:8px;">+ Add Field</button>
        <input type="hidden" name="fields_json" id="fieldsJson">

        <label style="margin-top:14px;">""" + icon("bolt", 14) + """ Link Buttons (shown under the embed)</label>
        <div id="buttonsWrap"></div>
        <button type="button" class="btn btn-ghost" onclick="addButton()" style="margin-top:8px;">+ Add Button</button>
        <input type="hidden" name="buttons_json" id="buttonsJson">

        <button class="btn btn-primary" type="submit" style="margin-top:18px;">""" + icon("check", 16) + """ Save Template</button>
      </form>

      <div class="card">
        <h3>""" + icon("power", 18) + """ Send this template now</h3>
        <form method="POST" action="/dashboard/{{ guild.id }}/embeds/{{ template.get('name','') }}/send">
          <select name="channel_id">{% for c in text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("megaphone", 16) + """ Send Now</button>
        </form>
        <p style="color:var(--muted);font-size:12px;margin-top:10px;">To use this template automatically for Welcome/Leave/Boost/Level-Up, set its type above and it will appear as an available template on the Overview tab; for Ticket Welcome pick it in the Tickets tab; for Auto-Responder pick it in the Auto-Responders tab.</p>
      </div>

      <p><a href="/dashboard/{{ guild.id }}/embeds" style="color:var(--accent2);">← Back to templates</a></p>
    </div>
    """ + MENTION_PICKER_JS + """
    <script>
    window.__mentionData = {members:[],roles:[],channels:[]};
    fetch('/dashboard/""" + str(guild.id) + """/mentionables').then(r=>r.json()).then(d=>{ window.__mentionData = d; });
    attachMentionPicker('descBox');
    document.getElementById('imgUrl').addEventListener('input', function(){
      const p = document.getElementById('imgPreview'); p.src = this.value; p.style.display = this.value ? 'block' : 'none';
    });
    document.getElementById('thumbUrl').addEventListener('input', function(){
      const p = document.getElementById('thumbPreview'); p.src = this.value; p.style.display = this.value ? 'block' : 'none';
    });
    let fieldCount = 0;
    function addField(f){
      f = f || {name:'',value:'',inline:false};
      const wrap = document.getElementById('fieldsWrap');
      const row = document.createElement('div');
      row.style.cssText = 'border:1px solid #2a2350;border-radius:10px;padding:10px;margin-top:8px;';
      row.innerHTML = '<input placeholder="Field name" class="f-name" value="'+(f.name||'').replace(/"/g,'&quot;')+'">' +
        '<input placeholder="Field value" class="f-value" style="margin-top:6px;" value="'+(f.value||'').replace(/"/g,'&quot;')+'">' +
        '<label style="margin-top:6px;"><input type="checkbox" class="f-inline" '+(f.inline?'checked':'')+' style="width:auto;display:inline;"> Inline</label>' +
        '<button type="button" class="btn btn-danger btn-sm" style="margin-top:6px;" onclick="this.parentElement.remove()">Remove</button>';
      wrap.appendChild(row);
    }
    function addButton(b){
      b = b || {label:'',url:''};
      const wrap = document.getElementById('buttonsWrap');
      const row = document.createElement('div');
      row.style.cssText = 'border:1px solid #2a2350;border-radius:10px;padding:10px;margin-top:8px;';
      row.innerHTML = '<input placeholder="Button label" class="b-label" value="'+(b.label||'').replace(/"/g,'&quot;')+'">' +
        '<input placeholder="https://..." class="b-url" style="margin-top:6px;" value="'+(b.url||'').replace(/"/g,'&quot;')+'">' +
        '<button type="button" class="btn btn-danger btn-sm" style="margin-top:6px;" onclick="this.parentElement.remove()">Remove</button>';
      wrap.appendChild(row);
    }
    (""" + _json.dumps(template.get("fields", []) or []) + """).forEach(addField);
    (""" + _json.dumps(template.get("buttons", []) or []) + """).forEach(addButton);
    document.getElementById('embedForm').addEventListener('submit', function(){
      const rows = document.querySelectorAll('#fieldsWrap > div');
      const fields = Array.from(rows).map(r => ({
        name: r.querySelector('.f-name').value,
        value: r.querySelector('.f-value').value,
        inline: r.querySelector('.f-inline').checked,
      }));
      document.getElementById('fieldsJson').value = JSON.stringify(fields);
      const brows = document.querySelectorAll('#buttonsWrap > div');
      const buttons = Array.from(brows).map(r => ({
        label: r.querySelector('.b-label').value,
        url: r.querySelector('.b-url').value,
      }));
      document.getElementById('buttonsJson').value = JSON.stringify(buttons);
    });
    </script>
    """


@app.route("/dashboard/<guild_id>/embeds")
def embed_list(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    templates = data.get("embed_templates", {})
    body = """
    <div class="container">
      <h2>""" + icon("bolt", 22) + """ Templates — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/embeds") + """
      <div class="card">
        <p style="color:var(--muted);font-size:13px;">One builder for every automation: Welcome, Leave, Boost, Level-Up, Ticket, Auto-Responder and standalone announcements. Every template supports GIF images.</p>
        <a class="btn btn-primary" href="/dashboard/{{ guild.id }}/embeds/new">+ New Template</a>
      </div>
      <div class="grid">
      {% for name, tpl in templates.items() %}
        <div class="card">
          <b>{{ name }}</b> <span class="badge badge-on" style="margin-left:6px;">{{ type_labels.get(tpl.get('type','custom'), 'Custom') }}</span>
          {% if tpl.get('image_url') %}<img src="{{ tpl['image_url'] }}" style="max-width:100%;border-radius:8px;margin:8px 0;" onerror="this.style.display='none'">{% endif %}
          <p style="color:var(--muted);font-size:13px;">{{ (tpl.get('description') or '')[:80] }}</p>
          <a class="btn btn-ghost btn-sm" href="/dashboard/{{ guild.id }}/embeds/{{ name }}/edit">""" + icon("gear", 14) + """ Edit</a>
          <form method="POST" action="/dashboard/{{ guild.id }}/embeds/{{ name }}/link" style="display:inline;">
            <button class="btn btn-ghost btn-sm" type="submit">""" + icon("check", 14) + """ Use as {{ type_labels.get(tpl.get('type','custom'),'Custom') }}</button>
          </form>
          <form method="POST" action="/dashboard/{{ guild.id }}/embeds/{{ name }}/delete" style="display:inline;" onsubmit="return confirm('Delete this template?');">
            <button class="btn btn-danger btn-sm" type="submit">""" + icon("trash", 14) + """ Delete</button>
          </form>
        </div>
      {% else %}
        <p>No templates yet — create one for welcome, leave, boost, level-up, tickets, auto-responders, or announcements.</p>
      {% endfor %}
      </div>
      <p><a href="/dashboard/{{ guild.id }}" style="color:var(--accent2);">← Back to server settings</a></p>
    </div>
    """
    return render(f"Templates - {guild.name}", body, guild=guild, templates=templates, type_labels=TEMPLATE_TYPES)


@app.route("/dashboard/<guild_id>/embeds/<name>/link", methods=["POST"])
def embed_link(guild_id, name):
    """Attach a template to its type's automation (welcome/leave/boost/levelup) in one click."""
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    templates = data.get("embed_templates", {})
    if name not in templates:
        return "Template not found", 404
    ttype = templates[name].get("type", "custom")
    if ttype in ("welcome", "leave", "boost", "levelup"):
        data[ttype]["template"] = name
        save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/embeds")


@app.route("/dashboard/<guild_id>/embeds/new", methods=["GET", "POST"])
def embed_new(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return "Template name required", 400
        tpl = _template_from_form(name)
        data.setdefault("embed_templates", {})[name] = tpl
        save_guild_data(guild_id, data)
        return redirect(f"/dashboard/{guild_id}/embeds/{name}/edit")
    text_channels = guild.text_channels[:25]
    body = _embed_form_body(guild, {}, text_channels, name_locked=False, action_url=f"/dashboard/{guild.id}/embeds/new")
    return render(f"New Template - {guild.name}", body, guild=guild, template={}, text_channels=text_channels, template_types=TEMPLATE_TYPES)


def _template_from_form(name):
    fields_raw = request.form.get("fields_json", "[]")
    buttons_raw = request.form.get("buttons_json", "[]")
    try:
        fields = _json.loads(fields_raw)
    except ValueError:
        fields = []
    try:
        buttons = _json.loads(buttons_raw)
    except ValueError:
        buttons = []
    return {
        "name": name,
        "type": request.form.get("type", "custom"),
        "author_name": request.form.get("author_name", ""),
        "author_icon": request.form.get("author_icon", ""),
        "title": request.form.get("title", ""),
        "description": request.form.get("description", ""),
        "color": request.form.get("color", "#7C3AED").lstrip("#"),
        "image_url": request.form.get("image_url", ""),
        "thumbnail_url": request.form.get("thumbnail_url", ""),
        "footer_text": request.form.get("footer_text", ""),
        "footer_icon": request.form.get("footer_icon", ""),
        "fields": [f for f in fields if f.get("name") or f.get("value")],
        "buttons": [b for b in buttons if b.get("url")],
    }


@app.route("/dashboard/<guild_id>/embeds/<name>/edit", methods=["GET", "POST"])
def embed_edit(guild_id, name):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    templates = data.get("embed_templates", {})
    if name not in templates:
        return "Template not found", 404
    if request.method == "POST":
        templates[name] = _template_from_form(name)
        save_guild_data(guild_id, data)
    text_channels = guild.text_channels[:25]
    body = _embed_form_body(guild, templates[name], text_channels, name_locked=True, action_url=f"/dashboard/{guild.id}/embeds/{name}/edit")
    return render(f"Edit {name} - {guild.name}", body, guild=guild, template=templates[name], text_channels=text_channels, template_types=TEMPLATE_TYPES)


@app.route("/dashboard/<guild_id>/embeds/<name>/delete", methods=["POST"])
def embed_delete(guild_id, name):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    data.get("embed_templates", {}).pop(name, None)
    save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/embeds")


@app.route("/dashboard/<guild_id>/embeds/<name>/send", methods=["POST"])
def embed_send(guild_id, name):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    templates = data.get("embed_templates", {})
    if name not in templates:
        return "Template not found", 404
    channel = guild.get_channel(int(request.form.get("channel_id")))
    if not channel:
        return "Channel not found", 400
    embed = build_embed_from_template(templates[name], guild=guild)
    try:
        run_on_bot(channel.send(embed=embed))
    except Exception as e:
        return f"Send failed: {e}", 500
    return redirect(f"/dashboard/{guild_id}/embeds/{name}/edit")


# ---------------- auto-responders ----------------

@app.route("/dashboard/<guild_id>/autoresponders", methods=["GET", "POST"])
def autoresponders_page(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    if request.method == "POST":
        trigger = request.form.get("trigger", "").strip()
        if trigger:
            data.setdefault("autoresponders", []).append({
                "trigger": trigger,
                "match": request.form.get("match", "contains"),
                "reply": request.form.get("reply", ""),
                "template": request.form.get("template") or None,
            })
            save_guild_data(guild_id, data)
        return redirect(f"/dashboard/{guild_id}/autoresponders")
    templates = {n: t for n, t in data.get("embed_templates", {}).items() if t.get("type") == "autoresponder"}
    body = """
    <div class="container">
      <h2>""" + icon("reply", 22) + """ Auto-Responders — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/autoresponders") + """
      <div class="card">
        <h3>""" + icon("bolt", 18) + """ New Auto-Responder</h3>
        <form method="POST">
          <label>Trigger keyword/phrase</label>
          <input name="trigger" placeholder="e.g. discord invite" required>
          <label style="margin-top:10px;">Match type</label>
          <select name="match">
            <option value="contains">Message contains trigger</option>
            <option value="exact">Message is exactly the trigger</option>
          </select>
          <label style="margin-top:10px;">Plain text reply (used if no template selected)</label>
          <textarea name="reply" placeholder="Reply text, supports {user} {server}"></textarea>
          <label style="margin-top:10px;">Or use a rich embed template (type = Auto-Responder)</label>
          <select name="template">
            <option value="">None</option>
            {% for n in templates.keys() %}<option value="{{ n }}">{{ n }}</option>{% endfor %}
          </select>
          <button class="btn btn-primary" type="submit" style="margin-top:12px;">""" + icon("check", 16) + """ Add</button>
        </form>
      </div>
      <div class="grid">
      {% for ar in autoresponders %}
        <div class="card">
          <b>{{ ar.trigger }}</b> <span class="badge badge-on">{{ ar.match }}</span>
          <p style="color:var(--muted);font-size:13px;">{{ ar.template and ('Template: ' + ar.template) or ar.reply }}</p>
          <form method="POST" action="/dashboard/{{ guild.id }}/autoresponders/{{ loop.index0 }}/delete">
            <button class="btn btn-danger btn-sm" type="submit">""" + icon("trash", 14) + """ Delete</button>
          </form>
        </div>
      {% else %}
        <p>No auto-responders yet.</p>
      {% endfor %}
      </div>
      <p><a href="/dashboard/{{ guild.id }}/embeds/new" style="color:var(--accent2);">+ Create an Auto-Responder embed template</a></p>
    </div>
    """
    return render(f"Auto-Responders - {guild.name}", body, guild=guild, autoresponders=data.get("autoresponders", []), templates=templates)


@app.route("/dashboard/<guild_id>/autoresponders/<int:idx>/delete", methods=["POST"])
def autoresponder_delete(guild_id, idx):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    ars = data.get("autoresponders", [])
    if 0 <= idx < len(ars):
        ars.pop(idx)
        save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/autoresponders")


# ---------------- role menus (button/select based) ----------------

@app.route("/dashboard/<guild_id>/rolemenus", methods=["GET", "POST"])
def rolemenus_page(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    if request.method == "POST":
        menu_id = request.form.get("menu_id", "").strip().lower().replace(" ", "-")
        if menu_id:
            data.setdefault("reaction_role_menus", {})[menu_id] = {
                "title": request.form.get("title", "Choose your roles"),
                "description": request.form.get("description", "Select from the menu below."),
                "placeholder": request.form.get("placeholder", "Choose your roles..."),
                "multi": request.form.get("multi") == "on",
                "options": data.get("reaction_role_menus", {}).get(menu_id, {}).get("options", []),
            }
            save_guild_data(guild_id, data)
        return redirect(f"/dashboard/{guild_id}/rolemenus")
    roles = sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
    body = """
    <div class="container">
      <h2>""" + icon("role", 22) + """ Role Menus — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/rolemenus") + """
      <div class="card">
        <h3>""" + icon("bolt", 18) + """ New Role Menu</h3>
        <form method="POST">
          <label>Menu ID (short, no spaces)</label>
          <input name="menu_id" placeholder="colors" required>
          <label style="margin-top:10px;">Title</label>
          <input name="title" value="Choose your roles">
          <label style="margin-top:10px;">Description</label>
          <textarea name="description">Select from the menu below.</textarea>
          <label style="margin-top:10px;">Placeholder text</label>
          <input name="placeholder" value="Choose your roles...">
          <label style="margin-top:10px;"><input type="checkbox" name="multi" checked style="width:auto;display:inline;"> Allow selecting multiple roles at once</label>
          <button class="btn btn-primary" type="submit" style="margin-top:12px;">""" + icon("check", 16) + """ Save Menu</button>
        </form>
      </div>
      <div class="grid">
      {% for mid, menu in menus.items() %}
        <div class="card">
          <b>{{ mid }}</b> — {{ menu.title }}
          <p style="color:var(--muted);font-size:13px;">{{ menu.options|length }} role option(s)</p>
          <a class="btn btn-ghost btn-sm" href="/dashboard/{{ guild.id }}/rolemenus/{{ mid }}">""" + icon("gear", 14) + """ Manage Options</a>
          <form method="POST" action="/dashboard/{{ guild.id }}/rolemenus/{{ mid }}/post" style="display:inline;">
            <select name="channel_id" style="display:inline-block;width:auto;">{% for c in guild.text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
            <button class="btn btn-primary btn-sm" type="submit">""" + icon("power", 14) + """ Post</button>
          </form>
          <form method="POST" action="/dashboard/{{ guild.id }}/rolemenus/{{ mid }}/delete" style="display:inline;">
            <button class="btn btn-danger btn-sm" type="submit">""" + icon("trash", 14) + """ Delete</button>
          </form>
        </div>
      {% else %}
        <p>No role menus yet — create one above, add role options, then post it in a channel with a live button/select menu (more reliable than emoji reactions).</p>
      {% endfor %}
      </div>
    </div>
    """
    return render(f"Role Menus - {guild.name}", body, guild=guild, menus=data.get("reaction_role_menus", {}))


@app.route("/dashboard/<guild_id>/rolemenus/<menu_id>", methods=["GET", "POST"])
def rolemenu_edit(guild_id, menu_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    menus = data.get("reaction_role_menus", {})
    if menu_id not in menus:
        return "Menu not found", 404
    if request.method == "POST":
        role_id = request.form.get("role_id")
        label = request.form.get("label") or "Role"
        if role_id:
            menus[menu_id].setdefault("options", []).append({"role_id": role_id, "label": label, "emoji": request.form.get("emoji") or None})
            save_guild_data(guild_id, data)
        return redirect(f"/dashboard/{guild_id}/rolemenus/{menu_id}")
    roles = sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
    menu = menus[menu_id]
    body = """
    <div class="container">
      <h2>""" + icon("role", 22) + """ Menu: {{ menu_id }} — {{ guild.name }}</h2>
      <div class="card">
        <h3>Add Role Option</h3>
        <form method="POST">
          <div class="grid">
            <div><label>Role</label><select name="role_id">{% for r in roles %}<option value="{{ r.id }}">{{ r.name }}</option>{% endfor %}</select></div>
            <div><label>Label</label><input name="label" placeholder="Display label"></div>
            <div><label>Emoji (optional)</label><input name="emoji" placeholder="🎨"></div>
          </div>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("check", 16) + """ Add Option</button>
        </form>
      </div>
      <div class="card">
        <h3>Current Options</h3>
        {% for opt in menu.get('options',[]) %}
        <div class="chip">{{ opt.emoji or '' }} {{ opt.label }} → {{ role_name(opt.role_id) }}
          <form method="POST" action="/dashboard/{{ guild.id }}/rolemenus/{{ menu_id }}/option/{{ loop.index0 }}/delete" style="display:inline;"><button type="submit">×</button></form>
        </div>
        {% else %}<p style="color:var(--muted);">No options yet.</p>{% endfor %}
      </div>
      <p><a href="/dashboard/{{ guild.id }}/rolemenus" style="color:var(--accent2);">← Back to role menus</a></p>
    </div>
    """
    role_map = {str(r.id): r.name for r in guild.roles}
    return render(f"Menu {menu_id}", body, guild=guild, menu=menu, menu_id=menu_id, roles=roles, role_name=lambda rid: role_map.get(str(rid), rid))


@app.route("/dashboard/<guild_id>/rolemenus/<menu_id>/option/<int:idx>/delete", methods=["POST"])
def rolemenu_option_delete(guild_id, menu_id, idx):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    menus = data.get("reaction_role_menus", {})
    if menu_id in menus and 0 <= idx < len(menus[menu_id].get("options", [])):
        menus[menu_id]["options"].pop(idx)
        save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/rolemenus/{menu_id}")


@app.route("/dashboard/<guild_id>/rolemenus/<menu_id>/delete", methods=["POST"])
def rolemenu_delete(guild_id, menu_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    data.get("reaction_role_menus", {}).pop(menu_id, None)
    save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/rolemenus")


@app.route("/dashboard/<guild_id>/rolemenus/<menu_id>/post", methods=["POST"])
def rolemenu_post(guild_id, menu_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    menu = data.get("reaction_role_menus", {}).get(menu_id)
    if not menu:
        return "Menu not found", 404
    channel = guild.get_channel(int(request.form.get("channel_id")))
    if not channel:
        return "Channel not found", 400
    from embeds import branded_embed as _be
    embed = _be(title=menu.get("title", "Choose your roles"), description=menu.get("description", ""))
    try:
        run_on_bot(channel.send(embed=embed, view=build_role_menu_view(guild.id, menu_id, menu)))
    except Exception as e:
        return f"Failed to post: {e}", 500
    return redirect(f"/dashboard/{guild_id}/rolemenus")


# ---------------- multi ticket panels ----------------

@app.route("/dashboard/<guild_id>/tickets", methods=["GET", "POST"])
def ticket_config(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    notice = None
    if request.method == "POST":
        t = data["tickets"]
        t["category_id"] = request.form.get("category_id") or None
        t["support_role_id"] = request.form.get("support_role_id") or None
        t["log_channel_id"] = request.form.get("log_channel_id") or None
        t["embed_template"] = request.form.get("embed_template") or None
        t["transcripts_enabled"] = request.form.get("transcripts_enabled") == "on"
        save_guild_data(guild_id, data)
        notice = "Ticket settings saved."

    categories = guild.categories
    roles = sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
    text_channels = guild.text_channels
    templates = {n: tpl for n, tpl in data.get("embed_templates", {}).items() if tpl.get("type") in ("ticket", "custom")}
    t = data["tickets"]
    body = """
    <div class="container">
      <h2>""" + icon("ticket", 22) + """ Tickets — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/tickets") + """
      {% if notice %}<div class="card" style="border-color:#2b6e46;color:#5ee89a;">""" + icon("check", 16) + """ {{ notice }}</div>{% endif %}

      <form method="POST" class="card">
        <h3>""" + icon("gear", 18) + """ Default Ticket Panel</h3>
        <label>Ticket category (new ticket channels go here)</label>
        <select name="category_id">
          <option value="">None</option>
          {% for c in categories %}<option value="{{ c.id }}" {{ 'selected' if t.get('category_id')==c.id|string else '' }}>{{ c.name }}</option>{% endfor %}
        </select>
        <label style="margin-top:14px;">Support role (auto-added to every ticket)</label>
        <select name="support_role_id">
          <option value="">None</option>
          {% for r in roles %}<option value="{{ r.id }}" {{ 'selected' if t.get('support_role_id')==r.id|string else '' }}>{{ r.name }}</option>{% endfor %}
        </select>
        <label style="margin-top:14px;">Log channel (ticket-closed notices + transcripts)</label>
        <select name="log_channel_id">
          <option value="">None</option>
          {% for c in text_channels %}<option value="{{ c.id }}" {{ 'selected' if t.get('log_channel_id')==c.id|string else '' }}>#{{ c.name }}</option>{% endfor %}
        </select>
        <label style="margin-top:14px;">Welcome embed template (shown inside each ticket)</label>
        <select name="embed_template">
          <option value="">Default</option>
          {% for name in templates.keys() %}<option value="{{ name }}" {{ 'selected' if t.get('embed_template')==name else '' }}>{{ name }}</option>{% endfor %}
        </select>
        <label style="margin-top:14px;"><input type="checkbox" name="transcripts_enabled" {{ 'checked' if t.get('transcripts_enabled',True) else '' }} style="width:auto;display:inline;"> Save a transcript to the log channel when a ticket closes</label>
        <button class="btn btn-primary" type="submit" style="margin-top:16px;">""" + icon("check", 16) + """ Save Settings</button>
      </form>

      <div class="card">
        <h3>""" + icon("power", 18) + """ Post the default ticket panel</h3>
        <p style="color:var(--muted);font-size:13px;">Posts a message with a live "Open Ticket" button that keeps working forever (even after bot restarts).</p>
        <form method="POST" action="/dashboard/{{ guild.id }}/tickets/post">
          <select name="channel_id">{% for c in text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("ticket", 16) + """ Post Panel Now</button>
        </form>
      </div>

      <div class="card">
        <h3>""" + icon("ticket", 18) + """ Extra Ticket Panels (Support / Report / Partnership, etc.)</h3>
        <form method="POST" action="/dashboard/{{ guild.id }}/tickets/panels/new">
          <div class="grid">
            <div><label>Panel key (no spaces)</label><input name="panel_key" placeholder="report" required></div>
            <div><label>Button label</label><input name="button_label" placeholder="Report a user"></div>
            <div><label>Category</label><select name="category_id"><option value="">None</option>{% for c in categories %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}</select></div>
            <div><label>Support role</label><select name="support_role_id"><option value="">None</option>{% for r in roles %}<option value="{{ r.id }}">{{ r.name }}</option>{% endfor %}</select></div>
          </div>
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("check", 16) + """ Create Panel</button>
        </form>
        {% for key, panel in ticket_panels.items() %}
        <div class="card" style="margin-top:12px;">
          <b>{{ key }}</b> — {{ panel.button_label }}
          <form method="POST" action="/dashboard/{{ guild.id }}/tickets/panels/{{ key }}/post" style="display:inline;">
            <select name="channel_id" style="display:inline-block;width:auto;">{% for c in text_channels %}<option value="{{ c.id }}">#{{ c.name }}</option>{% endfor %}</select>
            <button class="btn btn-primary btn-sm" type="submit">""" + icon("power", 14) + """ Post</button>
          </form>
          <form method="POST" action="/dashboard/{{ guild.id }}/tickets/panels/{{ key }}/delete" style="display:inline;">
            <button class="btn btn-danger btn-sm" type="submit">""" + icon("trash", 14) + """ Delete</button>
          </form>
        </div>
        {% endfor %}
      </div>

      <p><a href="/dashboard/{{ guild.id }}" style="color:var(--accent2);">← Back to server settings</a></p>
    </div>
    """
    return render(f"Tickets - {guild.name}", body, guild=guild, categories=categories, roles=roles,
                   text_channels=text_channels, templates=templates, t=t, notice=notice,
                   ticket_panels=data.get("ticket_panels", {}))


@app.route("/dashboard/<guild_id>/tickets/post", methods=["POST"])
def ticket_post_panel(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    channel = guild.get_channel(int(request.form.get("channel_id")))
    if not channel:
        return "Channel not found", 400
    tpl_name = data["tickets"].get("embed_template")
    templates = data.get("embed_templates", {})
    if tpl_name and tpl_name in templates:
        embed = build_embed_from_template(templates[tpl_name], guild=guild)
    else:
        from embeds import branded_embed as _be
        embed = _be(title="Support Tickets", description="Click the button below to open a private support ticket.")
    try:
        message = run_on_bot(post_ticket_panel(guild, channel, embed))
        data["tickets"]["panel_channel_id"] = str(channel.id)
        data["tickets"]["panel_message_id"] = str(message.id)
        save_guild_data(guild_id, data)
    except Exception as e:
        return f"Failed to post panel: {e}", 500
    return redirect(f"/dashboard/{guild_id}/tickets")


@app.route("/dashboard/<guild_id>/tickets/panels/new", methods=["POST"])
def ticket_panel_new(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    key = request.form.get("panel_key", "").strip().lower().replace(" ", "-")
    if key:
        data.setdefault("ticket_panels", {})[key] = {
            "name": key,
            "button_label": request.form.get("button_label") or "Open Ticket",
            "category_id": request.form.get("category_id") or None,
            "support_role_id": request.form.get("support_role_id") or None,
            "embed_template": None,
        }
        save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/tickets")


@app.route("/dashboard/<guild_id>/tickets/panels/<key>/delete", methods=["POST"])
def ticket_panel_delete(guild_id, key):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    data.get("ticket_panels", {}).pop(key, None)
    save_guild_data(guild_id, data)
    return redirect(f"/dashboard/{guild_id}/tickets")


@app.route("/dashboard/<guild_id>/tickets/panels/<key>/post", methods=["POST"])
def ticket_panel_post(guild_id, key):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    panel = data.get("ticket_panels", {}).get(key)
    if not panel:
        return "Panel not found", 404
    channel = guild.get_channel(int(request.form.get("channel_id")))
    if not channel:
        return "Channel not found", 400
    from embeds import branded_embed as _be
    embed = _be(title=panel.get("name", "Support"), description="Click the button below to open a ticket.")
    try:
        run_on_bot(post_ticket_panel(guild, channel, embed, panel_key=key, label=panel.get("button_label", "Open Ticket")))
    except Exception as e:
        return f"Failed to post: {e}", 500
    return redirect(f"/dashboard/{guild_id}/tickets")


# ---------------- command toggles ----------------

@app.route("/dashboard/<guild_id>/commands", methods=["GET", "POST"])
def commands_toggle_page(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    if request.method == "POST":
        enabled_list = request.form.getlist("enabled_cmd")
        all_cmds = [c for _, v in COMMANDS_LIST.items() for c in v[1]]
        data["disabled_commands"] = [c for c in all_cmds if c not in enabled_list]
        save_guild_data(guild_id, data)
        return redirect(f"/dashboard/{guild_id}/commands")
    disabled = set(data.get("disabled_commands", []))
    body = """
    <div class="container">
      <h2>""" + icon("commands", 22) + """ Command Toggles — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/commands") + """
      <form method="POST" class="card">
        <p style="color:var(--muted);font-size:13px;">Uncheck any command to disable it on this server (works for both prefix and slash usage).</p>
        {% for cat, cdata in commands.items() %}
        <h3 style="margin-top:18px;">{{ icon(cdata[0],16)|safe }} {{ cat }}</h3>
        <div class="grid">
        {% for c in cdata[1] %}
          <label><input type="checkbox" name="enabled_cmd" value="{{ c }}" {{ '' if c in disabled else 'checked' }} style="width:auto;display:inline;"> {{ c }}</label>
        {% endfor %}
        </div>
        {% endfor %}
        <button class="btn btn-primary" type="submit" style="margin-top:16px;">""" + icon("check", 16) + """ Save</button>
      </form>
    </div>
    """
    return render(f"Command Toggles - {guild.name}", body, guild=guild, commands=COMMANDS_LIST, disabled=disabled)


# ---------------- analytics ----------------

@app.route("/dashboard/<guild_id>/analytics")
def analytics_page(guild_id):
    guild, member = _require_guild_manager(guild_id)
    if not guild:
        return redirect("/auth/login")
    data = get_guild_data(guild_id)
    stats = data.get("stats_daily", {})
    days = sorted(stats.keys())[-14:]
    joins = [stats.get(d, {}).get("joins", 0) for d in days]
    leaves = [stats.get(d, {}).get("leaves", 0) for d in days]
    cmds = [stats.get(d, {}).get("commands", 0) for d in days]
    body = """
    <div class="container">
      <h2>""" + icon("chart", 22) + """ Analytics — {{ guild.name }}</h2>
      """ + _tabs_html(guild.id, "/analytics") + """
      <div class="card">
        <h3>Last 14 days</h3>
        <canvas id="chart" height="140"></canvas>
      </div>
      <div class="stats">
        <div class="stat"><b>{{ joins|sum }}</b><span class="label">Joins</span></div>
        <div class="stat"><b>{{ leaves|sum }}</b><span class="label">Leaves</span></div>
        <div class="stat"><b>{{ cmds|sum }}</b><span class="label">Commands Used</span></div>
      </div>
    </div>
    <script>
    const days = """ + _json.dumps(days) + """;
    const joins = """ + _json.dumps(joins) + """;
    const leaves = """ + _json.dumps(leaves) + """;
    const cmds = """ + _json.dumps(cmds) + """;
    const canvas = document.getElementById('chart');
    const ctx = canvas.getContext('2d');
    function draw(){
      const w = canvas.clientWidth; canvas.width = w; canvas.height = 200;
      ctx.clearRect(0,0,w,200);
      const max = Math.max(1, ...joins, ...leaves, ...cmds);
      const stepX = w / Math.max(days.length,1);
      function line(data, color){
        ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 2;
        data.forEach((v,i)=>{
          const x = i*stepX + stepX/2, y = 190 - (v/max)*170;
          if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        });
        ctx.stroke();
      }
      line(joins, '#5ee89a'); line(leaves, '#f28c8c'); line(cmds, '#a78bfa');
    }
    draw(); window.addEventListener('resize', draw);
    </script>
    """
    return render(f"Analytics - {guild.name}", body, guild=guild, joins=joins, leaves=leaves, cmds=cmds)


# ---------------- owner panel ----------------

@app.route("/owner", methods=["GET", "POST"])
def owner_panel():
    user = session.get("user")
    if not user or str(user["id"]) not in config.OWNER_IDS:
        return "Forbidden", 403
    gdata = get_global_data()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "toggle_maintenance":
            gdata["maintenance"] = not gdata.get("maintenance", False)
        elif action == "add_blacklist":
            target = request.form.get("target_id")
            if target:
                gdata["blacklist_users"].append(target)
        save_global_data(gdata)
        gdata = get_global_data()

    bot_instance = app.config.get("BOT_INSTANCE")
    servers = len(bot_instance.guilds) if bot_instance and bot_instance.is_ready() else 0
    users_count = sum(g.member_count or 0 for g in bot_instance.guilds) if bot_instance and bot_instance.is_ready() else 0

    body = """
    <div class="container">
      <h2>""" + icon("shield", 22) + """ Owner Panel</h2>
      <div class="stats">
        <div class="stat">""" + icon("server", 20) + """<b>{{ servers }}</b><span class="label">Servers</span></div>
        <div class="stat">""" + icon("users", 20) + """<b>{{ users_count }}</b><span class="label">Users</span></div>
        <div class="stat">""" + icon("chart", 20) + """<b>{{ gdata['total_commands_used'] }}</b><span class="label">Commands Used</span></div>
      </div>
      <div class="card">
        <p>Maintenance Mode: <span class="badge {{ 'badge-on' if gdata['maintenance'] else 'badge-off' }}">{{ 'ON' if gdata['maintenance'] else 'OFF' }}</span></p>
        <form method="POST"><input type="hidden" name="action" value="toggle_maintenance">
          <button class="btn btn-primary" type="submit">""" + icon("power", 16) + """ Toggle Maintenance</button>
        </form>
      </div>
      <div class="card">
        <h3>""" + icon("users", 18) + """ Blacklist a User</h3>
        <form method="POST">
          <input type="hidden" name="action" value="add_blacklist">
          <input name="target_id" placeholder="Discord User ID">
          <button class="btn btn-primary" type="submit" style="margin-top:10px;">""" + icon("shield", 16) + """ Blacklist</button>
        </form>
        <p style="margin-top:10px;color:var(--muted);font-size:13px;">Current: {{ gdata['blacklist_users']|join(', ') }}</p>
      </div>
      <div class="card">
        <h3>""" + icon("chart", 18) + """ Recent Logs</h3>
        <pre style="white-space:pre-wrap;color:var(--muted);font-size:13px;">{{ gdata['logs'][-20:]|join('\\n') }}</pre>
      </div>
    </div>
    """
    return render("Owner Panel", body, gdata=gdata, servers=servers, users_count=users_count)


# ---------------- auth (Discord OAuth2) ----------------

@app.route("/auth/login")
def auth_login():
    url = (
        f"{config.DISCORD_API}/oauth2/authorize?client_id={config.CLIENT_ID}"
        f"&redirect_uri={config.REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    )
    return redirect(url)


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return redirect("/dashboard")
    data = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post(f"{config.DISCORD_API}/oauth2/token", data=data, headers=headers, timeout=10)
    if token_resp.status_code != 200:
        return "Discord login failed. Check CLIENT_ID / CLIENT_SECRET / REDIRECT_URI.", 400
    access_token = token_resp.json().get("access_token")
    user_resp = requests.get(f"{config.DISCORD_API}/users/@me", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    user = user_resp.json()
    session["user"] = {"id": user.get("id"), "username": user.get("username")}
    return redirect("/dashboard")


@app.route("/auth/logout")
def auth_logout():
    session.pop("user", None)
    return redirect("/")


# ---------------- json api ----------------

@app.route("/api/stats")
def api_stats():
    bot_instance = app.config.get("BOT_INSTANCE")
    ready = bool(bot_instance and bot_instance.is_ready())
    return jsonify({
        "servers": len(bot_instance.guilds) if ready else 0,
        "users": sum(g.member_count or 0 for g in bot_instance.guilds) if ready else 0,
        "commands": sum(len(v[1]) for v in COMMANDS_LIST.values()),
        "online": ready,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})
