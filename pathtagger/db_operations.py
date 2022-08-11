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


def get_all_favorite_paths():
    return DB.table("favorite_paths").all()


def get_favorite_path(path: str):
    return DB.table("favorite_paths").get(where("path") == path)


def insert_favorite_path(path: str):
    return DB.table("favorite_paths").insert({"path": path})


def delete_favorite_path(path: str):
    DB.table("favorite_paths").remove(where("path") == path)


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


def insert_mapping(path: str, tag_ids: Optional[List[int]] = None):
    if path:
        return DB.insert({"path": path, "tag_ids": tag_ids or []})
    return None


def get_mapping_by_path(path: str):
    return DB.get(where("path") == path)


def delete_mappings(mapping_ids: List[int]):
    DB.remove(doc_ids=mapping_ids)


def update_mapping(mapping_id: int, path: str):
    DB.update({"path": path}, doc_ids=[mapping_id])


def get_filtered_mappings(
    tag_ids_to_include: List[int],
    tag_ids_to_exclude: List[int],
    path_name_like: Optional[str] = None,
):
    tag_str_ids_to_include = [str(tag_id) for tag_id in tag_ids_to_include]
    tag_str_ids_to_exclude = [str(tag_id) for tag_id in tag_ids_to_exclude]
    if path_name_like:
        return DB.table("_default").search(
            (Query().tag_ids.all(tag_str_ids_to_include))
            & (~(Query().tag_ids.any(tag_str_ids_to_exclude)))
            & (Query().path.test(lambda x: x.lower().find(path_name_like.lower()) > -1))
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
