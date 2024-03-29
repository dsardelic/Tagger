import logging
import os
import unittest.mock
from ast import literal_eval
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import call

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

# pylint: disable=too-many-public-methods
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=protected-access
# pylint: disable=expression-not-assigned
# pylint: disable=too-many-lines


def _table_row_count(soup, element_id):
    if not (elements := soup.select(f"#{element_id}")):
        # element does not exist
        # if it should exist, it may 'contain' 0 rows
        return -1
    if len(elements) > 1:
        raise KeyError("Two or more elements have the same id")
    return len(soup.select_one(f"#{element_id}").find_all("tr"))


class Test(SimpleTestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
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
        logging.disable(logging.NOTSET)

    @parameterized.expand(
        [
            ("dataset is None", None),
            ("dataset empty", []),
        ]
    )
    def test__get_extended_dataset_falsy(self, _, dataset):
        self.assertEqual(views._get_extended_dataset(dataset), dataset)

    @parameterized.expand(
        [
            ("mixed", [1, 6], [{1}, set()]),
        ]
    )
    def test__get_extended_dataset_truthy(self, _, mapping_ids, exp_tag_ids):
        exp_keys = {
            "abs_path_str",
            "system_path_str",
            "db_path_str",
            "path_exists",
            "path_is_dir",
        }
        mappings = [
            db_operations.get_mapping(mapping_id=mapping_id)
            for mapping_id in mapping_ids
        ]
        act_extended_dataset = views._get_extended_dataset(mappings)
        self.assertTrue(len(act_extended_dataset) == len(mapping_ids))
        for i, act_mapping in enumerate(act_extended_dataset):
            self.assertTrue(all(key in act_mapping.keys() for key in exp_keys))
            if exp_tag_ids[i]:
                self.assertEqual(
                    sorted(act_mapping["tags"]),
                    sorted(
                        db_operations.get_tag(tag_id=exp_tag_id)
                        for exp_tag_id in exp_tag_ids[i]
                    ),
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
            _table_row_count(
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
    @unittest.mock.patch.object(views.db, "update_mapping_path")
    def test_mapping_details_post(
        self,
        _,
        new_db_path_str,
        exp_update_mapping_path_called,
        mock_update_mapping_path,
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
        if exp_update_mapping_path_called:
            mock_update_mapping_path.assert_called_once_with(
                mapping_id, new_db_path_str
            )
        else:
            mock_update_mapping_path.assert_not_called()

    @parameterized.expand(
        [
            ("path missing", None),
            ("path empty", ""),
            ("dot path", "."),
            ("mapping does not exist yet", "/home/dino/Pictures"),
            ("mapping already exists", "/home/dino/Downloads"),
        ]
    )
    @unittest.mock.patch.object(views.db, "insert_mapping")
    def test_add_mapping(
        self,
        _,
        db_path_str,
        mock_insert_mapping,
    ):
        data = {"path": db_path_str} if db_path_str else {}
        response = self.client.post(
            reverse(f"{urls.app_name}:add_mapping"), {**data}, follow=True
        )
        self.assertRedirects(response, reverse(f"{urls.app_name}:mappings_list"))
        mock_insert_mapping.assert_called_once()

    @parameterized.expand(
        [
            ("querydict is None", None, set(), set()),
            ("querydict empty", {}, set(), set()),
            ("single invalid key", {"foo": "append"}, set(), set()),
            ("single invalid action", {"tag_2": "foo"}, set(), set()),
            ("single append", {"tag_2": "append"}, {2}, set()),
            ("single remove", {"tag_2": "remove"}, set(), {2}),
            (
                "tutti frutti",
                {
                    "tag_3": "remove",
                    "tag_4": "invalid action",
                    "tag_2": "append",
                    "foo": "append",
                    "tag_6": "bar",
                    "tag_1": "append",
                    "tag_7": {"append", "remove"},
                },
                {1, 2},
                {3},
            ),
        ]
    )
    @unittest.mock.patch.object(views, "_get_tag_ids_for_tag_names")
    def test__parse_tag_ids_to_append_and_remove(
        self,
        _,
        querydict,
        exp_tag_ids_to_append,
        exp_tag_ids_to_remove,
        mock__get_tag_ids_for_tag_names,
    ):
        mock__get_tag_ids_for_tag_names_return_value = object()
        mock__get_tag_ids_for_tag_names.return_value = {
            mock__get_tag_ids_for_tag_names_return_value
        }
        new_tag_names = object()
        (
            act_tag_ids_to_append,
            act_tag_ids_to_remove,
        ) = views._parse_tag_ids_to_append_and_remove(querydict, new_tag_names)
        self.assertTrue(act_tag_ids_to_append.issuperset(exp_tag_ids_to_append))
        self.assertIn(
            mock__get_tag_ids_for_tag_names_return_value, act_tag_ids_to_append
        )
        self.assertEqual(act_tag_ids_to_remove, exp_tag_ids_to_remove)

    @parameterized.expand(
        [
            ("None", None, set()),
            ("empty", "", set()),
            ("single comma", ",", set()),
            ("regular one", "foo", {"foo"}),
            ("regular one, messy", "   foo ", {"foo"}),
            ("regular one, messy, trailing comma", "   foo  , ", {"foo"}),
            ("regular two, messy", "foo,bar", {"foo", "bar"}),
            ("regular two, messy", "  foo,bar    ", {"foo", "bar"}),
            ("regular two, messy, leading comma", "  ,   foo, bar    ", {"foo", "bar"}),
        ]
    )
    def test__parse_tag_names_from_string(self, _, new_tag_names_str, exp_tag_names):
        self.assertEqual(
            views._parse_tag_names_from_string(new_tag_names_str), exp_tag_names
        )

    @parameterized.expand(
        [
            ("tag_names_str is None", None, set(), set()),
            ("empty tag_names_str", "", set(), set()),
            ("single comma", ",", set(), set()),
            ("single existing", "Documents", {"Documents"}, set()),
            ("single nonexistent", "Foo", set(), {"Foo"}),
            ("multiple existing", "Music,Documents", {"Music", "Documents"}, set()),
            ("multiple nonexistent", "Bar, Foo", set(), {"Foo", "Bar"}),
            (
                "mixed",
                "Foo,Music,Bar,Fubar,Documents",
                {"Music", "Documents"},
                {"Foo", "Bar", "Fubar"},
            ),
        ]
    )
    @unittest.mock.patch.object(views.db, "insert_tag")
    def test__get_tag_ids_for_tag_names(
        self,
        _,
        new_tag_names_str,
        exp_existing_tag_names,
        exp_new_tag_names,
        mock_insert_tag,
    ):
        mock_insert_tag_rvals = [object() for _ in range(len(exp_new_tag_names))]
        mock_insert_tag.side_effect = mock_insert_tag_rvals
        act_tag_ids = views._get_tag_ids_for_tag_names(new_tag_names_str)
        self.assertTrue(
            act_tag_ids.issuperset(
                {
                    db_operations.get_tag(name=name).doc_id
                    for name in exp_existing_tag_names
                }
            )
        )
        if exp_new_tag_names:
            mock_insert_tag.assert_has_calls(
                [call(name, params.DEFAULT_TAG_COLOR) for name in exp_new_tag_names],
                any_order=True,
            )
        else:
            mock_insert_tag.assert_not_called()
        self.assertTrue(
            all(new_tag_id in act_tag_ids for new_tag_id in mock_insert_tag_rvals)
        )

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
        for param in ("mapping_id", "new_tag_names"):
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
        [
            (
                [],
                [],
                None,
                None,
                [True, True, True, True, False, True],
                [True, True, True, True, False, False],
                6,
                4,
                1,
                1,
                8,
            ),
            (
                [1, 2],
                [],
                "di",
                "all",
                [True, False],
                [True, False],
                2,
                1,
                0,
                1,
                5,
            ),
            (
                [1],
                [2],
                "do",
                "all",
                [],
                [],
                -1,
                0,
                0,
                0,
                -1,
            ),
            (
                [2],
                [2],
                "do",
                "all",
                [],
                [],
                -1,
                0,
                0,
                0,
                -1,
            ),
            (
                [3],
                [2],
                "do",
                "all",
                [True],
                [True],
                1,
                1,
                0,
                0,
                1,
            ),
            (
                [3],
                [],
                "jpg",
                "existent",
                [],
                [],
                -1,
                0,
                0,
                0,
                -1,
            ),
            (
                [],
                [1],
                "jpg",
                "existent",
                [True],
                [False],
                1,
                0,
                1,
                0,
                0,
            ),
            (
                [],
                [3],
                None,
                "nonexistent",
                [False, False, False, False],
                [False, False, False, False],
                4,
                0,
                0,
                4,
                4,
            ),
        ]
    )
    @unittest.mock.patch.object(views.Path, "is_dir")
    @unittest.mock.patch.object(views.Path, "exists")
    def test_mappings_list_nonempty(
        self,
        tag_ids_to_include,
        tag_ids_to_exclude,
        path_name_like,
        path_type,
        path_exists,
        path_is_dir,
        exp_mappings_table_row_count,
        exp_folders_count,
        exp_files_count,
        exp_nonexistent_count,
        exp_mappings_tags_count,
        mock_path_exists,
        mock_path_is_dir,
    ):
        mock_path_exists.side_effect = path_exists
        mock_path_is_dir.side_effect = path_is_dir
        data = {
            "tag_id_include": tag_ids_to_include,
            "tag_id_exclude": tag_ids_to_exclude,
            "path_type": path_type,
            "path_name_like": path_name_like,
        }
        for param in list(data.keys()):
            if data[param] is None:
                del data[param]
        response = self.client.get(reverse(f"{urls.app_name}:mappings_list"), {**data})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mappings_list.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")

        # prebrojati pathove u mappings tablici
        self.assertEqual(
            _table_row_count(soup, "mappings_table_body"), exp_mappings_table_row_count
        )
        if exp_mappings_table_row_count > -1:
            self.assertIsNone(soup.select_one("#no_defined_mappings"))
            self.assertIsNone(soup.select_one("#no_matching_mappings"))
            # prebrojati vrste pathova u mappings tablici
            self.assertEqual(
                len(soup.select_one("#mappings_table_body").select(".folder-path")),
                exp_folders_count,
            )
            self.assertEqual(
                len(
                    [
                        element.a
                        for element in soup.select_one("#mappings_table_body").select(
                            ".folder-path"
                        )
                    ]
                ),
                exp_folders_count,
            )
            self.assertEqual(
                len(soup.select_one("#mappings_table_body").select(".nonfolder-path")),
                exp_files_count,
            )
            self.assertEqual(
                len(
                    soup.select_one("#mappings_table_body").select(".nonexistent-path")
                ),
                exp_nonexistent_count,
            )
            # prebrojati tagove u mappings tablici
            self.assertEqual(
                len(soup.select_one("#mappings_table_body").select(".tag")),
                exp_mappings_tags_count,
            )
        else:
            self.assertIsNone(soup.select_one("#mappings_table_body"))
            self.assertIsNone(soup.select_one("#no_defined_mappings"))
            self.assertIsNotNone(soup.select_one("#no_matching_mappings"))

        # provjerit sadržaj path_name_contains
        self.assertEqual(
            soup.select_one("#PathNameLikeTextbox")["value"],
            path_name_like if path_name_like else "",
        )

        # provjerit sadržaj path_type radio grupe
        if not path_type or path_type == "all":
            self.assertEqual(soup.select_one("#PathTypeAllRadio")["checked"], "")
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeExistentRadio")["checked"]
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeNonexistentRadio")["checked"]
        elif path_type == "existent":
            self.assertEqual(soup.select_one("#PathTypeExistentRadio")["checked"], "")
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeAllRadio")["checked"]
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeNonexistentRadio")["checked"]
        elif path_type == "nonexistent":
            self.assertEqual(
                soup.select_one("#PathTypeNonexistentRadio")["checked"], ""
            )
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeAllRadio")["checked"]
            with self.assertRaises(KeyError):
                soup.select_one("#PathTypeExistentRadio")["checked"]

        # provjeriti prikazane tagove
        self.assertEqual(_table_row_count(soup, "tags_table_body"), 3)
        for tag_id in [tag.doc_id for tag in views.db.get_all_tags()]:
            if tag_id in tag_ids_to_include:
                self.assertEqual(
                    soup.select_one(f"#filter_tag_{tag_id}_include")["checked"], ""
                )
            else:
                with self.assertRaises(KeyError):
                    soup.select_one(f"#filter_tag_{tag_id}_include")["checked"]
            if tag_id in tag_ids_to_exclude:
                self.assertEqual(
                    soup.select_one(f"#filter_tag_{tag_id}_exclude")["checked"], ""
                )
            else:
                with self.assertRaises(KeyError):
                    soup.select_one(f"#filter_tag_{tag_id}_exclude")["checked"]

    def test_mappings_list_empty(self):
        views.db.DB.purge_table("_default")
        data = {"path_type": "all"}
        response = self.client.get(reverse(f"{urls.app_name}:mappings_list"), {**data})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/mappings_list.html"
            in [template.name for template in response.templates]
        )
        soup = BeautifulSoup(response.content, "lxml")
        self.assertIsNone(soup.select_one("#mappings_table_body"))
        self.assertIsNone(soup.select_one("#no_matching_mappings"))
        self.assertIsNotNone(soup.select_one("#no_defined_mappings"))
        self.assertEqual(_table_row_count(soup, "tags_table_body"), -1)

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
            _table_row_count(
                BeautifulSoup(response.content, "lxml"), "mappings_table_body"
            ),
            3,
        )

    @parameterized.expand(
        [
            ("name is None", None, "#AB3456", None, False),
            ("empty name", "", "#AB3456", None, False),
            ("color is None", "New tag name", None, None, False),
            ("empty color", "New tag name", "", None, False),
            ("own name", "Videos", "#AB3456", "#AB3456", True),
            ("some other existing name", "Music", "#AB3456", "#AB3456", True),
            ("valid name and color", "New tag name", "#AB3456", "#AB3456", True),
        ]
    )
    @unittest.mock.patch.object(views.db, "update_tag")
    def test_tag_details_post(
        self, _, name, color, exp_color, exp_update_tag_called, mock_update_tag
    ):
        tag_id = 2
        data = {"name": name, "color": color}
        for param in list(data.keys()):
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
            ("name is None", None, "#AB3456", "#AB3456", False),
            ("empty name", "", "#AB3456", "#AB3456", False),
            ("name already exists", "Videos", "#AB3456", "#AB3456", True),
            ("no color", "New tag name", None, params.DEFAULT_TAG_COLOR, True),
            ("empty color", "New tag name", "", params.DEFAULT_TAG_COLOR, True),
            ("valid name and color", "New tag name", "#AB3456", "#AB3456", True),
        ]
    )
    @unittest.mock.patch.object(views.db, "insert_tag")
    def test_add_tag(
        self, _, name, color, exp_color, exp_insert_tag_called, mock_insert_tag
    ):
        data = {"name": name, "color": color}
        for param in list(data.keys()):
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
            _table_row_count(
                BeautifulSoup(response.content, "lxml"), "tags_table_body"
            ),
            3,
        )

        db_operations.DB.purge_tables()
        response = self.client.get(reverse(f"{urls.app_name}:tags_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _table_row_count(
                BeautifulSoup(response.content, "lxml"), "tags_table_body"
            ),
            -1,
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

    @parameterized.expand(
        [
            (MyPath(None, True), False, False, []),
            (MyPath("/", True), True, True, [{"name": "/", "path_str": "/"}]),
            (
                MyPath("/home", True),
                True,
                True,
                [
                    {"name": "/", "path_str": "/"},
                    {"name": "home", "path_str": "/home"},
                ],
            ),
            (
                MyPath("/home", True),
                True,
                False,
                [{"name": "/", "path_str": "/"}],
            ),
            (
                MyPath("/home", True),
                False,
                False,
                [{"name": "/", "path_str": "/"}],
            ),
            (
                MyPath("/home/dino", True),
                True,
                True,
                [
                    {"name": "/", "path_str": "/"},
                    {"name": "home", "path_str": "/home"},
                    {"name": "dino", "path_str": "/home/dino"},
                ],
            ),
            (
                MyPath("/home/dino", True),
                True,
                False,
                [
                    {"name": "/", "path_str": "/"},
                    {"name": "home", "path_str": "/home"},
                ],
            ),
            (
                MyPath("/home/dino", True),
                False,
                False,
                [
                    {"name": "/", "path_str": "/"},
                    {"name": "home", "path_str": "/home"},
                ],
            ),
        ]
    )
    @unittest.mock.patch.object(views.Path, "is_dir")
    @unittest.mock.patch.object(views.Path, "exists")
    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_mypath_tokens(
        self, mypath, act_exists, act_is_dir, exp_tokens, mock_exists, mock_is_dir
    ):
        mock_exists.return_value = act_exists
        mock_is_dir.return_value = act_is_dir
        self.assertEqual(views.mypath_tokens(mypath), exp_tokens)

    @parameterized.expand(
        [
            (MyPath(None, True), False, [], []),
            (
                MyPath("/", True),
                True,
                [
                    {
                        "path_str": "/Downloads",
                        "db_path_str": "/Downloads",
                        "name": "Downloads",
                    },
                    {
                        "path_str": "/.bashrc",
                        "db_path_str": "/.bashrc",
                        "name": ".bashrc",
                    },
                ],
                [],
            ),
            (
                MyPath("/home/dino", True),
                True,
                [
                    {
                        "path_str": "/home/dino/Downloads",
                        "db_path_str": "/home/dino/Downloads",
                        "name": "Downloads",
                    },
                    {
                        "path_str": "/home/dino/.bashrc",
                        "db_path_str": "/home/dino/.bashrc",
                        "name": ".bashrc",
                    },
                ],
                [1, 2, 3],
            ),
            (
                MyPath("/home/dino/Downloads", True),
                False,
                [],
                [],
            ),
        ]
    )
    @unittest.mock.patch.object(views.MyPath, "get_children")
    @unittest.mock.patch.object(views.db, "get_tag")
    def test_mypath_children_data(
        self,
        mypath,
        is_dir,
        partial_exp_data,
        exp_tag_ids,
        mock_get_tag,
        mock_get_children,
    ):
        if is_dir:
            mock_get_children.return_value = [
                MyPath(mypath.abs_path / "Downloads", True),
                MyPath(mypath.abs_path / ".bashrc", True),
            ]
        else:
            mock_get_children.return_value = []
        if not (act_data := views.mypath_children_data(mypath)):
            self.assertEqual(act_data, partial_exp_data)
        else:
            for act_item, exp_item in zip(act_data, partial_exp_data):
                self.assertEqual(act_item["path_str"], exp_item["path_str"])
                self.assertEqual(act_item["db_path_str"], exp_item["db_path_str"])
                self.assertEqual(act_item["name"], exp_item["name"])
                if exp_tag_ids:
                    mock_get_tag.assert_has_calls(
                        [call(tag_id=exp_tag_id) for exp_tag_id in exp_tag_ids]
                    )

    @parameterized.expand(
        [
            (
                MyPath("no_anchor", True),
                None,
                False,
                False,
                False,
                False,
                False,
                None,
                None,
                None,
            ),
            (MyPath("/", True), None, True, True, True, True, False, 1, 0, True),
            (MyPath("/home", True), None, True, True, True, True, True, 2, 0, False),
            (
                MyPath("/home/nonexistent_path", True),
                None,
                False,
                False,
                False,
                False,
                False,
                None,
                None,
                None,
            ),
            (
                MyPath("/home/dino", True),
                None,
                True,
                True,
                True,
                True,
                True,
                3,
                4,
                False,
            ),
            (
                MyPath("/home/dino", True),
                None,
                True,
                True,
                False,
                False,
                True,
                3,
                0,
                False,
            ),
            (
                MyPath("/home/dino", True),
                None,
                True,
                False,
                False,
                False,
                True,
                2,
                None,
                False,
            ),
            (
                MyPath("/home/dino/Music", True),
                None,
                True,
                True,
                False,
                False,
                True,
                4,
                0,
                True,
            ),
            ################################################
            (
                MyPath("no_anchor", True),
                "/home/dino",
                False,
                False,
                False,
                False,
                False,
                None,
                None,
                None,
            ),
            (
                MyPath("/", True),
                "/home/dino",
                True,
                True,
                True,
                False,
                False,
                1,
                0,
                False,
            ),
            (
                MyPath("/home", True),
                "/home/dino",
                True,
                True,
                True,
                False,
                True,
                2,
                0,
                False,
            ),
            (
                MyPath("/home/nonexistent_path", True),
                "/home/dino",
                False,
                False,
                False,
                False,
                False,
                None,
                None,
                None,
            ),
            (
                MyPath("/home/dino", True),
                "/home/dino",
                True,
                True,
                True,
                True,
                True,
                3,
                0,
                True,
            ),
            (
                MyPath("/home/dino", True),
                "/home/dino",
                True,
                True,
                False,
                False,
                True,
                3,
                0,
                True,
            ),
            (
                MyPath("/home/dino", True),
                "/home/dino",
                True,
                False,
                False,
                False,
                True,
                2,
                0,
                True,
            ),
            (
                MyPath("/home/dino/Music", True),
                "/home/dino",
                True,
                True,
                False,
                False,
                True,
                4,
                0,
                False,
            ),
        ]
    )
    @unittest.mock.patch.object(views.MyPath, "get_children")
    @unittest.mock.patch.object(views.Path, "is_dir")
    @unittest.mock.patch.object(views.Path, "exists")
    def test_path_details(
        self,
        mypath,
        base_path_str,
        path_exists,
        path_is_dir,
        path_has_children,
        exp_tags_table_visible,
        exp_link_to_parent_path_visible,
        exp_path_tokens_count,
        exp_child_path_tags_count,
        exp_favorite_icon,
        mock_pathlib_exists,
        mock_pathlib_is_dir,
        mock_mypath_get_children,
    ):
        if path_is_dir:
            assert path_exists  # this is how pathlib.is_dir() works
        if path_has_children:
            assert path_exists and path_is_dir

        params.BASE_PATH = Path(base_path_str) if base_path_str else None
        mock_pathlib_exists.return_value = path_exists
        if path_has_children:
            mock_mypath_get_children.return_value = [
                MyPath(mypath.abs_path / "Downloads", True),
                MyPath(mypath.abs_path / "Music", True),
                MyPath(mypath.abs_path / ".bashrc", True),
            ]
            mock_pathlib_is_dir.side_effect = [
                True,
                True,
                True,
                True,
                False,
            ]
        else:
            mock_mypath_get_children.return_value = []
            mock_pathlib_is_dir.side_effect = [path_is_dir, path_is_dir]

        response = self.client.get(
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={"abs_path_str": mypath.raw_path},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            f"{urls.app_name}/path_details.html"
            in [template.name for template in response.templates]
        )

        soup = BeautifulSoup(response.content, "lxml")

        # check the 'favorite' icon
        favorite_icon_img = soup.select_one("#favorite_icon")
        if exp_favorite_icon is None:
            self.assertIsNone(favorite_icon_img)
        elif exp_favorite_icon:
            self.assertTrue(favorite_icon_img["src"].endswith("star-24-yellow.ico"))
            self.assertEqual(favorite_icon_img["title"], "Remove from favorites")
        else:
            self.assertTrue(favorite_icon_img["src"].endswith("star-24-gray.ico"))
            self.assertEqual(favorite_icon_img["title"], "Add to favorites")

        # is the table with tags shown
        self.assertEqual(
            _table_row_count(soup, "tags_table_body"),
            3 if exp_tags_table_visible else -1,
        )

        # are all child paths displayed
        self.assertEqual(
            _table_row_count(soup, "path_children_table_body"),
            3 if path_has_children else -1,
        )

        # are child paths' tags displayed
        if path_has_children:
            self.assertEqual(
                len(soup.select_one("#path_children_table_body").select(".tag")),
                exp_child_path_tags_count,
            )

        # what if there are no child paths
        if path_exists:
            self.assertEqual(
                len(soup.select("#no_child_paths_message")),
                0 if path_has_children else 1,
            )

        # is the link to the parent path shown
        self.assertEqual(
            len(soup.select("#link_to_parent_path")),
            1 if exp_link_to_parent_path_visible else 0,
        )

        # what is displayed for nonexistent paths
        self.assertEqual(
            len(soup.select("#invalid_path_message")),
            0 if path_exists else 1,
        )
        self.assertEqual(
            len(soup.select("#invalid_path_str")),
            0 if path_exists else 1,
        )
        if not path_exists and mypath.abs_path_str:
            self.assertTrue(
                soup.select_one("#invalid_path_str").text.endswith(mypath.abs_path_str)
            )

        # are all path tokens shown
        if path_exists:
            self.assertEqual(
                len(soup.select_one("#path_tokens").findAll("a")), exp_path_tokens_count
            )
        else:
            self.assertIsNone(soup.select_one("#path_tokens"))

    @parameterized.expand(
        [
            ("None", None, 0),
            ("empty", set(), 0),
            ("sole invalid", {""}, 0),
            ("sole nonexistent", {"/foo"}, 1),
            ("sole existing", {"/media"}, 1),
            ("invalid plus nonexistent", {"", "/foo"}, 1),
            ("invalid plus existing", {"", "/media"}, 1),
            ("nonexisting plus existing", {"/foo", "/media"}, 2),
            (
                "mixed",
                {"/foo", "/media", "", "/bar", "/fubar", "/home/dino/Downloads"},
                5,
            ),
        ]
    )
    def test__prepare_mapping_ids_for_tag_update(
        self,
        _,
        raw_path_strs,
        exp_mapping_ids_count,
    ):
        self.assertEqual(
            len(views._prepare_mapping_ids_for_tag_update(raw_path_strs)),
            exp_mapping_ids_count,
        )

    @parameterized.expand(
        [
            ("no paths, no new tag names, no current path", 0, None, None),
            ("no paths, no new tag names, with current path", 0, None, object()),
            ("no paths, with new tag names, no current path", 0, object(), None),
            ("no paths, with new tag names, with current path", 0, object(), object()),
            ("1 path, no new tag names, no current path", 1, None, None),
            ("1 path, no new tag names, with current path", 1, None, object()),
            ("1 path, with new tag names, no current path", 1, object(), None),
            ("1 path, with new tag names, with current path", 1, object(), object()),
            ("3 paths, no new tag names, no current path", 1, None, None),
            ("3 paths, no new tag names, with current path", 1, None, object()),
            ("3 paths, with new tag names, no current path", 1, object(), None),
            ("3 paths, with new tag names, with current path", 1, object(), object()),
        ]
    )
    @unittest.mock.patch.object(views.db, "remove_tags_from_mappings")
    @unittest.mock.patch.object(views.db, "append_tags_to_mappings")
    @unittest.mock.patch.object(views, "_parse_tag_ids_to_append_and_remove")
    @unittest.mock.patch.object(views, "_prepare_mapping_ids_for_tag_update")
    def test_edit_path_tags(
        self,
        _,
        raw_path_str_parameter_count,
        new_tag_names_parameter,
        current_path_parameter,
        mock__prepare_mapping_ids_for_tag_update,
        mock__parse_tag_ids_to_append_and_remove,
        mock_append_tags_to_mappings,
        mock_remove_tags_from_mappings,
    ):
        raw_path_strs = {object() for _ in range(raw_path_str_parameter_count)}
        mock__parse_tag_ids_to_append_and_remove_rval1 = object()
        mock__parse_tag_ids_to_append_and_remove_rval2 = object()
        mock__parse_tag_ids_to_append_and_remove.return_value = (
            mock__parse_tag_ids_to_append_and_remove_rval1,
            mock__parse_tag_ids_to_append_and_remove_rval2,
        )
        data = (
            {"path": raw_path_str for raw_path_str in raw_path_strs}
            if raw_path_str_parameter_count
            else {}
        )
        if new_tag_names_parameter:
            data["new_tag_names"] = new_tag_names_parameter
        if current_path_parameter:
            data["current_path"] = current_path_parameter
        response = self.client.post(
            reverse(f"{urls.app_name}:edit_path_tags"), {**data}, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                f"{urls.app_name}:path_details",
                kwargs={"abs_path_str": current_path_parameter},
            ),
            fetch_redirect_response=False,
        )
        if raw_path_str_parameter_count:
            mock_append_tags_to_mappings.assert_called_once_with(
                mock__parse_tag_ids_to_append_and_remove_rval1,
                mock__prepare_mapping_ids_for_tag_update(raw_path_strs),
            )
            mock_remove_tags_from_mappings.assert_called_once_with(
                mock__parse_tag_ids_to_append_and_remove_rval2,
                mock__prepare_mapping_ids_for_tag_update(raw_path_strs),
            )
        else:
            mock_append_tags_to_mappings.assert_not_called()
            mock_remove_tags_from_mappings.assert_not_called()

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
    @unittest.mock.patch.object(views.db, "delete_favorite")
    @unittest.mock.patch.object(views.db, "insert_favorite")
    @unittest.mock.patch.object(views.db, "get_favorite")
    def test_toggle_favorite_path(
        self,
        _,
        abs_path_str,
        is_ajax_call,
        prev_is_favorite,
        exp_insert_or_delete_called,
        exp_json_response_dict,
        mock_get_favorite,
        mock_insert_favorite,
        mock_delete_favorite,
    ):
        data = {"path": abs_path_str} if abs_path_str else {}
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"} if is_ajax_call else {}
        mock_get_favorite.return_value = prev_is_favorite
        response = self.client.post(
            reverse(f"{urls.app_name}:toggle_favorite_path"),
            {**data},
            follow=True,
            **headers,
        )
        if exp_insert_or_delete_called:
            if prev_is_favorite:
                mock_insert_favorite.assert_not_called()
                mock_delete_favorite.assert_called_once()
            else:
                mock_insert_favorite.assert_called_once()
                mock_delete_favorite.assert_not_called()
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
            _table_row_count(
                BeautifulSoup(response.content, "lxml"), "favorites_table_body"
            ),
            2,
        )
