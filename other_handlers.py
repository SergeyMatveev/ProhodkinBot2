# other_handlers.py

import logging
import os
import re

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config import PRODUCTION_CHAT_ID, ORDERS_FILE, ORDER_CHAT_ID
from messages import (
    START_MESSAGE,
    STOP_MESSAGE,
    QR_CODE_ERROR_MESSAGE1,
    QR_CODE_ERROR_MESSAGE2,
    QR_CODE_ORDER_NOT_FOUND_MESSAGE,
    QR_CODE_THANK_YOU_MESSAGE
)
from utils import load_orders, save_photo, ORDERS_DIR, send_photo


# Функция для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    logging.info(f"Пользователь {user.username}, UserID {user.id} вызвал команду /start.")

    # Получаем параметр из команды /start
    if context.args:
        campaign = context.args[0]
        logging.info(f"Пользователь {user.username}, UserID {user.id} пришел по рекламной кампании: {campaign}")
        text = f"Пользователь {user.username}, UserID {user.id} пришел по рекламной кампании: {campaign}"
        await context.bot.send_message(chat_id=ORDER_CHAT_ID, text=text)
        await update.message.reply_text(START_MESSAGE)
    else:
        # Обычное приветственное сообщение, если параметр не передан
        await update.message.reply_text(START_MESSAGE)

# Регистрируем команду start
start_handler = CommandHandler('start', start)


async def stop_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Обработчик команды /stop
    logging.info(
        f"Остановка процесса для пользователя {update.message.from_user.username}, UserID {update.message.from_user.id}")
    context.user_data.clear()
    await update.message.reply_text(STOP_MESSAGE)
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик ошибок
    try:
        logging.error(msg="Exception while handling an update:", exc_info=context.error)
    except Exception as e:
        logging.error("Error in error handler: %s", e)


async def handle_qr_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик для получения QR-кодов
    logging.info("Обработка полученного QR-кода.")

    if str(update.message.chat_id) != str(PRODUCTION_CHAT_ID):
        logging.warning("Получено сообщение не из PRODUCTION_CHAT_ID.")
        return

    if not update.message.photo or not update.message.caption:
        logging.warning("Фото или подпись отсутствуют в сообщении.")
        await update.message.reply_text(QR_CODE_ERROR_MESSAGE1)
        return

    # Извлекаем номер заказа из подписи
    order_number_match = re.search(r'\b\d+\b', update.message.caption)
    if not order_number_match:
        logging.warning("Номер заказа не найден в подписи.")
        await update.message.reply_text(QR_CODE_ERROR_MESSAGE2)
        return

    order_number = int(order_number_match.group())
    orders = load_orders(ORDERS_FILE)

    # Ищем заказ в списке заказов
    for order in orders:
        if order['order_number'] == order_number:
            chat_id = order['chat_id']
            photo_file = await save_photo(order_number, update, context, step="_qrcode")
            order_dir = os.path.join(ORDERS_DIR, f'Order{order_number}')
            photo_file = os.path.join(order_dir, 'photo_step_qrcode.jpg')

            await update.message.reply_text(f"Заказ №{order_number} выполнен.")
            logging.info(f"Заказ {order_number} найден и обработан.")

            caption = f"Вот ваш QR-код для заказа №{order_number}."
            await send_photo(update, context, chat_id, photo_file, caption)
            logging.info(f"QR-код для заказа {order_number} отправлен пользователю.")

            # Отправляем QR-код в ORDER_CHAT_ID
            caption_order = f"QR-код для заказа номер {order_number}"
            await send_photo(update, context, ORDER_CHAT_ID, photo_file, caption_order)
            logging.info(f"QR-код для заказа {order_number} отправлен в ORDER_CHAT_ID.")

            # Дополнительное сообщение пользователю
            await context.bot.send_message(chat_id=chat_id, text=QR_CODE_THANK_YOU_MESSAGE)
            logging.info("Пользователю отправлено благодарственное сообщение.")
            return

    # Если заказ не найден
    await update.message.reply_text(QR_CODE_ORDER_NOT_FOUND_MESSAGE)
    logging.error(f"Заказ {order_number} не найден в списке заказов.")


qr_code_handler = MessageHandler(filters.PHOTO, handle_qr_code)
