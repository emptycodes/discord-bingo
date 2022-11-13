import io
import asyncio
from PIL.Image import Image
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from bingo.main import Session, TemplateNotFoundError

import i18n


def render_to_io(render: Image):
    output = io.BytesIO()
    render.save(output, 'PNG')
    output.seek(0)

    return output


class BingoGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

        i18n.load_path.append("messages")

    @commands.command('sync')
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.sync_tree_bot',
                        default='Synced!'))

    # Custom decorator for check channel in session...
    @commands.command('start')
    @commands.has_role('Administracja')
    async def start_game(self, ctx: commands.Context, template_name: str,
                         field_titles_file_name: str):
        if ctx.channel.id in self.sessions:
            return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.game_already_exists_on_the_channel',
                                          default='Game already exists!'))

        try:
            with open("fields_files/" + field_titles_file_name, "r") as f:
                field_titles = f.read().splitlines()
        except OSError:
            return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.fields_file_not_exist',
                                          default='Fields file doesn’t exist!'))

        try:
            self.sessions[ctx.channel.id] = Session(
                template_name=template_name,
                field_titles=field_titles,
            )
        except TemplateNotFoundError:
            return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.template_file_not_exist',
                                          default='Template file doesn’t exist'))

        return await ctx.send(i18n.t(f'{str(ctx.channel.id)}.game_stared',
                                     default='Bingo game has started!'))

    @commands.command('bingo')
    async def bingo_command(self, ctx: commands.Context):
        if ctx.channel.id not in self.sessions:
            return

        session = self.sessions[ctx.channel.id]
        if ctx.author not in session.players:
            discord_user = ctx.author
            player = session.add_player(discord_user)

            file = render_to_io(
                player.render()
            )

            await discord_user.send(i18n.t(f'{str(ctx.channel.id)}.added_to_game_session_on_dm',
                                    default='Do you have a bingo on your board? '
                                            'Type the /bingo command on the game sessions channel!'),
                                    file=discord.File(file, filename="bingo.png"))

            return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.added_to_game_session_on_channel',
                                          default='Psst! A board with fields was sent to your Direct Messages!'))

        else:
            player = session.players[ctx.author]
            if player in session.winners:
                return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.player_already_won_bingo',
                                       default="You're already on the podium!"))

            bingo = player.check()
            if not bingo:
                return await ctx.reply(i18n.t(f'{str(ctx.channel.id)}.player_has_not_bingo',
                                       default="You don't have bingo on your board!"))

        file = render_to_io(
            player.render()
        )

        return await ctx.send(i18n.t(f'{str(ctx.channel.id)}.player_win_bingo',
                                     username=player.user.name, place=player.victory_place,
                                     default=f"{player.user.name} wins ${player.victory_place} place!"),
                              file=discord.File(file, filename=f"bingo.png"))

    @app_commands.command(name='mark')
    @app_commands.describe(field_name='Name of field what you want to mark')
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
                       default="Field with this name not exists!"))

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
        fields = self.sessions[ctx.channel.id].fields
        field_names = []
        for field in fields:
            if current.lower() in field.title.lower() and \
                    not field.marked:
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

        session = self.sessions[ctx.channel.id]
        winners = session.winners

        message = i18n.t(f'{str(ctx.channel.id)}.winners_announcement',
                         default=f'Winners:') + "\n"
        for winner in winners[:20]:
            message += f'{str(winner.victory_place)}. {winner.user.name} ' \
                       f'({winner.victory_timestamp.strftime("%H:%M:%S.%f")[:-2]})\n'

        del self.sessions[ctx.channel.id]
        return await ctx.send(message)


def setup(bot):
    bot.add_cog(BingoGame(bot))