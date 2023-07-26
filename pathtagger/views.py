import os
import re
from pathlib import Path, PosixPath
from typing import Dict, List, Optional, Union
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import redirect, render

from pathtagger import db_operations as db
from Tagger import params, settings


class MyPath:
    NT_ABS_PATH_STR_REGEX = r"^[A-Za-z]:[\\\/]"
    NT_DB_PATH_STR_REGEX = r"^[\\\/]"

    def __init__(self, raw_path: Union[Path, str], is_abs_path: bool):
        self.raw_path = raw_path
        if raw_path is None:
            self.abs_path_str = None
            return
        # no weird db_paths allowed
        if os.name == "posix" and not str(raw_path).startswith("/"):
            self.abs_path_str = None
            return
        if os.name == "nt":
            if (
                is_abs_path and not re.match(self.NT_ABS_PATH_STR_REGEX, str(raw_path))
            ) or (
                not is_abs_path
                and not re.match(self.NT_DB_PATH_STR_REGEX, str(raw_path))
            ):
                self.abs_path_str = None
                return
        formatted_raw_path_str = Path(raw_path).as_posix().strip("/")
        if isinstance(Path(raw_path), PosixPath):
            formatted_raw_path_str = "/" + formatted_raw_path_str
        if is_abs_path or not params.BASE_PATH:
            self.abs_path_str = formatted_raw_path_str
        else:
            self.abs_path_str = params.BASE_PATH.joinpath(
                formatted_raw_path_str.lstrip("/")
            ).as_posix()

    @property
    def db_path_str(self) -> Optional[str]:
        if self.abs_path_str is None:
            return None
        abs_path = Path(self.abs_path_str)
        if not params.BASE_PATH:
            return abs_path.as_posix()
        if abs_path == params.BASE_PATH:
            return "/"
        if params.BASE_PATH in abs_path.parents:
            return "/" + "/".join(abs_path.parts[len(params.BASE_PATH.parts) :])
        return None

    @property
    def db_path(self) -> Optional[Path]:
        if self.db_path_str is None:
            return None
        return Path(self.db_path_str)

    @property
    def abs_path(self) -> Optional[Path]:
        if self.abs_path_str is None:
            return None
        return Path(self.abs_path_str)

    @property
    def is_valid_db_path_str(self) -> bool:
        return self.db_path_str not in (None, ".")

    def get_children(self) -> List["MyPath"]:
        return [
            MyPath(child_raw_path, True)
            for child_raw_path in sorted(
                list(self.abs_path.glob("*")),
                key=lambda x: (1 - x.is_dir(), str(x).upper()),
            )
        ]


def get_extended_dataset(dataset):
    for element in dataset:
        mypath = MyPath(element["path"], False)
        element["abs_path_str"] = mypath.abs_path_str
        element["system_path_str"] = str(mypath.abs_path)
        element["db_path_str"] = mypath.db_path_str
        element["path_exists"] = mypath.abs_path.exists()
        element["path_is_dir"] = mypath.abs_path.is_dir()
        if element.get("tag_ids", []):
            element["tags"] = [
                db.get_tag_by_id(int(mapping_tag_id))
                for mapping_tag_id in element["tag_ids"]
            ]
    return dataset


def get_drive_root_dirs():
    if os.name == "nt":
        from ctypes import windll  # pylint: disable=import-outside-toplevel

        bitfield = windll.kernel32.GetLogicalDrives()
        masks = [(1 << n, chr(ord("A") + n)) for n in range(ord("Z") - ord("A") + 1)]
        return [
            {"path_str": drive + ":/", "system_path_str": drive + ":\\"}
            for mask, drive in masks
            if bitfield & mask
        ]
    return []


def mapping_details(request, mapping_id):
    if request.method == "POST":
        mypath = MyPath(request.POST.get("path"), True)
        if mypath.is_valid_db_path_str:
            db.update_mapping(mapping_id, mypath.db_path_str)
        return redirect("pathtagger:mappings_list")
    return render(
        request,
        "pathtagger/mapping_details.html",
        {"mapping": get_extended_dataset([db.get_mapping(mapping_id)]).pop()},
    )


def add_mapping(request):
    mypath = MyPath(request.POST.get("path"), True)
    if mypath.is_valid_db_path_str and not db.get_mapping_by_path(mypath.db_path_str):
        db.insert_mapping(mypath.db_path_str, [])
    return redirect("pathtagger:mappings_list")


def parse_tag_ids_to_append_and_remove(querydict):
    tag_ids_to_append, tag_ids_to_remove = [], []
    for key, action in querydict.items():
        if key.startswith("tag_"):
            if action == "append":
                tag_ids_to_append.append(int(key.strip("tag_")))
            elif action == "remove":
                tag_ids_to_remove.append(int(key.strip("tag_")))
            # ignore tags that are to be simultaneously appended and removed
            # i.e. set(action) == {"append", "remove"}
    return tag_ids_to_append, tag_ids_to_remove


def create_tags(new_tag_names):
    tag_ids = []
    if new_tag_names:
        for raw_name in new_tag_names.strip(",").split(","):
            name = raw_name.strip()
            if name and not db.get_tag_by_name(name):
                tag_ids.append(db.insert_tag(name, params.DEFAULT_TAG_COLOR))
    return tag_ids


def edit_mappings(request):
    if request.POST.get("action_delete"):
        return delete_mappings(request)
    if request.POST.get("action_edit_tags"):
        if mapping_ids := [
            int(mapping_id) for mapping_id in request.POST.getlist("mapping_id")
        ]:
            tag_ids_to_append, tag_ids_to_remove = parse_tag_ids_to_append_and_remove(
                request.POST
            )
            tag_ids_to_append.extend(create_tags(request.POST.get("new_tag_names")))
            db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
            db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    return redirect("pathtagger:mappings_list")


def delete_mappings(request):
    db.delete_mappings(
        [int(mapping_id) for mapping_id in request.POST.getlist("mapping_id")]
    )
    return redirect("pathtagger:mappings_list")


def mappings_list(request):
    tag_ids_to_include = [
        int(tag_id) for tag_id in request.GET.getlist("tag_id_include")
    ]
    tag_ids_to_exclude = [
        int(tag_id) for tag_id in request.GET.getlist("tag_id_exclude")
    ]
    path_name_like = request.GET.get("path_name_like", "")
    path_type = request.GET.get("path_type", "all")
    mappings = get_extended_dataset(
        db.get_filtered_mappings(tag_ids_to_include, tag_ids_to_exclude, path_name_like)
    )
    if path_type == "existent":
        mappings = [mapping for mapping in mappings if mapping["path_exists"]]
    elif path_type == "nonexistent":
        mappings = [mapping for mapping in mappings if not mapping["path_exists"]]
    filters = {
        "tag_ids_to_include": tag_ids_to_include,
        "tag_ids_to_exclude": tag_ids_to_exclude,
        "path_name_like": path_name_like,
        "path_type": path_type,
    }
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
    if request.method == "POST":
        if (
            (name := request.POST.get("name"))
            and not db.get_tag_by_name(name)
            and (color := request.POST.get("color", params.DEFAULT_TAG_COLOR))
        ):
            db.update_tag(tag_id, name, color)
        return redirect("pathtagger:tags_list")
    return render(
        request,
        "pathtagger/tag_details.html",
        {
            "tag": db.get_tag_by_id(tag_id),
            "mappings": get_extended_dataset(db.get_tag_mappings(tag_id)),
        },
    )


def add_tag(request):
    if (
        (name := request.POST.get("name"))
        and not db.get_tag_by_name(name)
        and (color := request.POST.get("color", params.DEFAULT_TAG_COLOR))
    ):
        db.insert_tag(name, color)
    return redirect("pathtagger:tags_list")


def delete_tags(request):
    db.delete_tags([int(tag_id) for tag_id in request.POST.getlist("tag_id")])
    return redirect("pathtagger:tags_list")


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag["occurrences"] = len(db.get_tag_mappings(tag.doc_id))
    return render(request, "pathtagger/tags_list.html", {"tags": tags})


def remove_tag_from_mappings(request, tag_id):
    db.remove_tags_from_mappings(
        [tag_id],
        [int(mapping_id) for mapping_id in request.POST.getlist("mapping_id")],
    )
    return redirect("pathtagger:tag_details", tag_id=tag_id)


def mypath_tokens(mypath: MyPath) -> List[Dict[str, str]]:
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
                    db.get_tag_by_id(int(mapping_tag_id))
                    for mapping_tag_id in mapping["tag_ids"]
                ]
                if (mapping := db.get_mapping_by_path(mypath_child.db_path_str))
                and mapping.get("tag_ids", [])
                else []
            ),
        }
        for mypath_child in mypath.get_children()
    ]


def path_details(request, abs_path_str):
    mypath = MyPath(abs_path_str, True)
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
                "path_is_favorite": bool(db.get_favorite_path(mypath.db_path_str)),
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


def edit_path_tags(request):
    if paths := request.POST.getlist("path"):
        mapping_ids = []
        for path in paths:
            if mapping := db.get_mapping_by_path(path):
                mapping_ids.append(mapping.doc_id)
            else:
                mapping_ids.append(db.insert_mapping(path, []))
        tag_ids_to_append, tag_ids_to_remove = parse_tag_ids_to_append_and_remove(
            request.POST
        )
        tag_ids_to_append.extend(create_tags(request.POST.get("new_tag_names")))
        db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
        db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    return redirect(
        "pathtagger:path_details", path_str=request.POST.get("current_path")
    )


def toggle_favorite_path(request):
    mypath = MyPath(request.POST.get("path"), True)
    if mypath.is_valid_db_path_str:
        if db.get_favorite_path(mypath.db_path_str):
            db.delete_favorite_path(mypath.db_path_str)
            is_favorite = False
        else:
            db.insert_favorite_path(mypath.db_path_str)
            is_favorite = True
        if request.is_ajax():
            return JsonResponse({"status": "ok", "is_favorite": str(bool(is_favorite))})
    elif request.is_ajax():
        return JsonResponse({"status": "nok"})
    return redirect("pathtagger:homepage")


def root_path_redirect(_):
    root_path = MyPath(
        params.BASE_PATH if params.BASE_PATH else Path(Path(settings.BASE_DIR).anchor),
        True,
    )
    return redirect("pathtagger:path_details", abs_path_str=root_path.abs_path_str)


def homepage(request):
    return render(
        request,
        "pathtagger/homepage.html",
        {"favorite_paths": get_extended_dataset(db.get_all_favorite_paths())},
    )
