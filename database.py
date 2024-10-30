import asyncpg
import csv
import io


async def init_db():
    """
    Инициализация базы данных: создание таблиц, если они не существуют.
    """
    pool = await asyncpg.create_pool(dsn='postgresql://postgres:postgres@localhost:5432/postgres')

    async with pool.acquire() as conn:
        # Создание таблицы users
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id VARCHAR(255) UNIQUE,
                username VARCHAR(255),
                language VARCHAR(255) DEFAULT 'rus',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Создание таблицы orders
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                order_number INTEGER UNIQUE,
                name_in_order VARCHAR(255),
                plan_date_of_prohod VARCHAR(255),
                contact VARCHAR(255),
                airport VARCHAR(255),
                sent_business_lounge BOOLEAN DEFAULT FALSE,
                sent_payment BOOLEAN DEFAULT FALSE,
                sent_qrcode BOOLEAN DEFAULT FALSE,
                feedback_requested BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Создание таблицы help_requests
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS help_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                text_of_request VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Создание таблицы user_steps
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_steps (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                process VARCHAR(255),
                order_id INTEGER REFERENCES orders(id),
                step VARCHAR(255),
                message VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    return pool


async def get_user(pool, telegram_id):
    """
    Получение пользователя по telegram_id.
    """
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE telegram_id=$1', telegram_id)
    return user


async def create_user(pool, telegram_id, username, language='rus'):
    """
    Создание нового пользователя.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO users (telegram_id, username, language) VALUES ($1, $2, $3)',
            telegram_id, username, language
        )
        user = await conn.fetchrow('SELECT * FROM users WHERE telegram_id=$1', telegram_id)
    return user


async def store_user_step(pool, user_id, process, order_id, step, message):
    """
    Сохранение шага пользователя.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO user_steps (user_id, process, order_id, step, message) VALUES ($1, $2, $3, $4, $5)',
            user_id, process, order_id, step, message
        )


async def get_last_order_number(pool):
    """
    Получение последнего номера заказа.
    """
    async with pool.acquire() as conn:
        result = await conn.fetchval('SELECT MAX(order_number) FROM orders')
        return result or 0


async def create_order(pool, user_id):
    """
    Создание нового заказа.
    """
    order_number = await get_last_order_number(pool) + 1
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO orders (user_id, order_number) VALUES ($1, $2)',
            user_id, order_number
        )
        order = await conn.fetchrow('SELECT * FROM orders WHERE order_number=$1', order_number)
    return order


async def update_order(pool, order_id, data):
    """
    Обновление заказа.
    """
    set_clause = ', '.join([f"{key}=${i + 2}" for i, key in enumerate(data.keys())])
    values = list(data.values())
    async with pool.acquire() as conn:
        await conn.execute(
            f'UPDATE orders SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=$1',
            order_id, *values
        )


async def mark_order_completed(pool, order_id):
    """
    Отметка заказа как выполненного.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            'UPDATE orders SET sent_qrcode=TRUE, updated_at=CURRENT_TIMESTAMP WHERE id=$1',
            order_id
        )


async def create_help_request(pool, user_id, text_of_request):
    """
    Создание запроса в поддержку.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO help_requests (user_id, text_of_request) VALUES ($1, $2)',
            user_id, text_of_request
        )


async def backup_db(pool):
    """
    Создание резервной копии базы данных.
    """
    async with pool.acquire() as conn:
        tables = ['users', 'orders', 'help_requests', 'user_steps']
        csv_files = {}
        for table in tables:
            records = await conn.fetch(f'SELECT * FROM {table}')
            if records:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(records[0].keys())
                for record in records:
                    writer.writerow(record.values())
                csv_files[table] = output.getvalue()
    return csv_files


async def get_order_by_number(pool, order_number):
    """
    Получение заказа по номеру заказа.
    """
    async with pool.acquire() as conn:
        order = await conn.fetchrow('SELECT * FROM orders WHERE order_number=$1', order_number)
    return order


async def get_user_by_id(pool, user_id):
    """
    Получение пользователя по его ID.
    """
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE id=$1', user_id)
    return user
