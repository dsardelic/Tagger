from django.shortcuts import render, redirect
from django.http import JsonResponse

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


def tag_details(request):
    pass


def add_tag(request):
    name = request.POST.get('name', '')
    color = request.POST.get('color', '')
    if name and color and not db.get_tags(name):
        db.insert_tag(name, color)
    return redirect('pathtagger:tags_list')


def delete_tags(request):
    tag_ids = request.POST.getlist('tag_id', [])
    db.delete_tags(map(int, tag_ids))
    return redirect('pathtagger:tags_list')


def tags_list(request):
    tags = db.get_all_tags()
    for tag in tags:
        tag['occurrences'] = len(db.get_tag_mappings(tag.doc_id))
    return render(
        request,
        'pathtagger/tags_list.html',
        {"tags": tags}
    )


def remove_tag_from_mappings(request):
    pass


def path_details(request):
    pass


def edit_path_tags(request):
    pass


def toggle_favorite_path(request):
    path = request.POST.get('path', '')
    if path:
        favorite_paths = db.get_favorite_paths(path)
        if favorite_paths:
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
        {"favorite_paths": db.get_all_favorite_paths()}
    )
