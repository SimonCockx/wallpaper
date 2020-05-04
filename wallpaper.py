import ctypes
import random
from typing import List

import pythoncom
import pywintypes
import win32gui
from win32com.shell import shell, shellcon

import os
import sched
import time

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

user32 = ctypes.windll.user32


def _make_filter(class_name: str, title: str):
    """https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumwindows"""

    def enum_windows(handle: int, h_list: list):
        if not (class_name or title):
            h_list.append(handle)
        if class_name and class_name not in win32gui.GetClassName(handle):
            return True  # continue enumeration
        if title and title not in win32gui.GetWindowText(handle):
            return True  # continue enumeration
        h_list.append(handle)

    return enum_windows


def find_window_handles(parent: int = None, window_class: str = None, title: str = None) -> List[int]:
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


def force_refresh():
    user32.UpdatePerUserSystemParameters(1)


def enable_activedesktop():
    """https://stackoverflow.com/a/16351170"""
    try:
        progman = find_window_handles(window_class='Progman')[0]
        cryptic_params = (0x52c, 0, 0, 0, 500, None)
        user32.SendMessageTimeoutW(progman, *cryptic_params)
    except IndexError as e:
        raise WindowsError('Cannot enable Active Desktop') from e


def set_wallpaper(image_path, use_activedesktop = True):
    if use_activedesktop:
        enable_activedesktop()
    pythoncom.CoInitialize()
    iad = pythoncom.CoCreateInstance(shell.CLSID_ActiveDesktop,
                                     None,
                                     pythoncom.CLSCTX_INPROC_SERVER,
                                     shell.IID_IActiveDesktop)
    iad.SetWallpaper(str(image_path), 0)
    iad.ApplyChanges(shellcon.AD_APPLY_ALL)
    force_refresh()


def get_all_files_with_ext(folder, extensions):
    return [os.path.join(path, filename)
            for path, dirs, files in os.walk(folder)
            for filename in files
            if filename.endswith(extensions)]


def format_image(path, text, path_out):
    img = Image.open(path).convert('RGB')
    img.load()
    width, height = img.size
    if width < 100 or height < 100:
        return False
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("Arial.ttf", int(16*height/400))
    text_w, text_h = draw.textsize(text, font)
    try:
        draw.text((int(0.97*(width-text_w)), int(0.95*(height-text_h))), text, fill='rgb(255, 255, 255)', font=font)
    except IndexError:
        print('Warning! Could not write text on ' + path)
    img.save(path_out)
    return True


s = sched.scheduler(time.time, time.sleep)
image_extensions = ('png', 'bpm', 'jpg', 'jpeg', 'bmp')
root_folder = os.path.abspath('.')
wait_seconds = 5
all_images = get_all_files_with_ext(root_folder, image_extensions)
last_path = None


def run(sc):
    global last_path
    while True:
        path = random.choice(all_images)
        while path == last_path or path.endswith('temp.jpg'):
            path = random.choice(all_images)
        name = os.path.relpath(path, root_folder)
        if format_image(path, name, 'temp.jpg'):
            break
    last_path = path
    print("Setting background to", name)
    set_wallpaper(os.path.abspath('temp.jpg'))
    s.enter(wait_seconds, 1, run, (sc,))


s.enter(wait_seconds, 1, run, (s,))
s.run()
