import configparser
import os

from . import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))
DB_PATH = config['DEFAULT']['DB_PATH']
DEFAULT_TAG_COLOR = config['DEFAULT']['DEFAULT_TAG_COLOR']
