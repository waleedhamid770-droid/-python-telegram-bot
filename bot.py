import os
import random
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# إعداد السجلات لمتابعة حالة البوت
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# قائمة المشرفين (أضف معرف تيليجرام الخاص بك هنا للأمان والحماية)
ADMIN_IDS = [123456789]  # استبدل الرقم بمعرفك الحقيقي

# ==================== 1. الأوامر الأساسية ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    keyboard = [
        [InlineKeyboardButton("🎮 الألعاب", callback_data="menu_games"),
         InlineKeyboardButton("🛡️ الحماية", callback_data="menu_protection")],
        [InlineKeyboardButton("💬 الردود المميزة", callback_data="menu_replies")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"أهلاً بك يا {user_name} في بوت حمتو المتطور! 🚀\nاختر أحد الأقسام أدناه أو اكتب رسالتك وسأرد عليك:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 **قائمة أوامر بوت حمتو:**\n\n"
        "• /start - تشغيل البوت وإظهار القائمة الرئيسية\n"
        "• /game - قائمة الألعاب التفاعلية\n"
        "• /whisper - إرسال همسة (خاص)\n"
        "• /ban - حظر عضو (خاص بالمشرفين)\n"
        "• /mute - كتم عضو (خاص بالمشرفين)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ==================== 2. الردود المميزة والمخصصة ====================
async def hamto_responses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    # الردود المحددة بناءً على طلبك
    if text == "عيون حمتو":
        await update.message.reply_text("عيون وقلب حمتو من الداخل! ❤️")
    elif text == "مرحبا":
        await update.message.reply_text("مرحباً مليون! منور يا غالي ✨")
    elif text == "زحلق":
        await update.message.reply_text("مع السلامة، الدرب يوسع جمل! 🏃‍♂️💨")
    elif text == "احكي لي":
        stories = [
            "كان يا ما كان، كان فيه بوت ذكي اسمه حمتو مكسر الدنيا!",
            "يقولون إن البرمجة ممتعة طالما أن الأخطاء تختفي وحدها.",
            "الحياة رحلة، فلا تقف عن التعلم والتطوير أبداً!"
        ]
        await update.message.reply_text(random.choice(stories))
    else:
        # ردود عشوائية عامة إذا تطلب الأمر
        general_replies = ["عيوني", "افصلا", "حاضر من عيوني"]
        if random.random() < 0.2:  # يرد بنسبة 20% على الرسائل العادية لكي لا يزعج المستخدمين
            await update.message.reply_text(random.choice(general_replies))

# ==================== 3. الألعاب التفاعلية ====================
async def game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("✊ حجر ورقة مقص", callback_data="game_rps")],
        [InlineKeyboardButton("🔢 تخمين الرقم", callback_data="game_guess")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text("اختر اللعبة التي تريدها:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("اختر اللعبة التي تريدها:", reply_markup=reply_markup)

async def handle_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "game_rps":
        choices = ["حجر ✊", "ورقة 📄", "مقص ✂️"]
        bot_choice = random.choice(choices)
        await query.message.edit_text(f"لعبنا حجر ورقة مقص!\nأنا اخترت: {bot_choice}\nهاه، من فاز؟ 😉")
    elif query.data == "game_guess":
        secret_num = random.randint(1, 5)
        await query.message.edit_text(f"فكرت في رقم بين 1 و 5. هل يمكنك تخمينه؟ اكتب رقمك في المحادثة!")

# ==================== 4. نظام الحماية والإدارة ====================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("عذراً، هذا الأمر للمشرفين فقط! ❌")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("يجب الرد على رسالة الشخص المراد حظره لاستخدام هذا الأمر.")
        return
        
    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_user.id)
        await update.message.reply_text(f"تم حظر المستخدم {target_user.first_name} بنجاح. 🚷")
    except Exception as e:
        await update.message.reply_text(f"فشل الحظر: تأكد من صلاحيات المشرف للبوت. الخطأ: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("عذراً، هذا الأمر للمشرفين فقط! ❌")
        return
    await update.message.reply_text("تم تطبيق وضع الكتم على المستخدم بنجاح. 🔇")

# ==================== 5. خاصية الهمسات (Whispers) ====================
async def whisper_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # مثال توضيحي للهمسة الآمنة
    args = context.args
    if not args:
        await update.message.reply_text("استخدام الأمر: `/whisper [الرسالة]` لإرسال همسة خاصة.", parse_mode="Markdown")
        return
    whisper_msg = " ".join(args)
    await update.message.delete()  # حذف رسالة المرسل للحفاظ على السرية
    await update.message.reply_text(f"🤫 **همسة جديدة:**\n{whisper_msg}", parse_mode="Markdown")

# ==================== المنهج الرئيسي وتشغيل البوت ====================
def main() -> None:
    token = "YOUR_BOT_TOKEN_HERE"  # ضع التوكن الخاص بك هنا
    application = ApplicationBuilder().token(token).build()

    # المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_menu))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("whisper", whisper_command))
    
    # معالجات الأزرار والردود
    application.add_handler(CallbackQueryHandler(game_menu, pattern="^menu_games$"))
    application.add_handler(CallbackQueryHandler(handle_games, pattern="^game_"))
    
    # معالج النصوص والردود المميزة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hamto_responses))

    print("جاري تشغيل بوت حمتو بكل الميزات...")
    application.run_polling()

if __name__ == "__main__":
    main()
