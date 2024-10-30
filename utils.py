# utils.py

import logging
import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from config import ORDER_CHAT_ID, PRODUCTION_CHAT_ID, ORDERS_DIR


def load_orders(file_path):
    # Загружаем список заказов из файла
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            orders = json.load(file)
            logging.info(f"Загружено {len(orders)} заказов из {file_path}.")
            return orders
    else:
        with open(file_path, 'w') as file:
            json.dump([], file)
        logging.warning(f"Файл {file_path} не найден. Создан новый файл.")
        return []


def save_orders(file_path, orders):
    # Сохраняем список заказов в файл
    with open(file_path, 'w') as file:
        json.dump(orders, file, indent=4)
    logging.info(f"Сохранено {len(orders)} заказов в {file_path}.")


def create_order_data(context, order_number, start_time, chat_id, username, user_id):
    # Создаем данные нового заказа
    order_data = {
        "order_number": order_number,
        "chat_id": chat_id,
        "start_time": start_time,
        "username": username,
        "user_id": user_id
    }
    logging.info(f"Созданы данные заказа {order_number}.")
    return order_data


def initialize_order(context: ContextTypes.DEFAULT_TYPE, chat_id, username, user_id) -> bool:
    # Инициализируем новый заказ
    orders = load_orders('orders.txt')
    order_number = len(orders) + 1
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    order_data = create_order_data(context, order_number, start_time, chat_id, username, user_id)

    orders.append(order_data)
    save_orders('orders.txt', orders)

    context.user_data.update(order_data)
    logging.info(f"Заказ {order_number} инициализирован и добавлен в список заказов.")
    return True


async def save_photo(order_number, update, context, step, photo_number=None):
    # Сохраняем фото пользователя на сервер
    order_dir = os.path.join(ORDERS_DIR, f'Order{order_number}')
    os.makedirs(order_dir, exist_ok=True)
    photo_file = os.path.join(order_dir, f'photo_step{step}_{photo_number}.jpg') if photo_number else os.path.join(
        order_dir, f'photo_step{step}.jpg')
    photo = await update.message.photo[-1].get_file()
    await photo.download_to_drive(photo_file)
    logging.info(f"Фото сохранено: {photo_file}")
    return photo_file


async def handle_photo_sending(update, context, order_number, step, photo_file, photo_number=None):
    # Отправляем сохраненное фото в указанный чат
    if step == 5 and photo_number == 1:
        caption = f"Бизнес зал заказа номер {order_number}"
        context.user_data['photo_step5'] = photo_file
    elif step == 6 and photo_number == 2:
        caption = f"Оплата заказа номер {order_number}"
    else:
        caption = f"Фото из заказа номер {order_number}"

    await send_photo(update, context, ORDER_CHAT_ID, photo_file, caption)
    logging.info(f"Фото этапа {step} заказа {order_number} отправлено в ORDER_CHAT_ID.")


async def send_photo(update, context, chat_id, photo_path, caption):
    # Отправляем фото в указанный чат
    with open(photo_path, 'rb') as photo:
        await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
    logging.info(f"Фото {photo_path} отправлено в чат {chat_id} с подписью '{caption}'.")


async def log_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int):
    # Логируем шаг пользователя
    user = update.message.from_user
    logging.info(f"Step {step}, User {user.username}, UserID {user.id}, entered: {update.message.text}")


async def send_order_details(context: ContextTypes.DEFAULT_TYPE, order_number: int, chat_id):
    # Отправляем детали заказа в указанный чат
    order_file = os.path.join(ORDERS_DIR, f'Order{order_number}', f'order_{order_number}_data.json')

    if os.path.exists(order_file):
        with open(order_file, 'r', encoding='utf-8') as file:
            order_data = json.load(file)
        logging.info(f"Данные заказа {order_number} загружены для отправки.")

        details = (
            f"Новый заказ номер {order_number}:\n"
            f"Имя: {order_data['Имя']}\n"
            f"Аэропорт: {order_data['Аэропорт']}\n"
            f"Дата: {order_data['Дата']}\n"
        )
        await context.bot.send_message(chat_id=chat_id, text=details)
        logging.info(f"Детали заказа {order_number} отправлены в чат {chat_id}.")

        if str(chat_id) != PRODUCTION_CHAT_ID:
            user_data = context.user_data
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Юзернейм: @{user_data['username']}\nКонтакт: {user_data['contact']}\n"
            )
            logging.info(f"Дополнительная информация о пользователе отправлена в чат {chat_id}.")
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"Ошибка: данные заказа номер {order_number} не найдены.")
        logging.error(f"Данные заказа {order_number} не найдены.")


async def send_orders_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отправляем файл с заказами и последний лог-файл в ORDER_CHAT_ID
    logs_directory = 'logs'
    orders_file = 'orders.txt'
    backup_message = "Сохраню бекап файлы на всякий случай"

    # Отправляем сообщение о бекапе
    await context.bot.send_message(chat_id=ORDER_CHAT_ID, text=backup_message)
    logging.info("Отправлено сообщение о начале бекапа файлов.")

    # Находим последний лог-файл
    latest_log_file = None
    if os.path.exists(logs_directory):
        log_files = [f for f in os.listdir(logs_directory) if f.endswith('.log')]
        if log_files:
            latest_log_file = max(log_files, key=lambda x: datetime.strptime(x, '%Y-%m-%d_%H-%M-%S.log'))
            logging.info(f"Последний лог-файл: {latest_log_file}")

    # Отправляем последний лог-файл
    if latest_log_file:
        latest_log_path = os.path.join(logs_directory, latest_log_file)
        with open(latest_log_path, 'rb') as log_file:
            await context.bot.send_document(chat_id=ORDER_CHAT_ID, document=log_file, filename=latest_log_file)
        logging.info(f"Лог-файл {latest_log_file} отправлен в ORDER_CHAT_ID.")
    else:
        logging.error("Лог-файлы не найдены.")

    # Отправляем файл заказов
    if os.path.exists(orders_file):
        with open(orders_file, 'rb') as file:
            await context.bot.send_document(chat_id=ORDER_CHAT_ID, document=file, filename='orders.txt')
        logging.info("Файл orders.txt отправлен в ORDER_CHAT_ID.")
    else:
        logging.error("Файл orders.txt не существует.")


# Обработчик команды /make_backup
make_backup_handler = CommandHandler('make_backup', send_orders_file)


async def save_order_data(order_number, context):
    # Сохраняем данные заказа в JSON файл
    order_dir = os.path.join(ORDERS_DIR, f'Order{order_number}')
    os.makedirs(order_dir, exist_ok=True)
    order_file = os.path.join(order_dir, f'order_{order_number}_data.json')
    order_data = {
        "Имя": context.user_data.get('name'),
        "Аэропорт": context.user_data.get('airport'),
        "Дата": context.user_data.get('date')
    }
    with open(order_file, 'w', encoding='utf-8') as file:
        json.dump(order_data, file, ensure_ascii=False, indent=4)
    logging.info(f"Данные заказа {order_number} сохранены в {order_file}.")
