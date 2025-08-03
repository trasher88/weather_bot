import os
from dotenv import load_dotenv
import requests
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)

# Загружаем переменные из .env
load_dotenv()

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы состояний
AWAITING_CITY = 1

#TELEGRAM_TOKEN = "8265742864:AAEIXgn-1flIaYJwYjDFdL7_f6YtosIMGog"
#WEATHER_API_KEY = "a7d71869b1ad43ff9cd142803250308"

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🌤 Погода сейчас"), KeyboardButton("🔍 Поиск города")],
            [KeyboardButton("⚙️ Помощь"), KeyboardButton("❌ Закрыть меню")]
        ],
        resize_keyboard=True
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌦 Добро пожаловать в WeatherBot!\nВыберите действие:",
        reply_markup=get_main_menu()
    )
    return AWAITING_CITY


async def weather_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'current'
    await update.message.reply_text(
        "Введите город для получения текущей погоды:",
        reply_markup=None
    )
    return AWAITING_CITY


async def search_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'search'
    await update.message.reply_text(
        "🔍 Введите название города или региона для поиска.\n"
        "Можно уточнять страну: 'Париж, Франция'",
        reply_markup=None
    )
    return AWAITING_CITY


async def handle_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    mode = context.user_data.get('mode', 'current')

    try:
        if mode == 'search':
            response = requests.get(
                f"http://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={city}",
                timeout=10
            ).json()

            if not response:
                raise ValueError("Ничего не найдено")

            locations = "\n".join(
                f"{i + 1}. {loc['name']}, {loc.get('country', 'N/A')}"
                for i, loc in enumerate(response[:5]))

            await update.message.reply_text(
                f"🔍 Найдены варианты:\n{locations}\n\n"
                "Введите номер или уточните запрос:",
                reply_markup=get_main_menu()
            )

        else:
            response = requests.get(
            f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&lang=ru",
            timeout=10
        ).json()

            weather_data = (
                f"<b>🌦 Погода в {response['location']['name']}</b>\n"
                f"• 🌡 Температура: {response['current']['temp_c']}°C\n"
                f"• 💧 Влажность: {response['current']['humidity']}%\n"
                f"• 🌬 Ветер: {response['current']['wind_kph']} км/ч\n"
                f"• ☁ Состояние: {response['current']['condition']['text']}"
            )

            await update.message.reply_html(
                weather_data,
                reply_markup=get_main_menu()
            )

    except Exception as e:
        error_msg = {
            'search': "🔍 Ничего не найдено. Попробуйте другой запрос:",
            'current': "⚠️ Ошибка запроса погоды. Проверьте название города:"
        }.get(mode, "Произошла ошибка")

        await update.message.reply_text(
            error_msg,
            reply_markup=get_main_menu()
        )

    return AWAITING_CITY


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "• <b>🌤 Погода сейчас</b> - мгновенный результат по точному названию\n"
        "• <b>🔍 Поиск города</b> - поиск по частичному названию с уточнением\n"
        "• <b>/start</b> - открыть главное меню\n"
        "• <b>/help</b> - эта справка"
    )
    await update.message.reply_html(
        help_text,
        reply_markup=get_main_menu()
    )
    return AWAITING_CITY


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Меню скрыто. Для возврата нажмите /start",
        reply_markup=None
    )
    return ConversationHandler.END


def main():
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                AWAITING_CITY: [
                    MessageHandler(filters.Regex('^🌤 Погода сейчас$'), weather_now),
                    MessageHandler(filters.Regex('^🔍 Поиск города$'), search_city),
                    MessageHandler(filters.Regex('^⚙️ Помощь$'), help_command),
                    MessageHandler(filters.Regex('^❌ Закрыть меню$'), cancel),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_input)
                ]
            },
            fallbacks=[CommandHandler('start', start)]
        )

        app.add_handler(conv_handler)
        app.add_handler(CommandHandler('help', help_command))

        logger.info("Бот запущен...")
        app.run_polling()

    except Exception as e:
        logger.critical(f"Ошибка запуска: {e}")


if __name__ == "__main__":
    main()