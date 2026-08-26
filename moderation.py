"""Persistent Arabic group protection and moderation for the Telegram bot."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, TelegramError

LOGGER = logging.getLogger(__name__)
MOD_FILE = Path(__file__).parent / "data" / "moderation.json"
MOD_LOCK = threading.Lock()
LINK_RE = re.compile(
    r"(?i)(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+|"
    r"(?:[a-z0-9-]+\.)+(?:com|net|org|io|co|me|ly|info|xyz)(?:/\S*)?)"
)


def _default_group() -> dict[str, Any]:
    return {
        "protection": True,
        "anti_spam": True,
        "link_protection": True,
        "welcome": True,
        "warning_limit": 3,
        "spam_limit": 5,
        "spam_window": 8,
        "warnings": {},
        "logs": [],
    }


def _read() -> dict[str, Any]:
    try:
        return json.loads(MOD_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(data: dict[str, Any]) -> None:
    MOD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MOD_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(MOD_FILE)


def group_settings(chat_id: int) -> dict[str, Any]:
    key = str(chat_id)
    with MOD_LOCK:
        data = _read()
        group = _default_group()
        group.update(data.get(key, {}))
        group["warnings"] = data.get(key, {}).get("warnings", {})
        group["logs"] = data.get(key, {}).get("logs", [])
        return group


def update_settings(chat_id: int, **changes: Any) -> dict[str, Any]:
    key = str(chat_id)
    with MOD_LOCK:
        data = _read()
        group = _default_group()
        group.update(data.get(key, {}))
        group.update(changes)
        data[key] = group
        _write(data)
        return group


def _record(chat_id: int, **entry: Any) -> None:
    key = str(chat_id)
    with MOD_LOCK:
        data = _read()
        group = _default_group()
        group.update(data.get(key, {}))
        group["logs"] = (data.get(key, {}).get("logs", []) + [entry])[-100:]
        data[key] = group
        _write(data)


def _warnings(chat_id: int, user_id: int) -> list[dict[str, Any]]:
    return group_settings(chat_id).get("warnings", {}).get(str(user_id), [])


def warning_count(chat_id: int, user_id: int) -> int:
    return len(_warnings(chat_id, user_id))


def add_warning(chat_id: int, user_id: int, user_name: str, admin_name: str, reason: str) -> int:
    key = str(chat_id)
    user_key = str(user_id)
    with MOD_LOCK:
        data = _read()
        group = _default_group()
        group.update(data.get(key, {}))
        warnings = group.setdefault("warnings", {})
        warnings.setdefault(user_key, []).append(
            {
                "reason": reason or "بدون سبب",
                "admin": admin_name,
                "name": user_name,
                "time": datetime.now(timezone.utc).isoformat(),
            }
        )
        data[key] = group
        _write(data)
        count = len(warnings[user_key])
    _record(chat_id, action="warn", user=user_name, admin=admin_name, reason=reason or "بدون سبب")
    return count


def remove_warning(chat_id: int, user_id: int) -> int:
    key = str(chat_id)
    user_key = str(user_id)
    with MOD_LOCK:
        data = _read()
        group = _default_group()
        group.update(data.get(key, {}))
        warnings = group.setdefault("warnings", {})
        entries = warnings.get(user_key, [])
        if entries:
            entries.pop()
        if entries:
            warnings[user_key] = entries
        else:
            warnings.pop(user_key, None)
        data[key] = group
        _write(data)
        return len(entries)


def warnings_text(chat_id: int, user_id: int, name: str) -> str:
    entries = _warnings(chat_id, user_id)
    if not entries:
        return f"⚠️ لا توجد تحذيرات مسجلة على {name}."
    lines = [f"⚠️ تحذيرات {name}: {len(entries)}\n"]
    for index, entry in enumerate(entries, 1):
        lines.append(f"{index}. {entry.get('reason', 'بدون سبب')} — {entry.get('time', '')[:10]}")
    return "\n".join(lines)


async def is_admin(bot: Any, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except TelegramError:
        return False


async def bot_permissions(bot: Any, chat_id: int) -> tuple[bool, str]:
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
    except TelegramError:
        return False, "تعذر التحقق من صلاحيات البوت."
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        return False, "يجب أن يكون البوت مشرفاً في المجموعة."
    return True, ""


def is_group(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in ("group", "supergroup"))


async def require_admin(update: Update, context: Any) -> bool:
    if not is_group(update) or not update.effective_user or not update.effective_chat:
        if update.effective_message:
            await update.effective_message.reply_text("هذا الأمر متاح داخل المجموعات فقط.")
        return False
    if not await is_admin(context.bot, update.effective_chat.id, update.effective_user.id):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
        return False
    return True


def settings_keyboard(settings: dict[str, Any]) -> InlineKeyboardMarkup:
    def status(value: bool) -> str:
        return "✅ تشغيل" if value else "❌ إيقاف"

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"🛡️ الحماية: {status(settings['protection'])}", callback_data="mod:toggle:protection")],
            [InlineKeyboardButton(f"🛡️ مكافحة السبام: {status(settings['anti_spam'])}", callback_data="mod:toggle:anti_spam")],
            [InlineKeyboardButton(f"🔗 منع الروابط: {status(settings['link_protection'])}", callback_data="mod:toggle:link_protection")],
            [InlineKeyboardButton(f"👋 الترحيب: {status(settings['welcome'])}", callback_data="mod:toggle:welcome")],
            [
                InlineKeyboardButton("➖ حد التحذيرات", callback_data="mod:warning:-1"),
                InlineKeyboardButton(f"⚠️ {settings['warning_limit']}", callback_data="mod:noop"),
                InlineKeyboardButton("➕ حد التحذيرات", callback_data="mod:warning:1"),
            ],
            [
                InlineKeyboardButton("➖ حد السبام", callback_data="mod:spam:-1"),
                InlineKeyboardButton(f"📨 {settings['spam_limit']}", callback_data="mod:noop"),
                InlineKeyboardButton("➕ حد السبام", callback_data="mod:spam:1"),
            ],
            [InlineKeyboardButton("📋 سجل الإشراف", callback_data="mod:logs")],
            [InlineKeyboardButton("◀️ رجوع", callback_data="games")],
        ]
    )


def settings_text(settings: dict[str, Any]) -> str:
    return (
        "⚙️ إعدادات حماية المجموعة\n\n"
        f"الحماية العامة: {'✅ مفعلة' if settings['protection'] else '❌ متوقفة'}\n"
        f"مكافحة السبام: {'✅ مفعلة' if settings['anti_spam'] else '❌ متوقفة'}\n"
        f"منع الروابط: {'✅ مفعل' if settings['link_protection'] else '❌ متوقف'}\n"
        f"رسائل الترحيب: {'✅ مفعلة' if settings['welcome'] else '❌ متوقفة'}\n"
        f"الحد الأقصى للتحذيرات: {settings['warning_limit']}\n"
        f"حد السبام: {settings['spam_limit']} رسائل خلال {settings['spam_window']} ثوانٍ"
    )


async def settings_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context) or not update.effective_chat:
        return
    settings = group_settings(update.effective_chat.id)
    await update.effective_message.reply_text(settings_text(settings), reply_markup=settings_keyboard(settings))


async def settings_callback(query: Any, context: Any) -> bool:
    data = query.data or ""
    if not data.startswith("mod:"):
        return False
    if not await is_admin(context.bot, query.message.chat_id, query.from_user.id):
        await query.answer("⛔ لوحة الإعدادات للمشرفين فقط.", show_alert=True)
        return True
    chat_id = query.message.chat_id
    settings = group_settings(chat_id)
    parts = data.split(":")
    if parts[1] == "toggle" and len(parts) == 3:
        field = parts[2]
        update_settings(chat_id, **{field: not settings[field]})
    elif parts[1] == "warning":
        update_settings(chat_id, warning_limit=max(1, min(10, settings["warning_limit"] + int(parts[2]))))
    elif parts[1] == "spam":
        update_settings(chat_id, spam_limit=max(3, min(20, settings["spam_limit"] + int(parts[2]))))
    elif parts[1] == "logs":
        logs = settings.get("logs", [])[-10:]
        text = "📋 آخر إجراءات الإشراف:\n\n" + (
            "\n".join(f"• {item.get('action')} — {item.get('user', '')}" for item in logs)
            if logs else "لا توجد إجراءات مسجلة."
        )
        await query.answer()
        await query.edit_message_text(text, reply_markup=settings_keyboard(settings))
        return True
    await query.answer("تم تحديث الإعدادات ✅")
    settings = group_settings(chat_id)
    await query.edit_message_text(settings_text(settings), reply_markup=settings_keyboard(settings))
    return True


async def target_member(update: Update, context: Any) -> Any | None:
    if not update.effective_chat or not update.effective_message:
        return None
    if update.effective_message.reply_to_message:
        return update.effective_message.reply_to_message.from_user
    if context.args:
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(context.args[0]))
            return member.user
        except (ValueError, TelegramError):
            return None
    return None


async def target_is_protected(update: Update, context: Any, target: Any) -> bool:
    if not target or not update.effective_chat:
        return False
    if await is_admin(context.bot, update.effective_chat.id, target.id):
        if update.effective_message:
            await update.effective_message.reply_text("🛡️ لا يمكن معاقبة مشرف في المجموعة.")
        return True
    return False


async def warn_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /warn بالرد على رسالة العضو، ويمكنك كتابة السبب بعدها.")
        return
    if await target_is_protected(update, context, target):
        return
    reason = " ".join(context.args) if context.args else "بدون سبب"
    count = add_warning(update.effective_chat.id, target.id, target.full_name, update.effective_user.full_name, reason)
    limit = group_settings(update.effective_chat.id)["warning_limit"]
    text = f"⚠️ تم تحذير {target.full_name}.\nالتحذيرات: {count}/{limit}\nالسبب: {reason}"
    if count >= limit:
        ok, message = await mute_member(context.bot, update.effective_chat.id, target, 3600, "تجاوز حد التحذيرات")
        text += f"\n🔇 تم كتم العضو لمدة ساعة." if ok else f"\n⚠️ تعذر الكتم: {message}"
    await update.effective_message.reply_text(text)


async def warnings_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        target = update.effective_user
    await update.effective_message.reply_text(warnings_text(update.effective_chat.id, target.id, target.full_name))


async def unwarn_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /unwarn بالرد على رسالة العضو.")
        return
    remaining = remove_warning(update.effective_chat.id, target.id)
    await update.effective_message.reply_text(f"✅ تمت إزالة تحذير من {target.full_name}. المتبقي: {remaining}")


async def mute_member(bot: Any, chat_id: int, target: Any, seconds: int, reason: str) -> tuple[bool, str]:
    try:
        await bot.restrict_chat_member(
            chat_id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now(timezone.utc) + timedelta(seconds=seconds),
        )
        _record(chat_id, action="mute", user=target.full_name, reason=reason)
        return True, ""
    except TelegramError as error:
        return False, str(error)


async def mute_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /mute بالرد على رسالة العضو. المدة الافتراضية ساعة.")
        return
    if await target_is_protected(update, context, target):
        return
    ok, error = await mute_member(context.bot, update.effective_chat.id, target, 3600, "أمر مشرف")
    await update.effective_message.reply_text(
        f"🔇 تم كتم {target.full_name} لمدة ساعة." if ok else f"⚠️ تعذر الكتم: {error}"
    )


async def unmute_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /unmute بالرد على رسالة العضو.")
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True),
        )
        _record(update.effective_chat.id, action="unmute", user=target.full_name)
        await update.effective_message.reply_text(f"🔊 تم إلغاء كتم {target.full_name}.")
    except TelegramError as error:
        await update.effective_message.reply_text(f"⚠️ تعذر إلغاء الكتم: {error}")


async def ban_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /ban بالرد على رسالة العضو.")
        return
    if await target_is_protected(update, context, target):
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        _record(update.effective_chat.id, action="ban", user=target.full_name, admin=update.effective_user.full_name)
        await update.effective_message.reply_text(f"🚫 تم حظر {target.full_name}.")
    except TelegramError as error:
        await update.effective_message.reply_text(f"⚠️ تعذر الحظر: {error}")


async def kick_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target:
        await update.effective_message.reply_text("استخدم /kick بالرد على رسالة العضو.")
        return
    if await target_is_protected(update, context, target):
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        _record(update.effective_chat.id, action="kick", user=target.full_name, admin=update.effective_user.full_name)
        await update.effective_message.reply_text(f"👢 تم طرد {target.full_name}.")
    except TelegramError as error:
        await update.effective_message.reply_text(f"⚠️ تعذر الطرد: {error}")


async def unban_command(update: Update, context: Any) -> None:
    if not await require_admin(update, context):
        return
    target = await target_member(update, context)
    if not target and context.args:
        try:
            target = type("Target", (), {"id": int(context.args[0]), "full_name": context.args[0]})()
        except ValueError:
            target = None
    if not target:
        await update.effective_message.reply_text("استخدم /unban مع الرد على العضو أو اكتب رقمه.")
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id, only_if_banned=True)
        _record(update.effective_chat.id, action="unban", user=target.full_name, admin=update.effective_user.full_name)
        await update.effective_message.reply_text(f"✅ تم إلغاء حظر {target.full_name}.")
    except TelegramError as error:
        await update.effective_message.reply_text(f"⚠️ تعذر إلغاء الحظر: {error}")


def _spam_state(context: Any) -> dict[str, list[tuple[float, str]]]:
    return context.application.bot_data.setdefault("moderation_spam", {})


async def moderation_message(update: Update, context: Any) -> bool:
    if not is_group(update) or not update.effective_message or not update.effective_user or not update.effective_chat:
        return False
    settings = group_settings(update.effective_chat.id)
    if not settings["protection"]:
        return False
    user = update.effective_user
    if await is_admin(context.bot, update.effective_chat.id, user.id):
        return False
    text = update.effective_message.text or update.effective_message.caption or ""
    if settings["link_protection"] and LINK_RE.search(text):
        try:
            await update.effective_message.delete()
            await update.effective_chat.send_message("🔗 تم حذف رابط من عضو غير مشرف.")
            _record(update.effective_chat.id, action="link_delete", user=user.full_name)
        except TelegramError:
            await update.effective_chat.send_message(
                "⚠️ لم أستطع حذف الرابط. امنحني صلاحية حذف الرسائل لأتمكن من حماية المجموعة."
            )
        return True
    if settings["anti_spam"]:
        state = _spam_state(context)
        key = f"{update.effective_chat.id}:{user.id}"
        now = time.monotonic()
        recent = [(stamp, body) for stamp, body in state.get(key, []) if now - stamp <= settings["spam_window"]]
        recent.append((now, text))
        state[key] = recent[-settings["spam_limit"] :]
        repeated = len(recent) >= 3 and len({body for _, body in recent[-3:]}) == 1
        flooded = len(recent) >= settings["spam_limit"]
        if repeated or flooded:
            state[key] = []
            count = add_warning(update.effective_chat.id, user.id, user.full_name, "الحماية التلقائية", "رسائل متكررة أو كثيرة")
            await update.effective_message.reply_text(f"⚠️ {user.full_name}، تحذير تلقائي ({count}/{settings['warning_limit']}).")
            _record(update.effective_chat.id, action="spam_warning", user=user.full_name)
            if count >= settings["warning_limit"]:
                await mute_member(context.bot, update.effective_chat.id, user, 600, "سبام")
            return True
    return False


async def welcome(update: Update, context: Any) -> None:
    if not is_group(update) or not update.effective_chat:
        return
    if not group_settings(update.effective_chat.id)["welcome"]:
        return
    members = update.effective_message.new_chat_members if update.effective_message else []
    names = "، ".join(member.full_name for member in members)
    if names:
        await update.effective_message.reply_text(f"👋 أهلاً وسهلاً {names} في مجموعتنا!")