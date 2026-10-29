"""Lógica de conteo de personas: por frame, únicos y cruce de línea IN/OUT."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

Point = tuple[float, float]

DIRECTION_IN = "IN"
DIRECTION_OUT = "OUT"


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


@dataclass(frozen=True)
class CrossingEvent:
    track_id: int
    direction: str  # DIRECTION_IN o DIRECTION_OUT
    frame_idx: int


class LineCounter:
    """Cuenta entradas/salidas cuando el centroide de un track cruza un segmento.

    - El lado se calcula con el signo del producto cruz respecto a p1→p2.
    - Pasar de lado negativo a positivo es IN; al revés, OUT (`invert` lo invierte).
    - Solo cuenta si el cruce ocurre dentro del segmento, no en su prolongación.
    - Cada ID cuenta como máximo una vez por dirección. Con `once_per_id=True`
      cuenta una sola vez en total (el primer cruce): elimina los rebotes de
      quien sale y se queda parado en la puerta, a costa de no contar a quien
      entra y sale con el mismo ID.
    - Se ignoran los tracks con menos de `min_track_frames` frames de vida.
    - `band` (píxeles) crea una zona muerta a cada lado de la línea: hay que
      salir de la banda por el otro lado para que cuente. Evita contar doble a
      quien se queda parado sobre la línea.
    """

    def __init__(
        self,
        p1: Point,
        p2: Point,
        min_track_frames: int = 3,
        invert: bool = False,
        band: float = 0.0,
        once_per_id: bool = False,
    ) -> None:
        if p1 == p2:
            raise ValueError("La línea necesita dos puntos distintos")
        if band < 0:
            raise ValueError("band no puede ser negativa")
        self.p1 = p1
        self.p2 = p2
        self.min_track_frames = min_track_frames
        self.invert = invert
        self.band = band
        self.once_per_id = once_per_id
        self._length = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        self.last_side: dict[int, int] = {}
        self.track_ages: dict[int, int] = defaultdict(int)
        self.counted_in: set[int] = set()
        self.counted_out: set[int] = set()
        self.events: list[CrossingEvent] = []

    def signed_distance(self, point: Point) -> float:
        """Distancia con signo (píxeles) del punto a la recta p1→p2."""
        (x1, y1), (x2, y2), (cx, cy) = self.p1, self.p2, point
        cross = (x2 - x1) * (cy - y1) - (y2 - y1) * (cx - x1)
        return cross / self._length

    def side(self, point: Point) -> int:
        """-1 o +1 según el lado de la línea; 0 si está sobre ella o dentro de la banda."""
        d = self.signed_distance(point)
        if abs(d) <= self.band:
            return 0
        return (d > 0) - (d < 0)

    def within_segment(self, point: Point) -> bool:
        """True si la proyección del punto cae entre p1 y p2."""
        (x1, y1), (x2, y2), (cx, cy) = self.p1, self.p2, point
        dx, dy = x2 - x1, y2 - y1
        t = ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)
        return 0.0 <= t <= 1.0

    def update(
        self,
        track_ids: Sequence[int | None],
        centroids: Sequence[Point],
        frame_idx: int = 0,
    ) -> list[CrossingEvent]:
        """Procesa un frame y devuelve los cruces nuevos detectados en él."""
        new_events: list[CrossingEvent] = []
        for tid, centroid in zip(track_ids, centroids):
            if tid is None:
                continue
            self.track_ages[tid] += 1
            current = self.side(centroid)
            if current == 0:
                continue  # sobre la línea: se espera a que termine de cruzar
            previous = self.last_side.get(tid)
            self.last_side[tid] = current
            if previous is None or previous == current:
                continue
            if self.track_ages[tid] < self.min_track_frames:
                continue
            if not self.within_segment(centroid):
                continue
            event = self._register(tid, previous, current, frame_idx)
            if event is not None:
                new_events.append(event)
        return new_events

    def _register(self, tid: int, previous: int, current: int, frame_idx: int) -> CrossingEvent | None:
        is_in = previous < current
        if self.invert:
            is_in = not is_in
        direction = DIRECTION_IN if is_in else DIRECTION_OUT
        counted = self.counted_in if is_in else self.counted_out
        if tid in counted:
            return None
        if self.once_per_id and (tid in self.counted_in or tid in self.counted_out):
            return None
        counted.add(tid)
        event = CrossingEvent(tid, direction, frame_idx)
        self.events.append(event)
        return event

    @property
    def in_count(self) -> int:
        return len(self.counted_in)

    @property
    def out_count(self) -> int:
        return len(self.counted_out)


def parse_line(text: str) -> tuple[Point, Point]:
    """Convierte 'x1,y1,x2,y2' en dos puntos."""
    parts = [float(v) for v in text.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise ValueError(f"--line debe tener 4 números 'x1,y1,x2,y2', recibido: {text!r}")
    return (parts[0], parts[1]), (parts[2], parts[3])
