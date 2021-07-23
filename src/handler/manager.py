import logging
import os
import random
import time
from typing import Tuple, Any

import PIL.Image as Image
from .colorthief import ColorThief
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from .configmanager import ConfigManager, ConfigField, ConfigError
from .imageeditor import resize_and_center, RGB, write_label, image_from_file, rotate_left, rotate_right
from .imagesource import ImageSource
from .platform import platform

FileId = Tuple[ImageSource, str]


class EmptySourceError(Exception):
    def __init__(self, source: ImageSource, tries: int):
        super().__init__(f'Tried to read {tries} times from image source "{source.name}": no images found')


class WallpaperObserver:
    def on_config_change(self, field: ConfigField, value: Any) -> None:
        pass

    def on_wallpaper_change(self, file_id: FileId) -> None:
        pass


class WallpaperManager(PatternMatchingEventHandler):
    MAX_SCAN_TRIES = 3
    SCAN_FAIL_WAIT_SECONDS = 1.0
    TEMP_SOURCE_NAME = 'source.jpg'
    TEMP_WALLPAPER_NAME = 'wallpaper.jpg'
    MIN_SIZE = 100

    def __init__(self, config_path: str, temp_dir: str, font_path: str) -> None:
        super().__init__(patterns=[config_path])
        self._config_path = config_path
        self._temp_dir = temp_dir
        self._font_path = font_path
        self._current_index = -1
        self._history: list[FileId] = []
        self._config = ConfigManager()
        self._scanned_files: list[FileId] = []
        self._observers: list[WallpaperObserver] = []

    @property
    def current_source(self) -> ImageSource:
        return self._history[self._current_index][0]

    @property
    def current_path(self) -> str:
        return self._history[self._current_index][1]

    def subscribe(self, observer: WallpaperObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: WallpaperObserver) -> None:
        self._observers.remove(observer)

    def next(self) -> None:
        last_id = self._history[-1] if len(self._history) > 0 else None
        self._current_index += 1
        while self._current_index >= len(self._history):
            file_id = random.choice(self._scanned_files)
            if len(self._scanned_files) > 1:
                while file_id == last_id or file_id[1].endswith(self.TEMP_WALLPAPER_NAME):
                    file_id = random.choice(self._scanned_files)
            self._history.append(file_id)
        file_id = self._history[self._current_index]
        source_img = file_id[0].read_image(file_id[1])
        width, height = source_img.size
        while width < self.MIN_SIZE or height < self.MIN_SIZE:
            file_id = random.choice(self._scanned_files)
            self._history[self._current_index] = file_id
            source_img = file_id[0].read_image(file_id[1])
            width, height = source_img.size
        self._set_wallpaper(file_id, source_img)

    def previous(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            file_id = self._history[self._current_index]
            source_img = file_id[0].read_image(file_id[1])
            self._set_wallpaper(file_id, source_img)

    def rotate_current_left(self) -> None:
        source, path = file_id = self._history[self._current_index]
        source_img = image_from_file(self._source_path)
        source_img = rotate_left(source_img)
        self._set_wallpaper(file_id, source_img)
        source.write_image(path, source_img)

    def rotate_current_right(self) -> None:
        source, path = file_id = self._history[self._current_index]
        source_img = image_from_file(self._source_path)
        source_img = rotate_right(source_img)
        self._set_wallpaper(file_id, source_img)
        source.write_image(path, source_img)

    def show_source_of_current(self) -> None:
        source, path = self._history[self._current_index]
        source.show_source(path)

    def open_config(self) -> None:
        platform.open_file(self._config_path)

    def delete_current(self) -> None:
        source, path = file_id = self._history[self._current_index]
        source.delete_image(path)
        self._scanned_files.remove(file_id)
        del self._history[self._current_index]
        self._current_index -= 1
        self.next()

    def get_config(self, field: ConfigField) -> Any:
        return self._config.get_value(field)

    def start(self) -> None:
        self._watch_config_file()
        self.refresh_config()
        self.next()

    def invalidate_history_and_scan_sources(self) -> None:
        self._history = []
        self._current_index = -1
        self._scanned_files = []
        for s in self._config.get_value(ConfigField.SOURCES):
            scan = s.scan()
            failed = 0
            logging.info("Scanning %s for images...", s.name)
            while len(scan) == 0:
                logging.info(f'Scanned {s.name}, but found no images. Retrying.')
                failed += 1
                if failed >= self.MAX_SCAN_TRIES:
                    raise EmptySourceError(s, failed)
                time.sleep(self.SCAN_FAIL_WAIT_SECONDS)
                scan = s.scan()
            logging.info("Found %d images", len(scan))
            for path in scan:
                self._scanned_files.append((s, path))

    def refresh_config(self) -> None:
        logging.info("Reading config")
        changed = self._config.read(self._config_path)
        if len(self._config.get_value(ConfigField.SOURCES)) == 0:
            raise ConfigError('Invalid configuration: no image sources provided')
        if ConfigField.SOURCES in changed:
            self.invalidate_history_and_scan_sources()
            self.next()
        for observer in self._observers:
            for change in changed:
                observer.on_config_change(change, self._config.get_value(change))

    def _set_wallpaper(self, file_id: FileId, source_img: Image.Image) -> None:
        logging.info("Setting background to %s", file_id[1])
        self._create_wallpaper(file_id, source_img)
        platform.set_wallpaper(self._wallpaper_path)
        for observer in self._observers:
            observer.on_wallpaper_change(file_id)

    def _create_wallpaper(self, file_id: FileId, source_img: Image.Image) -> None:
        source, path = file_id
        source_img.save(self._source_path)
        background = self._find_matching_background(source_img)
        wallpaper = resize_and_center(source_img, self._config.get_value(ConfigField.HOR_RESOLUTION),
                                      self._config.get_value(ConfigField.VER_RESOLUTION), background)
        lbl = source.get_label(path)
        write_label(wallpaper, lbl, self._font_path,
                    self._config.get_value(ConfigField.LABEL_SIZE),
                    self._config.get_value(ConfigField.RIGHT_LABEL_MARGIN),
                    self._config.get_value(ConfigField.BOTTOM_LABEL_MARGIN))
        wallpaper.save(self._wallpaper_path)

    @property
    def _wallpaper_path(self) -> str:
        return os.path.join(self._temp_dir, self.TEMP_WALLPAPER_NAME)

    @property
    def _source_path(self) -> str:
        return os.path.join(self._temp_dir, self.TEMP_SOURCE_NAME)

    def _find_matching_background(self, img: Image.Image) -> RGB:
        w, h = img.size
        f = w*h/200/200
        if f > 1:
            img = img.resize((int(w/f), int(h/f)), Image.NEAREST)
        thief = ColorThief(img)
        return thief.get_color()

    def _watch_config_file(self):
        observer = Observer()
        observer.schedule(self, os.path.dirname(self._config_path), recursive=False)
        observer.daemon = False
        observer.start()

    def on_modified(self, event):
        self.refresh_config()
