from dotenv import load_dotenv  # Імпортуємо load_dotenv
import os  # Імпортуємо os для доступу до змінних середовища

load_dotenv()  # Завантажуємо змінні з файлу .env

bot_token = os.getenv("BOT_TOKEN")
courier_id = os.getenv("COURIER_ID")

print("Bot Token:", bot_token)
print("Courier ID:", courier_id)

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Стани розмови
SELECT_WINE, SELECT_VOLUME, SELECT_TIME, SELECT_EXTRA_VOLUME, ADD_COMMENT, CONFIRM_ORDER = range(6)

# Меню
wines = [
    ["Blue gun", "Do si"],
    ["Cadillac", "Blue dream"],
    ["Guns", "Pink"],
    ["Blue jeans", "Blue gorilla"],
    ["Boom THC", "Frosted"]
]
volumes = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["Більше 10"]]
extra_volumes = [["10", "15", "20", "25", "30", "35", "40", "45", "50"]]
times = [["20:00", "20:30", "21:00", "21:30"], ["22:00", "22:30", "23:00"], ["23:30"]]

# Словник замовлень
user_order = {
    'wines': [],
    'comment': ''
}

# Команди
async def start(update: Update, context: ContextTypes):
    user_order['wines'] = []
    user_order['comment'] = ''
    context.user_data['time_value'] = None  # Скидуємо час
    await update.message.reply_text(
        "Оберіть вино:",
        reply_markup=ReplyKeyboardMarkup(wines + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_WINE

async def select_wine(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    user_order['wines'].append({'wine': update.message.text, 'volume': None, 'extra_volume': None})
    await update.message.reply_text(
        "Оберіть літраж:",
        reply_markup=ReplyKeyboardMarkup(volumes + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_VOLUME

async def select_volume(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    user_order['wines'][-1]['volume'] = update.message.text
    if update.message.text == "Більше 10":
        await update.message.reply_text(
            "Оберіть додатковий літраж:",
            reply_markup=ReplyKeyboardMarkup(extra_volumes + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_EXTRA_VOLUME

    # Якщо час ще не обраний – запропонувати
    if not context.user_data.get('time_value'):
        await update.message.reply_text(
            "Оберіть час доставки:",
            reply_markup=ReplyKeyboardMarkup(times + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_TIME

    return await go_to_comment_step(update)

async def select_extra_volume(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    user_order['wines'][-1]['extra_volume'] = update.message.text

    if not context.user_data.get('time_value'):
        await update.message.reply_text(
            "Оберіть час доставки:",
            reply_markup=ReplyKeyboardMarkup(times + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_TIME

    return await go_to_comment_step(update)

async def select_time(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    context.user_data['time_value'] = update.message.text
    return await go_to_comment_step(update)

async def go_to_comment_step(update: Update):
    await update.message.reply_text(
        "Ви можете додати коментар або перейти до оформлення:",
        reply_markup=ReplyKeyboardMarkup(
            [['Додати коментар', 'Візьму ще', 'Замовити'], ['Скасувати']],
            one_time_keyboard=True, resize_keyboard=True
        )
    )
    return ADD_COMMENT

async def add_comment(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    if update.message.text == "Додати коментар":
        await update.message.reply_text("Введіть ваш коментар:")
        return ADD_COMMENT

    if update.message.text == "Візьму ще":
        await update.message.reply_text(
            "Оберіть наступне вино:",
            reply_markup=ReplyKeyboardMarkup(wines + [['Скасувати']], one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_WINE

    if update.message.text == "Замовити":
        return await confirm_order(update, context)

    user_order['comment'] = update.message.text
    await update.message.reply_text(
        "Коментар додано! Продовжуємо?",
        reply_markup=ReplyKeyboardMarkup(
            [['Візьму ще', 'Замовити', 'Скасувати']],
            one_time_keyboard=True, resize_keyboard=True
        )
    )
    return ADD_COMMENT

async def confirm_order(update: Update, context: ContextTypes):
    if not user_order['wines']:
        await update.message.reply_text("Ваш кошик порожній.")
        return ConversationHandler.END

    summary = "Ваше замовлення:\n\n"
    for i, item in enumerate(user_order['wines'], 1):
        line = f"{i}. {item['wine']}, {item['volume']}л"
        if item.get("extra_volume"):
            line += f" + {item['extra_volume']}л"
        summary += line + "\n"

    delivery_time = context.user_data.get("time_value")
    if delivery_time:
        summary += f"\nЧас доставки: {delivery_time}\n"

    if user_order.get('comment'):
        summary += f"\nКоментар: {user_order['comment']}\n"

    summary += "\nПідтвердити замовлення?"
    await update.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup([['Підтвердити', 'Скасувати']], one_time_keyboard=True, resize_keyboard=True)
    )
    return CONFIRM_ORDER

async def complete_order(update: Update, context: ContextTypes):
    if update.message.text == "Скасувати":
        return await cancel(update, context)

    if update.message.text == "Підтвердити":
        summary = "Нове замовлення:\n\n"
        for i, item in enumerate(user_order['wines'], 1):
            line = f"{i}. {item['wine']}, {item['volume']}л"
            if item.get("extra_volume"):
                line += f" + {item['extra_volume']}л"
            summary += line + "\n"

        delivery_time = context.user_data.get("time_value")
        if delivery_time:
            summary += f"\nЧас доставки: {delivery_time}\n"

        if user_order.get('comment'):
            summary += f"\nКоментар: {user_order['comment']}\n"

        # Надсилаємо кур’єру
        await context.bot.send_message(chat_id=courier_id, text=summary)
        await update.message.reply_text("Дякуємо! Замовлення надіслано кур’єру.")
        logging.info(f"Замовлення: {summary}")

        # Скидання даних для нового замовлення
        user_order['wines'] = []
        user_order['comment'] = ''
        context.user_data['time_value'] = None  # Очищаємо час

        # Запускаємо процес заново, щоб створити нове замовлення
        return await start(update, context)  # Повертаємося до початку

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes):
    await update.message.reply_text("Замовлення скасовано. Почнімо спочатку.")
    user_order['wines'] = []
    user_order['comment'] = ''
    return await start(update, context)

def main():
    application = ApplicationBuilder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_WINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_wine)],
            SELECT_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_volume)],
            SELECT_EXTRA_VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_extra_volume)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_time)],
            ADD_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_comment)],
            CONFIRM_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_order)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
