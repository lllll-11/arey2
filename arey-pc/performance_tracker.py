import time
import logging
from typing import Dict, Optional

logger = logging.getLogger("AreyTiming")

class PerformanceTracker:
    """
    Rastreador de latencia y observabilidad por etapas para Arey.
    Permite medir exactamente cuántos milisegundos toma cada paso del pipeline:
    Captura de Audio -> Whisper STT -> Enrutador Fast-Path -> Red/Cloud -> Inferencia Gemini -> Ejecución -> TTS Playback.
    """
    def __init__(self):
        self.stages: Dict[str, float] = {}
        self._start_times: Dict[str, float] = {}
        self._global_start: float = 0.0

    def start_pipeline(self):
        self.stages.clear()
        self._start_times.clear()
        self._global_start = time.perf_counter()

    def start_stage(self, stage_name: str):
        self._start_times[stage_name] = time.perf_counter()

    def end_stage(self, stage_name: str) -> float:
        start = self._start_times.get(stage_name)
        if start is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.stages[stage_name] = elapsed_ms
            return elapsed_ms
        return 0.0

    def get_total_elapsed_ms(self) -> float:
        if self._global_start > 0:
            return (time.perf_counter() - self._global_start) * 1000.0
        return 0.0

    def print_summary(self, command_text: str = ""):
        total_ms = self.get_total_elapsed_ms()
        border = "═" * 60
        logger.info(border)
        logger.info(f"⏱️ [DESGLOSE DE LATENCIA] Orden: '{command_text[:45]}'")
        logger.info("─" * 60)
        for stage, ms in self.stages.items():
            bar = "█" * max(1, int(ms / 30))
            logger.info(f"  • {stage.ljust(22)}: {ms:6.1f} ms  {bar}")
        logger.info("─" * 60)
        logger.info(f"  🚀 TIEMPO TOTAL         : {total_ms:6.1f} ms")
        logger.info(border)

perf_tracker = PerformanceTracker()
