import asyncio
import logging
from datetime import datetime
from app.ai.memory import memory_manager
from app.devices.broker import device_broker

logger = logging.getLogger("AreyScheduler")

class Scheduler:
    def __init__(self):
        self._running = False
        self._task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Programador de recordatorios y alarmas iniciado.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                now_iso = datetime.now().isoformat()
                due = await memory_manager.get_due_reminders(now_iso)
                for reminder in due:
                    rem_id = reminder["id"]
                    msg = reminder["message"]
                    target = reminder.get("target_device", "all")
                    logger.info(f"¡Recordatorio vencido! #{rem_id}: '{msg}' para '{target}'")

                    # Emitir evento a los dispositivos
                    await device_broker.broadcast_event(
                        event_type="reminder_alert",
                        data={"id": rem_id, "message": msg, "time": reminder["trigger_time"]}
                    )
                    await memory_manager.mark_reminder_done(rem_id)
            except Exception as e:
                logger.error(f"Error en el ciclo del programador: {e}")

            await asyncio.sleep(10)  # Verificar cada 10 segundos

scheduler = Scheduler()
