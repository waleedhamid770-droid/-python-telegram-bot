"""Additional Arabic group games for the Telegram bot."""

from __future__ import annotations

import random
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

WORD_ROUNDS = [
    ("قمر", ["شيء يظهر ليلاً", "يضيء في السماء", "ليس نجماً"]),
    ("كتاب", ["شيء نقرأه", "له صفحات", "قد يكون إلكترونياً"]),
    ("بحر", ["ماؤه مالح غالباً", "تعيش فيه الأسماك", "أكبر من النهر"]),
    ("تفاحة", ["فاكهة", "قد تكون حمراء أو خضراء", "سقطت على رأس نيوتن"]),
    ("مفتاح", ["نستخدمه لفتح شيء", "صغير غالباً", "قد يكون إلكترونياً"]),
]
LETTER_PROMPTS = [
    "اذكر اسم حيوان",
    "اذكر اسم بلد",
    "اذكر اسم طعام",
    "اذكر اسماً",
    "اذكر شيئاً في المنزل",
]
FAST_ROUNDS = [
    ("ما عاصمة قطر؟", ["الدوحة", "الرياض", "مسقط"], 0),
    ("كم عدد أصابع اليد الواحدة؟", ["أربعة", "خمسة", "ستة"], 1),
    ("ما لون السماء الصافية؟", ["أزرق", "أخضر", "أسود"], 0),
    ("ما الحيوان الذي يقول مواء؟", ["كلب", "قطة", "حصان"], 1),
]
GROUP_QUIZ = [
    ("ما أكبر كوكب في المجموعة الشمسية؟", ["الأرض", "المشتري", "المريخ"], 1),
    ("كم عدد أشهر السنة؟", ["10", "12", "14"], 1),
    ("ما أسرع حيوان بري؟", ["الفهد", "الفيل", "الأرنب"], 0),
    ("ما اللغة الرسمية في البرازيل؟", ["الإسبانية", "البرتغالية", "الفرنسية"], 1),
]
MOST_QUESTIONS = [
    "من الأكثر حباً للسهر؟",
    "من الأكثر احتمالاً أن يصبح مشهوراً؟",
    "من الأكثر حباً للمغامرات؟",
    "من الأكثر إضحاكاً في المجموعة؟",
    "من الأكثر تنظيماً؟",
]


def extra_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🧩 ألعاب المهارة", callback_data="cat:skill"),
                InlineKeyboardButton("👥 ألعاب المجموعة", callback_data="cat:group"),
            ],
            [
                InlineKeyboardButton("🎉 ألعاب المرح", callback_data="cat:fun"),
                InlineKeyboardButton("◀️ رجوع", callback_data="games"),
            ],
        ]
    )


def category_menu(category: str) -> InlineKeyboardMarkup:
    groups = {
        "classic": [
            ("🎭 صراحة", "game:truth"),
            ("🔥 تحدي", "game:challenge"),
            ("✂️ حجر ورق مقص", "game:rps"),
            ("🎯 تخمين الرقم", "game:guess"),
            ("🧠 سؤال وجواب", "game:quiz"),
            ("🎲 لعبة عشوائية", "game:random"),
        ],
        "skill": [
            ("🎯 تخمين الكلمة", "extra:word"),
            ("🔤 تحدي الحروف", "extra:letter"),
            ("⚡ أسرع إجابة", "extra:fast"),
        ],
        "group": [
            ("❌⭕ XO", "extra:xo"),
            ("🧠 مسابقة جماعية", "extra:groupquiz"),
            ("👥 من الأكثر؟", "extra:most"),
        ],
        "fun": [("🎲 الحظ", "extra:luck")],
    }
    buttons = [InlineKeyboardButton(label, callback_data=data) for label, data in groups[category]]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("◀️ رجوع", callback_data="games")])
    return InlineKeyboardMarkup(rows)


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
    )


def _bot_helpers() -> tuple[Any, Any]:
    # Import at call time to avoid a circular import with bot.py.
    from bot import add_points, player_name

    return add_points, player_name


def _name(user: Any) -> str:
    return _bot_helpers()[1](user)


def _busy(context: Any, key: str) -> bool:
    active = context.chat_data.get("active_game")
    return active is not None and active != key


async def start_extra(query: Any, context: Any, key: str) -> None:
    if _busy(context, key):
        await query.answer("هناك لعبة نشطة في هذه المحادثة. اضغط رجوع أولاً.", show_alert=True)
        return
    context.chat_data["active_game"] = key
    context.chat_data.setdefault("participants", {})[str(query.from_user.id)] = _name(query.from_user)
    if key == "word":
        word, hints = random.choice(WORD_ROUNDS)
        context.chat_data["word_game"] = {"word": word, "hints": hints, "shown": 1}
        await show_word(query, context)
    elif key == "letter":
        letter = random.choice(list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي"))
        context.chat_data["letter_game"] = {
            "letter": letter,
            "prompt": random.choice(LETTER_PROMPTS),
            "answers": [],
        }
        await query.answer()
        await query.edit_message_text(
            f"🔤 تحدي الحروف\n\nالحرف هو: «{letter}»\n"
            f"{context.chat_data['letter_game']['prompt']} يبدأ بحرف {letter}.\n"
            "أرسل إجابتك في المجموعة لتحصل على ⭐ نقطتين!",
            reply_markup=back_button(),
        )
    elif key == "fast":
        await new_fast(query, context)
    elif key == "xo":
        context.chat_data["xo"] = {"board": [""] * 9, "players": [], "turn": 0}
        await query.answer()
        await render_xo(query, context)
    elif key == "groupquiz":
        context.chat_data["groupquiz"] = {"index": 0, "scores": {}, "answered": set()}
        await new_group_question(query, context)
    elif key == "luck":
        await play_luck(query, context)
    elif key == "most":
        participants = context.chat_data.get("participants", {})
        context.chat_data["most"] = {
            "question": random.choice(MOST_QUESTIONS),
            "votes": {},
            "options": dict(participants),
        }
        await query.answer()
        await render_most(query, context)


async def show_word(query: Any, context: Any) -> None:
    game = context.chat_data["word_game"]
    await query.answer()
    await query.edit_message_text(
        "🎯 تخمين الكلمة\n\n"
        f"التلميح {game['shown']}: {game['hints'][game['shown'] - 1]}\n\n"
        "اكتب تخمينك في المحادثة. اطلب تلميحاً إضافياً إذا احتجت.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💡 تلميح إضافي", callback_data="extra:wordhint")],
                [InlineKeyboardButton("🔁 كلمة جديدة", callback_data="extra:wordnew")],
                [InlineKeyboardButton("◀️ رجوع", callback_data="games")],
            ]
        ),
    )


async def handle_word_text(update: Any, context: Any, text: str) -> bool:
    game = context.chat_data.get("word_game")
    if context.chat_data.get("active_game") != "word" or not game:
        return False
    guess = _normalize(text)
    if guess == _normalize(game["word"]):
        add_points, _ = _bot_helpers()
        total = add_points(update.effective_user, 5)
        context.chat_data["active_game"] = None
        await update.effective_message.reply_text(
            f"🎉 إجابة صحيحة يا {_name(update.effective_user)}!\n"
            f"الكلمة هي: {game['word']}\n+5 نقاط | مجموعك: ⭐ {total}",
            reply_markup=back_button(),
        )
    else:
        await update.effective_message.reply_text("ليست الكلمة الصحيحة. حاول مرة أخرى أو اطلب تلميحاً!")
    return True


async def handle_letter_text(update: Any, context: Any, text: str) -> bool:
    game = context.chat_data.get("letter_game")
    if context.chat_data.get("active_game") != "letter" or not game:
        return False
    answer = _normalize(text)
    if not answer or not answer.startswith(_normalize(game["letter"])):
        await update.effective_message.reply_text(
            f"الإجابة يجب أن تبدأ بحرف «{game['letter']}»."
        )
        return True
    answers = game["answers"]
    user_id = str(update.effective_user.id)
    if user_id in answers:
        await update.effective_message.reply_text("لقد حصلت على نقاطك في هذه الجولة بالفعل.")
        return True
    answers.append(user_id)
    total = _bot_helpers()[0](update.effective_user, 2)
    await update.effective_message.reply_text(
        f"✅ إجابة ممتازة يا {_name(update.effective_user)}: {text}\n"
        f"+2 نقاط | مجموعك: ⭐ {total}"
    )
    return True


async def handle_text(update: Any, context: Any, text: str) -> bool:
    """Route free-form answers for word and letter games."""
    if await handle_word_text(update, context, text):
        return True
    return await handle_letter_text(update, context, text)


def _normalize(value: str) -> str:
    return re.sub(r"[\sـًٌٍَُِّّْ]", "", value.strip().lower())


async def new_fast(query: Any, context: Any) -> None:
    question, answers, correct = random.choice(FAST_ROUNDS)
    context.chat_data["fast"] = {"correct": correct, "winner": None}
    await query.answer()
    await query.edit_message_text(
        f"⚡ أسرع إجابة\n\n{question}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(answer, callback_data=f"fast:{index}") for index, answer in enumerate(answers)]]
            + [[InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
        ),
    )


async def handle_fast(query: Any, context: Any, choice: int) -> None:
    game = context.chat_data.get("fast")
    if not game or game.get("winner"):
        await query.answer("تم حسم هذه الجولة بالفعل.", show_alert=True)
        return
    if choice != game["correct"]:
        await query.answer("إجابة غير صحيحة، أسرع!", show_alert=False)
        return
    game["winner"] = str(query.from_user.id)
    total = _bot_helpers()[0](query.from_user, 5)
    await query.answer("أنت الأسرع! 🎉")
    await query.edit_message_text(
        f"⚡ الفائز هو {_name(query.from_user)}! 🎉\n+5 نقاط | مجموعك: ⭐ {total}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 سؤال جديد", callback_data="extra:fastnew")],
                [InlineKeyboardButton("◀️ رجوع", callback_data="games")],
            ]
        ),
    )


def xo_keyboard(board: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for start in range(0, 9, 3):
        row = []
        for index in range(start, start + 3):
            row.append(InlineKeyboardButton(board[index] or "▫️", callback_data=f"xo:cell:{index}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("➕ انضمام للعبة", callback_data="xo:join")])
    rows.append([InlineKeyboardButton("🔁 لعبة جديدة", callback_data="extra:xonew"),
                 InlineKeyboardButton("◀️ رجوع", callback_data="games")])
    return InlineKeyboardMarkup(rows)


async def render_xo(query: Any, context: Any, notice: str = "") -> None:
    game = context.chat_data["xo"]
    players = game["players"]
    if len(players) < 2:
        text = "❌⭕ XO\n\nاضغط «انضمام» ليشارك لاعب ثانٍ."
    else:
        turn = players[game["turn"]]
        text = f"❌⭕ XO\n\nدور: {turn['name']}\n❌ {players[0]['name']}  |  ⭕ {players[1]['name']}"
    if notice:
        text += f"\n\n{notice}"
    await query.answer()
    await query.edit_message_text(text, reply_markup=xo_keyboard(game["board"]))


async def handle_xo(query: Any, context: Any, action: str, value: str = "") -> None:
    game = context.chat_data.get("xo")
    if not game:
        return
    user_id = str(query.from_user.id)
    if action == "join":
        if any(player["id"] == user_id for player in game["players"]):
            await query.answer("أنت مشارك بالفعل.")
        elif len(game["players"]) >= 2:
            await query.answer("اللعبة ممتلئة.", show_alert=True)
        else:
            symbol = "❌" if not game["players"] else "⭕"
            game["players"].append({"id": user_id, "name": _name(query.from_user), "symbol": symbol})
            await render_xo(query, context, f"انضم {_name(query.from_user)} للعبة.")
        return
    if len(game["players"]) < 2:
        await query.answer("يجب أن ينضم لاعبان أولاً.", show_alert=True)
        return
    if game["players"][game["turn"]]["id"] != user_id:
        await query.answer("ليس دورك.", show_alert=True)
        return
    index = int(value)
    if game["board"][index]:
        await query.answer("هذا المربع مستخدم.", show_alert=True)
        return
    game["board"][index] = game["players"][game["turn"]]["symbol"]
    winner = _winner(game["board"])
    if winner:
        player = game["players"][game["turn"]]
        total = _bot_helpers()[0](query.from_user, 5)
        await query.answer("فزت! 🎉")
        await query.edit_message_text(
            f"❌⭕ فاز {player['name']}! 🎉\n+5 نقاط | مجموعك: ⭐ {total}",
            reply_markup=xo_keyboard(game["board"]),
        )
        game["players"] = []
        return
    if all(game["board"]):
        await query.answer("تعادل! 🤝")
        await query.edit_message_text("❌⭕ انتهت اللعبة بالتعادل! 🤝", reply_markup=xo_keyboard(game["board"]))
        game["players"] = []
        return
    game["turn"] = 1 - game["turn"]
    await render_xo(query, context)


def _winner(board: list[str]) -> str:
    for a, b, c in ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)):
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return ""


async def new_group_question(query: Any, context: Any) -> None:
    game = context.chat_data["groupquiz"]
    if game["index"] >= len(GROUP_QUIZ):
        lines = ["🏁 انتهت المسابقة الجماعية!\n"]
        for index, (user_id, score) in enumerate(sorted(game["scores"].items(), key=lambda item: item[1], reverse=True), 1):
            lines.append(f"{index}. {score['name']} — ⭐ {score['points']}")
        context.chat_data["active_game"] = None
        await query.answer()
        await query.edit_message_text("\n".join(lines), reply_markup=back_button())
        return
    question, answers, _ = GROUP_QUIZ[game["index"]]
    game["answered"] = set()
    await query.answer()
    await query.edit_message_text(
        f"🧠 مسابقة جماعية — السؤال {game['index'] + 1}/{len(GROUP_QUIZ)}\n\n{question}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(answer, callback_data=f"gq:{index}") for index, answer in enumerate(answers)]]
            + [[InlineKeyboardButton("⏭️ السؤال التالي", callback_data="gq:next")],
               [InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
        ),
    )


async def handle_group_quiz(query: Any, context: Any, action: str) -> None:
    game = context.chat_data.get("groupquiz")
    if not game:
        return
    if action == "next":
        game["index"] += 1
        await new_group_question(query, context)
        return
    if str(query.from_user.id) in game["answered"]:
        await query.answer("أجبت عن هذا السؤال بالفعل.")
        return
    game["answered"].add(str(query.from_user.id))
    question, answers, correct = GROUP_QUIZ[game["index"]]
    answer = int(action)
    player = game["scores"].setdefault(str(query.from_user.id), {"name": _name(query.from_user), "points": 0})
    if answer == correct:
        player["points"] += 3
        _bot_helpers()[0](query.from_user, 3)
        result = "إجابة صحيحة! +3 نقاط 🎉"
    else:
        result = "إجابة غير صحيحة."
    await query.answer(result)
    await query.edit_message_text(
        f"🧠 {result}\n\nالسؤال {game['index'] + 1}: {question}\n"
        "يمكن لبقية اللاعبين الإجابة، ثم اضغط «السؤال التالي» للمتابعة.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(answer_text, callback_data=f"gq:{index}")
              for index, answer_text in enumerate(answers)]]
            + [[InlineKeyboardButton("⏭️ السؤال التالي", callback_data="gq:next")],
             [InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
        ),
    )


async def play_luck(query: Any, context: Any) -> None:
    outcome = random.choices(["win", "loss", "draw"], weights=[50, 30, 20])[0]
    amount = 2 if outcome == "win" else -1 if outcome == "loss" else 0
    total = _bot_helpers()[0](query.from_user, amount)
    messages = {"win": "حظك سعيد! ربحت ⭐ نقطتين 🎉", "loss": "هذه المرة لم يحالفك الحظ. خسرت نقطة واحدة.", "draw": "تعادل الحظ! لا ربح ولا خسارة 🤝"}
    context.chat_data["active_game"] = None
    await query.answer()
    await query.edit_message_text(
        f"🎲 الحظ\n\n{messages[outcome]}\nمجموعك الآن: ⭐ {total}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔁 جرب حظك", callback_data="extra:luck")],
             [InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
        ),
    )


async def render_most(query: Any, context: Any) -> None:
    game = context.chat_data["most"]
    options = game["options"] or {str(query.from_user.id): _name(query.from_user)}
    game["options"] = options
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"most:vote:{user_id}")]
        for user_id, name in list(options.items())[:8]
    ]
    buttons.append([InlineKeyboardButton("📊 عرض النتيجة", callback_data="most:result")])
    buttons.append([InlineKeyboardButton("◀️ رجوع", callback_data="games")])
    await query.answer()
    await query.edit_message_text(f"👥 من الأكثر؟\n\n{game['question']}\n\nصوّت لشخص واحد:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_most(query: Any, context: Any, action: str) -> None:
    game = context.chat_data.get("most")
    if not game:
        return
    if action.startswith("vote:"):
        game["votes"][str(query.from_user.id)] = action.split(":", 1)[1]
        await query.answer("تم تسجيل تصويتك ✅")
        return
    counts: dict[str, int] = {}
    for target in game["votes"].values():
        counts[target] = counts.get(target, 0) + 1
    winner_id = max(counts, key=counts.get) if counts else ""
    winner = game["options"].get(winner_id, "لا أحد بعد")
    context.chat_data["active_game"] = None
    await query.answer()
    await query.edit_message_text(
        f"👥 نتيجة «من الأكثر؟»\n\n{game['question']}\n"
        f"الفائز بالتصويت: {winner} 🎉\nعدد الأصوات: {counts.get(winner_id, 0)}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔁 سؤال جديد", callback_data="extra:most")],
             [InlineKeyboardButton("◀️ رجوع", callback_data="games")]]
        ),
    )


async def handle_callback(query: Any, context: Any, data: str) -> bool:
    if data.startswith("extra:"):
        action = data.split(":", 1)[1]
        if action in {"word", "letter", "fast", "xo", "groupquiz", "luck", "most"}:
            await start_extra(query, context, action)
        elif action == "wordhint":
            game = context.chat_data.get("word_game")
            if game:
                game["shown"] = min(game["shown"] + 1, len(game["hints"]))
                await show_word(query, context)
        elif action == "wordnew":
            context.chat_data.pop("word_game", None)
            await start_extra(query, context, "word")
        elif action == "fastnew":
            await new_fast(query, context)
        elif action == "xonew":
            await start_extra(query, context, "xo")
        return True
    if data.startswith("cat:"):
        await query.answer()
        await query.edit_message_text("🎮 اختر فئة الألعاب:", reply_markup=category_menu(data.split(":", 1)[1]))
        return True
    if data.startswith("fast:"):
        await handle_fast(query, context, int(data.split(":", 1)[1]))
        return True
    if data.startswith("xo:"):
        _, action, *value = data.split(":")
        await handle_xo(query, context, action, value[0] if value else "")
        return True
    if data.startswith("gq:"):
        await handle_group_quiz(query, context, data.split(":", 1)[1])
        return True
    if data.startswith("most:"):
        await handle_most(query, context, data.split(":", 1)[1])
        return True
    return False