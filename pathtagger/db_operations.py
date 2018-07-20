import configparser
import os
from pathlib import Path

from tinydb import TinyDB, Query, where

from Tagger import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))
db = TinyDB(config['DEFAULT']['db_path'])


def get_all_favorite_paths():
    favorite_paths = db.table('favorite_paths').all()
    for favorite_path in favorite_paths:
        path = Path(favorite_path['path'])
        favorite_path['exists'] = True if path.exists() else False
        favorite_path['is_folder'] = True if path.is_dir() else False
    return favorite_paths


def get_favorite_paths(path):
    return db.table('favorite_paths').search(where('path') == path)


def insert_favorite_path(path):
    return db.table('favorite_paths').insert({'path': path})


def delete_favorite_path(path):
    db.table('favorite_paths').remove(where('path') == path)


def get_all_tags():
    return db.table('tags').all()


def get_tags(name):
    return db.table('tags').search(where('name') == name)


def insert_tag(name, color):
    db.table('tags').insert({'name': name, 'color': color})


def delete_tags(tag_ids):
    if tag_ids:
        db.table('tags').remove(doc_ids=tag_ids)


def get_tag_mappings(tag_id):
    return db.search(Query().tags.all([str(tag_id)]))
