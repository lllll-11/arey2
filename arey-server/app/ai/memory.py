import os
import aiosqlite
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("AreyMemory")

class MemoryManager:
    def __init__(self, db_path: str = settings.DATABASE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Historial de conversación continuo y compartido
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    device_source TEXT NOT NULL,
                    tool_calls_json TEXT,
                    tool_results_json TEXT
                )
            """)

            # 2. Base de Conocimiento a Largo Plazo (Hechos, Preferencias, Hábitos aprendidos)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS facts_knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_topic TEXT NOT NULL,
                    fact_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 3. Rutinas y Macros aprendidos por voz ("Cuando diga X, haz Y")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    routine_name TEXT NOT NULL,
                    trigger_phrase TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # 4. Contactos sincronizados desde el teléfono
            await db.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 5. Recordatorios y Alarmas Programadas
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_time TEXT NOT NULL,
                    message TEXT NOT NULL,
                    target_device TEXT DEFAULT 'all',
                    completed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            await db.commit()
            logger.info("Base de datos de memoria unificada inicializada con éxito.")

    # ==================== HISTORIAL DE CONVERSACIÓN ====================

    async def add_message(
        self,
        role: str,
        content: str,
        device_source: str = "unknown",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO conversation_history 
                (timestamp, role, content, device_source, tool_calls_json, tool_results_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    role,
                    content,
                    device_source,
                    json.dumps(tool_calls) if tool_calls else None,
                    json.dumps(tool_results) if tool_results else None
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM (
                    SELECT * FROM conversation_history 
                    ORDER BY id DESC LIMIT ?
                ) ORDER BY id ASC
                """,
                (limit,)
            )
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "role": row["role"],
                    "content": row["content"],
                    "device_source": row["device_source"],
                    "tool_calls": json.loads(row["tool_calls_json"]) if row["tool_calls_json"] else None,
                    "tool_results": json.loads(row["tool_results_json"]) if row["tool_results_json"] else None
                })
            return messages

    # ==================== MEMORIA A LARGO PLAZO / HECHOS ====================

    async def save_fact(self, category: str, key_topic: str, fact_text: str) -> bool:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # Comprobar si ya existe para este key_topic
            cursor = await db.execute(
                "SELECT id FROM facts_knowledge_base WHERE key_topic = ? COLLATE NOCASE",
                (key_topic,)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    """
                    UPDATE facts_knowledge_base 
                    SET category = ?, fact_text = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (category, fact_text, now, row[0])
                )
            else:
                await db.execute(
                    """
                    INSERT INTO facts_knowledge_base (category, key_topic, fact_text, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (category, key_topic, fact_text, now, now)
                )
            await db.commit()
            return True

    async def get_all_facts(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM facts_knowledge_base ORDER BY category, key_topic")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== RUTINAS DINÁMICAS (VOICE MACROS) ====================

    async def save_routine(self, routine_name: str, trigger_phrase: str, actions: List[Dict[str, Any]]) -> bool:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM routines WHERE routine_name = ? COLLATE NOCASE OR trigger_phrase = ? COLLATE NOCASE",
                (routine_name, trigger_phrase)
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    """
                    UPDATE routines 
                    SET trigger_phrase = ?, actions_json = ?, enabled = 1
                    WHERE id = ?
                    """,
                    (trigger_phrase, json.dumps(actions), row[0])
                )
            else:
                await db.execute(
                    """
                    INSERT INTO routines (routine_name, trigger_phrase, actions_json, enabled, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (routine_name, trigger_phrase, json.dumps(actions), now)
                )
            await db.commit()
            return True

    async def get_all_routines(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM routines WHERE enabled = 1")
            rows = await cursor.fetchall()
            routines = []
            for row in rows:
                routines.append({
                    "id": row["id"],
                    "routine_name": row["routine_name"],
                    "trigger_phrase": row["trigger_phrase"],
                    "actions": json.loads(row["actions_json"]),
                    "created_at": row["created_at"]
                })
            return routines

    # ==================== CONTACTOS ====================

    async def sync_contacts(self, contacts: List[Dict[str, str]]) -> int:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # Limpiar y reinsertar
            await db.execute("DELETE FROM contacts")
            for c in contacts:
                name = c.get("name", "").strip()
                phone = c.get("phone", "").strip()
                if name and phone:
                    await db.execute(
                        "INSERT INTO contacts (name, phone_number, updated_at) VALUES (?, ?, ?)",
                        (name, phone, now)
                    )
            await db.commit()
            return len(contacts)

    async def search_contact(self, query: str) -> Optional[Dict[str, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Búsqueda exacta o parcial
            cursor = await db.execute(
                "SELECT name, phone_number FROM contacts WHERE name LIKE ? ORDER BY LENGTH(name) ASC LIMIT 1",
                (f"%{query}%",)
            )
            row = await cursor.fetchone()
            if row:
                return {"name": row["name"], "phone_number": row["phone_number"]}
            return None

    # ==================== RECORDATORIOS ====================

    async def add_reminder(self, trigger_time: str, message: str, target_device: str = "all") -> int:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO reminders (trigger_time, message, target_device, completed, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (trigger_time, message, target_device, now)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_due_reminders(self, current_time: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM reminders WHERE completed = 0 AND trigger_time <= ?",
                (current_time,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_reminder_done(self, reminder_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
            await db.commit()

memory_manager = MemoryManager()
