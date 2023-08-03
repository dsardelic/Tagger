import logging
import re
from collections import namedtuple
from typing import List, NamedTuple, Optional, Set, Union

from tinydb import Query, TinyDB, where

from Tagger import params

logger = logging.getLogger(__name__)


def load_db(path):
    return TinyDB(
        path,
        sort_keys=True,
        indent=4,
        separators=(",", ": "),
        encoding="utf-8",
        ensure_ascii=False,
    )


def _classify_doc_ids(doc_ids: List[int], reference_doc_ids: Set[int]) -> NamedTuple:
    DocIdClassification = namedtuple(
        "DocIdClassification", "invalid_doc_ids nonexistent_doc_ids existing_doc_ids"
    )
    if not (doc_ids and reference_doc_ids):
        return DocIdClassification(set(), set(), set())
    invalid_doc_ids = {doc_id for doc_id in doc_ids if not doc_id}
    valid_doc_ids = set(doc_ids) - invalid_doc_ids
    return DocIdClassification(
        invalid_doc_ids,
        valid_doc_ids - reference_doc_ids,
        valid_doc_ids.intersection(reference_doc_ids),
    )


def get_all_favorites():
    favorites = DB.table("favorite_paths").all()
    logger.debug("Returning %d favorites...", len(favorites))
    return favorites


def get_favorite(db_path_str: str):
    if not db_path_str:
        logger.warning("Invalid argument for parameter 'db_path_str': %r", db_path_str)
        return None
    logger.debug("DB path string: %r", db_path_str)
    if favorite := DB.table("favorite_paths").get(where("path") == db_path_str):
        logger.debug("Returning favorite (doc_id=%d)...", favorite.doc_id)
    else:
        logger.debug("Returning favorite %r...", favorite)
    return favorite


def insert_favorite(db_path_str: str):
    if not db_path_str:
        logger.warning("Invalid argument for parameter 'db_path_str': %r", db_path_str)
        return None
    logger.debug("DB path string: %r", db_path_str)
    if get_favorite(db_path_str):
        logger.info("Favorite (path=%r) already exists", db_path_str)
        return None
    if inserted_favorite_id := DB.table("favorite_paths").insert({"path": db_path_str}):
        logger.info("Inserted new favorite (doc_id=%d)", inserted_favorite_id)
    else:
        logger.error("Insertion of new favorite failed")
    return inserted_favorite_id


def delete_favorite(db_path_str: str):
    if not db_path_str:
        logger.warning("Invalid argument for parameter 'db_path_str': %r", db_path_str)
    logger.debug("DB path string: %r", db_path_str)
    if not get_favorite(db_path_str):
        logger.warning("No favorite (path=%r) found")
    else:
        logger.info("Deleting favorite (path=%r)...", db_path_str)
        DB.table("favorite_paths").remove(where("path") == db_path_str)


def get_all_tags():
    tags = DB.table("tags").all()
    logger.debug("Returning %d tags...", len(tags))
    return tags


def get_tag(*, tag_id: int = None, name: str = None):
    if name == "":  # pylint:disable=compare-to-empty-string
        logger.warning("Invalid argument for parameter 'name': %r", name)
        return None
    if not (tag_id or name):
        logger.error("Either truthy tag id or truthy tag name is required")
        return None
    tag = DB.table("tags").get(
        doc_id=tag_id if tag_id else None,
        cond=(where("name") == name) if name else None,
    )
    if tag and name:
        if tag["name"] == name:
            logger.debug("Returning tag (doc_id=%d)...", tag.doc_id)
            return tag
        logger.debug("Returning tag %r...", tag)
        return None
    if tag:
        logger.debug("Returning tag (doc_id=%d)...", tag.doc_id)
    else:
        logger.debug("Returning tag %r...", tag)
    return tag


def _is_valid_hex_color(color: str) -> bool:
    if not color or not isinstance(color, str):
        logger.warning("Invalid argument for parameter 'color': %r", color)
        return False
    if is_valid_color := bool(re.fullmatch(r"^#[0-9A-Fa-f]{6}$", color)):
        logger.debug("Valid color: %r", color)
    else:
        logger.debug("Invalid color: %r", color)
    return is_valid_color


def insert_tag(name: str, color: str) -> Optional[int]:
    if not name:
        logger.error("Invalid argument for parameter 'name': %r", name)
        return None
    logger.debug("Name: %r", name)
    if not (color and _is_valid_hex_color(color)):
        logger.error("Invalid argument for parameter 'color': %r", color)
        return None
    logger.debug("Color: %r", color)
    if get_tag(name=name):
        logger.error("Tag (name=%r) already exists", name)
        return None
    if inserted_tag_id := DB.table("tags").insert({"name": name, "color": color}):
        logger.info("Inserted new tag (doc_id=%d)", inserted_tag_id)
    else:
        logger.error("Tag insert failed!")
    return inserted_tag_id


def delete_tags(tag_ids: List[int]):
    (
        invalid_tag_ids,
        nonexistent_tag_ids,
        existing_tag_ids,
    ) = _classify_doc_ids(tag_ids, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains invalid tag ids: %r",
            invalid_tag_ids,
        )
    else:
        logger.debug("Invalid tag ids: %r", invalid_tag_ids)
    if nonexistent_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains nonexistent tag ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent tag ids: %r", nonexistent_tag_ids)
    existing_tag_id_strs = {str(tag_id) for tag_id in existing_tag_ids}
    mappings = DB.search(Query().tag_ids.any(existing_tag_id_strs))
    logger.debug(
        "Updating mappings with the following doc_ids: %r...",
        [mapping.doc_id for mapping in mappings],
    )
    for mapping in mappings:
        mapping["tag_ids"] = sorted(set(mapping["tag_ids"]) - existing_tag_id_strs)
    DB.write_back(mappings)
    logger.info("Deleting tags with the following doc_ids: %r...", existing_tag_ids)
    DB.table("tags").remove(doc_ids=existing_tag_ids)
    remove_mappings_without_tags()


def get_tag_mappings(tag_id: int):
    if not tag_id:
        logger.warning("Invalid argument for parameter 'tag_id': %r", tag_id)
    else:
        logger.debug("Tag id: %r", tag_id)
    mappings = DB.search(Query().tag_ids.all([str(tag_id)]))
    logger.debug("Returning %d mappings...", len(mappings))
    return mappings


def update_tag(tag_id: int, name: str, color: str):
    if not tag_id:
        logger.error("Invalid argument for parameter 'tag_id': %r", tag_id)
        return
    logger.debug("Tag id: %r", tag_id)
    if not name:
        logger.error("Invalid argument for parameter 'name': %r", name)
        return
    logger.debug("Name: %r", name)
    if not color:
        logger.error("Invalid argument for parameter 'color': %r", color)
        return
    logger.debug("Color: %r", color)
    if not _is_valid_hex_color(color):
        logger.error("Invalid color: %r", color)
        return
    if (tag := get_tag(name=name)) and tag.doc_id != tag_id:
        logger.error("Tag (name=%r) already exists", name)
        return
    if tag := get_tag(tag_id=tag_id):
        logger.info("Updating tag (doc_id=%r)...", tag.doc_id)
        DB.table("tags").update({"name": name, "color": color}, doc_ids=[tag_id])
    else:
        logger.error("Nonexistent tag (doc_id=%r)", tag_id)


def get_mapping(*, mapping_id: int = None, db_path_str: str = None):
    if db_path_str == "":  # pylint:disable=compare-to-empty-string
        logger.warning("Invalid argument for parameter 'db_path_str': %r", db_path_str)
        return None
    if not (mapping_id or db_path_str):
        logger.error("Either truthy mapping id or truthy mapping path is required")
        return None
    mapping = DB.get(
        doc_id=mapping_id if mapping_id else None,
        cond=(where("path") == db_path_str) if db_path_str else None,
    )
    if mapping and db_path_str:
        if mapping["path"] == db_path_str:
            logger.debug("Returning mapping (doc_id=%d)...", mapping.doc_id)
            return mapping
        logger.debug("Returning mapping %r...", mapping)
        return None
    if mapping:
        logger.debug("Returning mapping (doc_id=%d)...", mapping.doc_id)
    else:
        logger.debug("Returning mapping %r...", mapping)
    return mapping


def remove_tags_from_mappings(tag_ids: List[int], mapping_ids: List[int]):
    (
        invalid_tag_ids,
        nonexistent_tag_ids,
        existing_tag_ids,
    ) = _classify_doc_ids(tag_ids, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains invalid tag ids: %r",
            invalid_tag_ids,
        )
    else:
        logger.debug("Invalid tag ids: %r", invalid_tag_ids)
    if nonexistent_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains nonexistent tag ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent tag ids: %r", nonexistent_tag_ids)
    (
        invalid_mapping_ids,
        nonexistent_mapping_ids,
        existing_mapping_ids,
    ) = _classify_doc_ids(
        mapping_ids, {mapping.doc_id for mapping in get_all_mappings()}
    )
    if invalid_mapping_ids:
        logger.warning(
            "Argument for parameter mapping_ids contains invalid mapping ids: %r",
            invalid_mapping_ids,
        )
    else:
        logger.debug("Invalid mapping ids: %r", invalid_mapping_ids)
    if nonexistent_mapping_ids:
        logger.warning(
            "Argument for parameter mapping_ids contains nonexistent mapping ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent mapping ids: %r", nonexistent_mapping_ids)
    if existing_mappings := [
        get_mapping(mapping_id=mapping_id) for mapping_id in existing_mapping_ids
    ]:
        logger.info(
            "Updating mappings with the following doc_ids: %r...",
            [mapping.doc_id for mapping in existing_mappings],
        )
        for mapping in existing_mappings:
            mapping["tag_ids"] = sorted(
                set(mapping["tag_ids"]) - {str(tag_id) for tag_id in existing_tag_ids}
            )
        DB.write_back(existing_mappings)
    remove_mappings_without_tags()


def remove_mappings_without_tags():
    logger.debug("Removing mappings without tags...")
    DB.remove(Query().tag_ids.test(lambda x: not x))


def get_all_mappings():
    mappings = DB.all()
    logger.debug("Returning %d mappings...", len(mappings))
    return mappings


def insert_mapping(
    db_path_str: str, tag_ids: Union[List[int], None] = None
) -> Optional[int]:
    if not db_path_str:
        logger.error("Invalid argument for parameter 'db_path_str': %r", db_path_str)
        return None
    logger.debug("Db path string: %r", db_path_str)
    if get_mapping(db_path_str=db_path_str):
        logger.info("Mapping (path=%r) already exists", db_path_str)
        return None
    logger.debug("Tag ids: %r", tag_ids)
    if tag_ids is None:
        if inserted_mapping_id := DB.insert({"path": db_path_str, "tag_ids": []}):
            logger.debug("Inserted new mapping (doc_id=%d)", inserted_mapping_id)
        else:
            logger.error("Mapping insert failed!")
        return inserted_mapping_id
    if not isinstance(tag_ids, list):
        logger.error("Invalid argument for parameter 'tag_ids': %r", tag_ids)
        return None
    (
        invalid_tag_ids,
        nonexistent_tag_ids,
        existing_tag_ids,
    ) = _classify_doc_ids(tag_ids, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains invalid tag ids: %r",
            invalid_tag_ids,
        )
    else:
        logger.debug("Invalid tag ids: %r", invalid_tag_ids)
    if nonexistent_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains nonexistent tag ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent tag ids: %r", nonexistent_tag_ids)
    if inserted_mapping_id := DB.insert(
        {
            "path": db_path_str,
            "tag_ids": (
                [str(tag_id) for tag_id in existing_tag_ids] if existing_tag_ids else []
            ),
        }
    ):
        logger.info("Inserted new mapping (doc_id=%d)", inserted_mapping_id)
    else:
        logger.error("Mapping insert failed!")
    return inserted_mapping_id


def delete_mappings(mapping_ids: List[int]):
    (
        invalid_mapping_ids,
        nonexistent_mapping_ids,
        existing_mapping_ids,
    ) = _classify_doc_ids(
        mapping_ids, {mapping.doc_id for mapping in get_all_mappings()}
    )
    if invalid_mapping_ids:
        logger.warning(
            "Argument for parameter 'mapping_ids' contains invalid mapping ids: %r",
            invalid_mapping_ids,
        )
    else:
        logger.debug("Invalid mapping ids: %r", invalid_mapping_ids)
    if nonexistent_mapping_ids:
        logger.warning(
            "Argument for parameter 'mapping_ids' contains nonexistent mapping ids: %r",
            nonexistent_mapping_ids,
        )
    else:
        logger.debug("Nonexistent mapping ids: %r", nonexistent_mapping_ids)
    logger.info(
        "Deleting mappings with the following doc_ids: %r...", existing_mapping_ids
    )
    DB.remove(doc_ids=existing_mapping_ids)
    remove_mappings_without_tags()


def update_mapping_path(mapping_id: int, db_path_str: str) -> None:
    if not mapping_id:
        logger.error("Invalid argument for parameter 'mapping_id': %r", mapping_id)
        return
    logger.debug("Mapping id: %r", mapping_id)
    if not db_path_str:
        logger.error("Invalid argument for parameter 'db_path_str': %r", db_path_str)
        return
    logger.debug("Db path string: %r", db_path_str)
    if (
        mapping := get_mapping(db_path_str=db_path_str)
    ) and mapping.doc_id != mapping_id:
        logger.error("Mapping (path=%r) already exists", mapping)
        return
    if mapping := get_mapping(mapping_id=mapping_id):
        logger.info("Updating mapping (doc_id=%r)...", mapping.doc_id)
        DB.update({"path": db_path_str}, doc_ids=[mapping_id])
    else:
        logger.error("Nonexistent mapping (doc_id=%r)", mapping_id)


def get_filtered_mappings(
    tag_ids_to_include: List[int],
    tag_ids_to_exclude: List[int],
    db_path_str_like: Optional[str] = None,
):
    (
        invalid_tag_ids_to_include,
        nonexistent_tag_ids_to_include,
        existing_tag_ids_to_include,
    ) = _classify_doc_ids(tag_ids_to_include, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids_to_include:
        logger.warning(
            "Argument for parameter 'tag_ids_to_include' contains invalid tag ids: %r",
            invalid_tag_ids_to_include,
        )
    else:
        logger.debug("Invalid tag ids to include: %r", invalid_tag_ids_to_include)
    if nonexistent_tag_ids_to_include:
        logger.warning(
            "Argument for parameter 'tag_ids_to_include' "
            "contains nonexistent tag ids: %r",
            nonexistent_tag_ids_to_include,
        )
    else:
        logger.debug(
            "Nonexistent tag ids to include: %r", nonexistent_tag_ids_to_include
        )
    (
        invalid_tag_ids_to_exclude,
        nonexistent_tag_ids_to_exclude,
        existing_tag_ids_to_exclude,
    ) = _classify_doc_ids(tag_ids_to_exclude, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids_to_exclude:
        logger.warning(
            "Argument for parameter 'tag_ids_to_exclude' contains invalid tag ids: %r",
            invalid_tag_ids_to_exclude,
        )
    else:
        logger.debug("Invalid tag ids to exclude: %r", invalid_tag_ids_to_exclude)
    if nonexistent_tag_ids_to_exclude:
        logger.warning(
            "Argument for parameter 'tag_ids_to_exclude' "
            "contains nonexistent tag ids: %r",
            nonexistent_tag_ids_to_exclude,
        )
    else:
        logger.debug(
            "Nonexistent tag ids to exclude: %r", nonexistent_tag_ids_to_exclude
        )
    tag_str_ids_to_include = [str(tag_id) for tag_id in existing_tag_ids_to_include]
    tag_str_ids_to_exclude = [str(tag_id) for tag_id in existing_tag_ids_to_exclude]
    if db_path_str_like:  # pylint: disable=consider-ternary-expression
        mappings = DB.search(
            (Query().tag_ids.all(tag_str_ids_to_include))
            & (~(Query().tag_ids.any(tag_str_ids_to_exclude)))
            & (
                Query().path.test(
                    lambda x: x.lower().find(db_path_str_like.lower()) > -1
                )
            )
        )
    else:
        mappings = DB.search(
            (Query().tag_ids.all(tag_str_ids_to_include))
            & (~(Query().tag_ids.any(tag_str_ids_to_exclude)))
        )
    logger.debug("Returning %d mappings...", len(mappings))
    return mappings


def append_tags_to_mappings(tag_ids: List[int], mapping_ids: List[int]):
    (
        invalid_tag_ids,
        nonexistent_tag_ids,
        existing_tag_ids,
    ) = _classify_doc_ids(tag_ids, {tag.doc_id for tag in get_all_tags()})
    if invalid_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains invalid tag ids: %r",
            invalid_tag_ids,
        )
    else:
        logger.debug("Invalid tag ids: %r", invalid_tag_ids)
    if nonexistent_tag_ids:
        logger.warning(
            "Argument for parameter 'tag_ids' contains nonexistent tag ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent tag ids: %r", nonexistent_tag_ids)
    (
        invalid_mapping_ids,
        nonexistent_mapping_ids,
        existing_mapping_ids,
    ) = _classify_doc_ids(
        mapping_ids, {mapping.doc_id for mapping in get_all_mappings()}
    )
    if invalid_mapping_ids:
        logger.warning(
            "Argument for parameter 'mapping_ids' contains invalid mapping ids: %r",
            invalid_mapping_ids,
        )
    else:
        logger.debug("Invalid mapping ids: %r", invalid_mapping_ids)
    if nonexistent_mapping_ids:
        logger.warning(
            "Argument for parameter 'mapping_ids' contains nonexistent mapping ids: %r",
            nonexistent_tag_ids,
        )
    else:
        logger.debug("Nonexistent mapping ids: %r", nonexistent_mapping_ids)
    if existing_mappings := [
        get_mapping(mapping_id=mapping_id) for mapping_id in existing_mapping_ids
    ]:
        logger.info(
            "Updating mappings with the following doc_ids: %r...",
            [mapping.doc_id for mapping in existing_mappings],
        )
        for mapping in existing_mappings:
            mapping["tag_ids"] = sorted(
                set(mapping["tag_ids"]).union(
                    {str(tag_id) for tag_id in existing_tag_ids}
                )
            )
        DB.write_back(existing_mappings)


DB = load_db(params.DB_PATH)
logger.info(
    "Loaded database at %r. Found %d tags, %d mappings, and %d favorites.",
    params.DB_PATH,
    len(get_all_tags()),
    len(get_all_mappings()),
    len(get_all_favorites()),
)
