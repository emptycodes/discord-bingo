import random
from datetime import datetime

from bingo.helpers import render


class TemplateNotFoundError(Exception):
    pass


class FieldTitlesFileNotFoundError(Exception):
    pass


class UserIsExactlyPlayerError(Exception):
    pass


class Field:
    def render(self):
        return render.render_field(self.title)

    def __init__(self, session, title: str):
        self.session = session
        self.title = title

        self.marked = False
        self.is_sent = False
        self.players = set()

        self.rendered_field = self.render()

    def mark(self):
        if self.marked:
            return

        self.rendered_field = render.mark_field(self.rendered_field)

        self.session.marked_fields.append(self)

        # players = self.players.copy()
        for player in self.players:
            player.mark(self)

        self.marked = True
        # self.players = self.players.difference(players)

    def __iter__(self):
        return self.title


class Player:
    def render(self):
        self.rendered_board = render.render_template(self.session.template_name,
                                                     self.board)
        return self.rendered_board

    def __init__(self, session, user):
        self.session = session
        self.user = user

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

    def check(self):
        self.won = 5 in self.bingo["rows"] or \
                   5 in self.bingo["cols"] or \
                   5 in self.bingo["diagonal"]

        if self.won:
            self.victory_timestamp = datetime.now()

            self.session.winners.append(self)
            self.victory_place = self.session.winners.index(self) + 1

        return self.won


class Session:
    def __init__(self, template_name: str, field_titles):
        self.template_name = template_name
        self.field_titles = field_titles

        self.fields = [Field(self, field_title) for field_title in field_titles]
        self.marked_fields = []

        self.players = {}
        self.winners = []

        if not render.check_template_file(self.template_name):
            raise TemplateNotFoundError("Template not found")

    def generate_board(self, player: Player):
        selected_fields = random.sample(self.fields, 24)
        for selected_field in selected_fields:
            selected_field.players.add(player)

        return selected_fields

    def add_player(self, discord_user):
        if discord_user in self.players:
            raise UserIsExactlyPlayerError("Discord user is a player exactly")

        self.players[discord_user] = Player(self, discord_user)
        for marked_field in self.marked_fields:
            self.players[discord_user].mark(marked_field)

        return self.players[discord_user]
