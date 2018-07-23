from django.shortcuts import render, redirect
from django.http import JsonResponse
from pathlib import Path

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
                'mapping': get_extended_dataset([db.get_mapping(mapping_id)])[0],
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
    if path and not db.get_mapping_by_path(path):
        mapping_id = db.insert_mapping(path, [])
        return redirect('pathtagger:mapping_details', mapping_id=mapping_id)
    return redirect('pathtagger:mappings_list')


def edit_mappings_tags(request):
    pass


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
    path_type = request.GET.get('path_type', None)
    if not path_type:
        path_type = 'all'
    mappings = get_extended_dataset(
        db.get_filtered_mappings(
            tag_ids_to_include, tag_ids_to_exclude, path_name_like
        )
    )
    filters = {}
    filters['tag_ids_to_include'] = tag_ids_to_include
    filters['tag_ids_to_exclude'] = tag_ids_to_exclude
    filters['path_name_like'] = path_name_like
    filters['path_type'] = path_type
    return render(
        request,
        'pathtagger/mappings_list.html',
        {
            'mappings': get_extended_dataset(mappings),
            'filters': filters,
            'tags': db.get_all_tags()
        }
    )


def edit_mapping_tags(request):
    pass


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
    name, color = request.POST.get('name', ''), request.POST.get('color', '')
    if name and color and not db.get_tag_by_name(name):
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
    pass


def edit_path_tags(request):
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
    pass


def homepage(request):
    return render(
        request,
        'pathtagger/homepage.html',
        {'favorite_paths': get_extended_dataset(db.get_all_favorite_paths())}
    )
