"""File watcher for automatic ingestion of new documents."""

import logging
import time
from pathlib import Path
from typing import Callable, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

logger = logging.getLogger("apex_agent.watcher")


class IngestionWatcher:
    """Watches directories for new/modified files and triggers ingestion."""

    SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".eml", ".md", ".markdown"}

    def __init__(self, watch_dirs: list, ingestion_callback: Callable[[Path], None], debounce_seconds: float = 2.0):
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.ingestion_callback = ingestion_callback
        self.debounce_seconds = debounce_seconds
        self._observer = Observer()
        self._pending: dict = {}  # path -> (event_time, scheduled)
        self._processed: Set[str] = set()

    def start(self):
        """Start watching all configured directories."""
        handler = _Handler(self._on_file_event)
        
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                self._observer.schedule(handler, str(watch_dir), recursive=True)
                logger.info("Watching directory: %s", watch_dir)
            else:
                logger.warning("Watch directory does not exist: %s", watch_dir)
        
        self._observer.start()
        logger.info("File watcher started")

    def stop(self):
        """Stop watching."""
        self._observer.stop()
        self._observer.join()
        logger.info("File watcher stopped")

    def _on_file_event(self, path: Path, event_type: str):
        """Handle file system event."""
        # Check if supported extension
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return
        
        # Skip temp/hidden files
        if path.name.startswith(".") or path.name.startswith("~"):
            return
        
        # Skip already processed (modified event debounce)
        path_str = str(path)
        if path_str in self._processed:
            return
        
        logger.info("Detected %s: %s", event_type, path.name)
        
        # Trigger ingestion
        try:
            self.ingestion_callback(path)
            self._processed.add(path_str)
            logger.info("Ingested: %s", path.name)
        except Exception as e:
            logger.error("Failed to ingest %s: %s", path, e)


class _Handler(FileSystemEventHandler):
    """Internal event handler."""

    def __init__(self, callback: Callable):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            self.callback(Path(event.src_path), "created")

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(Path(event.src_path), "modified")


def start_watcher(watch_dirs: list, ingestion_callback: Callable) -> IngestionWatcher:
    """Convenience function to create and start a watcher."""
    watcher = IngestionWatcher(watch_dirs, ingestion_callback)
    watcher.start()
    return watcher
