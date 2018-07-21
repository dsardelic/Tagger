import configparser
import os

from tinydb import TinyDB, Query, where

from Tagger import settings


config = configparser.ConfigParser()
config.read(os.path.join(settings.BASE_DIR, 'Tagger.ini'))
db = TinyDB(config['DEFAULT']['db_path'])


def get_all_favorite_paths():
    return db.table('favorite_paths').all()


def get_favorite_path(path):
    return db.table('favorite_paths').get(where('path') == path)


def insert_favorite_path(path):
    return db.table('favorite_paths').insert({'path': path})


def delete_favorite_path(path):
    db.table('favorite_paths').remove(where('path') == path)


def get_all_tags():
    return db.table('tags').all()


def get_tag_by_name(name):
    return db.table('tags').get(where('name') == name)


def insert_tag(name, color):
    db.table('tags').insert({'name': name, 'color': color})


def delete_tags(tag_ids):
    if tag_ids:
        mappings = db.search(Query().tag_ids.any(list(map(str, tag_ids))))
        for mapping in mappings:
            mapping['tag_ids'] = list(
                set(mapping['tag_ids']) - set(map(str, tag_ids))
            )
        db.write_back(mappings)
        db.table('tags').remove(doc_ids=tag_ids)
        remove_mappings_without_tags()


def get_tag_mappings(tag_id):
    return db.search(Query().tag_ids.all([str(tag_id)]))


def get_tag_by_id(tag_id):
    return db.table('tags').get(doc_id=tag_id)


def update_tag(tag_id, name, color):
    if name or color:
        tag = get_tag_by_id(tag_id)
        if name:
            tag['name'] = name
        if color:
            tag['color'] = color
        db.table('tags').write_back([tag])


def get_mapping(mapping_id):
    return db.get(doc_id=mapping_id)


def remove_tags_from_mappings(tag_ids, mapping_ids):
    mappings = [get_mapping(mapping_id) for mapping_id in mapping_ids]
    for mapping in mappings:
        mapping['tag_ids'] = list(
            set(mapping['tag_ids']) - set(map(str, tag_ids))
        )
    db.write_back(mappings)
    remove_mappings_without_tags()


def remove_mappings_without_tags():
    db.remove(Query().tag_ids.test(lambda x: len(x) == 0))
