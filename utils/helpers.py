import re
import requests
import shutil

from typing import List


def is_pastebin_url(uri: str) -> bool:
    PASTEBIN_URL_PATTERN = r'https:\/\/pastebin.com\/raw\/[A-Za-z0-9]+'
    return bool(re.match(PASTEBIN_URL_PATTERN, uri))

def is_name_valid(name: str) -> bool:
    NAME_PATTERN = r'[A-Za-z0-9]'
    return bool(re.match(NAME_PATTERN, name))

def download_tileset(pastebin_url: str) -> List[dict]:
    r = requests.get(pastebin_url)
    r.raise_for_status()

    tiles_text = set(r.text.splitlines())
    return [{
        'secret': tile_text[0] == '$',
        'name': tile_text[1:].strip() if tile_text.startswith("$") else tile_text.strip()
    } for tile_text in tiles_text if tile_text.strip() != '']

def download_template(discord_cdn_url: str, channel_id: int, name: str) -> str:
    r = requests.get(discord_cdn_url, stream=True)
    r.raise_for_status()

    r.raw.decode_content = True

    filepath = f'{channel_id}_{name}.png'
    with open(f'templates/{filepath}', 'wb') as f:
        shutil.copyfileobj(r.raw, f)

    return filepath
