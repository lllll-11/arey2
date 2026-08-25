import asyncio
import os
import sys

# Agregar ruta de la aplicación al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.memory import MemoryManager
from app.ai.learning import LearningEngine
from app.devices.state import DeviceStateManager
from app.devices.broker import DeviceBroker

async def test_unified_memory_and_facts(tmp_path):
    test_db = str(tmp_path / "test_memory.db")
    memory = MemoryManager(db_path=test_db)
    await memory.init_db()

    # 1. Test de Historial Unificado
    await memory.add_message(role="user", content="Hola Arey", device_source="pc")
    await memory.add_message(role="assistant", content="Hola, ¿en qué te ayudo?", device_source="pc")
    await memory.add_message(role="user", content="¿Cuál es el estado de mi cel?", device_source="android")

    history = await memory.get_recent_history(limit=10)
    assert len(history) == 3
    assert history[0]["content"] == "Hola Arey"
    assert history[2]["device_source"] == "android"

    # 2. Test de Base de Hechos Aprendidos
    await memory.save_fact(category="preference", key_topic="musica_favorita", fact_text="Le gusta el rock clásico")
    await memory.save_fact(category="family", key_topic="cumple_mama", fact_text="El cumpleaños de su mamá es el 15 de mayo")
    
    facts = await memory.get_all_facts()
    assert len(facts) == 2
    assert any(f["key_topic"] == "musica_favorita" for f in facts)

    # 3. Test de Contactos
    contacts = [
        {"name": "Mama", "phone": "+525512345678"},
        {"name": "Carlos Gomez", "phone": "+525598765432"}
    ]
    synced = await memory.sync_contacts(contacts)
    assert synced == 2

    c = await memory.search_contact("Carlos")
    assert c is not None
    assert c["phone_number"] == "+525598765432"

    # 4. Test de Rutinas Dinámicas
    actions = [
        {"device": "pc", "action": "set_volume", "params": {"level_percent": 80}},
        {"device": "pc", "action": "open_app", "params": {"app_name": "spotify"}}
    ]
    saved = await memory.save_routine(
        routine_name="Modo Fiesta",
        trigger_phrase="activa modo fiesta",
        actions=actions
    )
    assert saved is True

    routines = await memory.get_all_routines()
    assert len(routines) == 1
    assert routines[0]["routine_name"] == "Modo Fiesta"

def test_device_state_manager():
    state_mgr = DeviceStateManager()
    state_mgr.update_device_status("pc", online=True, extra_data={"battery": 85, "volume": 70})
    
    info = state_mgr.get_device_info("pc")
    assert info["online"] is True
    assert info["battery"] == 85
    assert info["volume"] == 70

async def main():
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    try:
        from pathlib import Path
        print("[TEST] Ejecutando pruebas de memoria, hechos aprendidos, rutinas y contactos...")
        await test_unified_memory_and_facts(Path(temp_dir))
        print("[OK] Test de memoria unificada, hechos, contactos y rutinas: PASO.")
        test_device_state_manager()
        print("[OK] Test de estado de dispositivos: PASO.")
        print("\n[EXITO] TODAS LAS PRUEBAS DE LOGICA DE AREY PASARON CON EXITO!")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(main())
