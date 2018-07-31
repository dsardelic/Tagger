from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render, redirect

from Tagger import ini_parser

from . import db_operations as db


def get_extended_dataset(dataset):
    for element in dataset:
        path = Path(element['path'])
        element['path_exists'] = path.exists()
        element['path_is_folder'] = path.is_dir()
        if element.get('tag_ids', []):
            element['tags'] = [
                db.get_tag_by_id(int(mapping_tag_id))
                for mapping_tag_id in element['tag_ids']
            ]
    return dataset


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
        mappings = [mapping for mapping in mappings if not mapping['path_exists']]
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
    # TODO: complete me
    pass


def edit_path_tags(request):
    # TODO: complete me
    pass


def toggle_favorite_path(request):
    path = request.POST.get('path', '')
    if path:
        favorite_path = db.get_favorite_path(path)
        if favorite_path:
            ids = db.delete_favorite_path(path)
        else:
            ids = [db.insert_favorite_path(path)]
        if request.is_ajax():
            return JsonResponse({'status': 'ok', 'ids': ids})
        else:
            return redirect('pathtagger:homepage')
    else:
        return JsonResponse({'status': 'nok', 'ids': ids})


def root_path_redirect(request):
    # TODO: complete me
    pass


def homepage(request):
    return render(
        request,
        'pathtagger/homepage.html',
        {'favorite_paths': get_extended_dataset(db.get_all_favorite_paths())}
    )
