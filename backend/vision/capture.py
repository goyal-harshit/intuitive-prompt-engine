"""Frame acquisition. `FrameSource` abstracts the camera so tests can inject
recorded frames and a future browser-stream source can replace OpenCV."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

import numpy as np

from backend.core.config import CameraConfig


class FrameSource(ABC):
    @abstractmethod
    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        """Yield (timestamp_s, BGR frame)."""

    @abstractmethod
    def close(self) -> None: ...


class OpenCVCamera(FrameSource):
    def __init__(self, cfg: CameraConfig, retries: int = 5, retry_delay: float = 0.6) -> None:
        import sys
        import time

        import cv2

        self._cv2 = cv2
        # DirectShow opens/releases the webcam more reliably on Windows.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        # A camera handle can briefly linger after a previous, ungraceful exit,
        # so retry a few times before declaring it unavailable.
        self._cap = None
        for attempt in range(retries):
            cap = cv2.VideoCapture(cfg.index, backend)
            if cap.isOpened():
                self._cap = cap
                break
            cap.release()
            if attempt < retries - 1:
                time.sleep(retry_delay)
        if self._cap is None:
            raise RuntimeError(
                f"Camera {cfg.index} unavailable — it may be in use by another app "
                f"(Zoom, Teams, Camera) or blocked by Windows camera privacy settings")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
        self._cap.set(cv2.CAP_PROP_FPS, cfg.fps)

    def frames(self) -> Iterator[tuple[float, np.ndarray]]:
        import time

        assert self._cap is not None  # __init__ raises if the camera never opened
        while self._cap.isOpened():
            ok, frame = self._cap.read()
            if not ok:
                break
            yield time.monotonic(), self._cv2.flip(frame, 1)  # mirror for natural UX

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
