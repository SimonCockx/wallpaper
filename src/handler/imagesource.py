import os

from .imageeditor import image_from_file
from .platform import platform
from abc import ABC, abstractmethod

import PIL.Image as Image


EXTS = ('png', 'bmp', 'jpg', 'jpeg')


class ImageSource(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @property
    @abstractmethod
    def type_name(self) -> str:
        pass

    @abstractmethod
    def get_label(self, path: str) -> str:
        pass

    @abstractmethod
    def scan(self) -> list[str]:
        pass

    @abstractmethod
    def read_image(self, path: str) -> Image.Image:
        pass

    @abstractmethod
    def write_image(self, path: str, img: Image.Image) -> None:
        pass

    @abstractmethod
    def delete_image(self, path: str) -> None:
        pass

    @abstractmethod
    def show_source(self, path: str) -> None:
        pass

    @abstractmethod
    def __eq__(self, other):
        pass


class DirectorySource(ImageSource):
    type_name = 'directory'

    def __init__(self, name: str, root_folder: str) -> None:
        super().__init__(name)
        self.root_folder = root_folder

    def get_label(self, path: str) -> str:
        return os.path.splitext(os.path.relpath(path, self.root_folder))[0]

    def scan(self) -> list[str]:
        return [os.path.join(path, filename)
                for path, dirs, files in os.walk(self.root_folder)
                for filename in files
                if filename.lower().endswith(EXTS)]

    def read_image(self, path: str) -> Image.Image:
        return image_from_file(path)

    def write_image(self, path: str, img: Image.Image) -> None:
        img.save(path)

    def delete_image(self, path: str) -> None:
        os.remove(path)

    def show_source(self, path: str) -> None:
        platform.open_file_in_explorer(path)

    def __eq__(self, other):
        if isinstance(other, DirectorySource):
            return self.root_folder == other.root_folder
        return False
