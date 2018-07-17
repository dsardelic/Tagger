from django.shortcuts import render, redirect

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


def delete_tags(request):
    pass


def tags_list(request):
    pass


def remove_tag_from_mappings(request):
    pass


def path_details(request):
    pass


def edit_path_tags(request):
    pass


def toggle_favorite_path(request):
    pass


def root_path_redirect(request):
    pass


def homepage(request):
    return render(
        request,
        'pathtagger/homepage.html',
        {"favorite_paths": db.get_favorite_paths()}
    )
