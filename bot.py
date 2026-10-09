import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GAME_URL = os.environ.get(
"GAME_URL",
"https://cheshmha-ro-man.onrender.com"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [[
InlineKeyboardButton("🎡 ورود به چشم‌ها رو من", url=GAME_URL)
]]
await update.message.reply_text(
"سلام! 🎉\nبرای ورود به بازی و اجرای قرعه‌کشی روی دکمه زیر بزن.",
reply_markup=InlineKeyboardMarkup(keyboard)
)

def main():
if not BOT_TOKEN:
raise RuntimeError("BOT_TOKEN environment variable is missing")
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()

if **name** == "**main**":
main()
