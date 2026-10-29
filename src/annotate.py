"""Dibujo de cajas, IDs y panel de conteo sobre el frame."""
from __future__ import annotations

import cv2
import numpy as np

from src.detector import FrameDetections

BOX_COLOR = (0, 200, 255)     # BGR
TEXT_COLOR = (255, 255, 255)
PANEL_BG = (30, 30, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _scale(frame: np.ndarray) -> float:
    """Escala de texto/grosor relativa a 720p para que se vea igual en 4K."""
    return max(frame.shape[0] / 720.0, 0.6)


def draw_detections(frame: np.ndarray, dets: FrameDetections) -> None:
    s = _scale(frame)
    thickness = max(int(2 * s), 1)
    for (x1, y1, x2, y2), tid in zip(dets.boxes.astype(int), dets.track_ids):
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, thickness)
        label = f"ID {tid}" if tid is not None else "persona"
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.6 * s, thickness)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), BOX_COLOR, -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 5), FONT, 0.6 * s, (0, 0, 0), thickness)


def draw_panel(frame: np.ndarray, in_frame: int, unique: int) -> None:
    """Panel superior izquierdo. OpenCV no dibuja tildes, por eso 'UNICOS'."""
    s = _scale(frame)
    thickness = max(int(2 * s), 1)
    lines = [f"EN PANTALLA: {in_frame}", f"UNICOS: {unique}"]
    line_h = int(36 * s)
    width = int(300 * s)
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + width, 20 + line_h * len(lines)), PANEL_BG, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)
    for i, text in enumerate(lines):
        y = 10 + line_h * (i + 1)
        cv2.putText(frame, text, (22, y), FONT, 0.9 * s, TEXT_COLOR, thickness)


def annotate_frame(frame: np.ndarray, dets: FrameDetections, in_frame: int, unique: int) -> np.ndarray:
    draw_detections(frame, dets)
    draw_panel(frame, in_frame, unique)
    return frame
