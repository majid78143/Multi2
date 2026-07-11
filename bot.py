import io
import time
import datetime
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

import config
from embeds import (
    branded_embed, youtube_button_view, build_embed_from_template,
    build_view_from_template, apply_placeholders,
)
from storage import (
    get_guild_data, save_guild_data, get_global_data, save_global_data,
    increment_command_count, all_guild_ids, record_daily_stat,
)

START_TIME = time.time()

# ---------- permissions helpers ----------


def is_owner(user_id):
    return str(user_id) in config.OWNER_IDS


def is_blacklisted_user(user_id):
    return str(user_id) in get_global_data().get("blacklist_users", [])


def is_blacklisted_guild(guild_id):
    return str(guild_id) in get_global_data().get("blacklist_guilds", [])


def is_maintenance():
    return get_global_data().get("maintenance", False)


def has_manage_guild(member):
    return member.guild_permissions.manage_guild or is_owner(member.id)


def has_kick_perm(member):
    return member.guild_permissions.kick_members or is_owner(member.id)


def has_ban_perm(member):
    return member.guild_permissions.ban_members or is_owner(member.id)


def has_manage_messages(member):
    return member.guild_permissions.manage_messages or is_owner(member.id)


def command_disabled(guild_id, name):
    data = get_guild_data(guild_id)
    return name in data.get("disabled_commands", [])


# ---------- bot setup ----------


async def get_prefix(bot, message):
    if not message.guild:
        return config.DEFAULT_PREFIX
    return get_guild_data(message.guild.id).get("prefix", config.DEFAULT_PREFIX)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# in-memory trackers (reset on restart, fine for anti-raid/anti-nuke/spam windows)
_join_times = {}
_action_times = {}
_spam_times = {}  # (guild_id, user_id) -> [timestamps]
_active_giveaways = {}


async def guard_disabled(ctx_or_inter, name) -> bool:
    """Returns True (and replies) if the command is disabled on this server."""
    guild = ctx_or_inter.guild if hasattr(ctx_or_inter, "guild") else None
    if not guild:
        return False
    if command_disabled(guild.id, name):
        embed = branded_embed(description=f"The `{name}` command is disabled on this server.")
        if isinstance(ctx_or_inter, discord.Interaction):
            if ctx_or_inter.response.is_done():
                await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx_or_inter.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx_or_inter.send(embed=embed)
        return True
    return False


# ================= GENERAL =================


@bot.hybrid_command(name="help", description="Show all Pixel commands")
async def help_cmd(ctx):
    if await guard_disabled(ctx, "help"):
        return
    embed = branded_embed(
        title=f"{config.BOT_NAME} — Command Help",
        description=(
            "All-in-one control system for your server.\n"
            f"Default prefix: `{config.DEFAULT_PREFIX}` (change with `setprefix`), or use `/` slash commands.\n\n"
            "**General**\n`help`, `devinfo`, `ping`, `userinfo`, `serverinfo`, `avatar`, `afk`\n\n"
            "**Moderation**\n`ban`, `kick`, `mute`, `unmute`, `warn`, `warnings`, `clearwarnings`, "
            "`purge`, `lock`, `unlock`, `verify`\n\n"
            "**Server Setup (Manage Server)**\n`setprefix`, `setwelcome`, `setleave`, `setautorole`, "
            "`automod`, `setlogchannel`, `setmodlog`, `setverification`, `setsuggestionchannel`, "
            "`setsticky`, `removesticky`, `togglecommand`\n\n"
            "**Engagement**\n`rank`, `leaderboard`, `balance`, `daily`, `pay`, `shop`, `buy`, "
            "`setbirthday`, `birthdays`, `suggest`, `poll`, `remind`, `translate`, `giveaway`\n\n"
            "**Tickets & Roles**\n`ticket`, `closeticket`, `reactionrole add/remove/list`, `rolemenu`\n\n"
            "**Owner Only**\n`eval`, `blacklist`, `maintenance`, `broadcast`, `setstatus`, "
            "`forceleave`, `servers`\n\n"
            "Full template builder (welcome/leave/boost/level-up/tickets/auto-responder), reaction "
            "role menus, and analytics are available on the website dashboard."
        ),
    )
    await ctx.send(embed=embed, view=youtube_button_view())


@bot.hybrid_command(name="devinfo", description="Show developer/branding info")
async def devinfo(ctx):
    embed = branded_embed(
        title=f"Developer Info — {config.BOT_NAME}",
        description=(
            f"**Bot:** {config.BOT_NAME}\n"
            f"**Developed by:** {config.DEVELOPER}\n"
            f"**Organisation:** {config.BRAND}\n\n"
            "Thanks for using this bot! Support the project by subscribing to our YouTube channel."
        ),
    )
    await ctx.send(embed=embed, view=youtube_button_view())


@bot.hybrid_command(name="ping", description="Check bot latency")
async def ping(ctx):
    await ctx.send(embed=branded_embed(title="Pong!", description=f"Latency: `{round(bot.latency * 1000)}ms`"))


@bot.hybrid_command(name="userinfo", description="Show info about a member")
@app_commands.describe(member="Member to look up")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = branded_embed(title=f"User Info — {member.display_name}")
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at) if member.joined_at else "N/A", inline=True)
    embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at), inline=True)
    roles = ", ".join(r.mention for r in member.roles if r.name != "@everyone") or "None"
    embed.add_field(name="Roles", value=roles, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="serverinfo", description="Show info about this server")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = branded_embed(title=f"Server Info — {guild.name}")
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
    embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="avatar", description="Show a member's avatar")
@app_commands.describe(member="Member to look up")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = branded_embed(title=f"{member.display_name}'s Avatar")
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.hybrid_command(name="afk", description="Set yourself as AFK")
@app_commands.describe(reason="Reason you're away")
async def afk(ctx, *, reason: str = "AFK"):
    data = get_guild_data(ctx.guild.id)
    data["afk"][str(ctx.author.id)] = reason
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"{ctx.author.mention} is now AFK: {reason}"))


# ================= MODERATION =================


async def send_modlog(ctx, embed):
    data = get_guild_data(ctx.guild.id)
    channel_id = data.get("mod_log_channel")
    if channel_id:
        channel = ctx.guild.get_channel(int(channel_id))
        if channel:
            await channel.send(embed=embed)


@bot.hybrid_command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban", reason="Reason for the ban")
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not has_ban_perm(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to ban members."))
    await member.ban(reason=reason)
    embed = branded_embed(title="Member Banned", description=f"{member.mention} was banned.\n**Reason:** {reason}")
    await ctx.send(embed=embed)
    await send_modlog(ctx, embed)


@bot.hybrid_command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick", reason="Reason for the kick")
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not has_kick_perm(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to kick members."))
    await member.kick(reason=reason)
    embed = branded_embed(title="Member Kicked", description=f"{member.mention} was kicked.\n**Reason:** {reason}")
    await ctx.send(embed=embed)
    await send_modlog(ctx, embed)


@bot.hybrid_command(name="mute", description="Timeout a member")
@app_commands.describe(member="Member to mute", minutes="Duration in minutes", reason="Reason")
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason: str = "No reason provided"):
    if not has_kick_perm(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to mute members."))
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    embed = branded_embed(title="Member Muted", description=f"{member.mention} muted for {minutes} minutes.\n**Reason:** {reason}")
    await ctx.send(embed=embed)
    await send_modlog(ctx, embed)


@bot.hybrid_command(name="unmute", description="Remove a member's timeout")
@app_commands.describe(member="Member to unmute")
async def unmute(ctx, member: discord.Member):
    if not has_kick_perm(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to unmute members."))
    await member.timeout(None)
    await ctx.send(embed=branded_embed(description=f"{member.mention} has been unmuted."))


@bot.hybrid_command(name="warn", description="Warn a member")
@app_commands.describe(member="Member to warn", reason="Reason for the warning")
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if not has_kick_perm(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to warn members."))
    data = get_guild_data(ctx.guild.id)
    uid = str(member.id)
    data["warnings"].setdefault(uid, [])
    data["warnings"][uid].append(reason)
    save_guild_data(ctx.guild.id, data)
    count = len(data["warnings"][uid])
    embed = branded_embed(title="Member Warned", description=f"{member.mention} warned ({count} total).\n**Reason:** {reason}")
    await ctx.send(embed=embed)
    await send_modlog(ctx, embed)
    if count >= 3:
        try:
            await member.timeout(datetime.timedelta(hours=1), reason="Auto-mute: reached 3 warnings")
            await ctx.send(embed=branded_embed(description=f"{member.mention} auto-muted for 1 hour (3+ warnings)."))
        except discord.Forbidden:
            pass


@bot.hybrid_command(name="warnings", description="List a member's warnings")
@app_commands.describe(member="Member to check")
async def warnings_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_guild_data(ctx.guild.id)
    warns = data["warnings"].get(str(member.id), [])
    desc = "\n".join(f"{i+1}. {w}" for i, w in enumerate(warns)) or "No warnings."
    await ctx.send(embed=branded_embed(title=f"Warnings — {member.display_name}", description=desc))


@bot.hybrid_command(name="clearwarnings", description="Clear a member's warnings")
@app_commands.describe(member="Member to clear")
async def clearwarnings(ctx, member: discord.Member):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["warnings"][str(member.id)] = []
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Cleared warnings for {member.mention}."))


@bot.hybrid_command(name="purge", description="Bulk delete messages in this channel")
@app_commands.describe(amount="Number of messages to delete (max 100)")
async def purge(ctx, amount: int = 10):
    if not has_manage_messages(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to manage messages."))
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=min(amount, 100))
        await ctx.send(embed=branded_embed(description=f"Deleted {len(deleted)} messages."), ephemeral=True)
    else:
        deleted = await ctx.channel.purge(limit=min(amount, 100) + 1)
        msg = await ctx.send(embed=branded_embed(description=f"Deleted {len(deleted) - 1} messages."))
        await msg.delete(delay=4)


@bot.hybrid_command(name="lock", description="Lock this channel")
async def lock(ctx):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=branded_embed(description="🔒 Channel locked."))


@bot.hybrid_command(name="unlock", description="Unlock this channel")
async def unlock(ctx):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=branded_embed(description="🔓 Channel unlocked."))


@bot.hybrid_command(name="verify", description="Verify yourself to get the verified role")
async def verify(ctx):
    data = get_guild_data(ctx.guild.id)
    verification = data.get("verification", {})
    if not verification.get("enabled") or not verification.get("role_id"):
        return await ctx.send(embed=branded_embed(description="Verification is not set up on this server."))
    role = ctx.guild.get_role(int(verification["role_id"]))
    if role:
        await ctx.author.add_roles(role, reason="Self verification")
        await ctx.send(embed=branded_embed(description=f"{ctx.author.mention} you are now verified!"))


# ================= SERVER SETUP (automation) =================


@bot.hybrid_command(name="setprefix", description="Change the command prefix for this server")
@app_commands.describe(prefix="New prefix, e.g. !")
async def setprefix(ctx, prefix: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["prefix"] = prefix
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Prefix updated to `{prefix}`"))


@bot.hybrid_command(name="setwelcome", description="Enable welcome messages in a channel")
@app_commands.describe(channel="Channel to post welcome messages in", message="Plain fallback message ({user}, {server} supported)")
async def setwelcome(ctx, channel: discord.TextChannel, *, message: str = "Welcome {user} to {server}!"):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["welcome"]["enabled"] = True
    data["welcome"]["channel_id"] = str(channel.id)
    data["welcome"]["message"] = message
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=(
        f"Welcome messages set in {channel.mention}. Build a full embed + GIF template for this "
        "on the website dashboard's Template Builder for a richer welcome."
    )))


@bot.hybrid_command(name="setleave", description="Enable leave messages in a channel")
@app_commands.describe(channel="Channel to post leave messages in", message="Plain fallback message ({user}, {server} supported)")
async def setleave(ctx, channel: discord.TextChannel, *, message: str = "{user} left the server."):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["leave"]["enabled"] = True
    data["leave"]["channel_id"] = str(channel.id)
    data["leave"]["message"] = message
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Leave messages set in {channel.mention}."))


@bot.hybrid_command(name="setautorole", description="Set a role auto-assigned to new members")
@app_commands.describe(role="Role to auto-assign")
async def setautorole(ctx, role: discord.Role):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["autorole"] = str(role.id)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Auto-role set to {role.mention}."))


@bot.hybrid_command(name="automod", description="Turn auto-moderation on or off")
@app_commands.describe(state="on or off")
async def automod_cmd(ctx, state: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["automod"]["enabled"] = state.lower() in ("on", "enable", "true")
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Auto-moderation is now **{'ON' if data['automod']['enabled'] else 'OFF'}**."))


@bot.hybrid_command(name="setlogchannel", description="Set the server log channel")
@app_commands.describe(channel="Channel for server logs")
async def setlogchannel(ctx, channel: discord.TextChannel):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["log_channel"] = str(channel.id)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Server log channel set to {channel.mention}."))


@bot.hybrid_command(name="setmodlog", description="Set the moderation log channel")
@app_commands.describe(channel="Channel for moderation logs")
async def setmodlog(ctx, channel: discord.TextChannel):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["mod_log_channel"] = str(channel.id)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Mod-log channel set to {channel.mention}."))


@bot.hybrid_command(name="setverification", description="Enable self-verification with a role")
@app_commands.describe(role="Role given on verification")
async def setverification(ctx, role: discord.Role):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["verification"] = {"enabled": True, "role_id": str(role.id)}
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Verification enabled. New members use `verify` to get {role.mention}."))


@bot.hybrid_command(name="setsuggestionchannel", description="Set the channel for suggestions")
@app_commands.describe(channel="Channel for suggestions")
async def setsuggestionchannel(ctx, channel: discord.TextChannel):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["suggestion_channel"] = str(channel.id)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Suggestions will be posted in {channel.mention}."))


@bot.hybrid_command(name="setsticky", description="Set a sticky message for this channel")
@app_commands.describe(message="The sticky message text")
async def setsticky(ctx, *, message: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["sticky"][str(ctx.channel.id)] = {"message": message, "last_message_id": None}
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description="Sticky message set for this channel."))


@bot.hybrid_command(name="removesticky", description="Remove the sticky message from this channel")
async def removesticky(ctx):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    data["sticky"].pop(str(ctx.channel.id), None)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description="Sticky message removed for this channel."))


@bot.hybrid_command(name="togglecommand", description="Enable or disable a command on this server")
@app_commands.describe(command_name="Command name to toggle", state="on or off")
async def togglecommand(ctx, command_name: str, state: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    command_name = command_name.lower().lstrip("!/")
    disabled = set(data.get("disabled_commands", []))
    if state.lower() in ("off", "disable", "false"):
        disabled.add(command_name)
    else:
        disabled.discard(command_name)
    data["disabled_commands"] = list(disabled)
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"`{command_name}` is now **{'disabled' if command_name in disabled else 'enabled'}**."))


# ================= ENGAGEMENT =================


def xp_for_level(level):
    return 5 * (level ** 2) + 50 * level + 100


@bot.hybrid_command(name="rank", description="Check your level and XP")
@app_commands.describe(member="Member to check")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_guild_data(ctx.guild.id)
    profile = data["levels"].get(str(member.id), {"xp": 0, "level": 0})
    await ctx.send(embed=branded_embed(
        title=f"Rank — {member.display_name}",
        description=f"Level: **{profile['level']}**\nXP: **{profile['xp']}** / {xp_for_level(profile['level'])}",
    ))


@bot.hybrid_command(name="leaderboard", description="Show the server XP leaderboard")
async def leaderboard(ctx):
    data = get_guild_data(ctx.guild.id)
    entries = sorted(data["levels"].items(), key=lambda kv: (kv[1]["level"], kv[1]["xp"]), reverse=True)[:10]
    if not entries:
        desc = "No activity yet."
    else:
        lines = []
        for i, (uid, prof) in enumerate(entries):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            lines.append(f"**{i+1}.** {name} — Level {prof['level']} ({prof['xp']} XP)")
        desc = "\n".join(lines)
    await ctx.send(embed=branded_embed(title="Leaderboard", description=desc))


@bot.hybrid_command(name="balance", description="Check your coin balance")
@app_commands.describe(member="Member to check")
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = get_guild_data(ctx.guild.id)
    coins = data["economy"].get(str(member.id), {}).get("coins", 0)
    await ctx.send(embed=branded_embed(description=f"{member.mention} has **{coins}** coins."))


@bot.hybrid_command(name="daily", description="Claim your daily coins")
async def daily(ctx):
    data = get_guild_data(ctx.guild.id)
    uid = str(ctx.author.id)
    econ = data["economy"].setdefault(uid, {"coins": 0, "last_daily": 0})
    now = time.time()
    if now - econ.get("last_daily", 0) < 86400:
        remaining = int(86400 - (now - econ["last_daily"]))
        return await ctx.send(embed=branded_embed(description=f"Already claimed. Try again in {remaining // 3600}h {(remaining % 3600) // 60}m."))
    econ["coins"] += 100
    econ["last_daily"] = now
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"{ctx.author.mention} claimed **100 coins**! Balance: {econ['coins']}"))


@bot.hybrid_command(name="pay", description="Pay another member coins")
@app_commands.describe(member="Member to pay", amount="Amount of coins")
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send(embed=branded_embed(description="Amount must be positive."))
    data = get_guild_data(ctx.guild.id)
    sender = data["economy"].setdefault(str(ctx.author.id), {"coins": 0, "last_daily": 0})
    receiver = data["economy"].setdefault(str(member.id), {"coins": 0, "last_daily": 0})
    if sender["coins"] < amount:
        return await ctx.send(embed=branded_embed(description="Insufficient balance."))
    sender["coins"] -= amount
    receiver["coins"] += amount
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"{ctx.author.mention} paid {amount} coins to {member.mention}."))


@bot.hybrid_command(name="shop", description="View the server shop")
async def shop(ctx):
    data = get_guild_data(ctx.guild.id)
    items = data.get("shop_items") or {"vip": 500, "color_role": 300, "shoutout": 150}
    desc = "\n".join(f"**{k}** — {v} coins" for k, v in items.items())
    await ctx.send(embed=branded_embed(title="Shop", description=desc))


@bot.hybrid_command(name="buy", description="Buy an item from the shop")
@app_commands.describe(item="Item name from the shop")
async def buy(ctx, item: str):
    item = item.lower()
    data = get_guild_data(ctx.guild.id)
    items = data.get("shop_items") or {}
    if item not in items:
        return await ctx.send(embed=branded_embed(description="Item not found. Use `shop` to see items."))
    econ = data["economy"].setdefault(str(ctx.author.id), {"coins": 0, "last_daily": 0})
    price = items[item]
    if econ["coins"] < price:
        return await ctx.send(embed=branded_embed(description="Insufficient balance."))
    econ["coins"] -= price
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"{ctx.author.mention} purchased **{item}**!"))


@bot.hybrid_command(name="setbirthday", description="Set your birthday (DD-MM)")
@app_commands.describe(date="Format DD-MM, e.g. 25-12")
async def setbirthday(ctx, date: str):
    data = get_guild_data(ctx.guild.id)
    data["birthdays"][str(ctx.author.id)] = date
    save_guild_data(ctx.guild.id, data)
    await ctx.send(embed=branded_embed(description=f"Birthday set to **{date}**."))


@bot.hybrid_command(name="birthdays", description="List upcoming server birthdays")
async def birthdays(ctx):
    data = get_guild_data(ctx.guild.id)
    if not data["birthdays"]:
        return await ctx.send(embed=branded_embed(description="No birthdays set yet."))
    lines = []
    for uid, date in data["birthdays"].items():
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lines.append(f"{name} — {date}")
    await ctx.send(embed=branded_embed(title="Birthdays", description="\n".join(lines)))


@bot.hybrid_command(name="suggest", description="Submit a suggestion")
@app_commands.describe(text="Your suggestion")
async def suggest(ctx, *, text: str):
    data = get_guild_data(ctx.guild.id)
    channel_id = data.get("suggestion_channel")
    channel = ctx.guild.get_channel(int(channel_id)) if channel_id else ctx.channel
    embed = branded_embed(title="New Suggestion", description=text)
    embed.set_footer(text=f"Suggested by {ctx.author.display_name}")
    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    if channel != ctx.channel:
        await ctx.send(embed=branded_embed(description="Suggestion posted!"))


@bot.hybrid_command(name="poll", description="Create a reaction poll")
@app_commands.describe(question="Poll question", options="Options separated by | (pipe), e.g. Yes|No|Maybe")
async def poll(ctx, question: str, *, options: str = "Yes|No"):
    opts = [o.strip() for o in options.split("|") if o.strip()]
    if len(opts) < 2:
        return await ctx.send(embed=branded_embed(description="Provide at least 2 options separated by `|`."))
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    desc = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(opts[:9]))
    msg = await ctx.send(embed=branded_embed(title=question, description=desc))
    for i in range(min(len(opts), 9)):
        await msg.add_reaction(number_emojis[i])


@bot.hybrid_command(name="remind", description="Set a personal reminder")
@app_commands.describe(minutes="Minutes from now", text="Reminder text")
async def remind(ctx, minutes: int, *, text: str):
    await ctx.send(embed=branded_embed(description=f"Reminder set for {minutes} minute(s)."))

    async def reminder_task():
        await asyncio.sleep(minutes * 60)
        try:
            await ctx.channel.send(f"{ctx.author.mention} ⏰ Reminder: {text}")
        except discord.HTTPException:
            pass

    bot.loop.create_task(reminder_task())


@bot.hybrid_command(name="translate", description="Translate text to another language")
@app_commands.describe(target_lang="Target language code, e.g. es, fr, hi", text="Text to translate")
async def translate(ctx, target_lang: str, *, text: str):
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"en|{target_lang}"},
            timeout=10,
        )
        translated = resp.json()["responseData"]["translatedText"]
        await ctx.send(embed=branded_embed(title="Translation", description=translated))
    except Exception:
        await ctx.send(embed=branded_embed(description="Translation failed. Try again later."))


@bot.hybrid_command(name="giveaway", description="Start a giveaway")
@app_commands.describe(minutes="Duration in minutes", winners="Number of winners", prize="The prize")
async def giveaway(ctx, minutes: int, winners: int, *, prize: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    embed = branded_embed(title="🎉 Giveaway!", description=f"**Prize:** {prize}\nReact with 🎉 to enter!\nEnds in {minutes} minute(s). Winners: {winners}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    _active_giveaways[msg.id] = {"winners": winners, "prize": prize, "channel_id": ctx.channel.id}

    async def end_giveaway():
        await asyncio.sleep(minutes * 60)
        channel = ctx.guild.get_channel(ctx.channel.id)
        try:
            fetched = await channel.fetch_message(msg.id)
        except discord.NotFound:
            return
        reaction = discord.utils.get(fetched.reactions, emoji="🎉")
        users = [u async for u in reaction.users()] if reaction else []
        users = [u for u in users if not u.bot]
        if not users:
            return await channel.send(embed=branded_embed(description="No valid entries, giveaway cancelled."))
        picked = random.sample(users, min(winners, len(users)))
        mentions = ", ".join(u.mention for u in picked)
        await channel.send(embed=branded_embed(title="🎉 Giveaway Ended!", description=f"**Prize:** {prize}\nWinner(s): {mentions}"))

    bot.loop.create_task(end_giveaway())


# ================= TICKETS =================


def _resolve_ticket_embed(guild_id, panel_key, user):
    data = get_guild_data(guild_id)
    templates = data.get("embed_templates", {})
    tpl_name = None
    if panel_key and panel_key in data.get("ticket_panels", {}):
        tpl_name = data["ticket_panels"][panel_key].get("embed_template")
    else:
        tpl_name = data["tickets"].get("embed_template")
    if tpl_name and tpl_name in templates:
        embed = build_embed_from_template(templates[tpl_name], member=user, guild=None)
        if not embed.description:
            embed.description = f"{user.mention} welcome to your ticket! Support will be with you shortly."
        return embed
    return branded_embed(description=f"{user.mention} welcome to your ticket! Support will be with you shortly.")


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="\U0001F512", custom_id="pixel_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        if not channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        await interaction.response.send_message(embed=branded_embed(description="Closing this ticket in 5 seconds..."))
        data = get_guild_data(guild.id)

        # transcript
        if data["tickets"].get("transcripts_enabled", True):
            try:
                lines = []
                async for msg in channel.history(limit=500, oldest_first=True):
                    ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    content = msg.content or "(embed/attachment)"
                    lines.append(f"[{ts}] {msg.author}: {content}")
                transcript_text = "\n".join(lines) or "(no messages)"
                transcript_file = discord.File(io.BytesIO(transcript_text.encode("utf-8")), filename=f"{channel.name}-transcript.txt")
            except Exception:
                transcript_file = None
        else:
            transcript_file = None

        log_id = data["tickets"].get("log_channel_id")
        if log_id:
            log_channel = guild.get_channel(int(log_id))
            if log_channel:
                try:
                    embed = branded_embed(
                        title="Ticket Closed",
                        description=f"**Channel:** #{channel.name}\n**Closed by:** {interaction.user.mention}",
                    )
                    if transcript_file:
                        await log_channel.send(embed=embed, file=transcript_file)
                    else:
                        await log_channel.send(embed=embed)
                except discord.HTTPException:
                    pass
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except discord.HTTPException:
            pass


class TicketView(discord.ui.View):
    def __init__(self, panel_key=None, label="Open Ticket"):
        super().__init__(timeout=None)
        self.panel_key = panel_key
        custom_id = f"pixel_open_ticket:{panel_key}" if panel_key else "pixel_open_ticket"
        # rebuild the button with the correct custom_id/label since decorators can't be dynamic
        self.clear_items()
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.green, custom_id=custom_id)
        button.callback = self._open_ticket
        self.add_item(button)

    async def _open_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        data = get_guild_data(guild.id)
        panel = data.get("ticket_panels", {}).get(self.panel_key) if self.panel_key else None
        settings = panel if panel else data["tickets"]

        data["tickets"]["counter"] += 1
        number = data["tickets"]["counter"]
        save_guild_data(guild.id, data)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        support_role_id = settings.get("support_role_id")
        if support_role_id:
            role = guild.get_role(int(support_role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        category = None
        cat_id = settings.get("category_id")
        if cat_id:
            category = guild.get_channel(int(cat_id))
        prefix = (panel.get("name") if panel else None) or "ticket"
        safe_prefix = "".join(c for c in prefix.lower() if c.isalnum() or c == "-") or "ticket"
        channel = await guild.create_text_channel(f"ticket-{number}", overwrites=overwrites, category=category)
        embed = _resolve_ticket_embed(guild.id, self.panel_key, interaction.user)
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


async def post_ticket_panel(guild, channel, embed, panel_key=None, label="Open Ticket"):
    """Post (or repost) the permanent ticket panel with a live button. Called from the
    website via run_on_bot so it always stores a working message + persistent view."""
    message = await channel.send(embed=embed, view=TicketView(panel_key=panel_key, label=label))
    return message


_PERSISTENT_VIEWS_REGISTERED = False


def register_persistent_views():
    global _PERSISTENT_VIEWS_REGISTERED
    if _PERSISTENT_VIEWS_REGISTERED:
        return
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    # re-register any per-server custom ticket panels so their buttons keep working after restart
    for gid in all_guild_ids():
        data = get_guild_data(gid)
        for key, panel in data.get("ticket_panels", {}).items():
            bot.add_view(TicketView(panel_key=key, label=panel.get("button_label", "Open Ticket")))
        for menu_id, menu in data.get("reaction_role_menus", {}).items():
            try:
                bot.add_view(build_role_menu_view(gid, menu_id, menu))
            except Exception:
                pass
    _PERSISTENT_VIEWS_REGISTERED = True


@bot.hybrid_command(name="ticket", description="Post the default ticket panel here")
async def ticket_setup(ctx):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    embed = _resolve_ticket_embed(ctx.guild.id, None, ctx.author)
    await ctx.send(embed=embed, view=TicketView())


@bot.hybrid_command(name="closeticket", description="Close the current ticket channel")
async def closeticket(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(embed=branded_embed(description="This is not a ticket channel."))
    await ctx.send(embed=branded_embed(description="Closing ticket in 5 seconds..."))
    await asyncio.sleep(5)
    await ctx.channel.delete()


# ================= REACTION ROLES (legacy emoji-based) =================


@bot.hybrid_command(name="reactionrole", description="Manage emoji reaction roles")
@app_commands.describe(action="add, remove, or list", message_id="Message ID", emoji="Emoji", role="Role")
async def reactionrole(ctx, action: str, message_id: str = None, emoji: str = None, role: discord.Role = None):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    action = action.lower()
    if action == "add":
        if not (message_id and emoji and role):
            return await ctx.send(embed=branded_embed(description="Usage: reactionrole add <message_id> <emoji> @role"))
        data["reaction_roles"].append({"message_id": message_id, "emoji": emoji, "role_id": str(role.id)})
        save_guild_data(ctx.guild.id, data)
        try:
            msg = await ctx.channel.fetch_message(int(message_id))
            await msg.add_reaction(emoji)
        except (discord.NotFound, discord.HTTPException):
            pass
        await ctx.send(embed=branded_embed(description=f"Reaction role added: {emoji} → {role.mention}"))
    elif action == "remove":
        data["reaction_roles"] = [rr for rr in data["reaction_roles"] if not (rr["message_id"] == message_id and rr["emoji"] == emoji)]
        save_guild_data(ctx.guild.id, data)
        await ctx.send(embed=branded_embed(description="Reaction role removed."))
    elif action == "list":
        if not data["reaction_roles"]:
            return await ctx.send(embed=branded_embed(description="No reaction roles configured."))
        lines = [f"{rr['emoji']} → <@&{rr['role_id']}> (msg {rr['message_id']})" for rr in data["reaction_roles"]]
        await ctx.send(embed=branded_embed(title="Reaction Roles", description="\n".join(lines)))


@bot.event
async def on_raw_reaction_add(payload):
    if payload.member is None or payload.member.bot:
        return
    data = get_guild_data(payload.guild_id)
    for rr in data["reaction_roles"]:
        if rr["message_id"] == str(payload.message_id) and rr["emoji"] == str(payload.emoji):
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rr["role_id"]))
            if role:
                await payload.member.add_roles(role, reason="Reaction role")


@bot.event
async def on_raw_reaction_remove(payload):
    data = get_guild_data(payload.guild_id)
    for rr in data["reaction_roles"]:
        if rr["message_id"] == str(payload.message_id) and rr["emoji"] == str(payload.emoji):
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(int(rr["role_id"]))
            member = guild.get_member(payload.user_id)
            if role and member:
                await member.remove_roles(role, reason="Reaction role removed")


# ================= REACTION ROLE MENUS (button/select based, more reliable) =================


def build_role_menu_view(guild_id, menu_id, menu: dict):
    """Builds a persistent select-menu view for a button-based role menu configured on the website."""
    options = menu.get("options", [])[:25]
    multi = menu.get("multi", True)

    class RoleMenuSelect(discord.ui.Select):
        def __init__(self):
            select_options = [
                discord.SelectOption(label=o.get("label", "Role")[:100], value=o.get("role_id"), emoji=o.get("emoji") or None)
                for o in options if o.get("role_id")
            ]
            super().__init__(
                placeholder=menu.get("placeholder", "Choose your roles..."),
                min_values=0,
                max_values=len(select_options) if multi else 1,
                options=select_options or [discord.SelectOption(label="No roles configured", value="none")],
                custom_id=f"pixel_role_menu:{guild_id}:{menu_id}",
            )

        async def callback(self, interaction: discord.Interaction):
            guild = interaction.guild
            member = interaction.user
            all_role_ids = {o.get("role_id") for o in options if o.get("role_id")}
            selected = set(self.values)
            added, removed = [], []
            for rid in all_role_ids:
                role = guild.get_role(int(rid))
                if not role:
                    continue
                if rid in selected and role not in member.roles:
                    await member.add_roles(role, reason="Role menu")
                    added.append(role.mention)
                elif rid not in selected and role in member.roles:
                    await member.remove_roles(role, reason="Role menu")
                    removed.append(role.mention)
            parts = []
            if added:
                parts.append("Added: " + ", ".join(added))
            if removed:
                parts.append("Removed: " + ", ".join(removed))
            await interaction.response.send_message(
                embed=branded_embed(description="\n".join(parts) or "No changes."), ephemeral=True
            )

    view = discord.ui.View(timeout=None)
    view.add_item(RoleMenuSelect())
    return view


@bot.hybrid_command(name="rolemenu", description="Post a configured button/select role menu here")
@app_commands.describe(menu_id="The role menu ID from the website dashboard")
async def rolemenu(ctx, menu_id: str):
    if not has_manage_guild(ctx.author):
        return await ctx.send(embed=branded_embed(description="You don't have permission to do this."))
    data = get_guild_data(ctx.guild.id)
    menu = data.get("reaction_role_menus", {}).get(menu_id)
    if not menu:
        return await ctx.send(embed=branded_embed(description="Role menu not found. Create one on the website dashboard first."))
    embed = branded_embed(title=menu.get("title", "Choose your roles"), description=menu.get("description", "Select from the menu below."))
    await ctx.send(embed=embed, view=build_role_menu_view(ctx.guild.id, menu_id, menu))


# ================= OWNER ONLY =================


@bot.command(name="eval")
async def eval_cmd(ctx, *, code: str):
    if not is_owner(ctx.author.id):
        return
    try:
        result = eval(code)
        await ctx.send(embed=branded_embed(title="Eval Result", description=f"```py\n{result}\n```"))
    except Exception as e:
        await ctx.send(embed=branded_embed(title="Eval Error", description=f"```py\n{e}\n```"))


@bot.command(name="blacklist")
async def blacklist_cmd(ctx, action: str, target_type: str, target_id: str):
    if not is_owner(ctx.author.id):
        return
    data = get_global_data()
    key = "blacklist_users" if target_type.lower().startswith("user") else "blacklist_guilds"
    if action.lower() == "add":
        if target_id not in data[key]:
            data[key].append(target_id)
    elif action.lower() == "remove":
        data[key] = [x for x in data[key] if x != target_id]
    save_global_data(data)
    await ctx.send(embed=branded_embed(description=f"Blacklist updated: {key} {action} {target_id}"))


@bot.command(name="maintenance")
async def maintenance_cmd(ctx, state: str):
    if not is_owner(ctx.author.id):
        return
    data = get_global_data()
    data["maintenance"] = state.lower() in ("on", "enable", "true")
    save_global_data(data)
    await ctx.send(embed=branded_embed(description=f"Maintenance mode: **{'ON' if data['maintenance'] else 'OFF'}**"))


@bot.command(name="broadcast")
async def broadcast_cmd(ctx, *, message: str):
    if not is_owner(ctx.author.id):
        return
    count = 0
    for guild in bot.guilds:
        target = guild.system_channel
        if target:
            try:
                await target.send(embed=branded_embed(title="Announcement", description=message))
                count += 1
            except discord.HTTPException:
                pass
    await ctx.send(embed=branded_embed(description=f"Broadcast sent to {count} server(s)."))


@bot.command(name="setstatus")
async def setstatus_cmd(ctx, *, text: str):
    if not is_owner(ctx.author.id):
        return
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(embed=branded_embed(description=f"Status updated to: {text}"))


@bot.command(name="forceleave")
async def forceleave_cmd(ctx, guild_id: str):
    if not is_owner(ctx.author.id):
        return
    guild = bot.get_guild(int(guild_id))
    if guild:
        await guild.leave()
        await ctx.send(embed=branded_embed(description=f"Left server: {guild.name}"))
    else:
        await ctx.send(embed=branded_embed(description="Server not found."))


@bot.command(name="servers")
async def servers_cmd(ctx):
    if not is_owner(ctx.author.id):
        return
    total_users = sum(g.member_count or 0 for g in bot.guilds)
    await ctx.send(embed=branded_embed(title="Bot Stats", description=f"Servers: {len(bot.guilds)}\nUsers: {total_users}"))


# ================= EVENTS =================


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Watching(name=f"over your server | {config.DEFAULT_PREFIX}help"))
    print(f"[Pixel] Logged in as {bot.user} ({bot.user.id})")
    register_persistent_views()
    try:
        synced = await bot.tree.sync()
        print(f"[Pixel] Slash commands synced globally: {len(synced)}")
    except Exception as e:
        print(f"[Pixel] Global slash sync failed: {e}")
    # NOTE: Per-guild sync is done ONLY in on_guild_join (new servers).
    # Doing both global + per-guild on every restart causes duplicates/conflicts.

    if not birthday_loop.is_running():
        birthday_loop.start()
    if not status_rotation_loop.is_running():
        status_rotation_loop.start()
    if not keep_alive_loop.is_running():
        keep_alive_loop.start()


@bot.event
async def on_guild_join(guild):
    """Sync slash commands instantly the moment the bot joins a new server, instead of
    waiting for the next full bot restart -- this is the main fix for slash commands
    being missing/delayed on newly-added servers."""
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"[Pixel] Instantly synced {len(synced)} slash commands in new server: {guild.name}")
    except Exception as e:
        print(f"[Pixel] Instant sync failed for new server {guild.name}: {e}")


@bot.event
async def on_command(ctx):
    increment_command_count()
    if ctx.guild:
        record_daily_stat(ctx.guild.id, "commands")


@bot.event
async def on_app_command_completion(interaction, command):
    increment_command_count()
    if interaction.guild:
        record_daily_stat(interaction.guild.id, "commands")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
        return await ctx.send(embed=branded_embed(description=f"Invalid usage. Check `{config.DEFAULT_PREFIX}help`."))
    print(f"[Pixel] Command error: {error}")


async def _send_template_or_fallback(channel, member, guild, template_type, data, plain_key=None, plain_fallback=None, dm_also=False, extra=None):
    """Shared helper: send the rich embed template if the server configured one for this
    trigger type, otherwise fall back to the legacy plain-text message."""
    templates = data.get("embed_templates", {})
    section = data.get(template_type, {})
    tpl_name = section.get("template")
    sent = False
    if tpl_name and tpl_name in templates:
        embed = build_embed_from_template(templates[tpl_name], member=member, guild=guild, extra=extra)
        view = build_view_from_template(templates[tpl_name])
        if channel:
            await channel.send(embed=embed, view=view) if view else await channel.send(embed=embed)
            sent = True
        if section.get("dm_enabled") or dm_also:
            try:
                await member.send(embed=embed)
            except discord.HTTPException:
                pass
    elif plain_key and channel:
        text = apply_placeholders(section.get(plain_key, plain_fallback), member=member, guild=guild, extra=extra)
        embed = branded_embed(title=plain_fallback and None, description=text)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)
        sent = True
    return sent


@bot.event
async def on_member_join(member):
    guild = member.guild
    data = get_guild_data(guild.id)

    if is_blacklisted_guild(guild.id):
        return await guild.leave()

    record_daily_stat(guild.id, "joins")

    # anti-raid
    antiraid = data.get("antiraid", {})
    if antiraid.get("enabled", True):
        now = time.time()
        window = antiraid.get("join_window", 10)
        limit = antiraid.get("join_limit", 10)
        times = _join_times.setdefault(guild.id, [])
        times.append(now)
        _join_times[guild.id] = [t for t in times if now - t <= window]
        if len(_join_times[guild.id]) >= limit:
            try:
                await guild.edit(verification_level=discord.VerificationLevel.high)
            except discord.Forbidden:
                pass
            log_channel_id = data.get("log_channel")
            if log_channel_id:
                channel = guild.get_channel(int(log_channel_id))
                if channel:
                    await channel.send(embed=branded_embed(title="⚠️ Anti-Raid Triggered", description="Unusual join activity detected. Verification level raised."))

    # autorole
    if data.get("autorole"):
        role = guild.get_role(int(data["autorole"]))
        if role:
            try:
                await member.add_roles(role, reason="Autorole")
            except discord.Forbidden:
                pass

    # welcome (template-first, plain-text fallback)
    welcome = data.get("welcome", {})
    if welcome.get("enabled") and welcome.get("channel_id"):
        channel = guild.get_channel(int(welcome["channel_id"]))
        await _send_template_or_fallback(
            channel, member, guild, "welcome",
            data, plain_key="message", plain_fallback="Welcome {user} to {server}!",
        )


@bot.event
async def on_member_remove(member):
    guild = member.guild
    data = get_guild_data(guild.id)
    record_daily_stat(guild.id, "leaves")
    leave = data.get("leave", {})
    if leave.get("enabled") and leave.get("channel_id"):
        channel = guild.get_channel(int(leave["channel_id"]))
        await _send_template_or_fallback(
            channel, member, guild, "leave",
            data, plain_key="message", plain_fallback="{user} left the server.",
        )


@bot.event
async def on_member_update(before, after):
    """Detect server boosts (premium_since goes from None to a timestamp) and fire the boost template."""
    if before.premium_since is None and after.premium_since is not None:
        guild = after.guild
        data = get_guild_data(guild.id)
        boost = data.get("boost", {})
        if boost.get("enabled") and boost.get("channel_id"):
            channel = guild.get_channel(int(boost["channel_id"]))
            await _send_template_or_fallback(channel, after, guild, "boost", data)


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if is_blacklisted_user(message.author.id) or is_maintenance():
        return

    data = get_guild_data(message.guild.id)

    # AFK handling
    afk_map = data.get("afk", {})
    author_id = str(message.author.id)
    if author_id in afk_map:
        del afk_map[author_id]
        data["afk"] = afk_map
        save_guild_data(message.guild.id, data)
        await message.channel.send(embed=branded_embed(description=f"Welcome back {message.author.mention}, AFK removed."))
    for mention in message.mentions:
        mid = str(mention.id)
        if mid in afk_map:
            await message.channel.send(embed=branded_embed(description=f"{mention.display_name} is AFK: {afk_map[mid]}"))

    # auto-responders (keyword -> reply, supports templates)
    content_lower = message.content.lower().strip()
    for ar in data.get("autoresponders", []):
        trigger = (ar.get("trigger") or "").lower().strip()
        if not trigger:
            continue
        match_type = ar.get("match", "contains")
        is_match = (content_lower == trigger) if match_type == "exact" else (trigger in content_lower)
        if is_match:
            templates = data.get("embed_templates", {})
            tpl_name = ar.get("template")
            if tpl_name and tpl_name in templates:
                embed = build_embed_from_template(templates[tpl_name], member=message.author, guild=message.guild)
                view = build_view_from_template(templates[tpl_name])
                await (message.channel.send(embed=embed, view=view) if view else message.channel.send(embed=embed))
            elif ar.get("reply"):
                await message.channel.send(apply_placeholders(ar["reply"], member=message.author, guild=message.guild))
            break

    # automod
    automod = data.get("automod", {})
    if automod.get("enabled"):
        triggered_reason = None
        if any(word and word in content_lower for word in automod.get("banned_words", [])):
            triggered_reason = "banned word"
        if not triggered_reason and automod.get("block_invites") and ("discord.gg/" in content_lower or "discord.com/invite" in content_lower):
            whitelisted = automod.get("whitelisted_domains", [])
            if not any(dom in content_lower for dom in whitelisted):
                triggered_reason = "invite link"
        if not triggered_reason and automod.get("block_mass_mentions") and len(message.mentions) >= automod.get("mass_mention_limit", 5):
            triggered_reason = "mass mentions"
        if not triggered_reason and automod.get("block_caps"):
            letters = [c for c in message.content if c.isalpha()]
            if len(letters) >= automod.get("caps_min_length", 12):
                caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters) * 100
                if caps_ratio >= automod.get("caps_percent_limit", 70):
                    triggered_reason = "excessive caps"
        if not triggered_reason and automod.get("block_spam", True):
            key = (message.guild.id, message.author.id)
            now = time.time()
            window = automod.get("spam_window_seconds", 7)
            limit = automod.get("spam_message_limit", 5)
            times = _spam_times.setdefault(key, [])
            times.append(now)
            _spam_times[key] = [t for t in times if now - t <= window]
            if len(_spam_times[key]) >= limit:
                triggered_reason = "spam"

        if triggered_reason:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            warn_embed = branded_embed(description=f"{message.author.mention} your message was removed by auto-moderation ({triggered_reason}).")
            await message.channel.send(embed=warn_embed, delete_after=5)

            # strike system
            strikes = data.setdefault("automod_strikes", {})
            uid = str(message.author.id)
            strikes[uid] = strikes.get(uid, 0) + 1
            save_guild_data(message.guild.id, data)
            threshold = automod.get("strike_action_at", 3)
            if strikes[uid] >= threshold:
                action = automod.get("strike_action", "mute")
                try:
                    if action == "ban":
                        await message.author.ban(reason="Auto-moderation strikes exceeded")
                    elif action == "kick":
                        await message.author.kick(reason="Auto-moderation strikes exceeded")
                    else:
                        await message.author.timeout(
                            datetime.timedelta(minutes=automod.get("strike_mute_minutes", 30)),
                            reason="Auto-moderation strikes exceeded",
                        )
                    strikes[uid] = 0
                    save_guild_data(message.guild.id, data)
                    log_channel_id = data.get("mod_log_channel") or data.get("log_channel")
                    if log_channel_id:
                        log_channel = message.guild.get_channel(int(log_channel_id))
                        if log_channel:
                            await log_channel.send(embed=branded_embed(
                                title="Auto-Mod Strike Action",
                                description=f"{message.author.mention} reached {threshold} strikes -> **{action}**",
                            ))
                except discord.Forbidden:
                    pass
            return  # don't grant XP / process commands for a removed message

    # leveling (simple cooldown-free XP gain)
    profile = data["levels"].setdefault(str(message.author.id), {"xp": 0, "level": 0})
    profile["xp"] += random.randint(5, 15)
    needed = xp_for_level(profile["level"])
    if profile["xp"] >= needed:
        profile["xp"] -= needed
        profile["level"] += 1
        levelup = data.get("levelup", {})
        role_rewards = levelup.get("role_rewards", {})
        reward_role = None
        reward_role_id = role_rewards.get(str(profile["level"]))
        if reward_role_id:
            reward_role = message.guild.get_role(int(reward_role_id))
            if reward_role:
                try:
                    await message.author.add_roles(reward_role, reason=f"Level {profile['level']} reward")
                except discord.Forbidden:
                    reward_role = None
        target_channel = message.channel
        if levelup.get("enabled") and levelup.get("channel_id"):
            target_channel = message.guild.get_channel(int(levelup["channel_id"])) or message.channel
        extra = {"level": str(profile["level"])}
        sent = await _send_template_or_fallback(target_channel, message.author, message.guild, "levelup", data, extra=extra)
        if not sent:
            desc = f"🎉 {message.author.mention} leveled up to **level {profile['level']}**!"
            if reward_role:
                desc += f"\nUnlocked role: {reward_role.mention}"
            await target_channel.send(embed=branded_embed(description=desc))
    save_guild_data(message.guild.id, data)

    # sticky messages
    sticky = data.get("sticky", {}).get(str(message.channel.id))
    if sticky:
        try:
            if sticky.get("last_message_id"):
                old = await message.channel.fetch_message(int(sticky["last_message_id"]))
                await old.delete()
        except (discord.NotFound, discord.HTTPException):
            pass
        new_msg = await message.channel.send(embed=branded_embed(description=sticky["message"]))
        data["sticky"][str(message.channel.id)]["last_message_id"] = str(new_msg.id)
        save_guild_data(message.guild.id, data)

    await bot.process_commands(message)


async def _log_antinuke(guild, action_type, executor):
    data = get_guild_data(guild.id)
    antinuke = data.get("antinuke", {})
    if not antinuke.get("enabled", True) or executor is None:
        return
    now = time.time()
    window = antinuke.get("action_window", 20)
    limit = antinuke.get("action_limit", 5)
    key = (guild.id, executor.id)
    times = _action_times.setdefault(key, [])
    times.append(now)
    _action_times[key] = [t for t in times if now - t <= window]
    if len(_action_times[key]) >= limit:
        log_channel_id = data.get("log_channel")
        if log_channel_id:
            channel = guild.get_channel(int(log_channel_id))
            if channel:
                await channel.send(embed=branded_embed(title="🚨 Anti-Nuke Triggered", description=f"{executor.mention} performed {len(times)} {action_type} actions rapidly."))
        try:
            member = guild.get_member(executor.id)
            if member and not is_owner(member.id):
                await member.ban(reason="Anti-nuke: suspicious mass actions")
        except discord.Forbidden:
            pass


@bot.event
async def on_guild_channel_delete(channel):
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            await _log_antinuke(channel.guild, "channel-delete", entry.user)
    except discord.Forbidden:
        pass


@bot.event
async def on_guild_role_delete(role):
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            await _log_antinuke(role.guild, "role-delete", entry.user)
    except discord.Forbidden:
        pass


@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    data = get_guild_data(message.guild.id)
    log_channel_id = data.get("mod_log_channel") or data.get("log_channel")
    if log_channel_id:
        channel = message.guild.get_channel(int(log_channel_id))
        if channel:
            await channel.send(embed=branded_embed(title="Message Deleted", description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content or '(no text content)'}"))


@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    data = get_guild_data(before.guild.id)
    log_channel_id = data.get("mod_log_channel") or data.get("log_channel")
    if log_channel_id:
        channel = before.guild.get_channel(int(log_channel_id))
        if channel:
            embed = branded_embed(title="Message Edited")
            embed.add_field(name="Before", value=before.content or "(empty)", inline=False)
            embed.add_field(name="After", value=after.content or "(empty)", inline=False)
            embed.set_footer(text=f"{before.author} • {config.BRAND}", icon_url=config.LOGO_URL)
            await channel.send(embed=embed)


# ---------- birthday check loop ----------

@tasks.loop(hours=1)
async def birthday_loop():
    today = datetime.date.today().strftime("%d-%m")
    for guild in bot.guilds:
        data = get_guild_data(guild.id)
        for uid, date in data.get("birthdays", {}).items():
            if date == today:
                log_channel_id = data.get("log_channel")
                channel = guild.get_channel(int(log_channel_id)) if log_channel_id else guild.system_channel
                if channel:
                    member = guild.get_member(int(uid))
                    name = member.mention if member else uid
                    await channel.send(embed=branded_embed(title="🎂 Happy Birthday!", description=f"Everyone wish {name} a happy birthday!"))


@birthday_loop.before_loop
async def before_birthday_loop():
    await bot.wait_until_ready()


# ---------- rotating status loop ----------

@tasks.loop(minutes=2)
async def status_rotation_loop():
    """If any server configured a status rotation list, cycle the bot's global presence
    through them (global bot status is shared across all servers, so the first non-empty
    configured list wins)."""
    for gid in all_guild_ids():
        data = get_guild_data(gid)
        rotation = data.get("status_rotation", [])
        if rotation:
            text = random.choice(rotation)
            await bot.change_presence(activity=discord.Game(name=text))
            return


@status_rotation_loop.before_loop
async def before_status_rotation_loop():
    await bot.wait_until_ready()


# ---------- keep-alive loop (Render free plan sleep fix) ----------

@tasks.loop(minutes=5)
async def keep_alive_loop():
    """Har 5 minute mein apne web server ko ping karta hai taaki Render
    service ko sleep mode mein na jaane de."""
    try:
        import aiohttp
        url = f"http://127.0.0.1:{config.PORT}/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    pass  # alive
    except Exception:
        pass  # silently ignore -- ping fail hone se bot nahi rukta


@keep_alive_loop.before_loop
async def before_keep_alive_loop():
    await bot.wait_until_ready()


async def start_bot():
    if not config.BOT_TOKEN:
        print("[Pixel] BOT_TOKEN nahi mila -- bot login skip kar raha hoon. Website chalti rahegi.")
        return
    await bot.start(config.BOT_TOKEN)
