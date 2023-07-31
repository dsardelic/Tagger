from typing import List, Optional

from tinydb import Query, TinyDB, where

from Tagger import params


def load_db(path):
    return TinyDB(
        path,
        sort_keys=True,
        indent=4,
        separators=(",", ": "),
        encoding="utf-8",
        ensure_ascii=False,
    )


DB = load_db(params.DB_PATH)


def get_all_favorites():
    return DB.table("favorite_paths").all()


def get_favorite(db_path_str: str):
    return DB.table("favorite_paths").get(where("path") == db_path_str)


def insert_favorite(db_path_str: str):
    return DB.table("favorite_paths").insert({"path": db_path_str})


def delete_favorite(db_path_str: str):
    DB.table("favorite_paths").remove(where("path") == db_path_str)


def get_all_tags():
    return DB.table("tags").all()


def get_tag_by_name(name: str):
    return DB.table("tags").get(where("name") == name)


def insert_tag(name: str, color: str):
    return DB.table("tags").insert({"name": name, "color": color})


def delete_tags(tag_ids: List[int]):
    mappings = DB.table("_default").search(
        Query().tag_ids.any([str(tag_id) for tag_id in tag_ids])
    )
    for mapping in mappings:
        mapping["tag_ids"] = list(
            set(mapping["tag_ids"]) - {str(tag_id) for tag_id in tag_ids}
        )
    DB.write_back(mappings)
    DB.table("tags").remove(doc_ids=tag_ids)
    remove_mappings_without_tags()


def get_tag_mappings(tag_id: int):
    return DB.table("_default").search(Query().tag_ids.all([str(tag_id)]))


def get_tag_by_id(tag_id: int):
    return DB.table("tags").get(doc_id=tag_id)


def update_tag(tag_id: int, name: str, color: str):
    tag = get_tag_by_id(tag_id)
    tag["name"] = name
    tag["color"] = color
    DB.table("tags").write_back([tag])


def get_mapping(mapping_id: int):
    return DB.get(doc_id=mapping_id)


def remove_tags_from_mappings(tag_ids: List[int], mapping_ids: List[int]):
    mappings = [get_mapping(mapping_id) for mapping_id in mapping_ids]
    for mapping in mappings:
        mapping["tag_ids"] = list(
            set(mapping["tag_ids"]) - {str(tag_id) for tag_id in tag_ids}
        )
    DB.write_back(mappings)
    remove_mappings_without_tags()


def remove_mappings_without_tags():
    DB.remove(Query().tag_ids.test(lambda x: not x))


def get_all_mappings():
    return DB.all()


def insert_mapping(db_path_str: str, tag_ids: Optional[List[int]] = None):
    if db_path_str:
        return DB.insert({"path": db_path_str, "tag_ids": tag_ids or []})
    return None


def get_mapping_by_path(db_path_str: str):
    return DB.get(where("path") == db_path_str)


def delete_mappings(mapping_ids: List[int]):
    DB.remove(doc_ids=mapping_ids)
    remove_mappings_without_tags()


def update_mapping_path(mapping_id: int, db_path_str: str):
    DB.update({"path": db_path_str}, doc_ids=[mapping_id])


def get_filtered_mappings(
    tag_ids_to_include: List[int],
    tag_ids_to_exclude: List[int],
    db_path_str_like: Optional[str] = None,
):
    tag_str_ids_to_include = [str(tag_id) for tag_id in tag_ids_to_include]
    tag_str_ids_to_exclude = [str(tag_id) for tag_id in tag_ids_to_exclude]
    if db_path_str_like:
        return DB.table("_default").search(
            (Query().tag_ids.all(tag_str_ids_to_include))
            & (~(Query().tag_ids.any(tag_str_ids_to_exclude)))
            & (
                Query().path.test(
                    lambda x: x.lower().find(db_path_str_like.lower()) > -1
                )
            )
        )
    return DB.table("_default").search(
        (Query().tag_ids.all(tag_str_ids_to_include))
        & (~(Query().tag_ids.any(tag_str_ids_to_exclude)))
    )


def append_tags_to_mappings(tag_ids: List[int], mapping_ids: List[int]):
    mappings = [get_mapping(mapping_id) for mapping_id in mapping_ids]
    for mapping in mappings:
        mapping["tag_ids"] = list(
            set(mapping["tag_ids"]) | {str(tag_id) for tag_id in tag_ids}
        )
    DB.write_back(mappings)
