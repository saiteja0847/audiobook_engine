"""
Async Audio Writer
==================

Background thread for non-blocking audio file writes.
"""

import threading
import queue
from pathlib import Path
from typing import Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AsyncAudioWriter:
    """
    Asynchronous audio file writer using background thread.

    Queues write operations and processes them in background to avoid
    blocking the main generation loop on disk I/O.

    Usage:
        writer = AsyncAudioWriter()
        writer.queue_write(audio_array, "output.wav", 24000)
        # ... continue generating ...
        writer.flush()  # Wait for all writes to complete
        writer.shutdown()
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._shutdown = False
        self._thread.start()
        self._active_writes = 0
        self._lock = threading.Lock()

    def queue_write(self, audio: np.ndarray, path: Path, sample_rate: int) -> None:
        """
        Queue an audio write operation.

        Args:
            audio: Audio data as numpy array (1D)
            path: Output file path
            sample_rate: Sample rate in Hz
        """
        with self._lock:
            self._active_writes += 1
        self._queue.put((audio, path, sample_rate))

    def _worker(self):
        """Background worker thread that processes write queue."""
        import soundfile as sf

        while not self._shutdown:
            try:
                # Wait for next write job (with timeout to check shutdown)
                item = self._queue.get(timeout=0.1)
                audio, path, sample_rate = item

                try:
                    # Perform the actual write
                    sf.write(str(path), audio, sample_rate)
                    logger.debug(f"Async write completed: {path.name}")
                except Exception as e:
                    logger.error(f"Async write failed for {path}: {e}")
                finally:
                    with self._lock:
                        self._active_writes -= 1
                    self._queue.task_done()

            except queue.Empty:
                continue

    def flush(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all queued writes to complete.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if all writes completed, False if timeout
        """
        try:
            self._queue.join()
            return True
        except:
            return False

    def shutdown(self):
        """
        Shutdown the writer and wait for pending writes.

        Call this before program exit to ensure all writes complete.
        """
        self.flush()
        self._shutdown = True
        self._thread.join(timeout=5.0)

    @property
    def pending_writes(self) -> int:
        """Number of writes still in queue or being processed."""
        with self._lock:
            return self._active_writes
