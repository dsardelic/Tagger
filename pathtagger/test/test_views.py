import os
import unittest.mock
from ast import literal_eval
from pathlib import Path
from tempfile import NamedTemporaryFile

from bs4 import BeautifulSoup
from django.apps import apps
from django.http.response import HttpResponse
from django.test import SimpleTestCase
from django.test.client import Client
from django.urls.base import reverse
from parameterized import parameterized

from pathtagger import db_operations, urls, views
from pathtagger.views import MyPath
from Tagger import params, settings


def _row_count(soup, element_id):
    elements = soup.select(f"#{element_id}")
    if not elements:
        # element does not exist
        # if it should exist, it may 'contain' 0 rows
        return -1
    if len(elements) > 1:
        raise Exception("Two or more elements have the same id")
    return len(soup.select_one(f"#{element_id}").find_all("tr"))


# pylint: disable=R0913,R0904
class Test(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        test_db_path_str = (
            apps.get_app_config(urls.app_name).path + "/test/resources/TaggerDB.json"
        )
        with NamedTemporaryFile(mode="wt", delete=False) as db_tmp_file:
            with open(test_db_path_str, "rt", encoding="utf-8") as ref_db_file:
                self.db_tmp_file_name = db_tmp_file.name
                db_tmp_file.write(ref_db_file.read())
        db_operations.DB = db_operations.load_db(self.db_tmp_file_name)
        params.DB_PATH = self.db_tmp_file_name
        params.BASE_PATH = None
        params.DEFAULT_TAG_COLOR = "#d9d9d9"

    def tearDown(self):
        os.remove(self.db_tmp_file_name)

    def test_get_extended_dataset(self):
        docs = db_operations.get_all_mappings()
        extended_dataset = views.get_extended_dataset(docs)
        self.assertTrue(len(extended_dataset) == 5)
        self.assertTrue(
            all(
                key in doc
                for doc in docs
                for key in [
                    "abs_path_str",
                    "system_path_str",
                    "db_path_str",
                    "path_exists",
                    "path_is_dir",
                ]
            )
        )
        self.assertEqual(
            ["tags" in doc for doc in docs], [True, True, True, True, True]
        )

    def test_get_drive_root_dirs(self):
        if os.name == "nt":
            self.assertIn(
                {"path_str": "C:/", "system_path_str": "C:\\"},
                views.get_drive_root_dirs(),
            )
        else:
            self.assertEqual(views.get_drive_root_dirs(), [])

    def test_mapping_details_get(self):
        mapping_id = 4
        response = self.client.get(
            reverse(
                f"{urls.app_name}:mapping_details", kwargs={"mapping_id": mapping_id}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mapping_details.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(
                BeautifulSoup(response.content, "lxml"), "mapping_tags_table_body"
            ),
            3,
        )

    @parameterized.expand(
        [
            ("path missing", None, False),
            ("path empty", "", False),
            ("dot path", ".", False),
            ("path non-empty", "/new_db_path_str", True),
        ]
    )
    @unittest.mock.patch.object(views.db, "update_mapping")
    def test_mapping_details_post(
        self, _, new_db_path_str, exp_update_mapping_called, mock_update_mapping
    ):
        mapping_id = 1
        data = {"path": new_db_path_str} if new_db_path_str else {}
        response = self.client.post(
            reverse(
                f"{urls.app_name}:mapping_details",
                kwargs={"mapping_id": mapping_id},
            ),
            {**data},
            follow=True,
        )
        self.assertRedirects(response, reverse(f"{urls.app_name}:mappings_list"))
        if exp_update_mapping_called:
            mock_update_mapping.assert_called_once_with(mapping_id, new_db_path_str)
        else:
            mock_update_mapping.assert_not_called()

    @parameterized.expand(
        [
            ("path missing", None, False),
            ("path empty", "", False),
            ("dot path", ".", False),
            ("mapping does not exist yet", "/home/dino/Pictures", True),
            ("mapping already exists", "/home/dino/Downloads", False),
        ]
    )
    @unittest.mock.patch.object(views.db, "insert_mapping")
    def test_add_mapping(
        self,
        _,
        db_path_str,
        exp_insert_mapping_called,
        mock_insert_mapping,
    ):
        data = {"path": db_path_str} if db_path_str else {}
        response = self.client.post(
            reverse(f"{urls.app_name}:add_mapping"), {**data}, follow=True
        )
        self.assertRedirects(response, reverse(f"{urls.app_name}:mappings_list"))
        if exp_insert_mapping_called:
            mock_insert_mapping.assert_called_once_with(db_path_str, [])
        else:
            mock_insert_mapping.assert_not_called()

    def test_parse_tag_ids_to_append_and_remove(self):
        data = {
            "tag_3": "remove",
            "tag_4": "invalid action",
            "tag_2": "append",
            "foo": "bar",
            "tag_1": "append",
        }
        tag_ids_to_append, tag_ids_to_remove = views.parse_tag_ids_to_append_and_remove(
            data
        )
        self.assertEqual(sorted(tag_ids_to_append), [1, 2])
        self.assertEqual(sorted(tag_ids_to_remove), [3])

    @parameterized.expand(
        [
            ("None", None, 0),
            ("empty", "", 0),
            ("single comma", ",", 0),
            ("regular one", "new tag 1", 1),
            ("regular one, messy", "   new tag 1 ", 1),
            ("regular one, messy, trailing comma", "   new tag 1  , ", 1),
            ("regular two, messy", "new tag 1,new tag 2", 2),
            ("regular two, messy", "  new tag 1,new tag 2    ", 2),
            ("regular two, messy, leading comma", "  ,   new tag 1, new tag 2    ", 2),
        ]
    )
    def test_create_tags(self, _, new_tag_names, exp_new_tags_count):
        self.assertEqual(len(views.create_tags(new_tag_names)), exp_new_tags_count)

    def test_edit_mappings_action_delete(self):
        with unittest.mock.patch.object(
            views, "delete_mappings", return_value=HttpResponse()
        ) as mock_delete_mappings:
            _ = self.client.post(
                reverse(f"{urls.app_name}:edit_mappings"), {"action_delete": "_"}
            )
        mock_delete_mappings.assert_called_once()

    @parameterized.expand(
        [
            ("None mappings", None, [], None, {}),
            ("no new tag names", ["3", "4", "5"], [3, 4, 5], None, {}),
            (
                "tags to create",
                ["3", "4", "5"],
                [3, 4, 5],
                "completely new tag 1, completely new tag 2",
                {},
            ),
            (
                "tags to add and remove",
                ["3", "4", "5"],
                [3, 4, 5],
                None,
                {"tag_3": "append", "tag_2": "remove"},
            ),
            (
                "tags to create, add and remove",
                ["3", "4", "5"],
                [3, 4, 5],
                "completely new tag 1, completely new tag 2",
                {"tag_3": "append", "tag_2": "remove"},
            ),
        ]
    )
    def test_edit_mappings_action_edit_tags(
        self, _, mapping_ids, exp_mapping_ids, new_tag_names, tags_to_append_and_remove
    ):
        data = {
            "action_edit_tags": "foo",
            "mapping_id": mapping_ids,
            "new_tag_names": new_tag_names,
            "tag_3": "append",
            "tag_2": "remove",
        }
        data.update(tags_to_append_and_remove)
        for param in ["mapping_id", "new_tag_names"]:
            if data[param] is None:
                del data[param]
        response = self.client.post(
            reverse(f"{urls.app_name}:edit_mappings"), {**data}, follow=True
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:mappings_list"),
            fetch_redirect_response=True,
        )

    @parameterized.expand(
        [
            ("None", None, [], True),
            ("empty", [], [], True),
            ("non-empty", ["1", "3", "5"], [1, 3, 5], True),
        ]
    )
    @unittest.mock.patch.object(views.db, "delete_mappings")
    def test_delete_mappings(
        self,
        _,
        mapping_ids,
        exp_mapping_ids,
        exp_delete_mappings_called,
        mock_delete_mappings,
    ):
        data = {"mapping_id": mapping_ids} if mapping_ids else {}
        response = self.client.post(
            reverse(f"{urls.app_name}:delete_mappings"), {**data}, follow=True
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:mappings_list"),
            fetch_redirect_response=True,
        )
        if exp_delete_mappings_called:
            mock_delete_mappings.assert_called_once_with(exp_mapping_ids)
        else:
            mock_delete_mappings.assert_not_called()

    @parameterized.expand(
        [(None, 5, 8), ("all", 5, 8), ("existent", 4, 6), ("nonexistent", 1, 2)]
    )
    def test_mappings_list(
        self, path_type, exp_mappings_table_row_count, exp_tag_count
    ):
        data = {"path_type": path_type} if path_type else {}
        response = self.client.get(reverse(f"{urls.app_name}:mappings_list"), {**data})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mappings_list.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(
            _row_count(soup, "mappings_table_body"), exp_mappings_table_row_count
        )
        self.assertEqual(
            len(soup.select_one("#mappings_table_body").select(".tag")), exp_tag_count
        )
        self.assertEqual(len(soup.select_one("#tags_table_body").select(".tag")), 3)

        db_operations.DB.purge_table("_default")
        response = self.client.get(reverse(f"{urls.app_name}:mappings_list"), {**data})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "mappings_table_body"),
            -1,
        )
        self.assertEqual(len(soup.select_one("#tags_table_body").select(".tag")), 3)

    def test_tag_details_get(self):
        tag_id = 2
        response = self.client.get(
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": tag_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/tag_details.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "mappings_table_body"),
            3,
        )

    @parameterized.expand(
        [
            ("no name", None, "#AB3456", "#AB3456", False),
            ("empty name", "", "#AB3456", "#AB3456", False),
            ("name already exists", "Videos", "#AB3456", "#AB3456", False),
            ("no color", "New tag name", None, params.DEFAULT_TAG_COLOR, True),
            ("empty color", "New tag name", "", "", False),
            ("valid name and color", "New tag name", "#AB3456", "#AB3456", True),
        ]
    )
    @unittest.mock.patch.object(views.db, "update_tag")
    def test_tag_details_post(
        self, _, name, color, exp_color, exp_update_tag_called, mock_update_tag
    ):
        tag_id = 2
        data = {"name": name, "color": color}
        for param in ["name", "color"]:
            if data[param] is None:
                del data[param]
        response = self.client.post(
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": tag_id}),
            {**data},
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:tags_list"),
            fetch_redirect_response=True,
        )
        if exp_update_tag_called:
            mock_update_tag.assert_called_once_with(tag_id, name, exp_color)
        else:
            mock_update_tag.assert_not_called()

    @parameterized.expand(
        [
            ("no name", None, "#AB3456", "#AB3456", False),
            ("empty name", "", "#AB3456", "#AB3456", False),
            ("name already exists", "Videos", "#AB3456", "#AB3456", False),
            ("no color", "New tag name", None, params.DEFAULT_TAG_COLOR, True),
            ("empty color", "New tag name", "", "", False),
            ("valid name and color", "New tag name", "#AB3456", "#AB3456", True),
        ]
    )
    @unittest.mock.patch.object(views.db, "insert_tag")
    def test_add_tag(
        self, _, name, color, exp_color, exp_insert_tag_called, mock_insert_tag
    ):
        data = {"name": name, "color": color}
        for param in ["name", "color"]:
            if data[param] is None:
                del data[param]
        response = self.client.post(
            reverse(f"{urls.app_name}:add_tag"), {**data}, follow=True
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:tags_list"),
            fetch_redirect_response=True,
        )
        if exp_insert_tag_called:
            mock_insert_tag.assert_called_once_with(name, exp_color)
        else:
            mock_insert_tag.assert_not_called()

    @parameterized.expand(
        [
            ("None", None, [], True),
            ("empty", [], [], True),
            ("non-empty", ["3", "2"], [3, 2], True),
        ]
    )
    @unittest.mock.patch.object(views.db, "delete_tags")
    def test_delete_tags(
        self, _, tag_ids, exp_tag_ids, exp_delete_tags_called, mock_delete_tags
    ):
        data = {"tag_id": tag_ids} if tag_ids else {}
        response = self.client.post(
            reverse(f"{urls.app_name}:delete_tags"), {**data}, follow=True
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:tags_list"),
            fetch_redirect_response=True,
        )
        if exp_delete_tags_called:
            mock_delete_tags.assert_called_once_with(exp_tag_ids)
        else:
            mock_delete_tags.assert_not_called()

    def test_tags_list(self):
        response = self.client.get(reverse(f"{urls.app_name}:tags_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/tags_list.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "tags_table_body"), 3
        )

        db_operations.DB.purge_tables()
        response = self.client.get(reverse(f"{urls.app_name}:tags_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "tags_table_body"), -1
        )

    @parameterized.expand(
        [
            ("None", None, []),
            ("empty list", [], []),
            ("non-empty list", ["1", "2", "3"], [1, 2, 3]),
        ]
    )
    @unittest.mock.patch.object(views.db, "remove_tags_from_mappings")
    def test_remove_tag_from_mappings(
        self, _, mapping_ids, exp_mapping_ids, mock_remove_tags_from_mappings
    ):
        tag_id = int()
        data = {"mapping_id": mapping_ids} if mapping_ids else {}
        response = self.client.post(
            reverse(
                f"{urls.app_name}:remove_tag_from_mappings", kwargs={"tag_id": tag_id}
            ),
            {**data},
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": tag_id}),
            fetch_redirect_response=True,
        )
        mock_remove_tags_from_mappings.assert_called_once_with(
            [tag_id], exp_mapping_ids
        )

    def test_path_details(self):
        ...

    def test_edit_path_tags(self):
        ...

    @parameterized.expand(
        [
            ("no path, non-ajax", None, False, False, None, None),
            ("no path, ajax", None, True, None, False, {"status": "nok"}),
            ("empty path, non-ajax", "", False, None, False, None),
            ("empty path, ajax", "", True, None, False, {"status": "nok"}),
            ("dot path, non-ajax", ".", False, None, False, None),
            ("dot path, ajax", ".", True, None, False, {"status": "nok"}),
            (
                "non-empty path, non-ajax, currently not favorite",
                "/home/dino",
                False,
                False,
                True,
                None,
            ),
            (
                "non-empty path, non-ajax, currently favorite",
                "/home/dino",
                False,
                True,
                True,
                None,
            ),
            (
                "non-empty path, ajax, currently not favorite",
                "/home/dino",
                True,
                False,
                True,
                {"status": "ok", "is_favorite": "True"},
            ),
            (
                "non-empty path, ajax, currently favorite",
                "/home/dino",
                True,
                True,
                True,
                {"status": "ok", "is_favorite": "False"},
            ),
        ]
    )
    @unittest.mock.patch.object(views.db, "delete_favorite_path")
    @unittest.mock.patch.object(views.db, "insert_favorite_path")
    @unittest.mock.patch.object(views.db, "get_favorite_path")
    def test_toggle_favorite_path(
        self,
        _,
        abs_path_str,
        is_ajax_call,
        prev_is_favorite,
        exp_insert_or_delete_called,
        exp_json_response_dict,
        mock_get_favorite_path,
        mock_insert_favorite_path,
        mock_delete_favorite_path,
    ):
        data = {"path": abs_path_str} if abs_path_str else {}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if is_ajax_call else {}
        mock_get_favorite_path.return_value = prev_is_favorite
        response = self.client.post(
            reverse(f"{urls.app_name}:toggle_favorite_path"),
            {**data},
            follow=True,
            **headers,
        )
        if exp_insert_or_delete_called:
            if prev_is_favorite:
                mock_insert_favorite_path.assert_not_called()
                mock_delete_favorite_path.assert_called_once()
            else:
                mock_insert_favorite_path.assert_called_once()
                mock_delete_favorite_path.assert_not_called()
        if is_ajax_call:
            self.assertEqual(
                literal_eval(response.content.decode("utf-8")), exp_json_response_dict
            )
        else:
            self.assertRedirects(
                response,
                reverse(f"{urls.app_name}:homepage"),
                fetch_redirect_response=True,
            )

    @parameterized.expand(
        [
            ("no base path", None),
            ("with existent base path", Path("/etc")),
            ("with nonexistent base path", Path("/fictitious_folder")),
        ]
    )
    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_root_path_redirect_posix(self, _, base_path):
        params.BASE_PATH = base_path
        response = self.client.get(reverse(f"{urls.app_name}:root_path_redirect"))
        self.assertRedirects(
            response,
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={
                    "abs_path_str": MyPath(base_path, True).abs_path_str
                    if base_path
                    else "/"
                },
            ),
        )

    @parameterized.expand(
        [
            ("no base path", None),
            ("with existent base path", r"C:\Windows"),
            ("with nonexistent base path", Path(r"C:\fictitious_folder")),
        ]
    )
    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_root_path_redirect_nt(self, _, base_path):
        params.BASE_PATH = base_path
        response = self.client.get(reverse(f"{urls.app_name}:root_path_redirect"))
        self.assertRedirects(
            response,
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={
                    "abs_path_str": base_path if base_path else settings.BASE_DIR[:3]
                },
            ),
        )

    def test_homepage(self):
        response = self.client.get(reverse(f"{urls.app_name}:homepage"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/homepage.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "favorites_table_body"),
            1,
        )