import os
import aiosqlite
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AreyLocalMemory")
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
DB_PATH = os.path.join(DB_DIR, "memory.db")

class LocalMemoryManager:
    """
    Gestor de memoria compartida continua en base de datos SQLite local en la laptop.
    """
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    device_source TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS learned_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_topic TEXT NOT NULL,
                    fact_text TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key_topic)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    routine_name TEXT UNIQUE NOT NULL,
                    trigger_phrase TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("💾 Base de datos de memoria local inicializada.")

    async def add_message(self, role: str, content: str, device_source: str = "pc"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO conversation_history (role, content, device_source) VALUES (?, ?, ?)",
                (role, content, device_source)
            )
            await db.commit()

    async def get_recent_history(self, limit: int = 4) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content, device_source, timestamp FROM conversation_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    async def save_fact(self, category: str, key_topic: str, fact_text: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO learned_facts (category, key_topic, fact_text, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key_topic) DO UPDATE SET
                    fact_text = excluded.fact_text,
                    updated_at = CURRENT_TIMESTAMP
            """, (category, key_topic, fact_text))
            await db.commit()

    async def get_all_facts(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT category, key_topic, fact_text FROM learned_facts")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_routines(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT routine_name, trigger_phrase, actions_json FROM user_routines")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

local_memory = LocalMemoryManager()
