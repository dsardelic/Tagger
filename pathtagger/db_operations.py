import configparser
import os

from tinydb import TinyDB, Query

from Tagger import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))
db = TinyDB(config['DEFAULT']['db_path'])
