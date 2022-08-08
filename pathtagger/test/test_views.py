import os
import tempfile
import unittest.mock
from pathlib import PosixPath, WindowsPath
from unittest.mock import sentinel

from bs4 import BeautifulSoup
from django.apps import apps
from django.http.response import HttpResponse
from django.test import SimpleTestCase
from django.test.client import Client
from django.urls.base import reverse
from parameterized import parameterized

from pathtagger import db_operations, urls, views
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


class Test(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self.db_tmp_file = tempfile.NamedTemporaryFile(mode="wt", delete=False)
        with open(
            apps.get_app_config(urls.app_name).path
            + "/test/resources/TestTaggerDB.json",
            "rt",
        ) as ref_db_file:
            self.db_tmp_file.write(ref_db_file.read())
        self.db_tmp_file.close()
        db_operations.DB = db_operations.load_db(self.db_tmp_file.name)
        params.DB_PATH = self.db_tmp_file.name
        params.BASE_PATH = None
        params.DEFAULT_TAG_COLOR = "#d9d9d9"

    def tearDown(self):
        os.remove(self.db_tmp_file.name)

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test__is_allowed_path_posix(self):
        test_data = [
            ("no base path", None, "/home/dino/Videos", True),
            ("base path parent", "/home/dino", "/home/dino/Videos", True),
            ("is base path", "/home/dino/Videos", "/home/dino/Videos", True),
            (
                "base path descendant",
                "/home/dino/Videos/movies",
                "/home/dino/Videos",
                False,
            ),
            ("no relation with base path", "/opt", "/home/dino/Videos", False),
        ]
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._is_allowed_path(PosixPath(path_str)), exp_rval)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test__is_allowed_path_nt(self):
        test_data = [
            ("no base path", None, r"C:\tools\eclipse", True),
            ("base path parent", r"C:\tools", r"C:\tools\eclipse", True,),
            ("is base path", r"C:\tools\eclipse", r"C:\tools\eclipse", True,),
            (
                "base path descendant",
                r"C:\tools\eclipse\plugins",
                r"C:\tools\eclipse",
                False,
            ),
            ("no relation with base path", r"C:\Windows", r"C:\tools\eclipse", False,),
        ]
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    WindowsPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(
                    views._is_allowed_path(WindowsPath(path_str)), exp_rval
                )

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test__get_db_path_str_posix(self):
        test_data = [
            ("no base path", None, "/home/dino/Videos", "/home/dino/Videos"),
            ("no relation with base path", "/opt", "/home/dino/Videos", None),
            (
                "base path parent",
                "/home/dino/Videos/movies",
                "/home/dino/Videos",
                None,
            ),
            ("is base path", "/home/dino/Videos", "/home/dino/Videos", "/"),
            ("base path descendant", "/home/dino", "/home/dino/Videos", "Videos"),
        ]
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._get_db_path_str(PosixPath(path_str)), exp_rval)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test__get_db_path_str_nt(self):
        test_data = [
            ("no base path", None, r"C:\tools\eclipse", "C:/tools/eclipse"),
            ("no relation with base path", r"C:\Windows", r"C:\tools\eclipse", None),
            (
                "base path parent",
                r"C:\tools\eclipse\plugins",
                r"C:\tools\eclipse",
                None,
            ),
            (
                "is base path",
                r"C:\tools\eclipse",
                r"C:\tools\eclipse",
                "C:/tools/eclipse",
            ),
            ("base path descendant", r"C:\tools", r"C:\tools\eclipse", "eclipse"),
        ]
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    WindowsPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(
                    views._get_db_path_str(WindowsPath(path_str)), exp_rval
                )

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test__join_with_base_path_posix(self):
        test_data = [
            ("no base path", None, PosixPath("Joinee"), PosixPath("Joinee")),
            (
                "base path and root joinee",
                "/home/dino",
                PosixPath("/"),
                PosixPath("/home/dino"),
            ),
            (
                "base path and non-root joinee",
                "/home/dino",
                PosixPath("Joinee"),
                PosixPath("/home/dino/Joinee"),
            ),
        ]
        for i, (_, base_path_str, path, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._join_with_base_path(path), exp_rval)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test__join_with_base_path_nt(self):
        test_data = [
            ("no base path", None, WindowsPath("Joinee"), WindowsPath("Joinee")),
            (
                "base path and root joinee",
                r"C:\tools",
                WindowsPath("/"),
                WindowsPath(r"C:\tools"),
            ),
            (
                "base path and non-root joinee",
                r"C:\tools",
                WindowsPath("Joinee"),
                WindowsPath(r"C:\tools\Joinee"),
            ),
        ]
        for i, (_, base_path_str, path, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    WindowsPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._join_with_base_path(path), exp_rval)

    def test__get_extended_dataset(self):
        docs = db_operations.get_all_mappings()
        extended_dataset = views._get_extended_dataset(docs)
        self.assertTrue(len(extended_dataset) == 5)
        self.assertTrue(
            all(
                key in doc
                for doc in docs
                for key in [
                    "path_str",
                    "system_path_str",
                    "db_path_str",
                    "path_exists",
                    "path_is_dir",
                ]
            )
        )
        self.assertEquals(
            ["tags" in doc for doc in docs], [True, True, True, True, True]
        )

    def test__get_drive_root_dirs(self):
        if os.name == "nt":
            self.assertIn(
                {"path_str": "C:/", "system_path_str": "C:\\"},
                views._get_drive_root_dirs(),
            )
        else:
            self.assertEqual(views._get_drive_root_dirs(), [])

    def test_mapping_details_get(self):
        response = self.client.get(
            reverse(f"{urls.app_name}:mapping_details", kwargs={"mapping_id": 4})
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

    @parameterized.expand([("allowed", True), ("not allowed", False)])
    @unittest.mock.patch.object(views.db, "update_mapping")
    @unittest.mock.patch.object(views, "_is_allowed_path")
    @unittest.mock.patch.object(views, "_get_db_path_str")
    def test_mapping_details_post(
        self,
        _,
        is_allowed_path,
        mock__get_db_path_str,
        mock__is_allowed_path,
        mock_update_mapping,
    ):
        mapping_id = int()
        new_path_str = sentinel.new_path_str
        mock__is_allowed_path.return_value = is_allowed_path
        mock__get_db_path_str.return_value = sentinel._get_db_path_str_rval
        response = self.client.post(
            reverse(
                f"{urls.app_name}:mapping_details", kwargs={"mapping_id": mapping_id}
            ),
            {"path": new_path_str},
        )
        self.assertRedirects(response, reverse(f"{urls.app_name}:mappings_list"))
        if is_allowed_path:
            mock__get_db_path_str.assert_called()
            mock_update_mapping.assert_called_once_with(
                mapping_id, sentinel._get_db_path_str_rval
            )
        else:
            mock_update_mapping.assert_not_called()

    def test_mapping_details_other(self):
        response = self.client.delete(
            reverse(f"{urls.app_name}:mapping_details", kwargs={"mapping_id": 4})
        )
        self.assertEqual(response.status_code, 405)

    @parameterized.expand(
        [
            ("not allowed and does not exist", False, False, 0),
            ("not allowed and already exists", False, True, 0),
            ("allowed and does not exist", True, False, 1),
            ("allowed but already exists", True, True, 0),
        ]
    )
    @unittest.mock.patch.object(views.db, "get_mapping_by_path")
    @unittest.mock.patch.object(views.db, "insert_mapping")
    @unittest.mock.patch.object(views, "_get_db_path_str")
    @unittest.mock.patch.object(views, "_is_allowed_path")
    def test_add_mapping(
        self,
        _,
        is_allowed_path,
        mapping_by_path_already_exists,
        exp_new_mapping_path_count,
        mock__is_allowed_path,
        mock__get_db_path_str,
        mock_insert_mapping,
        mock_get_mapping_by_path,
    ):
        new_mapping_path = sentinel.new_mapping_path
        mock_get_mapping_by_path.return_value = mapping_by_path_already_exists
        mock__get_db_path_str.return_value = sentinel._get_db_path_str_rval
        mock__is_allowed_path.return_value = is_allowed_path
        response = self.client.post(
            reverse(f"{urls.app_name}:add_mapping"), {"path": new_mapping_path}
        )
        self.assertRedirects(response, reverse(f"{urls.app_name}:mappings_list"))
        if exp_new_mapping_path_count:
            mock__get_db_path_str.assert_called()
            mock_insert_mapping.assert_called_once_with(
                sentinel._get_db_path_str_rval, []
            )
        else:
            mock_insert_mapping.assert_not_called()

    def test_parse_tag_ids_to_append_and_remove(self):
        querydict = {
            "tag_3": "remove",
            "tag_4": "invalid action",
            "tag_2": "append",
            "foo": "bar",
            "tag_1": "append",
        }
        tag_ids_to_append, tag_ids_to_remove = views.parse_tag_ids_to_append_and_remove(
            querydict
        )
        self.assertEqual(sorted(tag_ids_to_append), [1, 2])
        self.assertEqual(sorted(tag_ids_to_remove), [3])

    @parameterized.expand(
        [
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
        new_tag_names = new_tag_names
        self.assertEqual(len(views.create_tags(new_tag_names)), exp_new_tags_count)

    def test_edit_mappings_action_delete(self):
        with unittest.mock.patch.object(
            views, "delete_mappings", return_value=HttpResponse()
        ) as mock_delete_mappings:
            _ = self.client.post(
                reverse(f"{urls.app_name}:edit_mappings"), {"action_delete": "foo"}
            )
        mock_delete_mappings.assert_called_once()

    @parameterized.expand(
        [
            ("some mappings selected", ["3", "4", "5"], 5, 13, 5),
            ("no mappings selected", [], 5, 8, 3),
        ]
    )
    def test_edit_mappings_action_edit_tags(
        self,
        _,
        mapping_ids,
        exp_mappings_count,
        exp_total_applied_tags_count,
        exp_all_tags_count,
    ):
        response = self.client.post(
            reverse(f"{urls.app_name}:edit_mappings"),
            {
                "action_edit_tags": "foo",
                "mapping_id": mapping_ids,
                "tag_3": "append",
                "tag_2": "remove",
                "new_tag_names": "completely new tag 1, completely new tag 2",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mappings_list.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(_row_count(soup, "mappings_table_body"), exp_mappings_count)
        self.assertEqual(
            len(soup.select_one("#mappings_table_body").select(".tag")),
            exp_total_applied_tags_count,
        )
        self.assertEqual(
            len(soup.select_one("#tags_table_body").select(".tag")), exp_all_tags_count
        )

    def test_delete_mappings(self):
        response = self.client.post(
            reverse(f"{urls.app_name}:delete_mappings"), {"mapping_id": ["1", "3", "5"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mappings_list.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(_row_count(soup, "mappings_table_body"), 2)
        self.assertEqual(len(soup.select_one("#mappings_table_body").select(".tag")), 4)
        self.assertEqual(len(soup.select_one("#tags_table_body").select(".tag")), 3)

    @parameterized.expand([("all", 5, 8), ("existent", 4, 6), ("nonexistent", 1, 2)])
    def test_mappings_list(
        self, path_type, exp_mappings_table_row_count, exp_tag_count
    ):
        response = self.client.get(
            reverse(f"{urls.app_name}:mappings_list"), {"path_type": path_type}
        )
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
        response = self.client.get(reverse(f"{urls.app_name}:mappings_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "mappings_table_body"),
            -1,
        )
        self.assertEqual(len(soup.select_one("#tags_table_body").select(".tag")), 3)

    def test_tag_details_get(self):
        response = self.client.get(
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": 2})
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

    def test_tag_details_post(self):
        new_name, new_color = "New tag name", "#000001"
        response = self.client.post(
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": 2}),
            {"name": new_name, "color": new_color},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/tag_details.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")
        self.assertEqual(
            soup.select_one("input[form=TagEditForm][name=name]")["value"], new_name
        )
        self.assertEqual(
            soup.select_one("input[form=TagEditForm][name=color]")["value"], new_color
        )

    def test_tag_details_other(self):
        response = self.client.put(
            reverse(f"{urls.app_name}:tag_details", kwargs={"tag_id": 2})
        )
        self.assertEqual(response.status_code, 405)

    @parameterized.expand(
        [
            ("name and color", "New tag", "#AB3456", 4),
            ("empty name", "", "#AB3456", 3),
            ("empty color", "New tag", "", 4),
            ("name already exists", "Videos", "#AB3456", 3),
        ]
    )
    def test_add_tag(self, _, name, color, exp_tags_table_row_count):
        response = self.client.post(
            reverse(f"{urls.app_name}:add_tag"), {"name": name, "color": color}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/tags_list.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "tags_table_body"),
            exp_tags_table_row_count,
        )

    @parameterized.expand(
        [
            ("existing single", {"tag_id": ["3"]}, 2),
            ("existing many", {"tag_id": ["3", "2"]}, 1),
            ("none", {"tag_id": []}, 3),
            ("all", {"tag_id": ["1", "2", "3"]}, -1),
        ]
    )
    def test_delete_tags(self, _, post_data, exp_tags_table_row_count):
        response = self.client.post(reverse(f"{urls.app_name}:delete_tags"), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/tags_list.html"
            in [template.name for template in response.templates]
        )
        self.assertEqual(
            _row_count(BeautifulSoup(response.content, "lxml"), "tags_table_body"),
            exp_tags_table_row_count,
        )

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

    def test_remove_tag_from_mappings(self):
        ...

    def test_path_details(self):
        ...

    def test_edit_path_tags(self):
        ...

    def test_toggle_favorite_path_post(self):
        ...

    def test_toggle_favorite_path_other(self):
        response = self.client.patch(reverse(f"{urls.app_name}:toggle_favorite_path"))
        self.assertEqual(response.status_code, 405)

    @parameterized.expand([("no base path", None), ("with base path", "/home/dino")])
    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_root_path_redirect_posix(self, _, base_path):
        params.BASE_PATH = base_path
        response = self.client.get(reverse(f"{urls.app_name}:root_path_redirect"))
        self.assertRedirects(
            response,
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={"path_str": base_path if base_path else "/"},
            ),
        )

    @parameterized.expand([("no base path", None), ("with base path", r"C:\tools")])
    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_root_path_redirect_nt(self, _, base_path):
        params.BASE_PATH = base_path
        response = self.client.get(reverse(f"{urls.app_name}:root_path_redirect"))
        self.assertRedirects(
            response,
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={"path_str": base_path if base_path else settings.BASE_DIR[:3]},
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
