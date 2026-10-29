"""Lógica de conteo de personas: por frame y únicos (Fase 1)."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


class PeopleCounter:
    """Cuenta personas visibles por frame y personas únicas a lo largo del video.

    Un ID solo se considera "único" cuando lleva al menos `min_track_frames`
    frames de vida, para no contar ruido del tracker.
    """

    def __init__(self, min_track_frames: int = 3) -> None:
        self.min_track_frames = min_track_frames
        self.track_ages: dict[int, int] = defaultdict(int)
        self.unique_ids: set[int] = set()
        self.in_frame: int = 0
        self.max_simultaneous: int = 0

    def update(self, n_boxes: int, track_ids: Iterable[int | None]) -> None:
        """Actualiza los conteos con las detecciones de un frame."""
        self.in_frame = n_boxes
        self.max_simultaneous = max(self.max_simultaneous, n_boxes)
        for tid in track_ids:
            if tid is None:
                continue
            self.track_ages[tid] += 1
            if self.track_ages[tid] >= self.min_track_frames:
                self.unique_ids.add(tid)

    @property
    def unique_count(self) -> int:
        return len(self.unique_ids)
