import os
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render, redirect

from Tagger import ini_parser, settings

from . import db_operations as db


def get_extended_dataset(dataset):
    for element in dataset:
        path = Path(element['path'])
        element['path_exists'] = path.exists()
        element['path_is_dir'] = path.is_dir()
        if element.get('tag_ids', []):
            element['tags'] = [
                db.get_tag_by_id(int(mapping_tag_id))
                for mapping_tag_id in element['tag_ids']
            ]
    return dataset


def get_drive_root_dirs():
    if os.name == 'nt':
        from ctypes import windll
        bitfield = windll.kernel32.GetLogicalDrives()
        masks = [
            (1 << n, chr(ord('A') + n)) for n in range(ord('Z') - ord('A') + 1)
        ]
        return [
            {'path': drive + ':/', 'system_path': drive + ':\\'}
            for mask, drive in masks if bitfield & mask
        ]
    return []


def mapping_details(request, mapping_id):
    if request.method == 'GET':
        return render(
            request,
            'pathtagger/mapping_details.html',
            {
                'mapping': get_extended_dataset(
                        [db.get_mapping(mapping_id)]
                    ).pop(),
                'tags': db.get_all_tags()
            }
        )
    elif request.method == 'POST':
        path = request.POST.get('path', '')
        if path:
            db.update_mapping(mapping_id, path)
        return redirect('pathtagger:mapping_details', mapping_id=mapping_id)


def add_mapping(request):
    path = request.POST.get('path', '')
    if path:
        mapping = db.get_mapping_by_path(path)
        if not mapping:
            mapping_id = db.insert_mapping(path, [])
        else:
            mapping_id = mapping.doc_id
        return redirect('pathtagger:mapping_details', mapping_id=mapping_id)
    return redirect('pathtagger:mappings_list')


def edit_mappings(request):
    if request.POST.get('action_delete'):
        return delete_mappings(request)
    if request.POST.get('action_edit_tags'):
        mapping_ids = list(map(int, request.POST.getlist('mapping_id', [])))
        if mapping_ids:
            tag_ids_to_append, tag_ids_to_remove = [], []
            for key in request.POST:
                if key.startswith('tag_'):
                    value = request.POST.get(key, '')
                    if value == 'append':
                        tag_ids_to_append.append(int(key.strip('tag_')))
                    elif value == 'remove':
                        tag_ids_to_remove.append(int(key.strip('tag_')))
            new_tag_names_str = request.POST.get('new_tag_names', '')
            if new_tag_names_str:
                for name in new_tag_names_str.strip(',').split(','):
                    name = name.strip()
                    tag = db.get_tag_by_name(name)
                    if tag:
                        tag_ids_to_append.append(tag.doc_id)
                    else:
                        tag_ids_to_append.append(
                            db.insert_tag(name, ini_parser.DEFAULT_TAG_COLOR)
                        )
            db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
            db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
        return redirect('pathtagger:mappings_list')


def delete_mappings(request):
    db.delete_mappings(list(map(int, request.POST.getlist('mapping_id', []))))
    return redirect('pathtagger:mappings_list')


def mappings_list(request):
    tag_ids_to_include = list(
        map(int, request.GET.getlist('tag_id_include', []))
    )
    tag_ids_to_exclude = list(
        map(int, request.GET.getlist('tag_id_exclude', []))
    )
    path_name_like = request.GET.get('path_name_like', '')
    path_type = request.GET.get('path_type', 'all')
    mappings = get_extended_dataset(
        db.get_filtered_mappings(
            tag_ids_to_include, tag_ids_to_exclude, path_name_like
        )
    )
    if path_type == 'existent':
        mappings = [mapping for mapping in mappings if mapping['path_exists']]
    elif path_type == 'nonexistent':
        mappings = [
            mapping for mapping in mappings if not mapping['path_exists']
        ]
    filters = {}
    filters['tag_ids_to_include'] = tag_ids_to_include
    filters['tag_ids_to_exclude'] = tag_ids_to_exclude
    filters['path_name_like'] = path_name_like
    filters['path_type'] = path_type
    return render(
        request,
        'pathtagger/mappings_list.html',
        {
            'mappings': mappings,
            'no_mappings_at_all': len(db.get_all_mappings()) == 0,
            'filters': filters,
            'tags': db.get_all_tags()
        }
    )


def tag_details(request, tag_id):
    if request.method == 'GET':
        return render(
            request,
            'pathtagger/tag_details.html',
            {
                'tag': db.get_tag_by_id(tag_id),
                'mappings': get_extended_dataset(db.get_tag_mappings(tag_id))
            }
        )
    elif request.method == 'POST':
        tag_id = int(request.POST.get('tag_id', '0'))
        db.update_tag(
            tag_id, request.POST.get('name', ''), request.POST.get('color', '')
        )
        return redirect('pathtagger:tag_details', tag_id=tag_id)


def add_tag(request):
    name = request.POST.get('name', '')
    color = request.POST.get('color', ini_parser.DEFAULT_TAG_COLOR)
    if name and not db.get_tag_by_name(name):
        db.insert_tag(name, color)
    return redirect('pathtagger:tags_list')


def delete_tags(request):
    db.delete_tags(list(map(int, request.POST.getlist('tag_id', []))))
    return redirect('pathtagger:tags_list')


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag['occurrences'] = len(db.get_tag_mappings(tag.doc_id))
    return render(request, 'pathtagger/tags_list.html', {'tags': tags})


def remove_tag_from_mappings(request):
    tag_id = int(request.POST.get('tag_id', 0))
    db.remove_tags_from_mappings(
        [tag_id],
        list(map(int, request.POST.getlist('mapping_id', [])))
    )
    return redirect('pathtagger:tag_details', tag_id=tag_id)


def path_details(request, path):
    path_tokens, path_children = [], []
    ppath = Path(path)
    if ppath.exists():
        path_parts, path_parents = ppath.parts, list(reversed(ppath.parents))
        if ppath.is_dir():
            path_parents.append(ppath)
        for part, parent in zip(path_parts, path_parents):
            path_tokens.append({'name': part, 'path': parent.as_posix()})
        if ppath.is_dir():
            path_children = [
                {
                    'path': p.as_posix(),
                    'system_path': str(p),
                    'name': p.name,
                    'is_dir': p.is_dir()
                }
                for p in sorted(
                    list(ppath.glob('*')),
                    key=lambda x: (1 - x.is_dir(), str(x).upper())
                )
            ]
            for child in path_children:
                mapping = db.get_mapping_by_path(child['path'])
                if mapping and mapping.get('tag_ids', []):
                    child['tags'] = [
                        db.get_tag_by_id(int(mapping_tag_id))
                        for mapping_tag_id in mapping['tag_ids']
                    ]
    return render(
        request,
        'pathtagger/path_details.html',
        {
            'path': path,
            'system_path': str(ppath),
            'path_exists': ppath.exists(),
            'path_is_favorite': True if db.get_favorite_path(path) else False,
            'path_parent': ppath.parent.as_posix(),
            'path_tokens': path_tokens,
            'path_children': path_children,
            'tags': db.get_all_tags(),
            'drive_root_dir': get_drive_root_dirs()
        }
    )


def edit_path_tags(request):
    current_path = request.POST.get('current_path', '')
    paths = request.POST.getlist('path', [])
    if paths:
        mapping_ids = []
        for path in paths:
            mapping = db.get_mapping_by_path(path)
            if mapping:
                mapping_ids.append(mapping.doc_id)
            else:
                mapping_ids.append(db.insert_mapping(path, []))
        tag_ids_to_append, tag_ids_to_remove = [], []
        for key in request.POST:
            if key.startswith('tag_'):
                value = request.POST.get(key, '')
                if value == 'append':
                    tag_ids_to_append.append(int(key.strip('tag_')))
                elif value == 'remove':
                    tag_ids_to_remove.append(int(key.strip('tag_')))
        new_tag_names_str = request.POST.get('new_tag_names', '')
        if new_tag_names_str:
            for name in new_tag_names_str.strip(',').split(','):
                name = name.strip()
                tag = db.get_tag_by_name(name)
                if tag:
                    tag_ids_to_append.append(tag.doc_id)
                else:
                    tag_ids_to_append.append(
                        db.insert_tag(name, ini_parser.DEFAULT_TAG_COLOR)
                    )
        db.append_tags_to_mappings(tag_ids_to_append, mapping_ids)
        db.remove_tags_from_mappings(tag_ids_to_remove, mapping_ids)
    return redirect('pathtagger:path_details', path=current_path)


def toggle_favorite_path(request):
    path = request.POST.get('path', '')
    if path:
        favorite_path = db.get_favorite_path(path)
        if favorite_path:
            db.delete_favorite_path(path)
            is_favorite = False
        else:
            db.insert_favorite_path(path)
            is_favorite = True
        if request.is_ajax():
            return JsonResponse(
                {
                    "status": "ok",
                    "is_favorite": "true" if is_favorite else "false"
                }
            )
        else:
            return redirect('pathtagger:homepage')
    else:
        return JsonResponse({'status': 'nok'})


def root_path_redirect(request):
    return redirect(
        'pathtagger:path_details',
        path=Path(Path(settings.BASE_DIR).anchor).as_posix()
    )


def homepage(request):
    return render(
        request,
        'pathtagger/homepage.html',
        {'favorite_paths': get_extended_dataset(db.get_all_favorite_paths())}
    )
