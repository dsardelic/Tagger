import configparser
import os

from . import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))

if 'DB_PATH' in config['DEFAULT']:
    DB_PATH = config['DEFAULT']['DB_PATH']
else:
    DB_PATH = os.path.join(settings.BASE_DIR, 'TaggerDB.json')
print("Using database " + DB_PATH + "\n")

DEFAULT_TAG_COLOR = config['DEFAULT']['DEFAULT_TAG_COLOR']
