import logging
import random
from datetime import datetime, timedelta
import sqlite3
import json
import asyncio
import os
import aiohttp
from typing import Dict, List, Optional
import hashlib

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, CallbackQuery, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = '8432394657:AAHzrM5FvHGiYF8AvIMIgwYKIldM83Tg-VQ'
ADMIN_IDS = [7842497247]

# Инициализация бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База данных
DB_NAME = 'game_bot.db'

# URL для получения курса биткоина
BITCOIN_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

# ========== ДАННЫЕ ИГРЫ ==========
QUIZ_QUESTIONS = [
    {"question": "Столица Франции?", "options": ["Лондон", "Берлин", "Париж", "Мадрид"], "answer": 2, "category": "география"},
    {"question": "Самая длинная река в мире?", "options": ["Нил", "Амазонка", "Янцзы", "Миссисипи"], "answer": 1, "category": "география"},
    {"question": "Сколько планет в Солнечной системе?", "options": ["7", "8", "9", "10"], "answer": 1, "category": "астрономия"},
    {"question": "Столица Японии?", "options": ["Пекин", "Сеул", "Токио", "Бангкок"], "answer": 2, "category": "география"},
    {"question": "Кто написал 'Войну и мир'?", "options": ["Достоевский", "Толстой", "Чехов", "Гоголь"], "answer": 1, "category": "литература"},
    {"question": "Какой газ преобладает в атмосфере Земли?", "options": ["Кислород", "Углекислый газ", "Азот", "Водород"], "answer": 2, "category": "химия"},
    {"question": "Самое большое млекопитающее в мире?", "options": ["Слон", "Синий кит", "Жираф", "Белый медведь"], "answer": 1, "category": "биология"},
    {"question": "Кто открыл Америку?", "options": ["Магеллан", "Колумб", "Васко да Гама", "Джеймс Кук"], "answer": 1, "category": "история"},
    {"question": "Сколько континентов на Земле?", "options": ["5", "6", "7", "8"], "answer": 2, "category": "география"},
    {"question": "Столица Австралии?", "options": ["Сидней", "Мельбурн", "Канберра", "Брисбен"], "answer": 2, "category": "география"},
]

# Бизнесы
BUSINESSES = [
    {"id": 1, "name": "Шаурмичная", "emoji": "🌯", "price": 25000, "income_per_hour": 2500, "level_required": 1},
    {"id": 2, "name": "Ларёк", "emoji": "🍬", "price": 250000, "income_per_hour": 100000, "level_required": 3},
    {"id": 3, "name": "Ресторан", "emoji": "🍻", "price": 400000, "income_per_hour": 175000, "level_required": 5},
    {"id": 4, "name": "Магазин", "emoji": "🛍", "price": 1500000, "income_per_hour": 250000, "level_required": 8},
    {"id": 5, "name": "Завод", "emoji": "🏚", "price": 20000000, "income_per_hour": 1000000, "level_required": 12},
    {"id": 6, "name": "Шахта", "emoji": "🕳", "price": 3500000, "income_per_hour": 2500000, "level_required": 15},
]

# Кейсы
CASES = [
    {
        "id": 1,
        "name": "🥉 Бронзовый кейс",
        "price": 500,
        "min_reward": 300,
        "max_reward": 700,
        "level_required": 1
    },
    {
        "id": 2,
        "name": "🥇 Золотой кейс",
        "price": 1000,
        "min_reward": 800,
        "max_reward": 1800,
        "level_required": 2
    },
    {
        "id": 3,
        "name": "💰 Денежный кейс",
        "price": 2500,
        "min_reward": 2450,
        "max_reward": 3900,
        "level_required": 5
    }
]

# Магазин - предметы
SHOP_ITEMS = [
    {"id": 1, "name": "🏠 Дом", "price": 1000, "type": "property", "bonus": "Увеличивает максимальную энергию на 50"},
    {"id": 2, "name": "🚗 Машина (базовая)", "price": 500, "type": "vehicle", "bonus": "Увеличивает доход от работы на 10%"},
    {"id": 3, "name": "🚗 Машина (средняя)", "price": 5000, "type": "vehicle", "bonus": "Увеличивает доход от работы на 25%"},
    {"id": 4, "name": "🚗 Машина (премиум)", "price": 25000, "type": "vehicle", "bonus": "Увеличивает доход от работы на 50%"},
    {"id": 5, "name": "📱 Телефон (базовый)", "price": 300, "type": "phone", "bonus": "Дает +5% к доходам"},
    {"id": 6, "name": "📱 Телефон (средний)", "price": 2000, "type": "phone", "bonus": "Дает +15% к доходам"},
    {"id": 7, "name": "📱 Телефон (премиум)", "price": 10000, "type": "phone", "bonus": "Дает +30% к доходам"},
    {"id": 8, "name": "✈️ Самолет", "price": 1000000, "type": "vehicle", "bonus": "Дает +100% к доходам от бизнеса"},
    {"id": 9, "name": "⚡ Энергия", "price": 50, "type": "consumable", "bonus": "Восстанавливает 20 энергии"},
]

# Глобальная переменная для курса биткоина
bitcoin_price = 45000  # Начальное значение

# Хранилище для состояния
user_quiz_state = {}
user_bet_state = {}  # Для хранения ставок пользователей
user_player_ids = {}  # Кэш для player_id

# ========== ФУНКЦИИ БАЗЫ ДАННЫХ ==========

def init_db():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей, если она не существует
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                dollars INTEGER DEFAULT 100,
                bitcoins REAL DEFAULT 0.01,
                energy INTEGER DEFAULT 100,
                max_energy INTEGER DEFAULT 100,
                last_daily_reward TEXT,
                quiz_progress INTEGER DEFAULT 0,
                player_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица бизнесов пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                business_id INTEGER,
                purchased_at TEXT,
                last_collected TEXT,
                business_balance REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица предметов пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                item_name TEXT,
                purchased_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                to_user_id INTEGER,
                amount REAL,
                currency TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users (user_id),
                FOREIGN KEY (to_user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")

def generate_player_id(user_id: int) -> str:
    """Генерирует уникальный и постоянный ID игрока"""
    if user_id in user_player_ids:
        return user_player_ids[user_id]
    
    # Генерируем постоянный ID на основе user_id
    seed = f"player_{user_id}_game_bot"
    player_id = hashlib.md5(seed.encode()).hexdigest()[:8].upper()
    user_player_ids[user_id] = player_id
    return player_id

def get_user(user_id: int):
    """Получить пользователя из базы"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if not user_data:
            return None
        
        # Создаем словарь с данными пользователя
        user_dict = {
            'user_id': user_data[0],
            'username': user_data[1],
            'full_name': user_data[2],
            'level': user_data[3] if user_data[3] is not None else 1,
            'experience': user_data[4] if user_data[4] is not None else 0,
            'dollars': user_data[5] if user_data[5] is not None else 100,
            'bitcoins': user_data[6] if user_data[6] is not None else 0.01,
            'energy': user_data[7] if user_data[7] is not None else 100,
            'max_energy': user_data[8] if user_data[8] is not None else 100,
            'last_daily_reward': user_data[9],
            'quiz_progress': user_data[10] if user_data[10] is not None else 0,
            'player_id': user_data[11],
            'created_at': user_data[12] if len(user_data) > 12 else None
        }
        
        # Генерируем player_id если его нет
        if not user_dict.get('player_id'):
            player_id = generate_player_id(user_id)
            user_dict['player_id'] = player_id
            
            # Обновляем в базе
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET player_id = ? WHERE user_id = ?', (player_id, user_id))
            conn.commit()
            conn.close()
        
        # Убеждаемся, что значения не превышают максимумы
        if user_dict['energy'] > user_dict['max_energy']:
            user_dict['energy'] = user_dict['max_energy']
        
        return user_dict
        
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        # Возвращаем базовые данные
        return {
            'user_id': user_id,
            'username': None,
            'full_name': f"Игрок_{user_id}",
            'level': 1,
            'experience': 0,
            'dollars': 100,
            'bitcoins': 0.01,
            'energy': 100,
            'max_energy': 100,
            'quiz_progress': 0,
            'player_id': generate_player_id(user_id),
            'last_daily_reward': None,
            'created_at': None
        }

def get_user_by_player_id(player_id: str):
    """Найти пользователя по player_id"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE player_id = ?', (player_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return get_user(result[0])
        return None
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя по player_id {player_id}: {e}")
        return None

def create_or_update_user(user_id: int, username: str, full_name: str):
    """Создать или обновить пользователя"""
    try:
        user = get_user(user_id)
        
        if not user:
            # Генерируем постоянный player_id
            player_id = generate_player_id(user_id)
            
            # Создаем нового пользователя
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, player_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, full_name, player_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Создан новый пользователь: {user_id} - {full_name} с player_id {player_id}")
            
            # Возвращаем нового пользователя
            user = get_user(user_id)
        else:
            # Обновляем имя пользователя, если изменилось
            if user.get('username') != username or user.get('full_name') != full_name:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users SET username = ?, full_name = ? WHERE user_id = ?
                ''', (username, full_name, user_id))
                
                conn.commit()
                conn.close()
            
            # Всегда убеждаемся, что есть player_id
            if not user.get('player_id'):
                player_id = generate_player_id(user_id)
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET player_id = ? WHERE user_id = ?', (player_id, user_id))
                conn.commit()
                conn.close()
        
        # Всегда возвращаем актуальные данные
        return user
        
    except Exception as e:
        logger.error(f"Ошибка при создании/обновлении пользователя {user_id}: {e}")
        # Возвращаем базовые данные даже при ошибке
        return {
            'user_id': user_id,
            'username': username,
            'full_name': full_name,
            'level': 1,
            'experience': 0,
            'dollars': 100,
            'bitcoins': 0.01,
            'energy': 100,
            'max_energy': 100,
            'quiz_progress': 0,
            'player_id': generate_player_id(user_id),
            'last_daily_reward': None,
            'created_at': None
        }

def update_user_dollars(user_id: int, amount: float):
    """Обновить доллары пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Получаем текущий баланс
        cursor.execute('SELECT dollars FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        current_dollars = result[0] or 0
        new_dollars = current_dollars + amount
        
        if new_dollars < 0:
            new_dollars = 0
        
        cursor.execute('UPDATE users SET dollars = ? WHERE user_id = ?', (new_dollars, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении долларов пользователя {user_id}: {e}")
        return False

def update_user_bitcoins(user_id: int, amount: float):
    """Обновить биткоины пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT bitcoins FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        current_bitcoins = result[0] or 0.0
        new_bitcoins = current_bitcoins + amount
        
        if new_bitcoins < 0:
            new_bitcoins = 0
        
        cursor.execute('UPDATE users SET bitcoins = ? WHERE user_id = ?', (new_bitcoins, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении биткоинов пользователя {user_id}: {e}")
        return False

def update_user_energy(user_id: int, amount: int):
    """Обновить энергию пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT energy, max_energy FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        current_energy, max_energy = result
        current_energy = current_energy or 0
        max_energy = max_energy or 100
        
        new_energy = current_energy + amount
        
        if new_energy < 0:
            new_energy = 0
        elif new_energy > max_energy:
            new_energy = max_energy
        
        cursor.execute('UPDATE users SET energy = ? WHERE user_id = ?', (new_energy, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении энергии пользователя {user_id}: {e}")
        return False

def update_user_level(user_id: int, level: int):
    """Обновить уровень пользователя"""
    try:
        if level < 1:
            level = 1
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (level, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении уровня пользователя {user_id}: {e}")
        return False

def update_user_experience(user_id: int, experience: int):
    """Обновить опыт пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET experience = ? WHERE user_id = ?', (experience, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении опыта пользователя {user_id}: {e}")
        return False

def add_user_experience(user_id: int, exp_amount: int):
    """Добавить опыт пользователю"""
    try:
        user = get_user(user_id)
        if not user:
            return None
        
        new_experience = user['experience'] + exp_amount
        update_user_experience(user_id, new_experience)
        
        # Проверяем, нужно ли повысить уровень
        exp_needed = user['level'] * 100
        if new_experience >= exp_needed:
            # Повышаем уровень
            new_level = user['level'] + 1
            new_experience = new_experience - exp_needed
            update_user_level(user_id, new_level)
            update_user_experience(user_id, new_experience)
            return new_level  # Возвращаем новый уровень
        
        return user['level']
    except Exception as e:
        logger.error(f"Ошибка при добавлении опыта пользователю {user_id}: {e}")
        return None

def update_user_max_energy(user_id: int, max_energy: int):
    """Обновить максимальную энергию пользователя"""
    try:
        if max_energy < 100:
            max_energy = 100
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET max_energy = ? WHERE user_id = ?', (max_energy, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении максимальной энергии пользователя {user_id}: {e}")
        return False

def update_user_quiz_progress(user_id: int, progress: int):
    """Обновить прогресс викторины"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET quiz_progress = ? WHERE user_id = ?', (progress, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении прогресса викторины пользователя {user_id}: {e}")
        return False

def update_last_reward_time(user_id: int):
    """Обновить время последней награды"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET last_daily_reward = ? WHERE user_id = ?', (now, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени награды пользователя {user_id}: {e}")
        return False

def can_get_reward(user_id: int) -> tuple:
    """Проверка возможности получения награды"""
    try:
        user = get_user(user_id)
        if not user or not user.get('last_daily_reward'):
            return True, None
        
        last_reward_str = user['last_daily_reward']
        try:
            last_reward = datetime.strptime(last_reward_str, '%Y-%m-%d %H:%M:%S')
        except:
            # Если формат неверный, считаем что можно получить награду
            return True, None
        
        now = datetime.now()
        time_diff = now - last_reward
        hours_passed = time_diff.total_seconds() / 3600
        
        if hours_passed >= 2:
            return True, None
        else:
            # Вычисляем оставшееся время
            remaining_hours = 2 - hours_passed
            remaining_minutes = int((remaining_hours % 1) * 60)
            remaining_seconds = int(((remaining_hours % 1) * 60 % 1) * 60)
            
            return False, f"{int(remaining_hours)}ч {remaining_minutes}м {remaining_seconds}с"
            
    except Exception as e:
        logger.error(f"Ошибка при проверке награды пользователя {user_id}: {e}")
        return True, None

def get_user_businesses(user_id: int):
    """Получить бизнесы пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ub.*, 
                   CASE ub.business_id
                       WHEN 1 THEN 'Шаурмичная'
                       WHEN 2 THEN 'Ларёк'
                       WHEN 3 THEN 'Ресторан'
                       WHEN 4 THEN 'Магазин'
                       WHEN 5 THEN 'Завод'
                       WHEN 6 THEN 'Шахта'
                   END as name,
                   CASE ub.business_id
                       WHEN 1 THEN '🌯'
                       WHEN 2 THEN '🍬'
                       WHEN 3 THEN '🍻'
                       WHEN 4 THEN '🛍'
                       WHEN 5 THEN '🏚'
                       WHEN 6 THEN '🕳'
                   END as emoji,
                   CASE ub.business_id
                       WHEN 1 THEN 2500
                       WHEN 2 THEN 100000
                       WHEN 3 THEN 175000
                       WHEN 4 THEN 250000
                       WHEN 5 THEN 1000000
                       WHEN 6 THEN 2500000
                   END as income_per_hour
            FROM user_businesses ub
            WHERE ub.user_id = ?
        ''', (user_id,))
        
        businesses = cursor.fetchall()
        conn.close()
        
        result = []
        for biz in businesses:
            result.append({
                'id': biz[0],
                'user_id': biz[1],
                'business_id': biz[2],
                'purchased_at': biz[3],
                'last_collected': biz[4],
                'business_balance': biz[5] or 0,
                'name': biz[6],
                'emoji': biz[7],
                'income_per_hour': biz[8]
            })
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении бизнесов пользователя {user_id}: {e}")
        return []

def buy_business(user_id: int, business_id: int) -> bool:
    """Купить бизнес"""
    try:
        user = get_user(user_id)
        business = next((b for b in BUSINESSES if b['id'] == business_id), None)
        
        if not business or not user:
            return False
        
        if user['level'] < business['level_required']:
            return False
        
        if user['dollars'] < business['price']:
            return False
        
        # Проверяем, есть ли уже такой бизнес
        existing_businesses = get_user_businesses(user_id)
        if any(b['business_id'] == business_id for b in existing_businesses):
            return False
        
        # Покупаем бизнес
        update_user_dollars(user_id, -business['price'])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO user_businesses (user_id, business_id, purchased_at, last_collected)
            VALUES (?, ?, ?, ?)
        ''', (user_id, business_id, now, now))
        
        conn.commit()
        conn.close()
        
        # Добавляем опыт за покупку бизнеса
        add_user_experience(user_id, business['price'] // 100)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при покупке бизнеса {business_id} пользователем {user_id}: {e}")
        return False

def collect_business_income(user_id: int, business_db_id: int) -> float:
    """Собрать доход с бизнеса"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT business_balance, last_collected FROM user_businesses WHERE id = ? AND user_id = ?', 
                      (business_db_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return 0
        
        business_balance = result[0] or 0
        last_collected_str = result[1]
        
        # Обнуляем баланс и обновляем время сбора
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE user_businesses SET business_balance = 0, last_collected = ? WHERE id = ?', 
                      (now, business_db_id))
        
        conn.commit()
        conn.close()
        
        # Добавляем деньги пользователю
        update_user_dollars(user_id, business_balance)
        
        return business_balance
    except Exception as e:
        logger.error(f"Ошибка при сборе дохода с бизнеса {business_db_id}: {e}")
        return 0

def update_business_balances():
    """Обновить балансы всех бизнесов (вызывается периодически)"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Получаем все бизнесы
        cursor.execute('SELECT ub.id, ub.business_id, ub.last_collected FROM user_businesses ub')
        businesses = cursor.fetchall()
        
        for biz_id, business_id, last_collected_str in businesses:
            try:
                if not last_collected_str:
                    continue
                    
                last_collected = datetime.strptime(last_collected_str, '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                hours_passed = (now - last_collected).total_seconds() / 3600
                
                if hours_passed >= 1:
                    # Находим доход в час для этого бизнеса
                    business = next((b for b in BUSINESSES if b['id'] == business_id), None)
                    if business:
                        income_to_add = business['income_per_hour'] * hours_passed
                        
                        # Обновляем баланс
                        cursor.execute('''
                            UPDATE user_businesses 
                            SET business_balance = business_balance + ?
                            WHERE id = ?
                        ''', (income_to_add, biz_id))
            except:
                continue
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении балансов бизнесов: {e}")
        return False

def get_user_items(user_id: int):
    """Получить предметы пользователя"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT item_name, purchased_at FROM user_items WHERE user_id = ?', (user_id,))
        items = cursor.fetchall()
        
        conn.close()
        
        return [{'name': item[0], 'purchased_at': item[1]} for item in items]
    except Exception as e:
        logger.error(f"Ошибка при получении предметов пользователя {user_id}: {e}")
        return []

def add_user_item(user_id: int, item_name: str):
    """Добавить предмет пользователю"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO user_items (user_id, item_name, purchased_at) VALUES (?, ?, ?)',
                      (user_id, item_name, now))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении предмета пользователю {user_id}: {e}")
        return False

def create_transaction(from_user_id: int, to_user_id: int, amount: float, currency: str, description: str = ""):
    """Создать запись о транзакции"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions (from_user_id, to_user_id, amount, currency, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (from_user_id, to_user_id, amount, currency, description))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании транзакции: {e}")
        return False

# Инициализация базы
init_db()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Основная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="👤 Профиль")
    builder.button(text="🎮 Игры")
    builder.button(text="💼 Работа")
    builder.button(text="🏪 Магазин")
    builder.button(text="📊 Статистика")
    builder.button(text="🎁 Награда")
    builder.button(text="💼 Бизнесы")
    builder.button(text="🎁 Кейсы")
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_games_keyboard():
    """Клавиатура игр"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎰 Слоты", callback_data="game_slots")
    builder.button(text="🎲 Кости", callback_data="game_dice")
    builder.button(text="🎯 Дартс", callback_data="game_darts")
    builder.button(text="❓ Викторина", callback_data="game_quiz")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_work_keyboard():
    """Клавиатура работы"""
    builder = InlineKeyboardBuilder()
    builder.button(text="👷 Уборщик (50$)", callback_data="work_cleaner")
    builder.button(text="🚴 Курьер (100$)", callback_data="work_courier")
    builder.button(text="👨‍💼 Офисный работник (200$)", callback_data="work_office")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_work_again_keyboard(work_type: str):
    """Клавиатура для повторной работы"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Работать еще", callback_data=f"work_{work_type}")
    builder.button(text="💼 Другие работы", callback_data="back_to_works")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_shop_keyboard():
    """Клавиатура магазина"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Машины", callback_data="shop_cars")
    builder.button(text="📱 Телефоны", callback_data="shop_phones")
    builder.button(text="🏠 Недвижимость", callback_data="shop_property")
    builder.button(text="⚡ Энергия", callback_data="buy_energy")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_cars_keyboard():
    """Клавиатура машин"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Базовая (500$)", callback_data="buy_car_basic")
    builder.button(text="🚗 Средняя (5000$)", callback_data="buy_car_medium")
    builder.button(text="🚗 Премиум (25000$)", callback_data="buy_car_premium")
    builder.button(text="✈️ Самолет (1,000,000$)", callback_data="buy_plane")
    builder.button(text="« Назад в магазин", callback_data="back_to_shop")
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()

def get_phones_keyboard():
    """Клавиатура телефонов"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 Базовый (300$)", callback_data="buy_phone_basic")
    builder.button(text="📱 Средний (2000$)", callback_data="buy_phone_medium")
    builder.button(text="📱 Премиум (10000$)", callback_data="buy_phone_premium")
    builder.button(text="« Назад в магазин", callback_data="back_to_shop")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_property_keyboard():
    """Клавиатура недвижимости"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Дом (1000$)", callback_data="buy_house")
    builder.button(text="« Назад в магазин", callback_data="back_to_shop")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_back_keyboard():
    """Клавиатура назад"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="« Назад в меню")
    return builder.as_markup(resize_keyboard=True)

def get_play_again_keyboard(game_type: str, bet_amount: int = None):
    """Клавиатура для повторной игры"""
    builder = InlineKeyboardBuilder()
    if bet_amount:
        builder.button(text=f"🔄 Играть еще ({bet_amount}$)", callback_data=f"game_{game_type}_{bet_amount}")
    else:
        builder.button(text="🔄 Играть еще", callback_data=f"game_{game_type}")
    builder.button(text="🎮 Другие игры", callback_data="back_to_games")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_bet_keyboard(game_type: str):
    """Клавиатура для выбора ставки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="10$", callback_data=f"bet_{game_type}_10")
    builder.button(text="50$", callback_data=f"bet_{game_type}_50")
    builder.button(text="100$", callback_data=f"bet_{game_type}_100")
    builder.button(text="500$", callback_data=f"bet_{game_type}_500")
    builder.button(text="🎮 Другие игры", callback_data="back_to_games")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_quiz_keyboard(question_index: int = None):
    """Клавиатура для викторины"""
    builder = InlineKeyboardBuilder()
    
    if question_index is not None:
        question = QUIZ_QUESTIONS[question_index]
        for i, option in enumerate(question['options']):
            builder.button(text=option, callback_data=f"quiz_answer_{question_index}_{i}")
        builder.button(text="❌ Отмена", callback_data="quiz_cancel")
        builder.adjust(2, 2, 1)
    else:
        builder.button(text="▶️ Начать викторину", callback_data="quiz_start")
        builder.button(text="« Назад в меню", callback_data="back_main")
        builder.adjust(1, 1)
    
    return builder.as_markup()

def get_next_question_keyboard():
    """Клавиатура для следующего вопроса"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Следующий вопрос", callback_data="quiz_next")
    builder.button(text="❌ Завершить викторину", callback_data="quiz_finish")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_cases_keyboard():
    """Клавиатура кейсов"""
    builder = InlineKeyboardBuilder()
    for case in CASES:
        builder.button(text=f"{case['name']} ({case['price']}$)", callback_data=f"case_{case['id']}")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_businesses_keyboard():
    """Клавиатура бизнесов"""
    builder = InlineKeyboardBuilder()
    for business in BUSINESSES:
        builder.button(text=f"{business['emoji']} {business['name']} ({business['price']:,}$)", 
                      callback_data=f"business_{business['id']}")
    builder.button(text="💰 Собрать доход", callback_data="business_collect")
    builder.button(text="📊 Мои бизнесы", callback_data="business_my")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1, 1, 1, 1, 2)
    return builder.as_markup()

def get_my_businesses_keyboard(businesses):
    """Клавиатура для моих бизнесов"""
    builder = InlineKeyboardBuilder()
    for biz in businesses:
        builder.button(text=f"💰 Собрать {biz['emoji']} {biz['name']} ({biz['business_balance']:,.0f}$)", 
                      callback_data=f"collect_{biz['id']}")
    builder.button(text="« Назад к бизнесам", callback_data="back_to_businesses")
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def get_admin_keyboard():
    """Клавиатура админа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Рассылка", callback_data="admin_broadcast")
    builder.button(text="💰 Выдать деньги", callback_data="admin_give_money")
    builder.button(text="🎁 Выдать опыт", callback_data="admin_give_exp")
    builder.button(text="📋 Список пользователей", callback_data="admin_users")
    builder.button(text="« Назад в меню", callback_data="back_main")
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()

# ========== ФУНКЦИИ ДЛЯ КУРСА БИТКОИНА ==========

async def update_bitcoin_price():
    """Обновить курс биткоина"""
    global bitcoin_price
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BITCOIN_API_URL, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'bitcoin' in data and 'usd' in data['bitcoin']:
                        bitcoin_price = data['bitcoin']['usd']
                        logger.info(f"Курс биткоина обновлен: {bitcoin_price}$")
                    else:
                        # Если API не работает, используем случайное изменение
                        change = random.uniform(-500, 500)
                        bitcoin_price = max(10000, bitcoin_price + change)
                        logger.info(f"Курс биткоина изменен случайно: {bitcoin_price}$")
    except Exception as e:
        logger.error(f"Ошибка при обновлении курса биткоина: {e}")
        # Если ошибка, немного меняем курс случайно
        change = random.uniform(-100, 100)
        bitcoin_price = max(10000, bitcoin_price + change)

def format_money(amount: float) -> str:
    """Форматировать денежную сумму"""
    if amount >= 1000000:
        return f"{amount/1000000:.2f}M$"
    elif amount >= 1000:
        return f"{amount/1000:.1f}K$"
    else:
        return f"{amount:.0f}$"

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        
        # Создаем или получаем пользователя
        user = create_or_update_user(
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        welcome_text = (
            f"👋 Добро пожаловать, {message.from_user.full_name}!\n\n"
            f"🎮 <b>Andera Bot</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"₿ Биткоины: {user['bitcoins']:.4f} BTC\n"
            f"⚡ Энергия: {user['energy']}/{user['max_energy']}\n"
            f"🏆 Уровень: {user['level']}\n\n"
            f"🆔 Ваш ID для переводов: <code>{user['player_id']}</code>\n\n"
            f"✨ <b>Доступные функции:</b>\n"
            f"• 👤 Профиль - ваша статистика\n"
            f"• 🎮 Игры - слоты, кости, викторина\n"
            f"• 💼 Работа - заработок денег\n"
            f"• 🏪 Магазин - покупка предметов\n"
            f"• 📊 Статистика - лидеры\n"
            f"• 🎁 Награда - бонус каждые 2 часа\n"
            f"• 💼 Бизнесы - покупка и управление\n"
            f"• 🎁 Кейсы - испытайте удачу\n\n"
            f"💡 Используйте кнопки для навигации!"
        )
        
        await message.answer(welcome_text, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}")
        await message.answer("👋 Добро пожаловать в игровой бот! Используйте кнопки ниже.", reply_markup=get_main_keyboard())

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ панель"""
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await message.answer("❌ У вас нет доступа к админ-панели!")
            return
        
        admin_text = (
            f"👑 <b>Админ панель</b>\n\n"
            f"👤 Администратор: {message.from_user.full_name}\n"
            f"🆔 ID: {user_id}\n\n"
            f"📊 <b>Доступные команды:</b>\n"
            f"• 📊 Статистика - общая статистика бота\n"
            f"• 👥 Рассылка - отправить сообщение всем пользователям\n"
            f"• 💰 Выдать деньги - добавить деньги пользователю\n"
            f"• 🎁 Выдать опыт - добавить опыт пользователю\n"
            f"• 📋 Список пользователей - показать всех пользователей\n\n"
            f"⚠️ <b>Внимание:</b> Используйте функции осторожно!"
        )
        
        await message.answer(admin_text, reply_markup=get_admin_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в cmd_admin: {e}")
        await message.answer("❌ Ошибка доступа к админ-панели!")

@dp.message(F.text == "👤 Профиль")
async def handle_profile(message: Message):
    """Профиль пользователя"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            # Создаем пользователя если его нет
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        # Рассчитываем проценты
        energy_percent = (user['energy'] / user['max_energy']) * 100 if user['max_energy'] > 0 else 0
        exp_needed = user['level'] * 100
        exp_percent = (user['experience'] / exp_needed) * 100 if exp_needed > 0 else 0
        
        # Получаем предметы пользователя
        items = get_user_items(user_id)
        
        # Получаем бизнесы пользователя
        businesses = get_user_businesses(user_id)
        
        # Рассчитываем стоимость биткоинов в долларах
        btc_value = user['bitcoins'] * bitcoin_price
        
        # Проверяем доступность награды
        can_reward, remaining_time = can_get_reward(user_id)
        
        profile_text = (
            f"👤 <b>Профиль</b>\n\n"
            f"🏷️ Имя: {user['full_name']}\n"
            f"📧 @{user['username'] if user.get('username') else 'нет'}\n"
            f"🆔 ID: {user_id}\n"
            f"🎫 Player ID: <code>{user['player_id']}</code>\n\n"
            f"🏆 Уровень: {user['level']}\n"
            f"📈 Опыт: {user['experience']}/{exp_needed} ({exp_percent:.1f}%)\n\n"
            f"💰 Доллары: {format_money(user['dollars'])}\n"
            f"₿ Биткоины: {user['bitcoins']:.4f} BTC ({format_money(btc_value)})\n"
            f"📊 Курс BTC: {bitcoin_price:,.0f}$\n"
            f"⚡ Энергия: {user['energy']}/{user['max_energy']} ({energy_percent:.1f}%)\n\n"
            f"💼 Бизнесов: {len(businesses)}\n"
            f"📦 Предметов: {len(items)}\n"
            f"🧠 Прогресс викторины: {user['quiz_progress']}/{len(QUIZ_QUESTIONS)}\n\n"
        )
        
        if items:
            profile_text += "📦 <b>Ваши предметы:</b>\n"
            for item in items[:5]:  # Показываем только 5 последних
                profile_text += f"• {item['name']}\n"
            if len(items) > 5:
                profile_text += f"• ... и еще {len(items) - 5}\n"
            profile_text += "\n"
        
        if can_reward:
            profile_text += f"🎁 Награда: <b>Доступна сейчас!</b>\n"
        else:
            profile_text += f"🎁 Награда: <b>Доступна через {remaining_time}</b>\n"
        
        if user.get('created_at'):
            try:
                created_date = datetime.strptime(user['created_at'], '%Y-%m-%d %H:%M:%S')
                profile_text += f"\n📅 Создан: {created_date.strftime('%d.%m.%Y %H:%M')}"
            except:
                profile_text += f"\n📅 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        # Кнопка для передачи денег
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Передать деньги", callback_data="transfer_money")
        builder.button(text="📤 Показать мой ID", callback_data="show_my_id")
        builder.adjust(1, 1)
        
        await message.answer(profile_text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Ошибка в handle_profile: {e}")
        await message.answer("❌ Ошибка загрузки профиля! Попробуйте /start")

@dp.message(F.text == "🎮 Игры")
async def handle_games(message: Message):
    """Игры"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        games_text = (
            f"🎮 <b>Игры</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"⚡ Энергия: {user['energy']}/{user['max_energy']}\n\n"
            f"Выберите игру:\n\n"
            f"🎰 <b>Слоты</b> - классические игровые автоматы\n"
            f"🎲 <b>Кости</b> - сыграйте против бота\n"
            f"🎯 <b>Дартс</b> - проверьте свою меткость\n"
            f"❓ <b>Викторина</b> - проверьте знания (10 вопросов)\n\n"
            f"💡 Все игры дают опыт и деньги!"
        )
        
        await message.answer(games_text, reply_markup=get_games_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_games: {e}")
        await message.answer("🎮 <b>Игры</b>\n\nВыберите игру:", reply_markup=get_games_keyboard())

@dp.message(F.text == "💼 Работа")
async def handle_work(message: Message):
    """Работа"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        work_text = (
            f"💼 <b>Работа</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"⚡ Ваша энергия: {user['energy']}/{user['max_energy']}\n\n"
            f"<b>Доступные работы:</b>\n\n"
            f"👷 <b>Уборщик</b>\n"
            f"📝 Уборка помещений\n"
            f"💰 Зарплата: 50$\n"
            f"⚡ Энергии: 10\n"
            f"📈 Опыта: 5\n\n"
            f"🚴 <b>Курьер</b>\n"
            f"📝 Доставка товаров\n"
            f"💰 Зарплата: 100$\n"
            f"⚡ Энергии: 15\n"
            f"📈 Опыта: 10\n\n"
            f"👨‍💼 <b>Офисный работник</b>\n"
            f"📝 Работа в офисе\n"
            f"💰 Зарплата: 200$\n"
            f"⚡ Энергии: 20\n"
            f"📈 Опыта: 20\n\n"
            f"💡 После выполнения работы можно сразу начать новую!"
        )
        
        await message.answer(work_text, reply_markup=get_work_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_work: {e}")
        await message.answer("💼 <b>Работа</b>\n\nВыберите работу:", reply_markup=get_work_keyboard())

@dp.message(F.text == "🏪 Магазин")
async def handle_shop(message: Message):
    """Магазин"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        shop_text = (
            f"🏪 <b>Магазин</b>\n\n"
            f"💰 Баланс: {format_money(user['dollars'])}\n"
            f"₿ Биткоины: {user['bitcoins']:.4f} BTC\n\n"
            f"🛍️ <b>Категории товаров:</b>\n\n"
            f"🚗 <b>Машины</b>\n"
            f"📝 От базовой до премиум + самолет\n\n"
            f"📱 <b>Телефоны</b>\n"
            f"📝 От базового до премиум\n\n"
            f"🏠 <b>Недвижимость</b>\n"
            f"📝 Дома и квартиры\n\n"
            f"⚡ <b>Энергия</b>\n"
            f"📝 Восстановление энергии"
        )
        
        await message.answer(shop_text, reply_markup=get_shop_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_shop: {e}")
        await message.answer("🏪 <b>Магазин</b>\n\nВыберите категорию:", reply_markup=get_shop_keyboard())

@dp.message(F.text == "📊 Статистика")
async def handle_stats(message: Message):
    """Статистика"""
    try:
        # Получаем статистику из базы
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(dollars) FROM users')
        total_dollars_result = cursor.fetchone()
        total_dollars = total_dollars_result[0] if total_dollars_result and total_dollars_result[0] else 0
        
        cursor.execute('SELECT SUM(bitcoins) FROM users')
        total_bitcoins_result = cursor.fetchone()
        total_bitcoins = total_bitcoins_result[0] if total_bitcoins_result and total_bitcoins_result[0] else 0
        
        cursor.execute('SELECT full_name, dollars, level FROM users ORDER BY dollars DESC LIMIT 10')
        top_players = cursor.fetchall()
        
        conn.close()
        
        # Стоимость биткоинов в долларах
        btc_value = total_bitcoins * bitcoin_price
        
        stats_text = f"📊 <b>Статистика бота</b>\n\n"
        stats_text += f"👥 Всего игроков: {total_users}\n"
        stats_text += f"💰 Всего денег: {format_money(total_dollars)}\n"
        stats_text += f"₿ Всего биткоинов: {total_bitcoins:.4f} BTC ({format_money(btc_value)})\n"
        stats_text += f"📈 Курс BTC: {bitcoin_price:,.0f}$\n\n"
        
        if top_players:
            stats_text += "🏆 <b>Топ-10 по деньгам:</b>\n"
            for i, (name, dollars, level) in enumerate(top_players, 1):
                stats_text += f"{i}. {name}: {format_money(dollars)} (Ур. {level})\n"
        else:
            stats_text += "🏆 Топ игроков: пока нет данных\n"
        
        await message.answer(stats_text, reply_markup=get_back_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_stats: {e}")
        await message.answer("📊 <b>Статистика бота</b>\n\nДанные загружаются...", reply_markup=get_back_keyboard())

@dp.message(F.text == "🎁 Награда")
async def handle_daily_reward(message: Message):
    """Ежедневная награда (каждые 2 часа)"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        # Проверяем возможность получения награды
        can_reward, remaining_time = can_get_reward(user_id)
        
        if not can_reward:
            reward_text = (
                f"⏳ <b>Награда еще не доступна</b>\n\n"
                f"🎁 Вы уже получали награду менее 2 часов назад.\n"
                f"⏰ До следующей награды осталось: <b>{remaining_time}</b>\n\n"
                f"💡 Награду можно получать раз в 2 часа!\n"
                f"💰 Текущий баланс: {format_money(user['dollars'])}"
            )
            
            await message.answer(reward_text, reply_markup=get_back_keyboard())
            return
        
        # Выдаем награду
        dollars = random.randint(50, 150)
        btc_amount = random.uniform(0.0001, 0.001)
        
        update_user_dollars(user_id, dollars)
        update_user_bitcoins(user_id, btc_amount)
        update_last_reward_time(user_id)  # Обновляем время получения награды
        
        user = get_user(user_id)  # Получаем обновленные данные
        
        reward_text = (
            f"🎁 <b>Награда получена!</b>\n\n"
            f"💰 +{dollars}$\n"
            f"₿ +{btc_amount:.4f} BTC\n\n"
            f"🎉 Ваш новый баланс: {format_money(user['dollars'])}\n"
            f"₿ Биткоины: {user['bitcoins']:.4f} BTC\n\n"
            f"⏰ Следующая награда будет доступна через 2 часа!\n"
            f"📅 Время получения: {datetime.now().strftime('%H:%M')}"
        )
        
        await message.answer(reward_text, reply_markup=get_back_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_daily_reward: {e}")
        await message.answer("🎁 <b>Награда</b>\n\nПроизошла ошибка при получении награды!", reply_markup=get_back_keyboard())

@dp.message(F.text == "💼 Бизнесы")
async def handle_businesses(message: Message):
    """Бизнесы"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        businesses = get_user_businesses(user_id)
        total_income = sum(b['business_balance'] for b in businesses)
        
        business_text = (
            f"💼 <b>Бизнесы</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🏆 Уровень: {user['level']}\n"
            f"📊 Доход к сбору: {format_money(total_income)}\n"
            f"🏢 Ваших бизнесов: {len(businesses)}\n\n"
            f"<b>Доступные для покупки:</b>\n\n"
        )
        
        for business in BUSINESSES:
            owned = any(b['business_id'] == business['id'] for b in businesses)
            emoji = "✅" if owned else "🛒"
            level_required = f" | Требуется уровень: {business['level_required']}" if business['level_required'] > 1 else ""
            can_buy = user['level'] >= business['level_required']
            status = " (Доступно)" if can_buy and not owned else " (Недоступно)" if not can_buy else " (Куплено)"
            
            business_text += (
                f"{emoji} <b>{business['emoji']} {business['name']}</b>\n"
                f"💰 Цена: {format_money(business['price'])}\n"
                f"💵 Доход/час: {format_money(business['income_per_hour'])}{level_required}{status}\n\n"
            )
        
        business_text += "💡 Бизнесы приносят доход каждый час. Собирайте его вовремя!"
        
        await message.answer(business_text, reply_markup=get_businesses_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_businesses: {e}")
        await message.answer("💼 <b>Бизнесы</b>\n\nВыберите действие:", reply_markup=get_businesses_keyboard())

@dp.message(F.text == "🎁 Кейсы")
async def handle_cases(message: Message):
    """Кейсы"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            user = create_or_update_user(
                user_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
        
        cases_text = (
            f"🎁 <b>Кейсы</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🏆 Уровень: {user['level']}\n\n"
            f"<b>Доступные кейсы:</b>\n\n"
        )
        
        for case in CASES:
            can_buy = user['level'] >= case['level_required']
            status = "✅ Доступно" if can_buy else f"❌ Требуется уровень {case['level_required']}"
            
            cases_text += (
                f"🎁 <b>{case['name']}</b>\n"
                f"💰 Цена: {format_money(case['price'])}\n"
                f"🎯 Выигрыш: {format_money(case['min_reward'])} - {format_money(case['max_reward'])}\n"
                f"{status}\n\n"
            )
        
        cases_text += "💡 Открывайте кейсы и получайте деньги + опыт!"
        
        await message.answer(cases_text, reply_markup=get_cases_keyboard())
    except Exception as e:
        logger.error(f"Ошибка в handle_cases: {e}")
        await message.answer("🎁 <b>Кейсы</b>\n\nВыберите кейс:", reply_markup=get_cases_keyboard())

@dp.message(F.text == "« Назад в меню")
async def handle_back(message: Message):
    """Назад в меню"""
    await message.answer("🔙 Главное меню", reply_markup=get_main_keyboard())

# ========== ПЕРЕДАЧА ДЕНЕГ ==========

@dp.message(F.text.regexp(r'^перевод\s+\w+\s+\d+$'))
async def handle_transfer(message: Message):
    """Обработчик перевода денег"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            await message.answer("❌ Ошибка загрузки профиля!")
            return
        
        # Разбираем команду: "перевод PLAYER_ID СУММА"
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Неверный формат команды!\n\nИспользуйте: <code>перевод PLAYER_ID СУММА</code>\n\nПример: <code>перевод A1B2C3D4 100</code>")
            return
        
        target_player_id = parts[1].upper()
        try:
            amount = float(parts[2])
        except ValueError:
            await message.answer("❌ Сумма должна быть числом!")
            return
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0!")
            return
        
        if amount > user['dollars']:
            await message.answer(f"❌ Недостаточно денег! У вас {format_money(user['dollars'])}, а хотите перевести {format_money(amount)}")
            return
        
        # Находим получателя
        target_user = get_user_by_player_id(target_player_id)
        if not target_user:
            await message.answer(f"❌ Игрок с ID <code>{target_player_id}</code> не найден!")
            return
        
        if target_user['user_id'] == user_id:
            await message.answer("❌ Нельзя переводить деньги самому себе!")
            return
        
        # Проверяем минимальную сумму
        if amount < 10:
            await message.answer("❌ Минимальная сумма перевода - 10$!")
            return
        
        # Выполняем перевод
        update_user_dollars(user_id, -amount)
        update_user_dollars(target_user['user_id'], amount)
        
        # Записываем транзакцию
        create_transaction(
            from_user_id=user_id,
            to_user_id=target_user['user_id'],
            amount=amount,
            currency="USD",
            description=f"Перевод от {user['full_name']}"
        )
        
        # Получаем обновленные данные
        user = get_user(user_id)
        
        success_text = (
            f"✅ <b>Перевод выполнен успешно!</b>\n\n"
            f"👤 Отправитель: {user['full_name']}\n"
            f"👤 Получатель: {target_user['full_name']}\n"
            f"💰 Сумма: {format_money(amount)}\n"
            f"🎫 ID перевода: {target_player_id}\n\n"
            f"💵 Ваш новый баланс: {format_money(user['dollars'])}\n"
            f"📅 Время: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await message.answer(success_text)
        
        # Уведомляем получателя
        try:
            await bot.send_message(
                target_user['user_id'],
                f"💰 <b>Вы получили перевод!</b>\n\n"
                f"👤 Отправитель: {user['full_name']}\n"
                f"💰 Сумма: {format_money(amount)}\n"
                f"💵 Ваш новый баланс: {format_money(target_user['dollars'] + amount)}"
            )
        except:
            pass  # Если не получилось уведомить, ничего страшного
            
    except Exception as e:
        logger.error(f"Ошибка в handle_transfer: {e}")
        await message.answer("❌ Произошла ошибка при переводе!")

@dp.callback_query(F.data == "transfer_money")
async def handle_transfer_callback(callback: CallbackQuery):
    """Показать инструкцию по переводу"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        instruction_text = (
            f"💰 <b>Как перевести деньги?</b>\n\n"
            f"1. Получите Player ID у друга\n"
            f"2. Используйте команду:\n"
            f"<code>перевод PLAYER_ID СУММА</code>\n\n"
            f"📝 <b>Пример:</b>\n"
            f"<code>перевод {user['player_id']} 100</code>\n\n"
            f"🎫 <b>Ваш Player ID:</b>\n"
            f"<code>{user['player_id']}</code>\n\n"
            f"⚠️ <b>Важно:</b>\n"
            f"• Минимальная сумма: 10$\n"
            f"• Комиссия: 0%\n"
            f"• Нельзя переводить себе\n"
            f"• Проверяйте ID получателя!"
        )
        
        await callback.message.answer(instruction_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_transfer_callback: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "show_my_id")
async def handle_show_my_id(callback: CallbackQuery):
    """Показать мой ID"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        id_text = (
            f"🎫 <b>Ваш Player ID</b>\n\n"
            f"👤 Имя: {user['full_name']}\n"
            f"🎫 ID: <code>{user['player_id']}</code>\n\n"
            f"📋 <b>Как использовать:</b>\n"
            f"1. Дайте этот ID другу\n"
            f"2. Он введет команду:\n"
            f"<code>перевод {user['player_id']} СУММА</code>\n\n"
            f"💡 Пример:\n"
            f"<code>перевод {user['player_id']} 500</code>"
        )
        
        await callback.message.answer(id_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_show_my_id: {e}")
        await callback.answer("❌ Ошибка!")

# ========== INLINE ОБРАБОТЧИКИ ==========

@dp.callback_query(F.data == "back_main")
async def handle_back_main(callback: CallbackQuery):
    """Назад в главное меню"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("🔙 Главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_games")
async def handle_back_to_games(callback: CallbackQuery):
    """Назад к списку игр"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("🎮 <b>Игры</b>\n\nВыберите игру:", reply_markup=get_games_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_works")
async def handle_back_to_works(callback: CallbackQuery):
    """Назад к списку работ"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("💼 <b>Работа</b>\n\nВыберите работу:", reply_markup=get_work_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_shop")
async def handle_back_to_shop(callback: CallbackQuery):
    """Назад в магазин"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("🏪 <b>Магазин</b>\n\nВыберите категорию:", reply_markup=get_shop_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_businesses")
async def handle_back_to_businesses(callback: CallbackQuery):
    """Назад к бизнесам"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("💼 <b>Бизнесы</b>\n\nВыберите действие:", reply_markup=get_businesses_keyboard())
    await callback.answer()

# ========== РАБОТА ==========

@dp.callback_query(F.data == "work_cleaner")
async def handle_work_cleaner(callback: CallbackQuery):
    """Работа уборщиком"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['energy'] < 10:
            await callback.answer("❌ Недостаточно энергии!")
            return
        
        # Выполняем работу
        update_user_energy(user_id, -10)
        update_user_dollars(user_id, 50)
        
        # Добавляем опыт
        new_level = add_user_experience(user_id, 5)
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"💼 <b>Работа выполнена!</b>\n\n"
            f"👷 Уборщик\n"
            f"📝 Уборка помещений\n\n"
            f"🎉 <b>Награда:</b>\n"
            f"💰 +50$\n"
            f"⚡ Потрачено энергии: 10\n"
            f"📈 +5 опыта\n"
        )
        
        if new_level and new_level > user['level']:
            result_text += f"🏆 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🔋 Энергия: {user['energy']}/{user['max_energy']}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_work_again_keyboard("cleaner"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_work_cleaner: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "work_courier")
async def handle_work_courier(callback: CallbackQuery):
    """Работа курьером"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['energy'] < 15:
            await callback.answer("❌ Недостаточно энергии!")
            return
        
        # Выполняем работу
        update_user_energy(user_id, -15)
        update_user_dollars(user_id, 100)
        
        # Добавляем опыт
        new_level = add_user_experience(user_id, 10)
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"💼 <b>Работа выполнена!</b>\n\n"
            f"🚴 Курьер\n"
            f"📝 Доставка товаров\n\n"
            f"🎉 <b>Награда:</b>\n"
            f"💰 +100$\n"
            f"⚡ Потрачено энергии: 15\n"
            f"📈 +10 опыта\n"
        )
        
        if new_level and new_level > user['level']:
            result_text += f"🏆 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🔋 Энергия: {user['energy']}/{user['max_energy']}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_work_again_keyboard("courier"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_work_courier: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "work_office")
async def handle_work_office(callback: CallbackQuery):
    """Работа офисным работником"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['energy'] < 20:
            await callback.answer("❌ Недостаточно энергии!")
            return
        
        # Выполняем работу
        update_user_energy(user_id, -20)
        update_user_dollars(user_id, 200)
        
        # Добавляем опыт
        new_level = add_user_experience(user_id, 20)
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"💼 <b>Работа выполнена!</b>\n\n"
            f"👨‍💼 Офисный работник\n"
            f"📝 Работа в офисе\n\n"
            f"🎉 <b>Награда:</b>\n"
            f"💰 +200$\n"
            f"⚡ Потрачено энергии: 20\n"
            f"📈 +20 опыта\n"
        )
        
        if new_level and new_level > user['level']:
            result_text += f"🏆 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🔋 Энергия: {user['energy']}/{user['max_energy']}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_work_again_keyboard("office"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_work_office: {e}")
        await callback.answer("❌ Ошибка!")

# ========== МАГАЗИН ==========

@dp.callback_query(F.data == "shop_cars")
async def handle_shop_cars(callback: CallbackQuery):
    """Показать машины"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        cars_text = (
            f"🚗 <b>Машины и транспорт</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n\n"
            f"🛒 <b>Доступные транспортные средства:</b>\n\n"
            f"🚗 <b>Базовая машина</b> - 500$\n"
            f"📝 Увеличивает доход от работы на 10%\n\n"
            f"🚗 <b>Средняя машина</b> - 5,000$\n"
            f"📝 Увеличивает доход от работы на 25%\n\n"
            f"🚗 <b>Премиум машина</b> - 25,000$\n"
            f"📝 Увеличивает доход от работы на 50%\n\n"
            f"✈️ <b>Самолет</b> - 1,000,000$\n"
            f"📝 Увеличивает доход от бизнеса на 100%\n\n"
            f"💡 Бонусы суммируются!"
        )
        
        await callback.message.edit_text(cars_text, reply_markup=get_cars_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_shop_cars: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "shop_phones")
async def handle_shop_phones(callback: CallbackQuery):
    """Показать телефоны"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        phones_text = (
            f"📱 <b>Телефоны</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n\n"
            f"🛒 <b>Доступные телефоны:</b>\n\n"
            f"📱 <b>Базовый телефон</b> - 300$\n"
            f"📝 +5% ко всем доходам\n\n"
            f"📱 <b>Средний телефон</b> - 2,000$\n"
            f"📝 +15% ко всем доходам\n\n"
            f"📱 <b>Премиум телефон</b> - 10,000$\n"
            f"📝 +30% ко всем доходам\n\n"
            f"💡 Бонусы суммируются!"
        )
        
        await callback.message.edit_text(phones_text, reply_markup=get_phones_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_shop_phones: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "shop_property")
async def handle_shop_property(callback: CallbackQuery):
    """Показать недвижимость"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        property_text = (
            f"🏠 <b>Недвижимость</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n\n"
            f"🛒 <b>Доступная недвижимость:</b>\n\n"
            f"🏠 <b>Дом</b> - 1,000$\n"
            f"📝 Увеличивает максимальную энергию на 50\n\n"
            f"💡 Больше энергии = больше работы!"
        )
        
        await callback.message.edit_text(property_text, reply_markup=get_property_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_shop_property: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_house")
async def handle_buy_house(callback: CallbackQuery):
    """Покупка дома"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 1000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем дом
        update_user_dollars(user_id, -1000)
        # Увеличиваем максимальную энергию
        update_user_max_energy(user_id, user['max_energy'] + 50)
        # Добавляем предмет
        add_user_item(user_id, "🏠 Дом")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"🏠 Вы купили дом\n"
            f"💰 Потрачено: 1,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"⚡ Максимальная энергия увеличена на 50!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🔋 Макс. энергия: {user['max_energy']}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_house: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_car_basic")
async def handle_buy_car_basic(callback: CallbackQuery):
    """Покупка базовой машины"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 500:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем машину
        update_user_dollars(user_id, -500)
        # Добавляем предмет
        add_user_item(user_id, "🚗 Базовая машина")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"🚗 Вы купили базовую машину\n"
            f"💰 Потрачено: 500$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 Теперь вы зарабатываете на 10% больше от работы!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_car_basic: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_car_medium")
async def handle_buy_car_medium(callback: CallbackQuery):
    """Покупка средней машины"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 5000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем машину
        update_user_dollars(user_id, -5000)
        # Добавляем предмет
        add_user_item(user_id, "🚗 Средняя машина")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"🚗 Вы купили среднюю машину\n"
            f"💰 Потрачено: 5,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 Теперь вы зарабатываете на 25% больше от работы!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_car_medium: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_car_premium")
async def handle_buy_car_premium(callback: CallbackQuery):
    """Покупка премиум машины"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 25000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем машину
        update_user_dollars(user_id, -25000)
        # Добавляем предмет
        add_user_item(user_id, "🚗 Премиум машина")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"🚗 Вы купили премиум машину\n"
            f"💰 Потрачено: 25,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 Теперь вы зарабатываете на 50% больше от работы!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_car_premium: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_plane")
async def handle_buy_plane(callback: CallbackQuery):
    """Покупка самолета"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 1000000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем самолет
        update_user_dollars(user_id, -1000000)
        # Добавляем предмет
        add_user_item(user_id, "✈️ Самолет")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"✈️ Вы купили самолет\n"
            f"💰 Потрачено: 1,000,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 Теперь вы получаете на 100% больше от бизнеса!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_plane: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_phone_basic")
async def handle_buy_phone_basic(callback: CallbackQuery):
    """Покупка базового телефона"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 300:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем телефон
        update_user_dollars(user_id, -300)
        # Добавляем предмет
        add_user_item(user_id, "📱 Базовый телефон")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"📱 Вы купили базовый телефон\n"
            f"💰 Потрачено: 300$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 +5% ко всем доходам!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_phone_basic: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_phone_medium")
async def handle_buy_phone_medium(callback: CallbackQuery):
    """Покупка среднего телефона"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 2000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем телефон
        update_user_dollars(user_id, -2000)
        # Добавляем предмет
        add_user_item(user_id, "📱 Средний телефон")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"📱 Вы купили средний телефон\n"
            f"💰 Потрачено: 2,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 +15% ко всем доходам!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_phone_medium: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_phone_premium")
async def handle_buy_phone_premium(callback: CallbackQuery):
    """Покупка премиум телефона"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 10000:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем телефон
        update_user_dollars(user_id, -10000)
        # Добавляем предмет
        add_user_item(user_id, "📱 Премиум телефон")
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"📱 Вы купили премиум телефон\n"
            f"💰 Потрачено: 10,000$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"💰 +30% ко всем доходам!\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_phone_premium: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "buy_energy")
async def handle_buy_energy(callback: CallbackQuery):
    """Покупка энергии"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        if user['dollars'] < 50:
            await callback.answer("❌ Недостаточно денег!")
            return
        
        # Покупаем энергию
        update_user_dollars(user_id, -50)
        update_user_energy(user_id, 20)
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"⚡ Вы купили энергию\n"
            f"💰 Потрачено: 50$\n\n"
            f"✨ <b>Бонус:</b>\n"
            f"⚡ +20 энергии\n\n"
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🔋 Энергия: {user['energy']}/{user['max_energy']}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_energy: {e}")
        await callback.answer("❌ Ошибка!")

# ========== БИЗНЕСЫ ==========

@dp.callback_query(F.data.startswith("business_"))
async def handle_business(callback: CallbackQuery):
    """Обработка бизнесов"""
    try:
        data = callback.data
        
        if data == "business_collect":
            await handle_business_collect(callback)
        elif data == "business_my":
            await handle_business_my(callback)
        else:
            # Покупка бизнеса
            business_id = int(data.split("_")[1])
            await handle_business_buy(callback, business_id)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_business: {e}")
        await callback.answer("❌ Ошибка!")

async def handle_business_buy(callback: CallbackQuery, business_id: int):
    """Покупка бизнеса"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        business = next((b for b in BUSINESSES if b['id'] == business_id), None)
        if not business:
            await callback.answer("❌ Бизнес не найден!")
            return
        
        # Проверяем уровень
        if user['level'] < business['level_required']:
            await callback.answer(f"❌ Требуется уровень {business['level_required']}!")
            return
        
        # Проверяем деньги
        if user['dollars'] < business['price']:
            await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(business['price'])}")
            return
        
        # Покупаем бизнес
        if buy_business(user_id, business_id):
            user = get_user(user_id)  # Обновленные данные
            
            result_text = (
                f"✅ <b>Бизнес куплен!</b>\n\n"
                f"{business['emoji']} <b>{business['name']}</b>\n"
                f"💰 Потрачено: {format_money(business['price'])}\n"
                f"💵 Доход/час: {format_money(business['income_per_hour'])}\n\n"
                f"🎉 <b>Поздравляем с покупкой!</b>\n"
                f"📈 Бизнес начнет приносить доход через 1 час\n"
                f"💵 Ваш баланс: {format_money(user['dollars'])}\n\n"
                f"💡 Заходите регулярно собирать доход!"
            )
            
            await callback.message.edit_text(result_text)
        else:
            await callback.answer("❌ Не удалось купить бизнес! Возможно, он уже у вас есть.")
            
    except Exception as e:
        logger.error(f"Ошибка в handle_business_buy: {e}")
        await callback.answer("❌ Ошибка при покупке бизнеса!")

async def handle_business_collect(callback: CallbackQuery):
    """Собрать доход со всех бизнесов"""
    try:
        user_id = callback.from_user.id
        businesses = get_user_businesses(user_id)
        
        if not businesses:
            await callback.answer("❌ У вас нет бизнесов!")
            return
        
        total_collected = 0
        collected_businesses = []
        
        for business in businesses:
            collected = collect_business_income(user_id, business['id'])
            if collected > 0:
                total_collected += collected
                collected_businesses.append(business)
        
        if total_collected == 0:
            await callback.answer("💰 Нет дохода для сбора!")
            return
        
        user = get_user(user_id)  # Обновленные данные
        
        result_text = (
            f"💰 <b>Доход собран!</b>\n\n"
            f"💵 Всего собрано: {format_money(total_collected)}\n"
            f"🏢 Бизнесов: {len(collected_businesses)}\n\n"
        )
        
        if collected_businesses:
            result_text += "<b>Собрано с:</b>\n"
            for biz in collected_businesses[:5]:  # Показываем только первые 5
                result_text += f"• {biz['emoji']} {biz['name']}: {format_money(biz['business_balance'])}\n"
            
            if len(collected_businesses) > 5:
                result_text += f"• ... и еще {len(collected_businesses) - 5} бизнесов\n"
        
        result_text += f"\n💵 Новый баланс: {format_money(user['dollars'])}"
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_business_collect: {e}")
        await callback.answer("❌ Ошибка при сборе дохода!")

async def handle_business_my(callback: CallbackQuery):
    """Показать мои бизнесы"""
    try:
        user_id = callback.from_user.id
        businesses = get_user_businesses(user_id)
        
        if not businesses:
            await callback.answer("❌ У вас нет бизнесов!")
            return
        
        total_income = sum(b['business_balance'] for b in businesses)
        total_hourly = sum(b['income_per_hour'] for b in businesses)
        
        my_businesses_text = (
            f"🏢 <b>Мои бизнесы</b>\n\n"
            f"💰 Доход к сбору: {format_money(total_income)}\n"
            f"💵 Доход/час: {format_money(total_hourly)}\n"
            f"🏢 Всего бизнесов: {len(businesses)}\n\n"
            f"<b>Список бизнесов:</b>\n\n"
        )
        
        for business in businesses:
            try:
                last_collected = datetime.strptime(business['last_collected'], '%Y-%m-%d %H:%M:%S')
                hours_passed = (datetime.now() - last_collected).total_seconds() / 3600
                next_income = business['income_per_hour'] * hours_passed
            except:
                next_income = 0
            
            my_businesses_text += (
                f"{business['emoji']} <b>{business['name']}</b>\n"
                f"💵 Доход/час: {format_money(business['income_per_hour'])}\n"
                f"💰 Накоплено: {format_money(business['business_balance'])}\n"
                f"💸 Следующий: ~{format_money(next_income)}\n\n"
            )
        
        my_businesses_text += "💡 Нажмите на бизнес, чтобы собрать доход!"
        
        await callback.message.edit_text(my_businesses_text, reply_markup=get_my_businesses_keyboard(businesses))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_business_my: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data.startswith("collect_"))
async def handle_collect_single(callback: CallbackQuery):
    """Собрать доход с конкретного бизнеса"""
    try:
        business_db_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        collected = collect_business_income(user_id, business_db_id)
        
        if collected > 0:
            user = get_user(user_id)
            
            result_text = (
                f"✅ <b>Доход собран!</b>\n\n"
                f"💰 Собрано: {format_money(collected)}\n"
                f"💵 Новый баланс: {format_money(user['dollars'])}\n\n"
                f"💡 Заходите регулярно собирать доход!"
            )
            
            await callback.message.edit_text(result_text)
        else:
            await callback.answer("💰 Нет дохода для сбора!")
            
    except Exception as e:
        logger.error(f"Ошибка в handle_collect_single: {e}")
        await callback.answer("❌ Ошибка!")

# ========== КЕЙСЫ ==========

@dp.callback_query(F.data.startswith("case_"))
async def handle_case(callback: CallbackQuery):
    """Открытие кейса"""
    try:
        case_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        # Находим кейс
        case = next((c for c in CASES if c['id'] == case_id), None)
        if not case:
            await callback.answer("❌ Кейс не найден!")
            return
        
        # Проверяем уровень
        if user['level'] < case['level_required']:
            await callback.answer(f"❌ Требуется уровень {case['level_required']}!")
            return
        
        # Проверяем деньги
        if user['dollars'] < case['price']:
            await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(case['price'])}")
            return
        
        # Покупаем кейс
        update_user_dollars(user_id, -case['price'])
        
        # Анимация открытия
        await callback.message.edit_text(
            f"🎁 <b>Открываем {case['name']}...</b>\n\n"
            f"💰 Стоимость: {format_money(case['price'])}\n"
            f"⏳ Кейс открывается..."
        )
        
        # Небольшая задержка для анимации
        await asyncio.sleep(2)
        
        # Генерируем выигрыш
        money_reward = random.randint(case['min_reward'], case['max_reward'])
        
        # Начисляем выигрыш
        update_user_dollars(user_id, money_reward)
        
        # Добавляем опыт за открытие кейса
        exp_reward = case['price'] // 10  # 10% от стоимости кейса
        new_level = add_user_experience(user_id, exp_reward)
        
        user = get_user(user_id)  # Обновленные данные
        
        # Формируем результат
        result_text = (
            f"🎁 <b>{case['name']} открыт!</b>\n\n"
            f"💰 Выигрыш: {format_money(money_reward)}\n"
            f"📈 Опыта: +{exp_reward}\n"
        )
        
        if new_level and new_level > user['level']:
            result_text += f"\n🏆 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        else:
            result_text += "\n"
        
        result_text += (
            f"💵 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🏆 Уровень: {user['level']}"
        )
        
        await callback.message.edit_text(result_text)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_case: {e}")
        await callback.answer("❌ Ошибка при открытии кейса!")

# ========== ИГРЫ ==========

@dp.callback_query(F.data == "game_slots")
async def handle_game_slots(callback: CallbackQuery):
    """Игра в слоты - выбор ставки"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        slots_text = (
            f"🎰 <b>Игра в слоты</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🎯 Выберите ставку:\n\n"
            f"✨ <b>Выигрышные комбинации:</b>\n"
            f"🍒🍒🍒 - x2\n"
            f"🍋🍋🍋 - x3\n"
            f"🍊🍊🍊 - x5\n"
            f"💎💎💎 - x10\n"
            f"⭐⭐⭐ - x20\n\n"
            f"💡 Можно выбрать готовую ставку или ввести свою"
        )
        
        await callback.message.edit_text(slots_text, reply_markup=get_bet_keyboard("slots"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_game_slots: {e}")
        await callback.answer("❌ Ошибка в игре!")

@dp.callback_query(F.data == "game_dice")
async def handle_game_dice(callback: CallbackQuery):
    """Игра в кости - выбор ставки"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        dice_text = (
            f"🎲 <b>Игра в кости</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🎯 Выберите ставку:\n\n"
            f"✨ <b>Правила:</b>\n"
            f"• Бросаете кубик против бота\n"
            f"• У кого больше очков - тот выиграл\n"
            f"• При ничье ставка возвращается\n"
            f"• При выигрыше: x2 от ставки\n\n"
            f"💡 Можно выбрать готовую ставку или ввести свою"
        )
        
        await callback.message.edit_text(dice_text, reply_markup=get_bet_keyboard("dice"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_game_dice: {e}")
        await callback.answer("❌ Ошибка в игре!")

@dp.callback_query(F.data == "game_darts")
async def handle_game_darts(callback: CallbackQuery):
    """Игра в дартс - выбор ставки"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        darts_text = (
            f"🎯 <b>Игра в дартс</b>\n\n"
            f"💰 Ваш баланс: {format_money(user['dollars'])}\n"
            f"🎯 Выберите ставку:\n\n"
            f"✨ <b>Правила:</b>\n"
            f"• Кидаете дротик в мишень\n"
            f"• Чем ближе к центру - тем больше выигрыш\n"
            f"• Максимальный выигрыш: x5 от ставки\n\n"
            f"💡 Можно выбрать готовую ставку или ввести свою"
        )
        
        await callback.message.edit_text(darts_text, reply_markup=get_bet_keyboard("darts"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_game_darts: {e}")
        await callback.answer("❌ Ошибка в игре!")

@dp.callback_query(F.data == "game_quiz")
async def handle_game_quiz(callback: CallbackQuery):
    """Викторина"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        quiz_text = (
            f"❓ <b>Викторина</b>\n\n"
            f"🏆 Уровень: {user['level']}\n"
            f"🧠 Прогресс: {user['quiz_progress']}/{len(QUIZ_QUESTIONS)}\n\n"
            f"✨ <b>Правила:</b>\n"
            f"• 10 вопросов из разных категорий\n"
            f"• За каждый правильный ответ: 50$ + 10 опыта\n"
            f"• За прохождение всех вопросов: бонус 500$ + 100 опыта\n\n"
            f"💡 Проверьте свои знания!"
        )
        
        await callback.message.edit_text(quiz_text, reply_markup=get_quiz_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_game_quiz: {e}")
        await callback.answer("❌ Ошибка в игре!")

# Обработчики ставок
@dp.callback_query(F.data.startswith("bet_"))
async def handle_bet(callback: CallbackQuery):
    """Обработка ставок"""
    try:
        data = callback.data
        parts = data.split("_")
        
        if len(parts) >= 3:
            game_type = parts[1]
            bet_amount = int(parts[2])
            
            user_id = callback.from_user.id
            user = get_user(user_id)
            
            if not user:
                await callback.answer("❌ Ошибка загрузки профиля!")
                return
            
            if user['dollars'] < bet_amount:
                await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(bet_amount)}")
                return
            
            # Сохраняем ставку
            user_bet_state[user_id] = {
                'game_type': game_type,
                'bet_amount': bet_amount
            }
            
            # Играем в выбранную игру
            if game_type == "slots":
                await play_slots(callback, user_id, bet_amount)
            elif game_type == "dice":
                await play_dice(callback, user_id, bet_amount)
            elif game_type == "darts":
                await play_darts(callback, user_id, bet_amount)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_bet: {e}")
        await callback.answer("❌ Ошибка в игре!")

# ИСПРАВЛЕНИЕ: Добавляем обработчик для кнопки "Играть еще" с определенной ставкой
@dp.callback_query(F.data.startswith("game_"))
async def handle_game_play_again(callback: CallbackQuery):
    """Обработчик для кнопки 'Играть еще' с определенной ставкой"""
    try:
        data = callback.data
        parts = data.split("_")
        
        if len(parts) >= 3:
            game_type = parts[1]
            bet_amount = int(parts[2])
            
            user_id = callback.from_user.id
            user = get_user(user_id)
            
            if not user:
                await callback.answer("❌ Ошибка загрузки профиля!")
                return
            
            if user['dollars'] < bet_amount:
                await callback.answer(f"❌ Недостаточно денег! Нужно {format_money(bet_amount)}")
                return
            
            # Играем в выбранную игру
            if game_type == "slots":
                await play_slots(callback, user_id, bet_amount)
            elif game_type == "dice":
                await play_dice(callback, user_id, bet_amount)
            elif game_type == "darts":
                await play_darts(callback, user_id, bet_amount)
        elif len(parts) == 2:
            # Если только game_type без ставки, показываем выбор ставки
            game_type = parts[1]
            if game_type == "slots":
                await handle_game_slots(callback)
            elif game_type == "dice":
                await handle_game_dice(callback)
            elif game_type == "darts":
                await handle_game_darts(callback)
            elif game_type == "quiz":
                await handle_game_quiz(callback)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_game_play_again: {e}")
        await callback.answer("❌ Ошибка в игре!")

async def play_slots(callback: CallbackQuery, user_id: int, bet_amount: int):
    """Игра в слоты"""
    try:
        # Символы для слотов
        symbols = ["🍒", "🍋", "🍊", "💎", "⭐", "🔔", "7️⃣"]
        
        # Крутим слоты
        slot1 = random.choice(symbols)
        slot2 = random.choice(symbols)
        slot3 = random.choice(symbols)
        
        # Определяем выигрыш
        win_multiplier = 0
        
        if slot1 == slot2 == slot3:
            if slot1 == "🍒":
                win_multiplier = 2
            elif slot1 == "🍋":
                win_multiplier = 3
            elif slot1 == "🍊":
                win_multiplier = 5
            elif slot1 == "💎":
                win_multiplier = 10
            elif slot1 == "⭐":
                win_multiplier = 20
            elif slot1 == "🔔":
                win_multiplier = 15
            elif slot1 == "7️⃣":
                win_multiplier = 50
        
        win_amount = bet_amount * win_multiplier if win_multiplier > 0 else 0
        
        # Обновляем баланс
        if win_amount > 0:
            update_user_dollars(user_id, win_amount - bet_amount)
            result = "🏆 ВЫ ВЫИГРАЛИ!"
        else:
            update_user_dollars(user_id, -bet_amount)
            result = "😢 ВЫ ПРОИГРАЛИ"
        
        # Добавляем опыт
        exp_reward = bet_amount // 10
        new_level = add_user_experience(user_id, exp_reward)
        
        user = get_user(user_id)
        
        result_text = (
            f"🎰 <b>Игра в слоты</b>\n\n"
            f"🎯 Ставка: {format_money(bet_amount)}\n\n"
            f"🎰 <b>Результат:</b>\n"
            f"[ {slot1} | {slot2} | {slot3} ]\n\n"
        )
        
        if win_multiplier > 0:
            result_text += f"✨ Комбинация: {slot1} {slot2} {slot3}\n"
            result_text += f"💰 Множитель: x{win_multiplier}\n"
            result_text += f"🏆 Выигрыш: {format_money(win_amount)}\n"
        else:
            result_text += "💔 Нет выигрышной комбинации\n"
        
        result_text += f"\n{result}\n\n"
        
        if new_level and new_level > user['level']:
            result_text += f"🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"📈 Опыт: +{exp_reward}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_play_again_keyboard("slots", bet_amount))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в play_slots: {e}")
        await callback.answer("❌ Ошибка в игре!")

async def play_dice(callback: CallbackQuery, user_id: int, bet_amount: int):
    """Игра в кости"""
    try:
        # Бросаем кости
        user_dice = random.randint(1, 6)
        bot_dice = random.randint(1, 6)
        
        # Определяем победителя
        if user_dice > bot_dice:
            win_amount = bet_amount * 2
            update_user_dollars(user_id, win_amount - bet_amount)
            result = "🏆 ВЫ ВЫИГРАЛИ!"
        elif user_dice < bot_dice:
            update_user_dollars(user_id, -bet_amount)
            result = "😢 ВЫ ПРОИГРАЛИ"
        else:
            # Ничья - возвращаем ставку
            result = "🤝 НИЧЬЯ"
        
        # Добавляем опыт
        exp_reward = bet_amount // 10
        new_level = add_user_experience(user_id, exp_reward)
        
        user = get_user(user_id)
        
        result_text = (
            f"🎲 <b>Игра в кости</b>\n\n"
            f"🎯 Ставка: {format_money(bet_amount)}\n\n"
            f"🎲 <b>Результат:</b>\n"
            f"👤 Ваш кубик: {user_dice}\n"
            f"🤖 Кубик бота: {bot_dice}\n\n"
        )
        
        if user_dice > bot_dice:
            result_text += f"🏆 Вы выиграли: {format_money(win_amount)}\n"
        elif user_dice < bot_dice:
            result_text += f"😢 Вы проиграли: {format_money(bet_amount)}\n"
        else:
            result_text += f"🤝 Ничья! Ставка возвращена\n"
        
        result_text += f"\n{result}\n\n"
        
        if new_level and new_level > user['level']:
            result_text += f"🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"📈 Опыт: +{exp_reward}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_play_again_keyboard("dice", bet_amount))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в play_dice: {e}")
        await callback.answer("❌ Ошибка в игре!")

async def play_darts(callback: CallbackQuery, user_id: int, bet_amount: int):
    """Игра в дартс"""
    try:
        # Бросаем дротик
        score = random.randint(1, 10)  # 1-10 баллов
        
        # Определяем выигрыш (чем ближе к 10, тем больше)
        if score >= 9:
            multiplier = 5
        elif score >= 7:
            multiplier = 3
        elif score >= 5:
            multiplier = 2
        elif score >= 3:
            multiplier = 1.5
        else:
            multiplier = 1
        
        win_amount = int(bet_amount * multiplier)
        
        # Обновляем баланс
        if win_amount > bet_amount:
            update_user_dollars(user_id, win_amount - bet_amount)
            result = "🏆 ВЫ ВЫИГРАЛИ!"
        else:
            update_user_dollars(user_id, -bet_amount)
            result = "😢 ВЫ ПРОИГРАЛИ"
        
        # Добавляем опыт
        exp_reward = bet_amount // 10
        new_level = add_user_experience(user_id, exp_reward)
        
        user = get_user(user_id)
        
        result_text = (
            f"🎯 <b>Игра в дартс</b>\n\n"
            f"🎯 Ставка: {format_money(bet_amount)}\n\n"
            f"🎯 <b>Результат:</b>\n"
            f"Ваш бросок: {score}/10 баллов\n"
            f"Множитель: x{multiplier}\n"
        )
        
        if win_amount > bet_amount:
            result_text += f"🏆 Выигрыш: {format_money(win_amount)}\n"
        else:
            result_text += f"😢 Проигрыш: {format_money(bet_amount - win_amount)}\n"
        
        result_text += f"\n{result}\n\n"
        
        if new_level and new_level > user['level']:
            result_text += f"🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}\n\n"
        
        result_text += (
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"📈 Опыт: +{exp_reward}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_play_again_keyboard("darts", bet_amount))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в play_darts: {e}")
        await callback.answer("❌ Ошибка в игре!")

# ========== ВИКТОРИНА ==========

@dp.callback_query(F.data == "quiz_start")
async def handle_quiz_start(callback: CallbackQuery):
    """Начать викторину"""
    try:
        user_id = callback.from_user.id
        user = get_user(user_id)
        
        if not user:
            await callback.answer("❌ Ошибка загрузки профиля!")
            return
        
        # Начинаем с первого вопроса
        question_index = 0
        
        user_quiz_state[user_id] = {
            'current_question': question_index,
            'correct_answers': 0,
            'total_reward': 0
        }
        
        question = QUIZ_QUESTIONS[question_index]
        
        quiz_text = (
            f"❓ <b>Вопрос {question_index + 1}/{len(QUIZ_QUESTIONS)}</b>\n\n"
            f"📚 Категория: {question['category']}\n\n"
            f"{question['question']}"
        )
        
        await callback.message.edit_text(quiz_text, reply_markup=get_quiz_keyboard(question_index))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_quiz_start: {e}")
        await callback.answer("❌ Ошибка в викторине!")

@dp.callback_query(F.data.startswith("quiz_answer_"))
async def handle_quiz_answer(callback: CallbackQuery):
    """Обработка ответа на вопрос викторины"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in user_quiz_state:
            await callback.answer("❌ Викторина не начата!")
            return
        
        data = callback.data
        parts = data.split("_")
        question_index = int(parts[2])
        answer_index = int(parts[3])
        
        question = QUIZ_QUESTIONS[question_index]
        is_correct = (answer_index == question['answer'])
        
        # Обновляем состояние
        if is_correct:
            user_quiz_state[user_id]['correct_answers'] += 1
            user_quiz_state[user_id]['total_reward'] += 50
            result_text = "✅ <b>Правильно!</b>"
        else:
            correct_answer = question['options'][question['answer']]
            result_text = f"❌ <b>Неправильно!</b>\n\nПравильный ответ: {correct_answer}"
        
        # Начисляем награду за правильный ответ
        if is_correct:
            update_user_dollars(user_id, 50)
            add_user_experience(user_id, 10)
        
        # Обновляем прогресс
        update_user_quiz_progress(user_id, question_index + 1)
        
        # Показываем результат
        await callback.message.edit_text(
            f"{result_text}\n\n"
            f"💰 +50$ за правильный ответ\n"
            f"📈 +10 опыта\n\n"
            f"✅ Правильных ответов: {user_quiz_state[user_id]['correct_answers']}/{question_index + 1}\n"
            f"💰 Всего выиграно: {format_money(user_quiz_state[user_id]['total_reward'])}",
            reply_markup=get_next_question_keyboard()
        )
        
        user_quiz_state[user_id]['current_question'] = question_index + 1
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_quiz_answer: {e}")
        await callback.answer("❌ Ошибка в викторине!")

@dp.callback_query(F.data == "quiz_next")
async def handle_quiz_next(callback: CallbackQuery):
    """Следующий вопрос викторины"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in user_quiz_state:
            await callback.answer("❌ Викторина не начата!")
            return
        
        next_question = user_quiz_state[user_id]['current_question']
        
        if next_question >= len(QUIZ_QUESTIONS):
            # Викторина закончена
            await handle_quiz_finish(callback)
            return
        
        question = QUIZ_QUESTIONS[next_question]
        
        quiz_text = (
            f"❓ <b>Вопрос {next_question + 1}/{len(QUIZ_QUESTIONS)}</b>\n\n"
            f"📚 Категория: {question['category']}\n\n"
            f"{question['question']}"
        )
        
        await callback.message.edit_text(quiz_text, reply_markup=get_quiz_keyboard(next_question))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_quiz_next: {e}")
        await callback.answer("❌ Ошибка в викторине!")

@dp.callback_query(F.data == "quiz_finish")
async def handle_quiz_finish(callback: CallbackQuery):
    """Завершить викторину"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in user_quiz_state:
            await callback.answer("❌ Викторина не начата!")
            return
        
        correct_answers = user_quiz_state[user_id]['correct_answers']
        total_reward = user_quiz_state[user_id]['total_reward']
        
        # Бонус за прохождение всех вопросов
        if correct_answers == len(QUIZ_QUESTIONS):
            bonus = 500
            exp_bonus = 100
            update_user_dollars(user_id, bonus)
            add_user_experience(user_id, exp_bonus)
            total_reward += bonus
            bonus_text = f"\n🎉 <b>Бонус за идеальный результат!</b>\n💰 +{bonus}$\n📈 +{exp_bonus} опыта\n"
        else:
            bonus_text = ""
        
        # Удаляем состояние викторины
        del user_quiz_state[user_id]
        
        user = get_user(user_id)
        
        result_text = (
            f"🏁 <b>Викторина завершена!</b>\n\n"
            f"✅ Правильных ответов: {correct_answers}/{len(QUIZ_QUESTIONS)}\n"
            f"💰 Всего выиграно: {format_money(total_reward)}\n"
            f"{bonus_text}\n"
            f"💵 Баланс: {format_money(user['dollars'])}\n"
            f"🏆 Уровень: {user['level']}"
        )
        
        await callback.message.edit_text(result_text, reply_markup=get_games_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_quiz_finish: {e}")
        await callback.answer("❌ Ошибка в викторине!")

@dp.callback_query(F.data == "quiz_cancel")
async def handle_quiz_cancel(callback: CallbackQuery):
    """Отмена викторины"""
    try:
        user_id = callback.from_user.id
        
        if user_id in user_quiz_state:
            del user_quiz_state[user_id]
        
        await callback.message.edit_text(
            "❌ Викторина отменена!\n\n"
            "🎮 Возвращаемся к играм...",
            reply_markup=get_games_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_quiz_cancel: {e}")
        await callback.answer("❌ Ошибка!")

# ========== АДМИН ПАНЕЛЬ ==========

@dp.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery):
    """Админ статистика"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ У вас нет доступа!")
            return
        
        # Получаем статистику из базы
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(dollars) FROM users')
        total_dollars_result = cursor.fetchone()
        total_dollars = total_dollars_result[0] if total_dollars_result and total_dollars_result[0] else 0
        
        cursor.execute('SELECT SUM(bitcoins) FROM users')
        total_bitcoins_result = cursor.fetchone()
        total_bitcoins = total_bitcoins_result[0] if total_bitcoins_result and total_bitcoins_result[0] else 0
        
        cursor.execute('SELECT COUNT(*) FROM user_businesses')
        total_businesses = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_transactions = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM user_items')
        total_items = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT full_name, dollars, level FROM users ORDER BY dollars DESC LIMIT 5')
        top_players = cursor.fetchall()
        
        conn.close()
        
        admin_stats_text = (
            f"📊 <b>Админ статистика</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"💰 Всего денег в системе: {format_money(total_dollars)}\n"
            f"₿ Всего биткоинов: {total_bitcoins:.4f} BTC\n"
            f"🏢 Всего бизнесов: {total_businesses}\n"
            f"📦 Всего предметов: {total_items}\n"
            f"💸 Всего транзакций: {total_transactions}\n"
            f"📈 Курс BTC: {bitcoin_price:,.0f}$\n\n"
        )
        
        if top_players:
            admin_stats_text += "🏆 <b>Топ-5 игроков:</b>\n"
            for i, (name, dollars, level) in enumerate(top_players, 1):
                admin_stats_text += f"{i}. {name}: {format_money(dollars)} (Ур. {level})\n"
        
        admin_stats_text += f"\n🔄 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}"
        
        await callback.message.edit_text(admin_stats_text, reply_markup=get_admin_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_stats: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast(callback: CallbackQuery):
    """Рассылка сообщений"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ У вас нет доступа!")
            return
        
        await callback.message.edit_text(
            "📢 <b>Рассылка сообщений</b>\n\n"
            "Для рассылки всем пользователям отправьте сообщение в формате:\n\n"
            "<code>рассылка ТЕКСТ_СООБЩЕНИЯ</code>\n\n"
            "Пример:\n"
            "<code>рассылка Привет всем! Новое обновление бота!</code>\n\n"
            "⚠️ <b>Внимание:</b> Рассылайте только важные сообщения!",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_broadcast: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "admin_give_money")
async def handle_admin_give_money(callback: CallbackQuery):
    """Выдать деньги"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ У вас нет доступа!")
            return
        
        await callback.message.edit_text(
            "💰 <b>Выдать деньги</b>\n\n"
            "Для выдачи денег пользователю отправьте сообщение в формате:\n\n"
            "<code>деньги USER_ID СУММА</code>\n\n"
            "Пример:\n"
            "<code>деньги 123456789 1000</code>\n\n"
            "⚠️ <b>Внимание:</b> Проверяйте ID пользователя перед выдачей!",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_give_money: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "admin_give_exp")
async def handle_admin_give_exp(callback: CallbackQuery):
    """Выдать опыт"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ У вас нет доступа!")
            return
        
        await callback.message.edit_text(
            "🎁 <b>Выдать опыт</b>\n\n"
            "Для выдачи опыта пользователю отправьте сообщение в формате:\n\n"
            "<code>опыт USER_ID КОЛИЧЕСТВО</code>\n\n"
            "Пример:\n"
            "<code>опыт 123456789 100</code>\n\n"
            "⚠️ <b>Внимание:</b> Опыт влияет на уровень игрока!",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_give_exp: {e}")
        await callback.answer("❌ Ошибка!")

@dp.callback_query(F.data == "admin_users")
async def handle_admin_users(callback: CallbackQuery):
    """Список пользователей"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in ADMIN_IDS:
            await callback.answer("❌ У вас нет доступа!")
            return
        
        # Получаем список пользователей
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, full_name, level, dollars FROM users ORDER BY dollars DESC LIMIT 20')
        users = cursor.fetchall()
        
        conn.close()
        
        if not users:
            await callback.message.edit_text(
                "📋 <b>Список пользователей</b>\n\n"
                "Пользователей пока нет!",
                reply_markup=get_admin_keyboard()
            )
            await callback.answer()
            return
        
        users_text = "📋 <b>Список пользователей</b> (Топ-20 по деньгам)\n\n"
        
        for i, (user_id, name, level, dollars) in enumerate(users, 1):
            users_text += f"{i}. {name} (ID: {user_id})\n"
            users_text += f"   Уровень: {level} | Деньги: {format_money(dollars)}\n\n"
        
        users_text += f"\n📊 Всего пользователей: {len(users)}"
        
        await callback.message.edit_text(users_text, reply_markup=get_admin_keyboard())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_users: {e}")
        await callback.answer("❌ Ошибка!")

# ИСПРАВЛЕНИЕ: Добавляем обработчики для админских команд
@dp.message(F.text.regexp(r'^рассылка\s+.+'))
async def handle_admin_broadcast_command(message: Message):
    """Обработчик команды рассылки"""
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await message.answer("❌ У вас нет доступа!")
            return
        
        # Извлекаем текст рассылки
        broadcast_text = message.text.replace('рассылка ', '', 1)
        
        if not broadcast_text or len(broadcast_text) < 5:
            await message.answer("❌ Текст рассылки слишком короткий!")
            return
        
        # Получаем всех пользователей
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        
        conn.close()
        
        total_users = len(users)
        success_count = 0
        fail_count = 0
        
        await message.answer(f"📢 Начинаю рассылку для {total_users} пользователей...")
        
        # Отправляем сообщение всем пользователям
        for user_tuple in users:
            try:
                await bot.send_message(
                    user_tuple[0],
                    f"📢 <b>Объявление от администрации:</b>\n\n{broadcast_text}"
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Небольшая задержка, чтобы не превысить лимиты
            except:
                fail_count += 1
        
        await message.answer(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Успешно отправлено: {success_count}\n"
            f"❌ Не удалось отправить: {fail_count}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_broadcast_command: {e}")
        await message.answer("❌ Ошибка при рассылке!")

@dp.message(F.text.regexp(r'^деньги\s+\d+\s+\d+'))
async def handle_admin_give_money_command(message: Message):
    """Обработчик команды выдачи денег"""
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await message.answer("❌ У вас нет доступа!")
            return
        
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Неверный формат! Используйте: <code>деньги USER_ID СУММА</code>")
            return
        
        target_user_id = int(parts[1])
        amount = int(parts[2])
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0!")
            return
        
        # Находим пользователя
        target_user = get_user(target_user_id)
        if not target_user:
            await message.answer(f"❌ Пользователь с ID {target_user_id} не найден!")
            return
        
        # Выдаем деньги
        update_user_dollars(target_user_id, amount)
        
        target_user = get_user(target_user_id)  # Обновленные данные
        
        await message.answer(
            f"✅ <b>Деньги выданы успешно!</b>\n\n"
            f"👤 Пользователь: {target_user['full_name']}\n"
            f"🎫 ID: {target_user_id}\n"
            f"💰 Выдано: {format_money(amount)}\n"
            f"💵 Новый баланс: {format_money(target_user['dollars'])}"
        )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                target_user_id,
                f"💰 <b>Администратор выдал вам деньги!</b>\n\n"
                f"💰 Сумма: +{format_money(amount)}\n"
                f"💵 Ваш баланс: {format_money(target_user['dollars'])}"
            )
        except:
            pass
        
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_give_money_command: {e}")
        await message.answer("❌ Ошибка при выдаче денег!")

@dp.message(F.text.regexp(r'^опыт\s+\d+\s+\d+'))
async def handle_admin_give_exp_command(message: Message):
    """Обработчик команды выдачи опыта"""
    try:
        user_id = message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await message.answer("❌ У вас нет доступа!")
            return
        
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("❌ Неверный формат! Используйте: <code>опыт USER_ID КОЛИЧЕСТВО</code>")
            return
        
        target_user_id = int(parts[1])
        exp_amount = int(parts[2])
        
        if exp_amount <= 0:
            await message.answer("❌ Количество опыта должно быть больше 0!")
            return
        
        # Находим пользователя
        target_user = get_user(target_user_id)
        if not target_user:
            await message.answer(f"❌ Пользователь с ID {target_user_id} не найден!")
            return
        
        # Выдаем опыт
        new_level = add_user_experience(target_user_id, exp_amount)
        
        target_user = get_user(target_user_id)  # Обновленные данные
        
        result_text = (
            f"✅ <b>Опыт выдан успешно!</b>\n\n"
            f"👤 Пользователь: {target_user['full_name']}\n"
            f"🎫 ID: {target_user_id}\n"
            f"📈 Выдано опыта: +{exp_amount}\n"
            f"🏆 Уровень: {target_user['level']}"
        )
        
        if new_level and new_level > target_user['level']:
            result_text += f"\n\n🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}"
        
        await message.answer(result_text)
        
        # Уведомляем пользователя
        try:
            level_up_text = ""
            if new_level and new_level > target_user['level']:
                level_up_text = f"\n🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b> Новый уровень: {new_level}"
            
            await bot.send_message(
                target_user_id,
                f"🎁 <b>Администратор выдал вам опыт!</b>\n\n"
                f"📈 Опыта: +{exp_amount}{level_up_text}\n"
                f"🏆 Ваш уровень: {target_user['level']}"
            )
        except:
            pass
        
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_give_exp_command: {e}")
        await message.answer("❌ Ошибка при выдаче опыта!")

# ========== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ ==========

async def periodic_tasks():
    """Периодические задачи"""
    while True:
        try:
            await asyncio.sleep(60)  # Каждую минуту
            
            # Обновляем балансы бизнесов
            update_business_balances()
            
            # Обновляем курс биткоина каждые 5 минут
            if datetime.now().minute % 5 == 0:
                await update_bitcoin_price()
                
        except Exception as e:
            logger.error(f"Ошибка в периодических задачах: {e}")
            await asyncio.sleep(60)

# ========== ЗАПУСК БОТА ==========

async def main():
    """Запуск бота"""
    logger.info("Запуск бота...")
    
    # Обновляем курс биткоина при старте
    await update_bitcoin_price()
    
    # Запускаем периодические задачи
    asyncio.create_task(periodic_tasks())
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())