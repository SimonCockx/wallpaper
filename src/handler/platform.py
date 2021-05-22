import platform as plat
from abc import ABC, abstractmethod
import logging


class Platform(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def open_file_in_explorer(self, path: str) -> None:
        pass

    @abstractmethod
    def open_file(self, path: str) -> None:
        pass

    @abstractmethod
    def set_wallpaper(self, path: str) -> None:
        pass


platform: Platform


pname = plat.system()
logging.info(f'Detected platform: {pname}')
if pname == 'Windows':
    import os
    import subprocess
    import ctypes
    import pythoncom
    import pywintypes
    import win32gui
    from win32com.shell import shell, shellcon
    from typing import Callable

    FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')

    user32 = ctypes.windll.user32

    def _make_filter(class_name: str, title: str) -> Callable[[int, list[int]], bool]:
        """https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumwindows"""

        def enum_windows(handle: int, h_list: list[int]) -> bool:
            if not (class_name or title):
                h_list.append(handle)
            if class_name and class_name not in win32gui.GetClassName(handle):
                return True  # continue enumeration
            if title and title not in win32gui.GetWindowText(handle):
                return True  # continue enumeration
            h_list.append(handle)

        return enum_windows


    def _find_window_handles(parent: int = None, window_class: str = None, title: str = None) -> list[int]:
        cb = _make_filter(window_class, title)
        try:
            handle_list = []
            if parent:
                win32gui.EnumChildWindows(parent, cb, handle_list)
            else:
                win32gui.EnumWindows(cb, handle_list)
            return handle_list
        except pywintypes.error:
            return []


    def _force_refresh() -> None:
        user32.UpdatePerUserSystemParameters(1)


    def _enable_activedesktop() -> None:
        """https://stackoverflow.com/a/16351170"""
        try:
            progman = _find_window_handles(window_class='Progman')[0]
            cryptic_params = (0x52c, 0, 0, 0, 500, None)
            user32.SendMessageTimeoutW(progman, *cryptic_params)
        except IndexError as e:
            raise WindowsError('Cannot enable Active Desktop') from e

    class Windows(Platform):
        name = 'Windows'

        def open_file_in_explorer(self, path: str) -> None:
            path = os.path.normpath(path)
            subprocess.run([FILEBROWSER_PATH, '/select,', path])

        def open_file(self, path: str) -> None:
            path = os.path.normpath(path)
            os.startfile(path)

        def set_wallpaper(self, image_path: str, use_activedesktop: bool = True) -> None:
            if use_activedesktop:
                _enable_activedesktop()
            pythoncom.CoInitialize()
            iad = pythoncom.CoCreateInstance(shell.CLSID_ActiveDesktop,
                                             None,
                                             pythoncom.CLSCTX_INPROC_SERVER,
                                             shell.IID_IActiveDesktop)
            iad.SetWallpaper(image_path, 0)
            iad.ApplyChanges(shellcon.AD_APPLY_ALL)
            _force_refresh()

    platform = Windows()

elif pname == 'Linux':
    import os
    import subprocess
    import pathlib
    import re

    def _is_running(process):
        # From http://www.bloggerpolis.com/2011/05/how-to-check-if-a-process-is-running-using-python/
        # and http://richarddingwall.name/2009/06/18/windows-equivalents-of-ps-and-kill-commands/
        try:  # Linux/Unix
            s = subprocess.Popen(["ps", "axw"], stdout=subprocess.PIPE)
        except subprocess.SubprocessError:  # Windows
            s = subprocess.Popen(["tasklist", "/v"], stdout=subprocess.PIPE)
        for x in s.stdout:
            if re.search(process, x):
                return True
        return False

    # Detect the desktop session in use: https://stackoverflow.com/a/21213358/3083982
    desktop_session = os.environ.get("DESKTOP_SESSION")
    if desktop_session is not None:  # easier to match if we doesn't have  to deal with caracter cases
        desktop_session = desktop_session.lower()
        if desktop_session not in ["gnome", "unity", "cinnamon", "mate", "xfce4", "lxde", "fluxbox",
                                   "blackbox", "openbox", "icewm", "jwm", "afterstep", "trinity", "kde"]:
            # Special cases #
            # Canonical sets $DESKTOP_SESSION to Lubuntu rather than LXDE if using LXDE.
            # There is no guarantee that they will not do the same with the other desktop environments.
            if "xfce" in desktop_session or desktop_session.startswith("xubuntu"):
                desktop_session = "xfce4"
            elif desktop_session.startswith("ubuntu"):
                desktop_session = "unity"
            elif desktop_session.startswith("lubuntu"):
                desktop_session = "lxde"
            elif desktop_session.startswith("kubuntu"):
                desktop_session = "kde"
            elif desktop_session.startswith("razor"):  # e.g. razorkwin
                desktop_session = "razor-qt"
            elif desktop_session.startswith("wmaker"):  # e.g. wmaker-common
                desktop_session = "windowmaker"
    elif os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_session = "kde"
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        if "deprecated" not in os.environ.get('GNOME_DESKTOP_SESSION_ID'):
            desktop_session = "gnome2"
    # From http://ubuntuforums.org/showthread.php?t=652320
    elif _is_running("xfce-mcs-manage"):
        desktop_session = "xfce4"
    elif _is_running("ksmserver"):
        desktop_session = "kde"

    logging.info(f'Detected desktop session: {desktop_session}')
    supported_desktops = ['cinnamon', 'gnome', 'unity', 'mate', 'gnome2']
    if desktop_session not in supported_desktops:
        logging.error(f"Unsupported desktop: {desktop_session}")
        raise SystemExit()

    class Linux(Platform):
        name = 'Linux'

        def open_file_in_explorer(self, path: str) -> None:
            path = os.path.dirname(os.path.normpath(path))
            subprocess.Popen(["xdg-open", path])

        def open_file(self, path: str) -> None:
            path = os.path.normpath(path)
            subprocess.run(['xdg-open', path])

        def set_wallpaper(self, image_path: str) -> None:
            p = pathlib.Path(image_path).as_uri()
            # partially taken from https://stackoverflow.com/a/21213504/3083982
            if desktop_session == 'cinnamon':
                subprocess.run(['gsettings', 'set', 'org.cinnamon.desktop.background', 'picture-uri', p], check=True)
            elif desktop_session in ['gnome', 'unity']:
                subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', p], check=True)
            elif desktop_session == 'mate':
                subprocess.run(["gsettings", "set", "org.mate.background", "picture-filename", p], check=True)
            elif desktop_session == 'gnome2':
                subprocess.run(["gconftool-2", "-t", "string", "--set", "/desktop/gnome/background/picture_filename",
                                "picture-filename", p], check=True)

    platform = Linux()

else:
    logging.error(f"Unsupported platform: {pname}")
    raise SystemExit()
