from bingo.helpers import render
from copy import copy
from PIL import ImageChops, Image

import pytest


@pytest.fixture
def field():
    return render.render_field("Test field")


def test_mark(field):
    after_mark = copy(field)
    marked_field = render.mark_field(field)

    difference = ImageChops.difference(marked_field, after_mark)
    assert difference.getdata() != \
           Image.new('RGBA', (render.FIELD_HEIGHT, render.FIELD_HEIGHT)).getdata()
