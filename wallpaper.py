import ctypes
import random
import stat
from typing import List

import os
import sched
import time

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from configparser import ConfigParser

import logging

import os

import pathlib


def set_wallpaper(image_path: str) -> None:
    os.system(f'gsettings set org.cinnamon.desktop.background picture-uri {pathlib.Path(image_path).as_uri()}')
    


def get_all_files_with_ext(folder: str, extensions):
    return [os.path.join(path, filename)
            for path, dirs, files in os.walk(folder)
            for filename in files
            if filename.endswith(extensions)]


def format_image(path: str, text: str, path_out: str) -> bool:
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


image_extensions = None
root_folder = None
wait_seconds = None
text_size = None
margin_x = None
margin_y = None
last_modified = None
all_images = []


def load_config():
    global last_modified
    modification_time = time.ctime(os.stat(configFilePath)[stat.ST_MTIME])
    if last_modified != modification_time:
        last_modified = modification_time
        logging.info("Reading config")
        config = ConfigParser()
        config.read(configFilePath)
        global image_extensions, root_folder, wait_seconds, text_size, margin_x, margin_y
        last_root_folder = root_folder
        last_image_extensions = image_extensions
        image_extensions = tuple(config['config']['image_extensions'].split(','))
        root_folder = os.path.abspath(config['config']['root_folder'])
        wait_seconds = float(config['config']['seconds_per_transition'])
        text_size = float(config['config']['text_size'])
        margin_x = float(config['config']['x_margin_percentage'])
        margin_y = float(config['config']['y_margin_percentage'])
        if last_root_folder != root_folder or last_image_extensions != image_extensions:
            scan_images()


def scan_images():
    global all_images
    logging.info("Scanning for images in %s...", root_folder)
    all_images = get_all_files_with_ext(root_folder, image_extensions)
    logging.info("Found %d images", len(all_images))


def run(sc):
    try:
        load_config()
        if len(all_images) == 0:
            scan_images()
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


scriptdir = os.path.dirname(__file__)
logging.basicConfig(filename=os.path.join(scriptdir, 'wallpapers.log'), format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', level=logging.DEBUG)
logging.debug("Started")
try:
    scriptdir = os.path.dirname(__file__)
    s = sched.scheduler(time.time, time.sleep)
    configFilePath = os.path.join(scriptdir, 'config')
    load_config()
    last_path = None
    temp_background_name = 'tempbackground.jpg'
    temp_background_path = os.path.join(scriptdir, temp_background_name)
    font_path = os.path.join(scriptdir, 'Arial.ttf')
    s.enter(wait_seconds, 1, run, (s,))
    s.run()
except Exception as e:
    logging.exception(e)
    logging.info('Exiting...')
    raise SystemExit()
