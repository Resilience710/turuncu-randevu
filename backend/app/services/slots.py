"""Randevu slot üretimi. Eski server.py:200-202'den port.

Şu an her gün için 09:00'dan başlayan 30 dakikalık 18 slot.
İleride işletme bazlı çalışma saatleri eklenebilir.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import List


def make_slots() -> List[str]:
    start = datetime(2026, 1, 1, 9, 0)
    return [(start + timedelta(minutes=30 * i)).strftime("%H:%M") for i in range(18)]


def make_slot_times() -> List[time]:
    return [time.fromisoformat(s) for s in make_slots()]
