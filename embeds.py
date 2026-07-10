import discord
import config


def branded_embed(title=None, description=None, color=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color if color is not None else config.COLOR_INT,
    )
    embed.set_thumbnail(url=config.LOGO_URL)
    embed.set_footer(text=f"{config.DEVELOPER} • {config.BRAND}", icon_url=config.LOGO_URL)
    embed.timestamp = discord.utils.utcnow()
    return embed


def youtube_button_view(extra_buttons=None):
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Subscribe on YouTube", style=discord.ButtonStyle.link,
                                     url=config.YOUTUBE_URL, emoji="▶️"))
    for btn in extra_buttons or []:
        view.add_item(btn)
    return view


def apply_placeholders(text, member=None, guild=None, extra=None):
    """Replace {user}, {user.mention}, {user.name}, {user.avatar}, {server}, {membercount},
    {inviter} placeholders inside any template string. Safe against missing values."""
    if not text:
        return text
    values = {
        "user": member.mention if member else "",
        "user.mention": member.mention if member else "",
        "user.name": (member.display_name if member else ""),
        "user.tag": str(member) if member else "",
        "user.avatar": (member.display_avatar.url if member else ""),
        "server": guild.name if guild else "",
        "membercount": str(guild.member_count) if guild else "",
        "inviter": "",
    }
    if extra:
        values.update(extra)
    out = text
    for key, val in values.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def build_embed_from_template(tpl: dict, member=None, guild=None, extra=None) -> discord.Embed:
    """Turn a saved template dict (from the website's universal template builder) into a
    real discord.Embed, applying {user}/{server}/etc placeholders. Mentions like <@id>,
    <@&id>, <#id> stored as plain text render as real pings/links automatically."""
    color = 0x7C3AED
    raw_color = (tpl.get("color") or "").strip().lstrip("#")
    if raw_color:
        try:
            color = int(raw_color, 16)
        except ValueError:
            pass

    def ph(text):
        return apply_placeholders(text, member=member, guild=guild, extra=extra)

    embed = discord.Embed(
        title=ph(tpl.get("title") or None),
        description=ph(tpl.get("description") or None),
        color=color,
    )
    if tpl.get("image_url"):
        embed.set_image(url=ph(tpl["image_url"]))
    if tpl.get("thumbnail_url"):
        embed.set_thumbnail(url=ph(tpl["thumbnail_url"]))
    if tpl.get("author_name"):
        embed.set_author(name=ph(tpl["author_name"]), icon_url=tpl.get("author_icon") or None)
    if tpl.get("footer_text"):
        embed.set_footer(text=ph(tpl["footer_text"]), icon_url=tpl.get("footer_icon") or None)
    for field in tpl.get("fields", []):
        name = ph((field.get("name") or "\u200b").strip()) or "\u200b"
        value = ph((field.get("value") or "\u200b").strip()) or "\u200b"
        embed.add_field(name=name, value=value, inline=bool(field.get("inline")))
    return embed


def build_view_from_template(tpl: dict):
    """Build a discord.ui.View with link buttons defined on the template, or None if empty."""
    buttons = tpl.get("buttons") or []
    if not buttons:
        return None
    view = discord.ui.View(timeout=None)
    for btn in buttons[:5]:
        label = (btn.get("label") or "Link").strip()[:80]
        url = btn.get("url") or ""
        if not url:
            continue
        view.add_item(discord.ui.Button(label=label, style=discord.ButtonStyle.link, url=url))
    return view
