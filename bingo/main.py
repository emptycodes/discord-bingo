import random
from datetime import datetime
from copy import copy
from collections import defaultdict

from typing import List
from discord import User

from bingo.helpers import render


class TemplateNotFoundError(Exception):
    pass


class FieldTitlesFileNotFoundError(Exception):
    pass


class UserIsExactlyPlayerError(Exception):
    pass


class Field:
    def render(self):
        title = "TOP SECRET" if self.is_secret else self.title
        return render.render_field(title)

    def __init__(self, session, title: str, secret: bool = False):
        self.session = session
        self.title = title
        self.is_secret = secret

        self.marked = False
        self.is_sent = False
        self.players = set()

        self.rendered_field = self.render()

    def mark(self):
        if self.marked:
            return

        if self.is_secret:
            self.rendered_field = render.render_field(self.title)

        self.rendered_field = render.mark_field(self.rendered_field)
        self.session.marked_fields.append(self)

        for player in self.players:
            player.mark(self)

        self.marked = True

    def __iter__(self):
        return self.title


class FieldGroup:
    def __init__(self, fields: list[Field]) -> None:
        self.fields = fields


class Player:
    def render(self):
        self.rendered_board = render.render_template(self.session.template_name,
                                                     self.board)
        return self.rendered_board

    def __init__(self, session, user):
        self.session: Session = session
        self.user: User = user

        self.username: str = copy(self.user.display_name)

        self.bingo = {
            "rows": [0, 0, 1, 0, 0],
            "cols": [0, 0, 1, 0, 0],
            "diagonal": [1, 1],
        }
        self.board = session.generate_board(self)
        self.rendered_board = self.render()

        self.won = False
        self.victory_timestamp = None
        self.victory_place = None

    def mark(self, field: Field):
        if field not in self.board or \
           self.won:
            return

        index = self.board.index(field)
        if index >= 12:
            index += 1

        row = index // 5
        col = index - (row * 5)

        self.bingo["rows"][row] += 1
        self.bingo["cols"][col] += 1

        if row == col:
            self.bingo["diagonal"][0] += 1
        elif row + col == 4:
            self.bingo["diagonal"][1] += 1

    def check(self, looser: bool = False):
        self.won = 5 in self.bingo["rows"] or \
                   5 in self.bingo["cols"] or \
                   5 in self.bingo["diagonal"]

        if self.won and not looser:
            self.victory_timestamp = datetime.now()

            self.session.winners.append(self)
            self.victory_place = self.session.winners.index(self) + 1

        return self.won


class Session:
    def __init__(self, template_name: str, fields: List[dict], tiles_set_id: int):
        self.template_name = template_name
        self.fields: List[dict[str, str, str]] = fields
        self.tiles_set_id = tiles_set_id

        self.fields = self.__get_fields()
        self.marked_fields = []

        self.players: dict[User, Player] = {}
        self.winners: List[User] = []

        if not render.check_template_file(self.template_name):
            raise TemplateNotFoundError("Template not found")

    def __get_fields(self) -> List[Field | FieldGroup]:
        fields: List[Field | FieldGroup] = []

        grouped_fields: dict[int] = defaultdict(list[str])
        for field in fields:
            if field['grouped_by'] != None:
                fields.append(Field(
                    self, field['title'], field['secret']
                ))
            else:
                grouped_fields[field['grouped_by']].append(
                    Field(self, field['title'], field['secret'])
                )

        for grouped_field in grouped_fields.items():
            fields.append(FieldGroup(grouped_field))

        return fields

    def generate_board(self, player: Player):
        selected_fields = random.sample(self.fields, 24)
        for selected_field in selected_fields:
            if selected_field is FieldGroup:
                selected_field = random.sample(selected_field.fields, 1)

            selected_field.players.add(player)

        return selected_fields

    def add_player(self, discord_user: User):
        if discord_user in self.players:
            raise UserIsExactlyPlayerError("Discord user is a player exactly")

        self.players[discord_user] = Player(self, discord_user)
        for marked_field in self.marked_fields:
            self.players[discord_user].mark(marked_field)

        return self.players[discord_user]
