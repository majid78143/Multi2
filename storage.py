import json
import os
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Unified template shape (used for welcome / leave / boost / levelup / ticket /
# autoresponder / raw "custom" templates). Every template type reuses this
# structure so ONE builder UI + ONE embed renderer works for all of them.
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATE = {
    "name": "",
    "type": "custom",  # welcome | leave | boost | levelup | ticket | autoresponder | custom
    "enabled": False,
    "channel_id": None,
    "dm_enabled": False,
    "plain_text": "",       # optional plain text sent alongside the embed
    "author_name": "",
    "author_icon": "",
    "title": "",
    "description": "",
    "color": "7C3AED",
    "image_url": "",       # supports GIF urls
    "thumbnail_url": "",
    "footer_text": "",
    "footer_icon": "",
    "fields": [],
    "buttons": [],          # [{label, url}]
}

DEFAULT_GUILD_DATA = {
    "prefix": "!",
    "welcome": {"enabled": False, "channel_id": None, "message": "Welcome {user} to {server}!", "template": None},
    "leave": {"enabled": False, "channel_id": None, "message": "{user} left the server.", "template": None},
    "boost": {"enabled": False, "channel_id": None, "template": None},
    "levelup": {"enabled": False, "channel_id": None, "template": None, "role_rewards": {}},
    "autorole": None,
    "automod": {
        "enabled": False,
        "banned_words": [],
        "block_invites": True,
        "block_mass_mentions": True,
        "mass_mention_limit": 5,
        "block_spam": True,
        "spam_message_limit": 5,
        "spam_window_seconds": 7,
        "block_caps": False,
        "caps_percent_limit": 70,
        "caps_min_length": 12,
        "strike_action_at": 3,
        "strike_action": "mute",  # mute | kick | ban
        "strike_mute_minutes": 30,
        "whitelisted_domains": [],
    },
    "automod_strikes": {},
    "log_channel": None,
    "mod_log_channel": None,
    "warnings": {},
    "levels": {},
    "economy": {},
    "shop_items": {"vip": 500, "color_role": 300, "shoutout": 150},
    "birthdays": {},
    "reaction_roles": [],
    "reaction_role_menus": {},
    "autoresponders": [],
    "tickets": {
        "category_id": None,
        "support_role_id": None,
        "counter": 0,
        "panel_channel_id": None,
        "panel_message_id": None,
        "log_channel_id": None,
        "button_label": "Open Ticket",
        "embed_template": None,
        "transcripts_enabled": True,
        "auto_close_hours": 0,
    },
    "ticket_panels": {},
    "embed_templates": {},
    "sticky": {},
    "afk": {},
    "verification": {"enabled": False, "role_id": None},
    "suggestion_channel": None,
    "antiraid": {"enabled": True, "join_limit": 10, "join_window": 10},
    "antinuke": {"enabled": True, "action_limit": 5, "action_window": 20},
    "disabled_commands": [],
    "status_rotation": [],
    "stats_daily": {},
}

DEFAULT_DATA = {
    "guilds": {},
    "global": {
        "blacklist_users": [],
        "blacklist_guilds": [],
        "maintenance": False,
        "total_commands_used": 0,
        "logs": [],
    },
}


def _load():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT_DATA))
    data.setdefault("guilds", {})
    data.setdefault("global", json.loads(json.dumps(DEFAULT_DATA["global"])))
    return data


def _save(data):
    with _lock:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)


def _deep_default(target, defaults):
    """Recursively fill in any missing keys from `defaults` into `target` (dict-only)."""
    changed = False
    for key, value in defaults.items():
        if key not in target:
            target[key] = json.loads(json.dumps(value))
            changed = True
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            if _deep_default(target[key], value):
                changed = True
    return changed


def get_guild_data(guild_id):
    data = _load()
    gid = str(guild_id)
    if gid not in data["guilds"]:
        data["guilds"][gid] = json.loads(json.dumps(DEFAULT_GUILD_DATA))
        _save(data)
    guild_data = data["guilds"][gid]
    if _deep_default(guild_data, DEFAULT_GUILD_DATA):
        _save(data)
    return guild_data


def save_guild_data(guild_id, guild_data):
    data = _load()
    data["guilds"][str(guild_id)] = guild_data
    _save(data)


def get_global_data():
    data = _load()
    return data["global"]


def save_global_data(global_data):
    data = _load()
    data["global"] = global_data
    _save(data)


def add_log(message):
    data = _load()
    data["global"]["logs"].append(message)
    data["global"]["logs"] = data["global"]["logs"][-200:]
    _save(data)


def increment_command_count():
    data = _load()
    data["global"]["total_commands_used"] = data["global"].get("total_commands_used", 0) + 1
    _save(data)


def all_guild_ids():
    data = _load()
    return list(data["guilds"].keys())


def record_daily_stat(guild_id, key):
    """Increment today's counter for `key` (e.g. 'joins', 'leaves', 'commands') for analytics charts."""
    import datetime
    data = _load()
    gid = str(guild_id)
    if gid not in data["guilds"]:
        data["guilds"][gid] = json.loads(json.dumps(DEFAULT_GUILD_DATA))
    guild_data = data["guilds"][gid]
    guild_data.setdefault("stats_daily", {})
    today = datetime.date.today().isoformat()
    day = guild_data["stats_daily"].setdefault(today, {})
    day[key] = day.get(key, 0) + 1
    # keep last 60 days only
    if len(guild_data["stats_daily"]) > 60:
        for old_key in sorted(guild_data["stats_daily"].keys())[:-60]:
            guild_data["stats_daily"].pop(old_key, None)
    _save(data)
