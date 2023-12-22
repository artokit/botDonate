import db_api
import os

DELIMITER = '-'*50

TEXTS = {
    'eng': None,
    'rus': None,
    'sp': None,
    'ch': None
}

for key in TEXTS:
    path = os.path.join(os.path.dirname(__file__), f'{key}.translate')
    TEXTS[key] = [i.strip() for i in open(path, 'rb').read().decode().split(DELIMITER)[:-1]]


async def translate_text(text: str, user_id: int) -> str:
    lang = await db_api.get_language(user_id)
    lang = lang if lang else 'eng'
    translated_text = TEXTS[lang][TEXTS['rus'].index(text)]
    return translated_text
