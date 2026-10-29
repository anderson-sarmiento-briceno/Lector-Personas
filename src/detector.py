"""Carga del modelo YOLO y detección + tracking de personas por frame."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from ultralytics import YOLO

PERSON_CLASS = 0  # COCO: 0 = person


@dataclass
class FrameDetections:
    boxes: np.ndarray                                   # (N, 4) xyxy en píxeles
    confidences: np.ndarray                             # (N,)
    track_ids: list[int | None] = field(default_factory=list)  # None si el tracker aún no asignó ID


class PersonDetector:
    def __init__(
        self,
        model_path: str,
        conf: float = 0.35,
        iou: float = 0.5,
        imgsz: int = 640,
        tracker: str = "bytetrack.yaml",
        device: str | None = None,
    ) -> None:
        self.model = YOLO(model_path)
        self.model_path = model_path
        self.track_kwargs = {
            "classes": [PERSON_CLASS],
            "conf": conf,
            "iou": iou,
            "imgsz": imgsz,
            "tracker": tracker,
            "persist": True,
            "verbose": False,
        }
        if device is not None:
            self.track_kwargs["device"] = device

    def track(self, frame: np.ndarray) -> FrameDetections:
        """Detecta y sigue personas en un frame (mantiene el estado del tracker entre llamadas)."""
        result = self.model.track(frame, **self.track_kwargs)[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return FrameDetections(np.empty((0, 4)), np.empty((0,)), [])

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        # boxes.id puede ser None si el tracker todavía no confirmó ningún track
        ids: list[int | None] = (
            boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(xyxy)
        )
        return FrameDetections(xyxy, confs, ids)
