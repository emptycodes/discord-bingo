from PIL import Image, ImageFont, ImageDraw, \
    UnidentifiedImageError
import re

import textwrap

TEMPLATE_DIR = "templates/"
FONT_DIR = "statics/fonts/"
DEFAULT_FONT = "Roboto-Regular.ttf"

FIELD_WIDTH, FIELD_HEIGHT = 144, 144
FIELD_TEXT_WIDTH = 12
MAXIMUM_FONT_SIZE = 25
FIELDS_LOCATION_PATTERN = [
    [[74, 138], [217, 281]],
    [[222, 138], [365, 281]],
    [[370, 138], [513, 281]],
    [[518, 138], [661, 281]],
    [[666, 138], [809, 281]],

    [[74, 286], [217, 429]],
    [[222, 286], [365, 429]],
    [[370, 286], [513, 429]],
    [[518, 286], [661, 429]],
    [[666, 286], [809, 429]],

    [[74, 434], [217, 577]],
    [[222, 434], [365, 577]],
    # [[370, 434], [513, 577]],
    [[518, 434], [661, 577]],
    [[666, 434], [809, 577]],

    [[74, 582], [217, 725]],
    [[222, 582], [365, 725]],
    [[370, 582], [513, 725]],
    [[518, 582], [661, 725]],
    [[666, 582], [809, 725]],

    [[74, 730], [217, 873]],
    [[222, 730], [365, 873]],
    [[370, 730], [513, 873]],
    [[518, 730], [661, 873]],
    [[666, 730], [809, 873]],
]


def check_template_file(name: str):
    try:
        Image.open(TEMPLATE_DIR + name).load()
    except FileNotFoundError:
        return False
    except UnidentifiedImageError:
        return False

    return True


def render_field(name: str):
    field = Image.new('RGBA', (FIELD_WIDTH, FIELD_HEIGHT))
    draw = ImageDraw.Draw(field)

    wrapped_name = textwrap.wrap(name, FIELD_TEXT_WIDTH)
    text = "\n".join(wrapped_name)

    font_object = None
    b_x, b_y = None, None

    for font_size in reversed(range(MAXIMUM_FONT_SIZE)):
        font_object = ImageFont.truetype(FONT_DIR + DEFAULT_FONT, font_size)
        _, _, b_x, b_y = draw.multiline_textbbox((0, 0), text, font=font_object)

        if b_x < FIELD_WIDTH and \
                b_y < FIELD_HEIGHT:
            break

    line_x_pos = (FIELD_WIDTH - b_x) / 2
    line_y_pos = (FIELD_HEIGHT - b_y) / 2

    draw.text((line_x_pos, line_y_pos),
              text,
              fill=(255, 255, 255),
              font=font_object,
              align='center',
              )

    return field


def mark_field(field: Image.Image):
    with Image.open(TEMPLATE_DIR + "mark.png") as mark:
        mark_x_pos = (field.width - mark.width) // 2
        mark_y_pos = (field.height - mark.height) // 2

        field.paste(mark,
                    (mark_x_pos,
                     mark_y_pos),
                    mark)

    return field


def render_template(template_name: str, players_board):
    template = Image.open(TEMPLATE_DIR + template_name)
    for n in range(24):
        template.paste(players_board[n].rendered_field,
                       (FIELDS_LOCATION_PATTERN[n][0][0],
                        FIELDS_LOCATION_PATTERN[n][0][1]),
                       players_board[n].rendered_field)

    return template
