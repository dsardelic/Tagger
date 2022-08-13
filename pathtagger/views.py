import os
from pathlib import Path, PosixPath
from typing import Optional, Union
from urllib.parse import quote

from django.http import JsonResponse
from django.shortcuts import redirect, render

from pathtagger import db_operations as db
from Tagger import params, settings


class MyPath:
    def __init__(self, raw_path: Union[Path, str], is_abs_path: bool):
        self.raw_path = raw_path
        if raw_path is None:
            self.abs_path_str = None
            return
        if is_abs_path or not params.BASE_PATH:
            self.abs_path_str = self._to_formatted_posix_path_str(raw_path)
        else:
            self.abs_path_str = params.BASE_PATH.joinpath(
                self._to_formatted_posix_path_str(raw_path).lstrip("/")
            ).as_posix()

    @property
    def db_path_str(self) -> Optional[str]:
        if self.abs_path_str is None:
            return None
        abs_path = Path(self._to_formatted_posix_path_str(self.abs_path_str))
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

    def is_taggable(self) -> bool:
        return self.abs_path_str not in (None, ".") and (
            not params.BASE_PATH
            or self.abs_path == params.BASE_PATH
            or params.BASE_PATH in self.abs_path.parents
        )

    def db_path_str_is_valid(self) -> bool:
        return self.db_path_str not in (None, ".")

    @staticmethod
    def _to_formatted_posix_path_str(path: Union[Path, str]) -> str:
        path = Path(path)
        if path.as_posix() == ".":
            return "."
        if isinstance(path, PosixPath):
            return "/" + path.as_posix().strip("/")
        return MyPath(path, True).abs_path_str


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
    if request.method == "POST":
        mypath = MyPath(request.POST.get("path"), False)
        if mypath.db_path_str_is_valid():
            db.update_mapping(mapping_id, mypath.db_path_str)
        return redirect("pathtagger:mappings_list")
    return render(
        request,
        "pathtagger/mapping_details.html",
        {"mapping": get_extended_dataset([db.get_mapping(mapping_id)]).pop()},
    )


def add_mapping(request):
    mypath = MyPath(request.POST.get("path"), True)
    if mypath.db_path_str_is_valid() and not db.get_mapping_by_path(mypath.db_path_str):
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
        for name in new_tag_names.strip(",").split(","):
            name = name.strip()
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
    if request.method == "POST":
        name = request.POST.get("name")
        color = request.POST.get("color", params.DEFAULT_TAG_COLOR)
        if name and color and not db.get_tag_by_name(name):
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
    name = request.POST.get("name")
    color = request.POST.get("color", params.DEFAULT_TAG_COLOR)
    if name and color and not db.get_tag_by_name(name):
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


def path_details(request, abs_path_str):
    path = Path(abs_path_str)
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
                    "db_path_str": MyPath(path_child, True).db_path_str,
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
            "path_str": abs_path_str,
            "system_path_str": str(path),
            "ajax_path_str": quote(abs_path_str),
            "is_root_path": path.anchor == str(path),
            "path_exists": path.exists(),
            "path_is_favorite": bool(
                db.get_favorite_path(MyPath(path, True).db_path_str)
            ),
            "path_parent": path.parent.as_posix(),
            "path_tokens": path_tokens,
            "path_children": path_children,
            "tags": db.get_all_tags(),
            "drive_root_dirs": get_drive_root_dirs(),
            "is_tagging_allowed": MyPath(path, True).is_taggable(),
        },
    )


def edit_path_tags(request):
    if paths := request.POST.getlist("path"):
        mapping_ids = []
        for path in paths:
            mapping = db.get_mapping_by_path(path)
            if mapping:
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
    if mypath.db_path_str_is_valid():
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
