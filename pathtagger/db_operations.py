import configparser
import os
from pathlib import Path

from tinydb import TinyDB, Query

from Tagger import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))
db = TinyDB(config['DEFAULT']['db_path'])


def get_favorite_paths():
    favorite_paths = db.table('favorite_paths').all()
    for favorite_path in favorite_paths:
        path = Path(favorite_path['path'])
        favorite_path['exists'] = True if path.exists() else False
        favorite_path['is_folder'] = True if path.is_dir() else False
    return favorite_paths
