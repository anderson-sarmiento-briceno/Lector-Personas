"""Apertura de videos/URLs y escritura del video de salida."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    total_frames: int  # 0 si es un stream o no se conoce


def open_video(source: str, default_fps: float = 30.0) -> tuple[cv2.VideoCapture, VideoInfo]:
    """Abre un archivo, URL o índice de cámara y devuelve la captura y sus metadatos."""
    src: str | int = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente de video: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0 or fps > 240:
        fps = default_fps
    info = VideoInfo(
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        fps=float(fps),
        total_frames=max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 0),
    )
    return cap, info


def create_writer(path: Path, info: VideoInfo, fps: float | None = None) -> cv2.VideoWriter:
    """Crea el VideoWriter MP4 de salida."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps or info.fps, (info.width, info.height))
    if not writer.isOpened():
        raise RuntimeError(f"No se pudo crear el video de salida: {path}")
    return writer


def output_stem(source: str) -> str:
    """Nombre base para las salidas (archivo -> su nombre; URL/cámara -> 'stream')."""
    if source.isdigit() or "://" in source:
        return "stream"
    return Path(source).stem
