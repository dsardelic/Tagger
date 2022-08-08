from django.urls import path

from . import views

app_name = "pathtagger"  # pylint: disable=C0103

urlpatterns = [  # pylint: disable=C0103
    path("mappings/<int:mapping_id>/", views.mapping_details, name="mapping_details"),
    path("mappings/add/", views.add_mapping, name="add_mapping"),
    path("mappings/edit/", views.edit_mappings, name="edit_mappings"),
    path("mappings/delete/", views.delete_mappings, name="delete_mappings"),
    path("mappings/", views.mappings_list, name="mappings_list"),
    path("tags/<int:tag_id>/", views.tag_details, name="tag_details"),
    path("tags/add/", views.add_tag, name="add_tag"),
    path("tags/delete/", views.delete_tags, name="delete_tags"),
    path("tags/", views.tags_list, name="tags_list"),
    path(
        "tag/removefrommappings/",
        views.remove_tag_from_mappings,
        name="remove_tag_from_mappings",
    ),
    path("path/<path:path_str>", views.path_details, name="path_details"),
    path("pathtagsedit/", views.edit_path_tags, name="edit_path_tags"),
    path(
        "togglefavoritepath/", views.toggle_favorite_path, name="toggle_favorite_path"
    ),
    path("rootpathredirect/", views.root_path_redirect, name="root_path_redirect"),
    path("", views.homepage, name="homepage"),
]
