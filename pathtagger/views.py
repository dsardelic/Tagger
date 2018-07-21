from django.shortcuts import render, redirect
from django.http import JsonResponse
from pathlib import Path

from . import db_operations as db


def mapping_details(request):
    pass


def delete_mappings(request):
    pass


def mappings_list(request):
    pass


def add_mapping(request):
    pass


def edit_mapping_tags(request):
    pass


def tag_details(request, tag_id):
    if request.method == 'GET':
        mappings = db.get_tag_mappings(tag_id)
        for mapping in mappings:
            mapping['path_exists'] = Path(mapping['path']).exists()
            mapping['path_is_folder'] = Path(mapping['path']).is_dir()
            mapping['tags'] = [
                db.get_tag_by_id(int(mapping_tag_id))
                for mapping_tag_id in mapping['tag_ids']
            ]
        return render(
            request,
            'pathtagger/tag_details.html',
            {
                "tag": db.get_tag_by_id(tag_id),
                "mappings": db.get_tag_mappings(tag_id)
            }
        )
    elif request.method == 'POST':
        tag_id = int(request.POST.get('tag_id', '0'))
        db.update_tag(
            tag_id,
            request.POST.get('name', ''),
            request.POST.get('color', '')
        )
        return redirect('pathtagger:tag_details', tag_id=tag_id)


def add_tag(request):
    name = request.POST.get('name', '')
    color = request.POST.get('color', '')
    if name and color and not db.get_tag_by_name(name):
        db.insert_tag(name, color)
    return redirect('pathtagger:tags_list')


def delete_tags(request):
    tag_ids = request.POST.getlist('tag_id', [])
    db.delete_tags(list(map(int, tag_ids)))
    return redirect('pathtagger:tags_list')


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag['occurrences'] = len(db.get_tag_mappings(tag.doc_id))
    return render(
        request, 'pathtagger/tags_list.html', {"tags": tags}
    )


def remove_tag_from_mappings(request):
    tag_id = int(request.POST.get('tag_id', 0))
    db.remove_tags_from_mappings(
        [tag_id],
        list(map(int, request.POST.getlist('mapping_id', [])))
    )
    return redirect('pathtagger:tag_details', tag_id=tag_id)


def path_details(request):
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
    favorite_paths = db.get_all_favorite_paths()
    for favorite_path in favorite_paths:
        path = Path(favorite_path['path'])
        favorite_path['exists'] = True if path.exists() else False
        favorite_path['is_folder'] = True if path.is_dir() else False
    return render(
        request,
        'pathtagger/homepage.html',
        {"favorite_paths": favorite_paths}
    )
