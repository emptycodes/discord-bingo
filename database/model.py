from typing import List
from sqlalchemy import String, BigInteger
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class TileSet(Base):
    __tablename__ = 'tile_set'

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(50))
    games_played: Mapped[int] = mapped_column(default=0)

    tiles: Mapped[List['Tile']] = relationship(
        back_populates='tile_set', cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return f'TileSet(id={self.id!r}, channel_id={self.channel_id!r} name={self.name!r})'


class Tile(Base):
    __tablename__ = 'tile'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    counter: Mapped[int] = mapped_column(default=0)
    secret: Mapped[bool] = mapped_column(default=False)

    tile_set_id: Mapped[int] = mapped_column(ForeignKey("tile_set.id"))
    tile_set: Mapped['TileSet'] = relationship(back_populates='tiles')

    def __repr__(self) -> str:
        return f'Tile(id={self.id!r}, name={self.name!r})'


class Template(Base):
    __tablename__ = 'template'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str]
    filepath: Mapped[str]

    def __repr__(self) -> str:
        return f'Template(id={self.id!r}, channel_id={self.channel_id!r} name={self.name!r}, filepath={self.filepath!r})' 


class Winner(Base):
    __tablename__ = 'winner'

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    points: Mapped[int] = mapped_column(default=0)
