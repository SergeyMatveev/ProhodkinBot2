# main.py

import logging
import os
from datetime import datetime, timezone
import time

from telegram.ext import ApplicationBuilder
from buy_handler import buy_conv_handler
from config import BOT_TOKEN
from help_handler import help_conv_handler
from other_handlers import start_handler, error_handler, qr_code_handler
from utils import make_backup_handler


def setup_logging():
    # Создаем директорию для логов, если она не существует
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Форматируем имя файла лога с текущим временем UTC
    log_time = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_dir, f"{log_time}.log")

    # Класс для форматирования времени в UTC
    class UTCFormatter(logging.Formatter):
        converter = time.gmtime

    # Устанавливаем формат логирования
    formatter = UTCFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Настраиваем обработчик для записи логов в файл
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Настраиваем обработчик для вывода логов в консоль
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Получаем корневой логгер и очищаем предыдущие обработчики
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    # Устанавливаем уровень логирования и добавляем обработчики
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Устанавливаем уровень логирования для логгера httpx
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    # Логируем успешную настройку логирования
    logger.info("Логирование настроено успешно.")


def main() -> None:
    # Настраиваем логирование
    setup_logging()
    logging.info("Запуск бота...")

    # Создаем приложение Telegram бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    logging.info("Приложение Telegram бота создано.")

    # Добавляем обработчики команд и сообщений
    app.add_handler(start_handler)
    logging.info("Обработчик команды /start добавлен.")

    app.add_handler(buy_conv_handler)
    logging.info("Обработчик диалога покупки добавлен.")

    app.add_handler(help_conv_handler)
    logging.info("Обработчик диалога помощи добавлен.")

    app.add_handler(qr_code_handler)
    logging.info("Обработчик QR-кода добавлен.")

    app.add_handler(make_backup_handler)
    logging.info("Обработчик команды /make_backup добавлен.")

    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)
    logging.info("Обработчик ошибок добавлен.")

    # Запускаем бота в режиме polling
    app.run_polling()
    logging.info("Бот запущен и работает в режиме polling.")


if __name__ == '__main__':
    main()
