import os
from pathlib import Path
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import redirect, render

from Tagger import params, settings

from . import db_operations as db


def _is_allowed_path(path: Path) -> bool:
    return (
        not params.BASE_PATH
        or path == params.BASE_PATH
        or params.BASE_PATH in path.parents
    )


def _get_db_path_str(path: Path) -> str:
    if not params.BASE_PATH:
        return path.as_posix()
    if path == params.BASE_PATH:
        return "/"
    if params.BASE_PATH in path.parents:
        return "/".join(path.parts[len(params.BASE_PATH.parts) :])
    return ""


def _get_extended_dataset(dataset):
    for element in dataset:
        db_path_str = element["path"]
        db_path = Path(db_path_str)
        if params.BASE_PATH:
            if db_path_str == "/":
                path = params.BASE_PATH
            else:
                path = params.BASE_PATH.joinpath(db_path)
        else:
            path = db_path
        element["path_str"] = path.as_posix()
        element["system_path_str"] = str(path)
        element["db_path_str"] = db_path.as_posix()
        element["path_exists"] = path.exists()
        element["path_is_dir"] = path.is_dir()
        if element.get("tag_ids", []):
            element["tags"] = [
                db.get_tag_by_id(int(mapping_tag_id))
                for mapping_tag_id in element["tag_ids"]
            ]
    return dataset


def _get_drive_root_dirs():
    if os.name == "nt":
        from ctypes import windll  # pylint: disable=C0415

        bitfield = windll.kernel32.GetLogicalDrives()
        masks = [(1 << n, chr(ord("A") + n)) for n in range(ord("Z") - ord("A") + 1)]
        return [
            {"path_str": drive + ":/", "system_path_str": drive + ":\\"}
            for mask, drive in masks
            if bitfield & mask
        ]
    return []


def mapping_details(request, mapping_id):
    if request.method == "GET":
        return render(
            request,
            "pathtagger/mapping_details.html",
            {
                "mapping": _get_extended_dataset([db.get_mapping(mapping_id)]).pop(),
                "tags": db.get_all_tags(),
            },
        )
    if request.method == "POST":
        if path_str := request.POST.get("path", ""):
            if _is_allowed_path(path := Path(path_str)):
                db.update_mapping(mapping_id, _get_db_path_str(path))
    return redirect("pathtagger:mappings_list")


def add_mapping(request):
    if path_str := request.POST.get("path", ""):
        path = Path(path_str)
        if _is_allowed_path(path) and not db.get_mapping_by_path(
            _get_db_path_str(path)
        ):
            db.insert_mapping(_get_db_path_str(path), [])
    return redirect("pathtagger:mappings_list")


def edit_mappings(request):
    if request.POST.get("action_delete"):
        return delete_mappings(request)
    if request.POST.get("action_edit_tags"):
        if mapping_ids := [
            int(mapping_id) for mapping_id in request.POST.getlist("mapping_id", [])
        ]:
            tag_ids_to_append = []
            tag_ids_to_remove = []
            for key in request.POST:
                if key.startswith("tag_"):
                    value = request.POST.get(key, "")
                    if value == "append":
                        tag_ids_to_append.append(int(key.strip("tag_")))
                    elif value == "remove":
                        tag_ids_to_remove.append(int(key.strip("tag_")))
            if new_tag_names_str := request.POST.get("new_tag_names", ""):
                for name in new_tag_names_str.strip(",").split(","):
                    name = name.strip()
                    if tag := db.get_tag_by_name(name):
                        tag_ids_to_append.append(tag.doc_id)
                    else:
                        tag_ids_to_append.append(
                            db.insert_tag(name, params.DEFAULT_TAG_COLOR)
                        )
            db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
            db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    return redirect("pathtagger:mappings_list")


def delete_mappings(request):
    db.delete_mappings(
        [int(mapping_id) for mapping_id in request.POST.getlist("mapping_id", [])]
    )
    return redirect("pathtagger:mappings_list")


def mappings_list(request):
    tag_ids_to_include = [
        int(tag_id) for tag_id in request.GET.getlist("tag_id_include", [])
    ]
    tag_ids_to_exclude = [
        int(tag_id) for tag_id in request.GET.getlist("tag_id_exclude", [])
    ]
    path_name_like = request.GET.get("path_name_like", "")
    path_type = request.GET.get("path_type", "all")
    mappings = _get_extended_dataset(
        db.get_filtered_mappings(tag_ids_to_include, tag_ids_to_exclude, path_name_like)
    )
    if path_type == "existent":
        mappings = [mapping for mapping in mappings if mapping["path_exists"]]
    elif path_type == "nonexistent":
        mappings = [mapping for mapping in mappings if not mapping["path_exists"]]
    filters = {}
    filters["tag_ids_to_include"] = tag_ids_to_include
    filters["tag_ids_to_exclude"] = tag_ids_to_exclude
    filters["path_name_like"] = path_name_like
    filters["path_type"] = path_type
    return render(
        request,
        "pathtagger/mappings_list.html",
        {
            "mappings": mappings,
            "no_mappings_at_all": not db.get_all_mappings(),
            "filters": filters,
            "tags": db.get_all_tags(),
        },
    )


def tag_details(request, tag_id):
    if request.method == "GET":
        return render(
            request,
            "pathtagger/tag_details.html",
            {
                "tag": db.get_tag_by_id(tag_id),
                "mappings": _get_extended_dataset(db.get_tag_mappings(tag_id)),
            },
        )
    if request.method == "POST":
        tag_id = int(request.POST.get("tag_id", "0"))
        db.update_tag(
            tag_id,
            request.POST.get("name", ""),
            request.POST.get("color", params.DEFAULT_TAG_COLOR),
        )
        return redirect("pathtagger:tag_details", tag_id=tag_id)
    return redirect("pathtagger:tags_list")


def add_tag(request):
    name = request.POST.get("name", "")
    if name and not db.get_tag_by_name(name):
        db.insert_tag(name, request.POST.get("color", params.DEFAULT_TAG_COLOR))
    return redirect("pathtagger:tags_list")


def delete_tags(request):
    db.delete_tags([int(tag_id) for tag_id in request.POST.getlist("tag_id", [])])
    return redirect("pathtagger:tags_list")


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag["occurrences"] = len(db.get_tag_mappings(tag.doc_id))
    return render(request, "pathtagger/tags_list.html", {"tags": tags})


def remove_tag_from_mappings(request):
    tag_id = int(request.POST.get("tag_id", 0))
    db.remove_tags_from_mappings(
        [tag_id],
        [int(mapping_id) for mapping_id in request.POST.getlist("mapping_id", [])],
    )
    return redirect("pathtagger:tag_details", tag_id=tag_id)


def path_details(request, path_str):
    path = Path(path_str)
    path_tokens = []
    path_children = []
    if path.exists():
        path_parents = list(reversed(path.parents))
        if path.is_dir():
            path_parents.append(path)
        path_tokens = [
            {"name": part, "path_str": parent.as_posix()}
            for part, parent in zip(path.parts, path_parents)
        ]
        if path.is_dir():
            path_children = [
                {
                    "path_str": path_child.as_posix(),
                    "db_path_str": _get_db_path_str(path_child),
                    "name": path_child.name,
                    "is_dir": path_child.is_dir(),
                }
                for path_child in sorted(
                    list(path.glob("*")), key=lambda x: (1 - x.is_dir(), str(x).upper())
                )
            ]
            for path_child in path_children:
                mapping = db.get_mapping_by_path(path_child["db_path_str"])
                if mapping and mapping.get("tag_ids", []):
                    path_child["tags"] = [
                        db.get_tag_by_id(int(mapping_tag_id))
                        for mapping_tag_id in mapping["tag_ids"]
                    ]
    return render(
        request,
        "pathtagger/path_details.html",
        {
            "path_str": path_str,
            "system_path_str": str(path),
            "ajax_path_str": quote(path_str),
            "is_root_path": path.anchor == str(path),
            "path_exists": path.exists(),
            "path_is_favorite": bool(db.get_favorite_path(_get_db_path_str(path))),
            "path_parent": path.parent.as_posix(),
            "path_tokens": path_tokens,
            "path_children": path_children,
            "tags": db.get_all_tags(),
            "drive_root_dirs": _get_drive_root_dirs(),
            "is_tagging_allowed": _is_allowed_path(path),
        },
    )


def edit_path_tags(request):
    if paths := request.POST.getlist("path", []):
        mapping_ids = []
        for path in paths:
            mapping = db.get_mapping_by_path(path)
            if mapping:
                mapping_ids.append(mapping.doc_id)
            else:
                mapping_ids.append(db.insert_mapping(path, []))
        tag_ids_to_append = []
        tag_ids_to_remove = []
        for key in request.POST:
            if key.startswith("tag_"):
                value = request.POST.get(key, "")
                if value == "append":
                    tag_ids_to_append.append(int(key.strip("tag_")))
                elif value == "remove":
                    tag_ids_to_remove.append(int(key.strip("tag_")))
        if new_tag_names_str := request.POST.get("new_tag_names", ""):
            for name in new_tag_names_str.strip(",").split(","):
                name = name.strip()
                if tag := db.get_tag_by_name(name):
                    tag_ids_to_append.append(tag.doc_id)
                else:
                    tag_ids_to_append.append(
                        db.insert_tag(name, params.DEFAULT_TAG_COLOR)
                    )
        db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
        db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    return redirect(
        "pathtagger:path_details", path_str=request.POST.get("current_path", "")
    )


def toggle_favorite_path(request):
    if path_str := request.POST.get("path", ""):
        path = Path(path_str)
        db_path_str = _get_db_path_str(path)
        if not db_path_str:
            db_path_str = "/"
        if db.get_favorite_path(db_path_str):
            db.delete_favorite_path(db_path_str)
            is_favorite = False
        elif _is_allowed_path(path):
            db.insert_favorite_path(db_path_str)
            is_favorite = True
        else:
            is_favorite = False
        if request.is_ajax():
            return JsonResponse({"status": "ok", "is_favorite": str(bool(is_favorite))})
    return redirect("pathtagger:homepage")


def root_path_redirect(request):  # pylint: disable=W0613
    return redirect(
        "pathtagger:path_details",
        path_str=Path(Path(settings.BASE_DIR).anchor).as_posix(),
    )


def homepage(request):
    return render(
        request,
        "pathtagger/homepage.html",
        {"favorite_paths": _get_extended_dataset(db.get_all_favorite_paths())},
    )
