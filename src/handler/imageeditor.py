from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import os


RGB = tuple[int, int, int]


def image_from_file(path: str) -> Image.Image:
    return Image.open(path).convert('RGB')


def rotate_left(img: Image.Image) -> Image.Image:
    return img.transpose(Image.ROTATE_90)


def rotate_right(img: Image.Image) -> Image.Image:
    return img.transpose(Image.ROTATE_270)


def resize_and_center(img: Image.Image, width: int, height: int, background: RGB) -> Image.Image:
    currw, currh = img.size
    if width/currw <= height/currh:
        f = width/currw
        innerw = width
        innerh = int(f*currh)
        offset = (0, (height - innerh)//2)
    else:
        f = height/currh
        innerw = int(f*currw)
        innerh = height
        offset = ((width - innerw)//2, 0)

    res = Image.new('RGB', (width, height), background)
    img = img.resize((innerw, innerh), Image.LANCZOS)
    res.paste(img, offset)

    return res


def write_label(img: Image.Image, text: str, font_path: str, preferred_font_size: float,
                right_margin: int, bottom_margin: int) -> None:
    font_path = os.path.normpath(font_path)
    width, height = img.size
    draw = ImageDraw.Draw(img, 'RGBA')
    font = ImageFont.truetype(font_path, int(preferred_font_size))
    text_w, text_h = draw.textsize(text, font)
    if text_w > width - 2 * right_margin:
        font = ImageFont.truetype(font_path, int(preferred_font_size * (width - 2 * right_margin) / text_w))
        text_w, text_h = draw.textsize(text, font)
    text_x, text_y = (width - text_w - right_margin, height - text_h - bottom_margin)
    draw.rectangle([(text_x, text_y), (text_x + text_w, text_y + text_h)], fill=(0, 0, 0, 100))
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
