"""Arabic Telegram games bot built with python-telegram-bot."""

from __future__ import annotations

import json
import logging
import os
import random
import threading
from pathlib import Path
from typing import Any, Final

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from games_extra import category_menu, extra_menu, handle_callback as handle_extra_callback, handle_text as handle_extra_text
from moderation import (
    ban_command,
    kick_command,
    moderation_message,
    mute_command,
    settings_callback,
    settings_command,
    unban_command,
    unmute_command,
    unwarn_command,
    warn_command,
    warnings_command,
    welcome,
)

LOGGER = logging.getLogger(__name__)
TOKEN_ENV: Final[str] = "TELEGRAM_BOT_TOKEN"
DATA_FILE = Path(__file__).parent / "data" / "players.json"
STORE_LOCK = threading.Lock()

GAME_NAMES: Final[dict[str, str]] = {
    "truth": "🎭 صراحة",
    "challenge": "🔥 تحدي",
    "rps": "✂️ حجر ورق مقص",
    "guess": "🎯 تخمين الرقم",
    "quiz": "🧠 سؤال وجواب",
}

TRUTH_QUESTIONS: Final[list[str]] = [
    "ما أكثر شيء يجعلك تبتسم بسرعة؟",
    "ما المهارة التي تتمنى إتقانها؟",
    "ما أجمل ذكرى لديك من طفولتك؟",
    "ما أكثر عادة تحاول تغييرها؟",
    "لو سافرت الآن، إلى أي بلد ستذهب؟",
]
CHALLENGES: Final[list[str]] = [
    "اكتب جملة كاملة من دون استخدام حرف الألف.",
    "أرسل أول ثلاثة رموز تعبيرية تظهر في لوحة مفاتيحك.",
    "اكتب اسمك معكوساً.",
    "امدح آخر شخص كتب رسالة في المجموعة.",
    "اكتب نكتة قصيرة من تأليفك.",
]
QUIZ_QUESTIONS: Final[list[tuple[str, list[str], int]]] = [
    ("ما عاصمة قطر؟", ["الدوحة", "الرياض", "مسقط"], 0),
    ("كم عدد أيام الأسبوع؟", ["خمسة", "سبعة", "عشرة"], 1),
    ("ما الكوكب المعروف بالكوكب الأحمر؟", ["المريخ", "الزهرة", "زحل"], 0),
    ("ما أكبر محيط على الأرض؟", ["الأطلسي", "الهندي", "الهادئ"], 2),
    ("كم ضلعاً للمثلث؟", ["ثلاثة", "أربعة", "خمسة"], 0),
]
RPS_NAMES: Final[dict[str, str]] = {
    "rock": "🪨 حجر",
    "paper": "📄 ورق",
    "scissors": "✂️ مقص",
}


def get_token() -> str:
    """Read and normalize the secret without ever logging it."""
    token = "".join(os.getenv(TOKEN_ENV, "").split())
    if not token:
        raise RuntimeError(
            f"Missing {TOKEN_ENV}. Create a bot with @BotFather and add its token "
            "to Replit Secrets before starting the bot."
        )
    return token


def _read_players() -> dict[str, dict[str, Any]]:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_players(players: dict[str, dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(DATA_FILE)


def player_name(user: Any) -> str:
    return (user.full_name or user.username or "لاعب").strip()


def add_points(user: Any, amount: int) -> int:
    """Persist points and the latest display name for a Telegram user."""
    user_id = str(user.id)
    with STORE_LOCK:
        players = _read_players()
        record = players.setdefault(
            user_id, {"name": player_name(user), "points": 0, "games_played": 0}
        )
        record["name"] = player_name(user)
        record["points"] = int(record.get("points", 0)) + amount
        record["games_played"] = int(record.get("games_played", 0)) + 1
        _write_players(players)
        return record["points"]


def get_player(user: Any) -> dict[str, Any]:
    with STORE_LOCK:
        record = _read_players().get(str(user.id), {})
        return {
            "name": player_name(user),
            "points": int(record.get("points", 0)),
            "games_played": int(record.get("games_played", 0)),
        }


def ranking() -> list[dict[str, Any]]:
    with STORE_LOCK:
        players = _read_players()
    return sorted(
        (
            {"name": str(value.get("name", "لاعب")), "points": int(value.get("points", 0))}
            for value in players.values()
        ),
        key=lambda item: item["points"],
        reverse=True,
    )


def games_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(name, callback_data=f"game:{key}")
        for key, name in GAME_NAMES.items()
    ]
    return InlineKeyboardMarkup(
        [
            buttons[:2],
            buttons[2:4],
            [buttons[4], InlineKeyboardButton("🎲 لعبة عشوائية", callback_data="game:random")],
            [InlineKeyboardButton("🏆 الترتيب", callback_data="rank")],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🎮 قائمة الألعاب", callback_data="games")]]
    )


def action_keyboard(
    callback: str, label: str = "🔁 مرة أخرى"
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data=callback)],
            [InlineKeyboardButton("🎮 قائمة الألعاب", callback_data="games")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "أهلاً بك! 👋\n\nأنا بوت ألعاب عربي. اكتب /games للعب، "
            "واجمع النقاط وتصدر الترتيب عبر /rank."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "الأوامر المتاحة:\n"
            "/games — افتح قائمة الألعاب\n"
            "/rank — ترتيب اللاعبين\n"
            "/points — نقاطك الحالية\n"
            "/profile — ملفك الشخصي\n"
            "\nأوامر المشرفين:\n"
            "/settings — إعدادات حماية المجموعة\n"
            "/warn /warnings /unwarn — إدارة التحذيرات\n"
            "/mute /unmute /kick /ban /unban — إدارة الأعضاء\n"
            "/about — معلومات عن البوت\n"
            "/id — رقم هذه المحادثة"
        )


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "بوت ألعاب عربي مبني باستخدام Python و python-telegram-bot.\n"
            "العب وحدك أو مع أصدقائك في المجموعة واجمع النقاط!"
        )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat and update.effective_message:
        await update.effective_message.reply_text(
            f"رقم هذه المحادثة هو: {update.effective_chat.id}"
        )


async def games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["active_game"] = None
    text = "🎮 اختر فئة الألعاب:\n\nكل إجابة صحيحة أو فوز يمنحك نقاطاً محفوظة."
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=extra_menu())


async def points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and update.effective_message:
        record = get_player(update.effective_user)
        await update.effective_message.reply_text(
            f"⭐ {record['name']}، لديك {record['points']} نقطة."
        )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and update.effective_message:
        record = get_player(update.effective_user)
        place = next(
            (index for index, item in enumerate(ranking(), 1) if item["name"] == record["name"]),
            "—",
        )
        await update.effective_message.reply_text(
            f"👤 الملف الشخصي\n\n"
            f"الاسم: {record['name']}\n"
            f"النقاط: ⭐ {record['points']}\n"
            f"الألعاب: 🎮 {record['games_played']}\n"
            f"المركز: #{place}"
        )


async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = format_rank()
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=back_keyboard())


def format_rank() -> str:
    players = ranking()
    if not players:
        return "🏆 الترتيب فارغ حالياً.\nابدأ اللعب لتظهر هنا!"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 أفضل اللاعبين:\n"]
    for index, player in enumerate(players[:10], 1):
        marker = medals[index - 1] if index <= 3 else f"{index}."
        lines.append(f"{marker} {player['name']} — ⭐ {player['points']}")
    return "\n".join(lines)


async def show_game(
    query: Any, context: ContextTypes.DEFAULT_TYPE, key: str
) -> None:
    active = context.chat_data.get("active_game")
    if active is not None and active != key:
        await query.answer("هناك لعبة نشطة في هذه المحادثة. اضغط رجوع أولاً.", show_alert=True)
        return
    context.chat_data["active_game"] = key
    if key == "random":
        key = random.choice(list(GAME_NAMES))
        await query.answer(f"تم اختيار {GAME_NAMES[key]}")
    else:
        await query.answer()

    if key in ("truth", "challenge"):
        pool = TRUTH_QUESTIONS if key == "truth" else CHALLENGES
        title = "🎭 صراحة" if key == "truth" else "🔥 تحدي"
        label = "سؤال صراحة جديد" if key == "truth" else "تحدي جديد"
        text = f"{title}\n\n{random.choice(pool)}\n\nأنجزها لتحصل على ⭐ نقطة!"
        markup = action_keyboard(f"new:{key}", f"🔁 {label}")
    elif key == "rps":
        text = "✂️ حجر ورق مقص\n\nاختر حركتك:"
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🪨 حجر", callback_data="rps:rock"),
                    InlineKeyboardButton("📄 ورق", callback_data="rps:paper"),
                ],
                [
                    InlineKeyboardButton("✂️ مقص", callback_data="rps:scissors"),
                    InlineKeyboardButton("🎮 الألعاب", callback_data="games"),
                ],
            ]
        )
    elif key == "guess":
        chat_id = str(query.message.chat_id)
        context.chat_data["guess_number"] = random.randint(1, 10)
        context.chat_data["guess_active"] = True
        text = "🎯 تخمين الرقم\n\nخمّن رقماً من 1 إلى 10. يمكن لكل أعضاء المجموعة المشاركة!"
        markup = guess_keyboard()
    else:
        text, markup = new_quiz(context)

    await query.edit_message_text(text, reply_markup=markup)


def guess_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(str(number), callback_data=f"guess:{number}")
                for number in range(1, 6)
            ],
            [
                InlineKeyboardButton(str(number), callback_data=f"guess:{number}")
                for number in range(6, 11)
            ],
            [InlineKeyboardButton("🎮 قائمة الألعاب", callback_data="games")],
        ]
    )


def new_quiz(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    question, answers, correct = random.choice(QUIZ_QUESTIONS)
    question_id = random.randint(1000, 999999)
    context.chat_data["quiz"] = {"id": question_id, "correct": correct}
    buttons = [
        InlineKeyboardButton(answer, callback_data=f"quiz:{question_id}:{index}")
        for index, answer in enumerate(answers)
    ]
    return (
        f"🧠 سؤال وجواب\n\n{question}",
        InlineKeyboardMarkup(
            [
                [buttons[0], buttons[1]],
                [buttons[2]],
                [InlineKeyboardButton("🎮 قائمة الألعاب", callback_data="games")],
            ]
        ),
    )


async def handle_rps(
    query: Any, context: ContextTypes.DEFAULT_TYPE, choice: str
) -> None:
    bot_choice = random.choice(list(RPS_NAMES))
    wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
    if choice == bot_choice:
        result, amount = "تعادل! 🤝", 1
    elif (choice, bot_choice) in wins:
        result, amount = "فزت! 🎉", 3
    else:
        result, amount = "حظاً أوفر! 😄", 0
    total = add_points(query.from_user, amount)
    await query.answer(result)
    await query.edit_message_text(
        f"✂️ حجر ورق مقص\n\n"
        f"اختيارك: {RPS_NAMES[choice]}\n"
        f"اختياري: {RPS_NAMES[bot_choice]}\n\n"
        f"{result}\n+{amount} نقطة | مجموعك: ⭐ {total}",
        reply_markup=action_keyboard("game:rps", "🔁 العب مرة أخرى"),
    )


async def handle_guess(
    query: Any, context: ContextTypes.DEFAULT_TYPE, number: int
) -> None:
    if not context.chat_data.get("guess_active"):
        await query.answer("ابدأ لعبة جديدة أولاً من /games", show_alert=True)
        return
    target = int(context.chat_data["guess_number"])
    if number == target:
        context.chat_data["guess_active"] = False
        total = add_points(query.from_user, 5)
        await query.answer("إجابة صحيحة! 🎉")
        await query.edit_message_text(
            f"🎯 أحسنت يا {player_name(query.from_user)}!\n"
            f"الرقم كان {target}.\n\n+5 نقاط | مجموعك: ⭐ {total}",
            reply_markup=action_keyboard("game:guess", "🔁 لعبة جديدة"),
        )
    else:
        hint = "أكبر" if number < target else "أصغر"
        await query.answer(f"جرّب رقماً {hint} من {number}!")


async def handle_quiz(
    query: Any, context: ContextTypes.DEFAULT_TYPE, question_id: int, answer: int
) -> None:
    quiz = context.chat_data.get("quiz", {})
    if quiz.get("id") != question_id:
        await query.answer("هذا السؤال انتهى، اضغط سؤال جديد.", show_alert=True)
        return
    if answer == int(quiz["correct"]):
        amount, result = 4, "إجابة صحيحة! 🎉"
    else:
        amount, result = 0, "إجابة غير صحيحة، حاول مرة أخرى في السؤال القادم."
    total = add_points(query.from_user, amount)
    await query.answer(result)
    await query.edit_message_text(
        f"🧠 سؤال وجواب\n\n{result}\n"
        f"{'+' + str(amount) + ' نقاط' if amount else 'لا توجد نقاط هذه المرة'}"
        f" | مجموعك: ⭐ {total}",
        reply_markup=action_keyboard("new:quiz", "🔁 سؤال جديد"),
    )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message:
        return
    data = query.data or ""
    if await settings_callback(query, context):
        return
    if data == "games":
        context.chat_data["active_game"] = None
    if await handle_extra_callback(query, context, data):
        return
    if data == "games":
        await query.answer()
        await query.edit_message_text(
            "🎮 اختر فئة الألعاب:\n\nكل إجابة صحيحة أو فوز يمنحك نقاطاً محفوظة.",
            reply_markup=extra_menu(),
        )
    elif data == "rank":
        await query.answer()
        await query.edit_message_text(format_rank(), reply_markup=back_keyboard())
    elif data.startswith("game:"):
        await show_game(query, context, data.split(":", 1)[1])
    elif data.startswith("new:"):
        await show_game(query, context, data.split(":", 1)[1])
    elif data.startswith("rps:"):
        await handle_rps(query, context, data.split(":", 1)[1])
    elif data.startswith("guess:"):
        await handle_guess(query, context, int(data.split(":", 1)[1]))
    elif data.startswith("quiz:"):
        _, question_id, answer = data.split(":")
        await handle_quiz(query, context, int(question_id), int(answer))
    else:
        await query.answer()


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message and update.effective_message.text:
        if await moderation_message(update, context):
            return
        if update.effective_user:
            context.chat_data.setdefault("participants", {})[
                str(update.effective_user.id)
            ] = player_name(update.effective_user)
        if await handle_extra_text(update, context, update.effective_message.text):
            return
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id if update.effective_chat else 0,
            action=ChatAction.TYPING,
        )
        await update.effective_message.reply_text(update.effective_message.text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Exception while processing update", exc_info=context.error)


def build_application() -> Application:
    application = ApplicationBuilder().token(get_token()).build()
    for command, handler in (
        ("start", start),
        ("help", help_command),
        ("about", about),
        ("id", chat_id),
        ("games", games),
        ("rank", rank),
        ("points", points),
        ("profile", profile),
        ("settings", settings_command),
        ("warn", warn_command),
        ("warnings", warnings_command),
        ("unwarn", unwarn_command),
        ("mute", mute_command),
        ("unmute", unmute_command),
        ("kick", kick_command),
        ("ban", ban_command),
        ("unban", unban_command),
    ):
        application.add_handler(CommandHandler(command, handler))
    application.add_handler(CallbackQueryHandler(callbacks))
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome)
    )
    application.add_handler
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_router)
    ) 
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hamto_reply))

    application.add_error_handler(error_handler)
    return application

HAMTO_RESPONSES = [
    "عيون حمتو 💋",
    "احكي",
    "مافاضي ليك",
    "كلامك كتير 🙂",
    "عيونه😔"
]

async def hamto_reply(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    if "بوت" in text or "حمتو" in text:
        await update.message.reply_text(random.choice(HAMTO_RESPONSES))


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    LOGGER.info("Starting Telegram games bot")
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
