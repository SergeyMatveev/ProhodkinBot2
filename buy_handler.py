# buy_handler.py

import asyncio
import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config import ORDER_CHAT_ID, PRODUCTION_CHAT_ID
from other_handlers import stop_all
from messages import (
    START_BUY_MESSAGE,
    ERROR_MESSAGE,
    STEP1_MESSAGE,
    STEP2_MESSAGE,
    STEP3_MESSAGE,
    STEP4_MESSAGE,
    STEP4_INSTALL_INSTRUCTION_MESSAGE,
    STEP4_SCREENSHOT_INSTRUCTION_MESSAGE,
    STEP5_ERROR_MESSAGE,
    ORDER_SAVED_MESSAGE,
    STEP6_MESSAGE,
    STEP6_ERROR_MESSAGE,
    ORDER_ACCEPTED_MESSAGE,
    PRODUCTION_ORDER_CAPTION,
)

from utils import (
    initialize_order,
    save_photo,
    save_order_data,
    log_user_step,
    send_order_details,
    send_photo,
    handle_photo_sending
)

# Определяем этапы диалога покупки
BUY_STEP1, BUY_STEP2, BUY_STEP3, BUY_STEP4, BUY_STEP5, BUY_STEP6 = range(6)


async def start_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Начало диалога покупки
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    user_id = update.message.from_user.id
    logging.info(f"Пользователь {username} начал диалог покупки.")

    # Инициализируем заказ
    if initialize_order(context, chat_id, username, user_id):
        await update.message.reply_text(START_BUY_MESSAGE)
        logging.info("Заказ инициализирован успешно.")
        return BUY_STEP1
    else:
        await update.message.reply_text(ERROR_MESSAGE)
        logging.error("Ошибка инициализации заказа.")
        return ConversationHandler.END


async def buy_step1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логируем ввод пользователя
    await log_user_step(update, context, BUY_STEP1)
    context.user_data['name'] = update.message.text
    logging.info(f"Имя пользователя сохранено: {context.user_data['name']}")
    await update.message.reply_text(STEP1_MESSAGE)
    return BUY_STEP2


async def buy_step2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логируем ввод пользователя
    await log_user_step(update, context, BUY_STEP2)
    context.user_data['date'] = update.message.text
    logging.info(f"Дата сохранена: {context.user_data['date']}")
    await update.message.reply_text(STEP2_MESSAGE)
    return BUY_STEP3


async def buy_step3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логируем ввод пользователя
    await log_user_step(update, context, BUY_STEP3)
    context.user_data['contact'] = update.message.text
    logging.info(f"Контакт сохранен: {context.user_data['contact']}")
    await update.message.reply_text(STEP3_MESSAGE)
    return BUY_STEP4


async def buy_step4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Логируем ввод пользователя
    await log_user_step(update, context, BUY_STEP4)
    context.user_data['airport'] = update.message.text
    logging.info(f"Аэропорт сохранен: {context.user_data['airport']}")

    order_number = context.user_data['order_number']

    # Сохраняем данные заказа в JSON файл
    await save_order_data(order_number, context)
    logging.info(f"Данные заказа {order_number} сохранены.")

    # Отправляем детали заказа в ORDER_CHAT_ID
    await send_order_details(context, order_number, ORDER_CHAT_ID)
    logging.info(f"Детали заказа {order_number} отправлены в ORDER_CHAT_ID.")

    await update.message.reply_text(STEP4_MESSAGE)

    with open('install_app.jpg', 'rb') as photo:
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=photo, caption=STEP4_INSTALL_INSTRUCTION_MESSAGE)
    logging.info("Инструкция по установке отправлена пользователю.")

    with open('screenshot_help.jpg', 'rb') as photo:
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=photo, caption=STEP4_SCREENSHOT_INSTRUCTION_MESSAGE)
    logging.info("Инструкция по скриншоту отправлена пользователю.")

    return BUY_STEP5


async def buy_step5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Проверяем, отправил ли пользователь фото
    if not update.message.photo:
        if update.message.document:
            await update.message.reply_text(STEP5_ERROR_MESSAGE)
            logging.warning("Пользователь отправил документ вместо фото.")
            return BUY_STEP5
        await update.message.reply_text(STEP5_ERROR_MESSAGE)
        logging.warning("Пользователь не отправил фото.")
        return BUY_STEP5

    # Логируем ввод пользователя
    await log_user_step(update, context, BUY_STEP5)
    order_number = context.user_data['order_number']

    # Сохраняем фото и отправляем его в ORDER_CHAT_ID
    photo_file = await save_photo(order_number, update, context, step=5, photo_number=1)
    await handle_photo_sending(update, context, order_number, step=5, photo_file=photo_file, photo_number=1)
    logging.info(f"Фото этапа 5 для заказа {order_number} сохранено и отправлено.")

    # Отправляем подтверждение пользователю
    await update.message.reply_text(
        ORDER_SAVED_MESSAGE.format(
            order_number=order_number,
            name=context.user_data['name'],
            airport=context.user_data['airport'],
            date=context.user_data['date']
        )
    )
    logging.info(f"Пользователю отправлено подтверждение о сохранении заказа {order_number}.")

    await update.message.reply_text(STEP6_MESSAGE)
    return BUY_STEP6


async def buy_step6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Проверяем, отправил ли пользователь фото
    if not update.message.photo:
        if update.message.document:
            await update.message.reply_text(STEP6_ERROR_MESSAGE)
            logging.warning("Пользователь отправил документ вместо фото на этапе 6.")
            return BUY_STEP6
        await update.message.reply_text(STEP6_ERROR_MESSAGE)
        logging.warning("Пользователь не отправил фото на этапе 6.")
        return BUY_STEP6

    order_number = context.user_data['order_number']

    # Сохраняем фото и отправляем его в ORDER_CHAT_ID
    photo_file = await save_photo(order_number, update, context, step=6, photo_number=2)
    await handle_photo_sending(update, context, order_number, step=6, photo_file=photo_file, photo_number=2)
    logging.info(f"Фото этапа 6 для заказа {order_number} сохранено и отправлено.")

    # Отправляем подтверждение пользователю
    await update.message.reply_text(
        ORDER_ACCEPTED_MESSAGE.format(order_number=order_number)
    )
    logging.info(f"Пользователю отправлено подтверждение о принятии заказа {order_number}.")

    # Запускаем асинхронную задачу для отправки заказа в PRODUCTION_CHAT_ID через 3 минуты
    context.application.create_task(
        schedule_send_order_details(context, order_number, update, context.user_data['photo_step5'])
    )
    logging.info(f"Запланирована отправка заказа {order_number} в PRODUCTION_CHAT_ID через 3 минуты.")

    return ConversationHandler.END


async def schedule_send_order_details(context: ContextTypes.DEFAULT_TYPE, order_number: int, update: Update,
                                      photo: str) -> None:
    # Ожидаем 3 минуты
    await asyncio.sleep(1)
    # Отправляем детали заказа в PRODUCTION_CHAT_ID
    await send_order_details(context, order_number, PRODUCTION_CHAT_ID)
    logging.info(f"Детали заказа {order_number} отправлены в PRODUCTION_CHAT_ID.")

    caption = PRODUCTION_ORDER_CAPTION.format(order_number=order_number)
    await send_photo(update, context, PRODUCTION_CHAT_ID, photo, caption)
    logging.info(f"Фото заказа {order_number} отправлено в PRODUCTION_CHAT_ID.")


# Создаем обработчик диалога покупки
buy_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('buy', start_buy)],
    states={
        BUY_STEP1: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_step1)],
        BUY_STEP2: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_step2)],
        BUY_STEP3: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_step3)],
        BUY_STEP4: [MessageHandler(filters.TEXT & ~filters.COMMAND, buy_step4)],
        BUY_STEP5: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, buy_step5)],
        BUY_STEP6: [MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, buy_step6)]
    },
    fallbacks=[CommandHandler('stop', stop_all)]
)
