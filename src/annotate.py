"""Dibujo de cajas, IDs, línea de conteo y panel de conteo sobre el frame."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.counter import Point
from src.detector import FrameDetections

BOX_COLOR = (0, 200, 255)     # BGR
TEXT_COLOR = (255, 255, 255)
PANEL_BG = (30, 30, 30)
LINE_COLOR = (255, 80, 255)
LINE_FLASH_COLOR = (0, 230, 0)
IN_COLOR = (0, 230, 0)
OUT_COLOR = (60, 60, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX


@dataclass
class PanelValues:
    in_frame: int
    unique: int
    ins: int | None = None   # None = sin línea de conteo
    outs: int | None = None


def _scale(frame: np.ndarray) -> float:
    """Escala de texto/grosor relativa a 720p para que se vea igual en 4K."""
    return max(frame.shape[0] / 720.0, 0.6)


def centroids_of(boxes: np.ndarray) -> list[Point]:
    """Centro de cada caja xyxy."""
    return [((x1 + x2) / 2, (y1 + y2) / 2) for x1, y1, x2, y2 in boxes.tolist()]


def draw_detections(frame: np.ndarray, dets: FrameDetections, show_centroids: bool = False) -> None:
    s = _scale(frame)
    thickness = max(int(2 * s), 1)
    for (x1, y1, x2, y2), tid in zip(dets.boxes.astype(int), dets.track_ids):
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, thickness)
        label = f"ID {tid}" if tid is not None else "persona"
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.6 * s, thickness)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), BOX_COLOR, -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 5), FONT, 0.6 * s, (0, 0, 0), thickness)
        if show_centroids:
            cv2.circle(frame, ((x1 + x2) // 2, (y1 + y2) // 2), max(int(5 * s), 2), BOX_COLOR, -1)


def draw_band(frame: np.ndarray, p1: Point, p2: Point, band: float) -> None:
    """Dos líneas finas paralelas a ±band que delimitan la zona muerta."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = (dx * dx + dy * dy) ** 0.5
    nx, ny = -dy / length * band, dx / length * band  # normal unitaria * band
    for sign in (1, -1):
        a = (int(p1[0] + sign * nx), int(p1[1] + sign * ny))
        b = (int(p2[0] + sign * nx), int(p2[1] + sign * ny))
        cv2.line(frame, a, b, LINE_COLOR, 1, cv2.LINE_AA)


def draw_line(frame: np.ndarray, p1: Point, p2: Point, band: float = 0.0, flash: bool = False) -> None:
    """Línea de conteo. `flash` la pinta de verde (alguien acaba de cruzar)."""
    s = _scale(frame)
    if band > 0:
        draw_band(frame, p1, p2, band)
    a = (int(p1[0]), int(p1[1]))
    b = (int(p2[0]), int(p2[1]))
    cv2.line(frame, a, b, LINE_FLASH_COLOR if flash else LINE_COLOR, max(int(4 * s), 2))
    for p in (a, b):
        cv2.circle(frame, p, max(int(7 * s), 3), LINE_COLOR, -1)


def draw_panel(frame: np.ndarray, values: PanelValues) -> None:
    """Panel superior izquierdo. OpenCV no dibuja tildes, por eso 'UNICOS'."""
    s = _scale(frame)
    thickness = max(int(2 * s), 1)
    lines: list[tuple[str, tuple[int, int, int]]] = [
        (f"EN PANTALLA: {values.in_frame}", TEXT_COLOR),
        (f"UNICOS: {values.unique}", TEXT_COLOR),
    ]
    if values.ins is not None:
        lines.append((f"ENTRADAS: {values.ins}", IN_COLOR))
        lines.append((f"SALIDAS: {values.outs}", OUT_COLOR))
    line_h = int(36 * s)
    width = int(300 * s)
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + width, 20 + line_h * len(lines)), PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)
    for i, (text, color) in enumerate(lines):
        y = 10 + line_h * (i + 1)
        cv2.putText(frame, text, (22, y), FONT, 0.9 * s, color, thickness)


def annotate_frame(
    frame: np.ndarray,
    dets: FrameDetections,
    values: PanelValues,
    line: tuple[Point, Point] | None = None,
    band: float = 0.0,
    flash: bool = False,
) -> np.ndarray:
    if line is not None:
        draw_line(frame, *line, band=band, flash=flash)
    draw_detections(frame, dets, show_centroids=line is not None)
    draw_panel(frame, values)
    return frame
