import time
from threading import Timer
from typing import Any

from ..handler.configmanager import ConfigField
from ..handler.manager import WallpaperManager, WallpaperObserver, FileId


class WallpaperTimer(WallpaperObserver):
    def __init__(self, manager: WallpaperManager) -> None:
        self.manager = manager
        self.thread = None
        self.start_time = -1
        self.cancel_time = -1
        self.is_running = False

    def _on_time(self) -> None:
        self.manager.next()

    def start(self) -> None:
        self.manager.subscribe(self)
        self.thread = Timer(self.manager.get_config(ConfigField.CHANGE_TIME), self._on_time)
        self.start_time = time.time()
        self.is_running = True
        self.thread.start()

    def restart(self) -> None:
        self.thread.cancel()
        t = self.manager.get_config(ConfigField.CHANGE_TIME)
        self.thread = Timer(t, self._on_time)
        self.start_time = time.time()
        self.is_running = True
        self.thread.start()

    def pause(self) -> None:
        if self.is_running:
            self.cancel_time = time.time()
            self.is_running = False
            self.thread.cancel()

    def resume(self) -> None:
        if not self.is_running:
            t = self.manager.get_config(ConfigField.CHANGE_TIME) - (self.cancel_time - self.start_time)
            self.thread = Timer(t, self._on_time)
            self.start_time = time.time()
            self.is_running = True
            self.thread.start()

    def _recalculate_time(self) -> None:
        if self.is_running:
            self.thread.cancel()
            current_time = time.time()
            t = self.manager.get_config(ConfigField.CHANGE_TIME) - (current_time - self.start_time)
            self.thread = Timer(t, self._on_time)
            self.is_running = True
            self.thread.start()

    def _create_thread(self, t: int) -> None:
        self.thread = Timer(t, self._on_time)
        self.thread.daemon = False

    def on_config_change(self, field: ConfigField, value: Any) -> None:
        if field == ConfigField.CHANGE_TIME:
            self._recalculate_time()

    def on_wallpaper_change(self, file_id: FileId) -> None:
        if self.is_running:
            self.restart()
