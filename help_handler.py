# help_handler.py

import logging
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

from buy_handler import stop_all
from config import ORDER_CHAT_ID, PRODUCTION_CHAT_ID
from messages import START_HELP_MESSAGE, SUPPLIER_MESSAGE_TEMPLATE, SUPPORT_MESSAGE_TEMPLATE, CONFIRMATION_MESSAGE

# Определяем этапы диалога
HELP_STEP1 = 1


async def log_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int):
    # Логируем шаг пользователя
    user = update.message.from_user
    logging.info(f"Help Step {step}: User {user.username} ({user.id}) entered: {update.message.text}")


async def start_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Начало диалога помощи
    logging.info(f"Пользователь {update.message.from_user.username} начал диалог помощи.")
    await update.message.reply_text(START_HELP_MESSAGE)
    return HELP_STEP1


async def help_step1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логируем ввод пользователя
    await log_user_step(update, context, HELP_STEP1)
    context.user_data['issue'] = update.message.text

    # Проверяем, из какого чата пришло сообщение
    if str(update.message.chat_id) == PRODUCTION_CHAT_ID:
        text = SUPPLIER_MESSAGE_TEMPLATE.format(
            username=update.message.from_user.username,
            user_id=update.message.from_user.id,
            issue=context.user_data['issue']
        )
        logging.info("Сообщение сформировано для поставщика.")
    else:
        text = SUPPORT_MESSAGE_TEMPLATE.format(
            username=update.message.from_user.username,
            user_id=update.message.from_user.id,
            issue=context.user_data['issue']
        )
        logging.info("Сообщение сформировано для поддержки.")

    # Отправляем сообщение в ORDER_CHAT_ID
    await context.bot.send_message(chat_id=ORDER_CHAT_ID, text=text)
    logging.info("Сообщение отправлено в ORDER_CHAT_ID.")

    # Отправляем подтверждение пользователю
    await update.message.reply_text(CONFIRMATION_MESSAGE)
    logging.info("Подтверждение отправлено пользователю.")
    return ConversationHandler.END


# Создаем обработчик диалога помощи
help_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('help', start_help)],
    states={
        HELP_STEP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, help_step1)],
    },
    fallbacks=[CommandHandler('stop', stop_all)],
)
