from __future__ import annotations

import json
import logging
import os
import random
import threading
from pathlib import Path
from typing import Any, Final

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("أهلاً بك! البوت يعمل بنجاح.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("أنا بوت حمتو، جاهز لتلبية طلباتك.")

async def hamto_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.text:
        responses = [
            "عيون حمتو",
            "زحلق",
            "افصلا",
            "عيوني"
        ]
        chosen_reply = random.choice(responses)
        await update.message.reply_text(chosen_reply)

def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # ضع التوكن الخاص بك هنا أو اتركه يسحبه من المتغيرات البيئية
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8925123826AAELvHygnvX5ck3M6hasr7s8VWZXHubRRzI")
    
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, hamto_response))

    application.run_polling()

if __name__ == "__main__":
    main()
