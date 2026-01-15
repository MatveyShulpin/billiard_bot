"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
from config import settings


def get_connection() -> sqlite3.Connection:
    """Получение подключения к БД"""
    conn = sqlite3.Connection(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Контекстный менеджер для работы с БД"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Инициализация базы данных"""
    # Создание директории для БД, если не существует
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Таблица столов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Таблица бронирований
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                table_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (table_id) REFERENCES tables (id)
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_time 
            ON bookings(start_time, end_time, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_user 
            ON bookings(user_id, status)
        """)
        
        # Таблица временных удержаний
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                table_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_holds_expires 
            ON holds(expires_at)
        """)
        
        # Таблица регистраций на турнир
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournament_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournament_status 
            ON tournament_registrations(status)
        """)
        
        # Проверка наличия столов
        cursor.execute("SELECT COUNT(*) as count FROM tables")
        if cursor.fetchone()['count'] == 0:
            # Добавление столов по умолчанию
            cursor.execute(
                "INSERT INTO tables (name) VALUES (?)",
                ("Леопардовый пул",)
            )
            cursor.execute(
                "INSERT INTO tables (name) VALUES (?)",
                ("Русский (Зеленый)",)
            )
        
        conn.commit()
