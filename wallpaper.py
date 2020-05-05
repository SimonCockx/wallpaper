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

from configparser import ConfigParser

import logging

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
    draw = ImageDraw.Draw(img, 'RGBA')
    font = ImageFont.truetype(font_path, int(text_size*height/400))
    text_w, text_h = draw.textsize(text, font)
    if text_w > width - 2*margin_x*width:
        font = ImageFont.truetype(font_path, int(text_size * height / 400 * (width - 2*margin_x*width)/text_w))
        text_w, text_h = draw.textsize(text, font)
    text_x, text_y = (width-text_w - width*margin_x, height-text_h - height*margin_y)
    try:
        draw.rectangle([(text_x, text_y), (text_x + text_w, text_y + text_h)], fill=(0, 0, 0, 100))
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    except IndexError:
        logging.warning('Warning! Could not write text on %s', path)
    img.save(path_out)
    return True


scriptdir = os.path.dirname(__file__)
logging.basicConfig(filename=os.path.join(scriptdir, 'wallpapers.log'), format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', level=logging.DEBUG)
logging.debug("Started")
try:
    scriptdir = os.path.dirname(__file__)
    s = sched.scheduler(time.time, time.sleep)
    config = ConfigParser()
    configFilePath = os.path.join(scriptdir, 'config')
    config.read(configFilePath)
    image_extensions = tuple(config['config']['image_extensions'].split(','))
    root_folder = os.path.abspath(config['config']['root_folder'])
    wait_seconds = float(config['config']['seconds_per_transition'])
    text_size = float(config['config']['text_size'])
    margin_x = float(config['config']['x_margin_percentage'])
    margin_y = float(config['config']['y_margin_percentage'])
    logging.debug("Scanning for images in %s...", root_folder)
    all_images = get_all_files_with_ext(root_folder, image_extensions)
    logging.debug("Found %d images", len(all_images))
    last_path = None
    temp_background_name = 'tempbackground.jpg'
    temp_background_path = os.path.join(scriptdir, temp_background_name)
    font_path = os.path.join(scriptdir, 'Arial.ttf')
except Exception as e:
    logging.exception(e)
    raise SystemExit()


def run(sc):
    try:
        global all_images
        if len(all_images) == 0:
            logging.debug("Scanning for images in %s...", root_folder)
            all_images = get_all_files_with_ext(root_folder, image_extensions)
            logging.debug("Found %d images", len(all_images))
        else:
            global last_path
            while True:
                path = random.choice(all_images)
                while path == last_path or path.endswith(temp_background_name):
                    path = random.choice(all_images)
                name = os.path.relpath(path, root_folder)
                if format_image(path, name, temp_background_path):
                    break
            last_path = path
            logging.info("Setting background to %s", name)
            set_wallpaper(os.path.abspath(temp_background_path))
    except Exception as e:
        logging.exception(e)
    s.enter(wait_seconds, 1, run, (sc,))


s.enter(wait_seconds, 1, run, (s,))
s.run()
