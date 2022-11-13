from bingo.main import Field, Player, Session

import pytest


def get_fields(fields_name):
    with open(f"tests/test_bingo/{fields_name}", "r") as f:
        fields = f.read().splitlines()
        return fields


@pytest.mark.parametrize(
    "fields", ["fields.txt"]
)
def test_get_session(fields):
    fields_lines = get_fields(fields)
    Session("template.png", fields_lines)


@pytest.fixture
def session():
    return Session("template.png", get_fields("fields.txt"))


def test_add_player(session):
    session.add_player("player")


def test_mark_field(session):
    session.add_player("player")

    for field in session.fields:
        field.mark()
        assert field.marked

    assert session.players["player"].bingo == {
            "rows": [5, 5, 5, 5, 5],
            "cols": [5, 5, 5, 5, 5],
            "diagonal": [5, 5],
        }

    assert session.players["player"].check()
