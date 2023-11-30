import logging
import os
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import redirect, render
from tinydb.database import Document

from pathtagger import db_operations as db
from pathtagger.mypath import MyPath
from Tagger import params, settings

logger = logging.getLogger(__name__)


def _get_extended_dataset(dataset: List[Document]) -> List[Document]:
    if not dataset:
        logger.debug("Falsy argument for parameter 'dataset': %r", dataset)
    else:
        for element in dataset:
            mypath = MyPath(element["path"], False)
            logger.debug("MyPath: %r", mypath)
            element["abs_path_str"] = mypath.abs_path_str
            element["system_path_str"] = str(mypath.abs_path)
            element["db_path_str"] = mypath.db_path_str
            element["path_exists"] = mypath.abs_path.exists()
            element["path_is_dir"] = mypath.abs_path.is_dir()
            if element.get("tag_ids", []):
                element["tags"] = [
                    db.get_tag(tag_id=int(mapping_tag_id))
                    for mapping_tag_id in element["tag_ids"]
                ]
    return dataset


def get_drive_root_dirs():
    drive_root_dirs = []
    if os.name == "nt":
        from ctypes import windll  # pylint: disable=import-outside-toplevel

        bitfield = windll.kernel32.GetLogicalDrives()
        masks = [(1 << n, chr(ord("A") + n)) for n in range(ord("Z") - ord("A") + 1)]
        drive_root_dirs = [
            {"path_str": drive + ":/", "system_path_str": drive + ":\\"}
            for mask, drive in masks
            if bitfield & mask
        ]
    logger.debug("Returning %d drive_root_dirs...", len(drive_root_dirs))
    return drive_root_dirs


def mapping_details(request, mapping_id):
    if not mapping_id:
        logger.warning("Invalid argument for parameter 'mapping_id': %r", mapping_id)
    else:
        logger.debug("Mapping id: %r", mapping_id)
    if request.method == "POST":
        if not (path_str := request.POST.get("path")):
            logger.error("Invalid value for request parameter 'path': %r", path_str)
        else:
            logger.debug("Path: %r", path_str)
        mypath = MyPath(path_str, True)
        logger.debug("MyPath: %r", mypath)
        if mypath.is_valid_db_path_str:
            db.update_mapping_path(mapping_id, mypath.db_path_str)
        return redirect("pathtagger:mappings_list")
    return render(
        request,
        "pathtagger/mapping_details.html",
        {
            "mapping": _get_extended_dataset(
                [db.get_mapping(mapping_id=mapping_id)]
            ).pop()
        },
    )


def add_mapping(request):
    if not (path_str := request.POST.get("path")):
        logger.warning("Invalid value for request parameter 'path': %r", path_str)
    else:
        logger.debug("Request parameter 'path': %r", path_str)
    mypath = MyPath(path_str, True)
    logger.debug("MyPath: %r", mypath)
    db.insert_mapping(mypath.db_path_str, [])
    return redirect("pathtagger:mappings_list")


def _parse_tag_ids_to_append_and_remove(querydict, new_tag_names):
    logger.debug("New tag names: %r", new_tag_names)
    tag_ids_to_append = _get_tag_ids_for_tag_names(new_tag_names)
    tag_ids_to_remove = set()
    if not querydict:
        logger.error("Invalid value for querydict: %r", querydict)
    else:
        logger.debug("Querydict: %r", querydict)
        for key, action in querydict.items():
            if key.startswith("tag_"):
                if action == "append":
                    tag_ids_to_append.add(int(key.strip("tag_")))
                elif action == "remove":
                    tag_ids_to_remove.add(int(key.strip("tag_")))
                # ignore tags that are to be simultaneously appended and removed
                if set(action) == {"append", "remove"}:
                    logger.warning(
                        "Same tag cannot be added and removed at the same time. "
                        "Ignoring (tag_id=%r).",
                        key.strip("tag_"),
                    )
        logger.debug(
            "Returning %d tags to append and %d tags to remove...",
            len(tag_ids_to_append),
            len(tag_ids_to_remove),
        )
    return tag_ids_to_append, tag_ids_to_remove


def _parse_tag_names_from_string(new_tag_names_str: str) -> Set[str]:
    logger.debug("New tag names: %r", new_tag_names_str)
    tag_names = (
        {
            stripped_token
            for token in new_tag_names_str.strip(",").split(",")
            if (stripped_token := token.strip())
        }
        if new_tag_names_str
        else set()
    )
    logger.debug("Returning tag_names %r...")
    return tag_names


def _get_tag_ids_for_tag_names(tag_names_str: str) -> Set[int]:
    logger.debug("New tag names: %r", tag_names_str)
    tag_ids = {
        tag.doc_id
        if (tag := db.get_tag(name=tag_name))
        else db.insert_tag(tag_name, params.DEFAULT_TAG_COLOR)
        for tag_name in _parse_tag_names_from_string(tag_names_str)
    }
    logger.debug("Returning %d tag ids...", len(tag_ids))
    return tag_ids


def edit_mappings(request):
    if request.POST.get("action_delete"):
        return delete_mappings(request)
    if request.POST.get("action_edit_tags"):
        if not (mapping_id_strs := request.POST.getlist("mapping_id")):
            logger.error(
                "Invalid values list for request parameter 'mapping_id': %r",
                mapping_id_strs,
            )
        else:
            logger.debug(
                "Request parameter 'mapping_id' values list: %r", mapping_id_strs
            )
        new_tag_names = request.POST.get("new_tag_names")
        logger.debug("New tag names: %r", new_tag_names)
        if mapping_ids := [int(mapping_id) for mapping_id in mapping_id_strs]:
            tag_ids_to_append, tag_ids_to_remove = _parse_tag_ids_to_append_and_remove(
                {
                    key: value
                    for key, value in request.POST.items()
                    if key.startswith("tag_")
                },
                new_tag_names,
            )
            tag_ids_to_append.update(_get_tag_ids_for_tag_names(new_tag_names))
            db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
            db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
        return redirect("pathtagger:mappings_list")
    logger.error(
        "Request should have exactly one of the following parameters: "
        "'action_delete', 'action_edit_tags'"
    )
    return redirect("pathtagger:mappings_list")


def delete_mappings(request):
    mapping_id_strs = request.POST.getlist("mapping_id")
    logger.debug("Mapping id values list: %r", mapping_id_strs)
    db.delete_mappings([int(mapping_id) for mapping_id in mapping_id_strs])
    return redirect("pathtagger:mappings_list")


def mappings_list(request):
    tag_id_include_strs = request.GET.getlist("tag_id_include")
    logger.debug("Tag id include values: %r", tag_id_include_strs)
    tag_id_exclude_strs = request.GET.getlist("tag_id_exclude")
    logger.debug("Tag id exclude values: %r", tag_id_exclude_strs)
    tag_ids_to_include = [int(tag_id) for tag_id in tag_id_include_strs]
    tag_ids_to_exclude = [int(tag_id) for tag_id in tag_id_exclude_strs]
    path_name_like = request.GET.get("path_name_like", "")
    logger.debug("Path name like: %r", path_name_like)
    path_type = request.GET.get("path_type", "all")
    logger.debug("Path type: %r", path_type)
    mappings = _get_extended_dataset(
        db.get_filtered_mappings(tag_ids_to_include, tag_ids_to_exclude, path_name_like)
    )
    if path_type == "existent":
        mappings = [mapping for mapping in mappings if mapping["path_exists"]]
    elif path_type == "nonexistent":
        mappings = [mapping for mapping in mappings if not mapping["path_exists"]]
    return render(
        request,
        "pathtagger/mappings_list.html",
        {
            "mappings": mappings,
            "no_mappings_at_all": not db.get_all_mappings(),
            "filters": {
                "tag_ids_to_include": tag_ids_to_include,
                "tag_ids_to_exclude": tag_ids_to_exclude,
                "path_name_like": path_name_like,
                "path_type": path_type,
            },
            "tags": db.get_all_tags(),
        },
    )


def tag_details(request, tag_id):
    if request.method == "POST":
        if not (name := request.POST.get("name")):
            logger.error("Invalid value for request parameter 'name': %r", name)
        else:
            logger.debug("Name: %r", name)
        if not (color := request.POST.get("color")):
            logger.error("Invalid value for request parameter 'color': %r", color)
        else:
            logger.debug("Color: %r", color)
        if name and color:
            db.update_tag(tag_id, name, color)
        return redirect("pathtagger:tags_list")
    return render(
        request,
        "pathtagger/tag_details.html",
        {
            "tag": db.get_tag(tag_id=tag_id),
            "mappings": _get_extended_dataset(db.get_tag_mappings(tag_id)),
        },
    )


def add_tag(request):
    if not (name := request.POST.get("name")):
        logger.error("Invalid value for request parameter 'name': %r", name)
    else:
        logger.debug("Name: %r", name)
    if not (color := request.POST.get("color")):
        logger.error("Invalid value for request parameter 'color': %r", color)
    else:
        logger.debug("Color: %r", color)
    if not color:
        color = params.DEFAULT_TAG_COLOR
    if name and color:
        db.insert_tag(name, color)
    return redirect("pathtagger:tags_list")


def delete_tags(request):
    if not (tag_ids := request.POST.getlist("tag_id")):
        logger.error("Invalid values list for request parameter 'tag_id': %r", tag_ids)
    else:
        logger.debug("Tag ids: %r", tag_ids)
    db.delete_tags([int(tag_id) for tag_id in tag_ids])
    return redirect("pathtagger:tags_list")


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag["occurrences"] = len(db.get_tag_mappings(tag.doc_id))
    return render(request, "pathtagger/tags_list.html", {"tags": tags})


def remove_tag_from_mappings(request, tag_id):
    if not tag_id:
        logger.warning("Invalid argument for parameter 'tag_id': %r", tag_id)
    else:
        logger.debug("Tag id: %r", tag_id)
    if not (mapping_ids := request.POST.getlist("mapping_id")):
        logger.error(
            "Invalid values list for request parameter 'mapping_id': %r", mapping_ids
        )
    else:
        logger.debug("Mapping id: %r", mapping_ids)
    db.remove_tags_from_mappings(
        [tag_id],
        [int(mapping_id) for mapping_id in mapping_ids],
    )
    return redirect("pathtagger:tag_details", tag_id=tag_id)


def mypath_tokens(mypath: MyPath) -> List[Dict[str, str]]:
    if not mypath:
        logger.warning("Invalid argument for parameter 'mypath': %r", mypath)
    else:
        logger.debug("Mypath: %r", mypath)
    if not mypath.abs_path:
        return []
    mypath_parents = list(reversed(mypath.abs_path.parents))
    if mypath.abs_path.is_dir():
        mypath_parents.append(mypath.abs_path)
    return [
        {"name": part, "path_str": parent.as_posix()}
        for part, parent in zip(mypath.abs_path.parts, mypath_parents)
    ]


def mypath_children_data(mypath: MyPath) -> List[Dict[str, str]]:
    if not mypath:
        logger.warning("Invalid argument for parameter 'mypath': %r", mypath)
    else:
        logger.debug("Mypath: %r", mypath)
    if not mypath.abs_path or not mypath.abs_path.is_dir():
        return []
    return [
        {
            "path_str": mypath_child.abs_path_str,
            "db_path_str": mypath_child.db_path_str,
            "name": mypath_child.abs_path.name,
            "is_dir": mypath_child.abs_path.is_dir(),
            "tags": (
                [
                    db.get_tag(tag_id=int(mapping_tag_id))
                    for mapping_tag_id in mapping["tag_ids"]
                ]
                if (mapping := db.get_mapping(db_path_str=mypath_child.db_path_str))
                and mapping.get("tag_ids", [])
                else []
            ),
        }
        for mypath_child in mypath.get_children()
    ]


def path_details(request, abs_path_str):
    if not abs_path_str:
        logger.warning(
            "Invalid argument for parameter 'abs_path_str': %r", abs_path_str
        )
    else:
        logger.debug("Absolute path string: %r", abs_path_str)
    mypath = MyPath(abs_path_str, True)
    logger.debug("MyPath: %r", mypath)
    if mypath.abs_path_str:
        return render(
            request,
            "pathtagger/path_details.html",
            {
                "path_str": mypath.abs_path_str,
                "system_path_str": str(mypath.abs_path),
                "ajax_path_str": quote(mypath.abs_path_str),
                "is_root_path": mypath.abs_path.anchor == str(mypath.abs_path),
                "path_exists": mypath.abs_path.exists(),
                "path_is_favorite": bool(db.get_favorite(mypath.db_path_str)),
                "path_parent": mypath.abs_path.parent.as_posix(),
                "path_tokens": mypath_tokens(mypath),
                "path_children": mypath_children_data(mypath),
                "tags": db.get_all_tags(),
                "drive_root_dirs": get_drive_root_dirs(),
                "is_tagging_allowed": mypath.is_valid_db_path_str,
            },
        )
    return render(
        request,
        "pathtagger/path_details.html",
        {
            "system_path_str": abs_path_str,
            "path_exists": False,
        },
    )


def _prepare_mapping_ids_for_tag_update(raw_path_strs: Set[str]) -> Set[int]:
    logger.debug("Raw path strings: %r", raw_path_strs)
    mapping_ids = set()
    if raw_path_strs:
        for raw_path_str in raw_path_strs:
            if not (mypath := MyPath(raw_path_str, True)):
                logger.warning("Invalid mypath: %r", mypath)
            else:
                logger.debug("MyPath: %r", mypath)
            if mapping := db.get_mapping(db_path_str=mypath.db_path_str):
                logger.debug("Mapping (path=%r) already exists", mapping)
                mapping_ids.add(mapping.doc_id)
            else:
                logger.debug("Mapping (path=%r) does not exist yet", mapping)
                if mapping_id := db.insert_mapping(mypath.db_path_str, []):
                    mapping_ids.add(mapping_id)
        logger.debug("Returning %d mapping ids...", len(mapping_ids))
    return mapping_ids


def edit_path_tags(request):
    if raw_path_strs := set(request.POST.getlist("path")):
        logger.debug("Raw path strings: %r", raw_path_strs)
        mapping_ids = _prepare_mapping_ids_for_tag_update(raw_path_strs)
        new_tag_names = request.POST.get("new_tag_names")
        logger.debug("New tag names: %r", new_tag_names)
        tag_ids_to_append, tag_ids_to_remove = _parse_tag_ids_to_append_and_remove(
            {
                key: value
                for key, value in request.POST.items()
                if key.startswith("tag_")
            },
            new_tag_names,
        )
        logger.debug("Mapping ids to update: %r", mapping_ids)
        logger.debug("Tag ids to append: %r", tag_ids_to_append)
        logger.debug("Tag ids to remove: %r", tag_ids_to_remove)
        db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
        db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    else:
        logger.error("Invalid value for request parameters 'path': %r", raw_path_strs)
    return redirect(
        "pathtagger:path_details", abs_path_str=request.POST.get("current_path")
    )


def toggle_favorite_path(request):
    path_str = request.POST.get("path")
    logger.debug("Absolute path string: %r", path_str)
    mypath = MyPath(path_str, os.name == "nt" and params.BASE_PATH is None)
    logger.debug("MyPath: %r", mypath)
    if mypath.is_valid_db_path_str:
        if db.get_favorite(mypath.db_path_str):
            db.delete_favorite(mypath.db_path_str)
            is_favorite = False
        else:
            db.insert_favorite(mypath.db_path_str)
            is_favorite = True
        if request.is_ajax():
            logger.debug("Sending Json response OK, is_favorite=%r", bool(is_favorite))
            return JsonResponse({"status": "ok", "is_favorite": str(bool(is_favorite))})
    elif request.is_ajax():
        logger.debug("Sending Json response NOK")
        return JsonResponse({"status": "nok"})
    return redirect("pathtagger:homepage")


def root_path_redirect(_):
    root_path = MyPath(
        params.BASE_PATH if params.BASE_PATH else Path(Path(settings.BASE_DIR).anchor),
        True,
    )
    logger.debug("Root path: %r", root_path)
    return redirect("pathtagger:path_details", abs_path_str=root_path.abs_path_str)


def homepage(request):
    return render(
        request,
        "pathtagger/homepage.html",
        {"favorites": _get_extended_dataset(db.get_all_favorites())},
    )
