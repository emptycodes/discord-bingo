import io
import asyncio
from PIL.Image import Image
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bingo.main import Session as BingoSession
from bingo.main import TemplateNotFoundError

from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy import func, desc, exists, and_
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import Session

from sqlalchemy_utils import database_exists, create_database

import redis
import json

from database import model
from os import environ

from utils import helpers

from PIL import Image

import i18n


def render_to_io(render: Image):
    output = io.BytesIO()
    render.save(output, 'PNG')
    output.seek(0)

    return output


class BingoGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions: dict[int, BingoSession] = {}

        self.engine = create_engine(environ.get('DB_URI'))
        self.__validate_database()

        self.redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

        i18n.load_path.append("messages")

    def __validate_database(self):
        if not database_exists(self.engine.url):
            create_database(self.engine.url)

    @commands.command('sync')
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.sync_tree_bot',
                        default='Synced!'))

    @commands.command('upload_tiles')
    @commands.has_role('Administracja')
    async def upload_tiles(self, ctx: commands.Context, name: str, pastebin_url: str):
        if not helpers.is_name_valid:
            return await ctx.reply('A name has invalid characters!')

        if not helpers.is_pastebin_url(pastebin_url):
            return await ctx.reply('Required is a URL starting with: https://pasetbin.com/raw/...')

        with Session(self.engine) as session:
            already_exists = session.query(exists().where(and_(
                model.TileSet.name == name,
                model.TileSet.channel_id == ctx.channel.id
            ))).scalar()

        if already_exists:
            return await ctx.reply(f'Name {name} is taken!')

        downloaded_tiles = helpers.download_tileset(pastebin_url)
        if len(downloaded_tiles) < 24:
            return await ctx.reply('The number of submitted tiles is less than 24!')

        with Session(self.engine) as session:
            tiles = model.TileSet(
                name=name,
                channel_id=ctx.channel.id,
                tiles=[
                    model.Tile(
                        name=tile['name'],
                        secret=tile['secret']
                    ) for tile in downloaded_tiles
                ]
            )

            session.add_all([tiles])
            session.commit()

        return await ctx.reply('Added new set of tiles!')


    @commands.command('upload_template')
    @commands.has_role('Administracja')
    async def upload_template(self, ctx: commands.Context, name: str):
        if not helpers.is_name_valid(name):
            return await ctx.reply('A name has invalid characters!')

        with Session(self.engine) as session:
            already_exists = session.query(exists().where(and_(
                model.Template.name == name,
                model.Template.channel_id == ctx.channel.id
            ))).scalar()

        if already_exists:
            return await ctx.reply(f'Name {name} is taken!')

        if len(ctx.message.attachments) < 0:
            return await ctx.reply('Send a template in attachment')

        attachment = ctx.message.attachments[0]

        if attachment.content_type != 'image/png':
            return await ctx.reply('Template must be PNG format')

        filepath = helpers.download_template(attachment.url, ctx.channel.id, name)
        with Image.open(f'templates/{filepath}') as img:
            width, height = img.size

        if not (width == 884 and height == 1036):
            return await ctx.reply('Template have not valid size (884 x 1036px)')

        with Session(self.engine) as session:
            template = model.Template(
                name=name,
                channel_id=ctx.channel.id,
                filepath=filepath
            )

            session.add_all([template])
            session.commit()

        return await ctx.reply('New template has been uploaded!')

    @commands.command('statistics')
    async def statistics(self, ctx: commands.Context):
        with Session(self.engine) as session:
            query = session.query(
                model.Winner.user_id,
                func.sum(model.Winner.points).label('total_points')
            ).filter(
                model.Winner.channel_id == ctx.channel.id
            ).group_by(
                model.Winner.user_id
            ).order_by(
                desc('total_points')
            )

            results = query.all()

        if not results:
            return await ctx.reply('Not one game has been played on this channel yet')

        message = '**Top 10** bingo players:\n'
        for user_id, total_points in results:
            member = await ctx.guild.fetch_member(user_id)
            message += f'- {member.display_name}: {total_points}\n'

        return await ctx.reply(message)

    @commands.command('test_notification')
    @commands.has_role('Administracja')
    async def test_notification(self, ctx: commands.Context):
        event = {
            'avatar': None,
            'winner': "test_notification",
            'place': 1,
        }

        self.redis_client.publish(
            ctx.channel.id,
            json.dumps(event)
        )

        return await ctx.reply('Test notification has been sent!')

    # Custom decorator for check channel in session...
    @commands.command('start')
    @commands.has_role('Administracja')
    async def start_game(self, ctx: commands.Context, template_name: str, tileset_name: str):
        if ctx.channel.id in self.sessions:
            return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.game_already_exists_on_the_channel',
                                          default='Game already exists!'))

        with Session(self.engine) as session:
            query = select(model.TileSet)\
                .where(model.TileSet.channel_id == ctx.channel.id)\
                .where(model.TileSet.name == tileset_name)\
                .limit(1)

            try:
                tiles_set = session.execute(query).one()[0]
            except (NoResultFound, MultipleResultsFound, IndexError):
                return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.fields_file_not_exist',
                                            default='Fields file doesn’t exist!'))

            field_titles = [{'name': tile.name,
                             'secret': tile.secret,
                             'grouped_by': tile.grouped_by} for tile in tiles_set.tiles]

        with Session(self.engine) as session:
            query = select(model.Template)\
                .where(model.Template.channel_id == ctx.channel.id)\
                .where(model.Template.name == template_name)\
                .limit(1)

            try:
                template = session.execute(query).one()[0]
            except (NoResultFound, MultipleResultsFound, IndexError):
                return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.template_file_not_exist',
                                                        default='Template file doesn’t exist'))

        try:
            self.sessions[ctx.channel.id] = BingoSession(
                template_name=template.filepath,
                fields=field_titles,
                tiles_set_id=tiles_set.id,
            )
        except TemplateNotFoundError:
            return await ctx.reply("Unexcepted error: Template don't exists in a filesystem")

        return await ctx.send(i18n.t(f'{str(ctx.channel.id)}.game_stared',
                                     default='Bingo game has started!'))

    @app_commands.command(name='bingo', description='Pick up a bingo board or check!')
    async def bingo(self, interaction: discord.Interaction):
        if interaction.channel.id not in self.sessions:
            return await interaction.response.send_message(
                'The game has not been started!', ephemeral=True
            )

        await interaction.response.defer()

        session = self.sessions[interaction.channel.id]
        if interaction.user not in session.players:
            discord_user = interaction.user
            player = session.add_player(discord_user)

            file = render_to_io(
                player.render()
            )

            await discord_user.send(i18n.t(f'{str(interaction.channel.id)}.added_to_game_session_on_dm',
                                    default='Do you have a bingo on your board? '
                                            'Type the /bingo command on the game sessions channel!'),
                                    file=discord.File(file, filename="bingo.png"))

            player_count = len(self.sessions[interaction.channel.id].players) - 1
            return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.added_to_game_session_on_channel',
                                                    player_count=player_count,
                                                    default=('Psst! A board with fields was sent to your Direct Messages!\n'
                                                             f'Including you, **{player_count} other players are playing!**')))

        else:
            player = session.players[interaction.user]
            if player in session.winners:
                return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.player_already_won_bingo',
                                                        default="You're already on the podium!"))

            won = player.check()
            if not won:
                return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.player_has_not_bingo',
                                                        default="You don't have bingo on your board!"))

        event = {
            'avatar': None,
            'winner': player.user.display_name,
            'place': player.victory_place,
        }

        self.redis_client.publish(
            interaction.channel.id,
            json.dumps(event)
        )

        file = render_to_io(
            player.render()
        )

        return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.player_win_bingo',
                                                        username=player.user.name, place=player.victory_place,
                                                        default=f"{player.user.name} wins ${player.victory_place} place!"),
                                                file=discord.File(file, filename=f"bingo.png"))

    @app_commands.command(name='mark', description='Mark the tile in bingo!')
    @app_commands.describe(field_name='Name of tile what you want to mark')
    @app_commands.checks.has_role("Administracja")
    async def mark(self, interaction: discord.Interaction, *, field_name: str):
        if interaction.channel.id not in self.sessions:
            return

        session = self.sessions[interaction.channel.id]

        await interaction.response.defer()

        selected_field = None
        for field in session.fields:
            if field.title == field_name:
                selected_field = field
                break

        if not selected_field:
            return await interaction.response.send_message(
                i18n.t(f'{str(interaction.channel.id)}.field_name_not_exists',
                       default="Field with this name not exists!"), ephemeral=True)

        if selected_field.is_sent:
            return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.field_is_marked',
                                                          field_title=selected_field.title,
                                                          default=f'Marked field: {selected_field.title}'))

        selected_field.mark()

        for player in selected_field.players:
            if player.won:
                continue

            file = render_to_io(
                player.render()
            )

            asyncio.get_event_loop().create_task(
                player.user.send(i18n.t(f'{str(interaction.channel.id)}.field_is_marked',
                                        field_title=selected_field.title,
                                        default=f'Marked field: {selected_field.title}'),
                                 file=discord.File(file, filename=f"bingo.png")))

        selected_field.is_sent = True

        return await interaction.followup.send(i18n.t(f'{str(interaction.channel.id)}.field_is_marked',
                                                        field_title=selected_field.title,
                                                        default=f'Marked field: {selected_field.title}'))


    @mark.autocomplete('field_name')
    async def field_name_autocomplete(
            self,
            ctx: discord.Interaction,
            current: str,
    ) -> List[app_commands.Choice[str]]:
        if not 'Administracja' in [role.name for role in ctx.user.roles]:
            return []

        fields = self.sessions[ctx.channel.id].fields
        field_names = []
        for field in fields:
            if current.lower() in field.title.lower() and not field.marked:
                field_names.append(field.title)

        field_names = field_names[:25]
        return [
            app_commands.Choice(name=field_name, value=field_name)
            for field_name in field_names if current.lower() in field_name.lower()
        ]

    @commands.command('stop')
    @commands.has_role('Administracja')
    async def stop_game(self, ctx: commands.Context):
        if ctx.channel.id not in self.sessions:
            return

        game_session = self.sessions[ctx.channel.id]
        winners = game_session.winners

        message = i18n.t(f'{str(ctx.channel.id)}.winners_announcement',
                         default=f'Winners:') + "\n"
        for winner in winners[:20]:
            message += f'{str(winner.victory_place)}. {winner.user.name} ' \
                       f'({winner.victory_timestamp.strftime("%H:%M:%S.%f")[:-2]})\n'

        await ctx.send(message)

        with Session(self.engine) as session:
            winners = [
                model.Winner(
                    channel_id=ctx.channel.id,
                    user_id=winner.user.id,
                    points=1
                ) for winner in winners
            ]
            session.add_all(winners)
            session.commit()

        with Session(self.engine) as session:
            session.query(model.TileSet).filter_by(id=game_session.tiles_set_id)\
                                        .update({model.TileSet.games_played: model.TileSet.games_played + 1})
            session.commit()

        with Session(self.engine) as session:
            marked_tiles = [field.title for field in game_session.fields if field.marked]
            session.query(model.Tile).filter_by(tile_set_id=game_session.tiles_set_id)\
                                     .filter(model.Tile.name.in_(marked_tiles))\
                                     .update({model.Tile.counter: model.Tile.counter + 1},
                                             synchronize_session=False)
            session.commit()

        message = 'Hall of Shame:\n'
        for user, player in self.sessions[ctx.channel.id].players.items():
            if not player.won and player.check(looser=True):
                message += f'- {user.display_name}\n'

        await ctx.send(message)

        del self.sessions[ctx.channel.id]


def setup(bot):
    bot.add_cog(BingoGame(bot))
