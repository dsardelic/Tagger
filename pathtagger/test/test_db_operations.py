import os
import unittest
from tempfile import NamedTemporaryFile

from django.apps import apps
from parameterized import parameterized

from pathtagger import db_operations, urls
from Tagger import params


class TestDbOperations(unittest.TestCase):
    def setUp(self):
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

    def tearDown(self):
        os.remove(self.db_tmp_file_name)

    def test_get_all_favorite_paths(self):
        favorites = db_operations.get_all_favorite_paths()
        self.assertEqual(len(favorites), 2)
        self.assertEqual(favorites[0].doc_id, 1)
        self.assertEqual(favorites[0]["path"], "/home/dino/Music")
        self.assertEqual(favorites[1].doc_id, 2)
        self.assertEqual(favorites[1]["path"], "/")

        db_operations.DB.purge_tables()
        self.assertEqual(db_operations.get_all_favorite_paths(), [])

    @parameterized.expand(
        [
            ("existing favorite path", "/", True, 2),
            ("nonexistent path", "/foo", False, None),
        ]
    )
    def test_get_favorite_path(
        self, _, favorite_path, exp_get_successful, exp_favorite_doc_id
    ):
        favorite = db_operations.get_favorite_path(favorite_path)
        if exp_get_successful:
            self.assertEqual(favorite.doc_id, exp_favorite_doc_id)
            self.assertEqual(favorite["path"], favorite_path)
        else:
            self.assertIsNone(favorite)

    @parameterized.expand(
        [
            # TODO ("None path", None, False),
            # TODO ("empty path", "", False),
            ("new path", "/new/favorite/path", True),
            # TODO ("existing path", "/home/dino/Music", False),
        ]
    )
    def test_insert_favorite_path(self, _, path_str, exp_insert_successful):
        favorite_prev = db_operations.get_favorite_path(path_str)
        favorites_count_prev = len(db_operations.get_all_favorite_paths())
        inserted_favorite_id = db_operations.insert_favorite_path(path_str)
        if exp_insert_successful:
            self.assertEqual(
                len(db_operations.get_all_favorite_paths()), favorites_count_prev + 1
            )
            self.assertIsNone(favorite_prev)
            inserted_favorite = db_operations.get_favorite_path(path_str)
            self.assertEqual(inserted_favorite["path"], path_str)
        else:
            self.assertIsNone(inserted_favorite_id)
            self.assertEqual(
                len(db_operations.get_all_favorite_paths()), favorites_count_prev
            )
            self.assertEqual(db_operations.get_favorite_path(path_str), favorite_prev)

    @parameterized.expand(
        [
            ("existing favorite path", "/home/dino/Music", 1),
            ("nonexistent favorite path", "/foo", 2),
        ]
    )
    def test_delete_favorite_path(self, _, mapping_path, exp_remaining_favorites_count):
        db_operations.delete_favorite_path(mapping_path)
        self.assertEqual(
            len(db_operations.get_all_favorite_paths()), exp_remaining_favorites_count
        )
        self.assertIsNone(db_operations.get_favorite_path(mapping_path))

    def test_get_all_tags(self):
        tags = db_operations.get_all_tags()
        self.assertEqual(len(tags), 3)
        self.assertEqual(tags[0].doc_id, 1)
        self.assertEqual(tags[0]["name"], "Music")
        self.assertEqual(tags[0]["color"], "#a40000")
        self.assertEqual(tags[1].doc_id, 2)
        self.assertEqual(tags[1]["name"], "Videos")
        self.assertEqual(tags[1]["color"], "#307895")
        self.assertEqual(tags[2].doc_id, 3)
        self.assertEqual(tags[2]["name"], "Documents")
        self.assertEqual(tags[2]["color"], "#bca455")

        db_operations.DB.purge_tables()
        self.assertEqual(db_operations.get_all_tags(), [])

    @parameterized.expand(
        [
            ("existing tag name", "Videos", True, 2, "#307895"),
            ("nonexistent tag name", "Movies", False, None, None),
        ]
    )
    def test_get_tag_by_name(
        self, _, tag_name, exp_get_successful, exp_tag_id, exp_tag_color
    ):
        tag = db_operations.get_tag_by_name(tag_name)
        if exp_get_successful:
            self.assertEqual(tag.doc_id, exp_tag_id)
            self.assertEqual(tag["name"], tag_name)
            self.assertEqual(tag["color"], exp_tag_color)
        else:
            self.assertIsNone(tag)

    @parameterized.expand(
        [
            # TODO ("None name", None, None, False),
            # TODO ("empty name", "", None, False),
            # TODO ("new name with None color", "New tag", None, False),
            # TODO ("new name with empty color", "New tag", "", False),
            ("new name with uppercase color", "New tag", "#ABCDEF", True),
            ("new name with lowercase color", "New tag", "#fedcba", True),
            ("new name with mixed case color", "New tag", "#1A2b3C", True),
            # TODO ("name already exists", "Videos", None, False),
        ]
    )
    def test_insert_tag(self, _, tag_name, tag_color, exp_insert_successful):
        if tag_name:
            tag_prev = db_operations.get_tag_by_name(tag_name)
        tags_count_prev = len(db_operations.get_all_tags())
        inserted_tag_id = db_operations.insert_tag(tag_name, tag_color)
        if exp_insert_successful:
            self.assertEqual(len(db_operations.get_all_tags()), tags_count_prev + 1)
            self.assertIsNone(tag_prev)
            inserted_tag = db_operations.get_tag_by_id(inserted_tag_id)
            self.assertEqual(inserted_tag["name"], tag_name)
            self.assertEqual(inserted_tag["color"], tag_color)
        else:
            self.assertIsNone(inserted_tag_id)
            self.assertEqual(len(db_operations.get_all_tags()), tags_count_prev)
            if tag_name:
                self.assertEqual(db_operations.get_tag_by_name(tag_name), tag_prev)

    @parameterized.expand(
        (
            ("none", [], 3, 5),
            ("one", [1], 2, 4),
            ("two", [1, 2], 1, 2),
            ("all", [1, 2, 3], 0, 0),
        )
    )
    def test_delete_tags(
        self,
        _,
        tag_ids,
        exp_remaining_tags_count,
        exp_remaining_mappings_count,
    ):
        # assume all valid and existing tag_ids
        db_operations.delete_tags(tag_ids)
        self.assertEqual(len(db_operations.get_all_tags()), exp_remaining_tags_count)
        self.assertEqual(
            len(db_operations.get_all_mappings()), exp_remaining_mappings_count
        )
        self.assertTrue(
            all(db_operations.get_tag_by_id(tag_id) is None for tag_id in tag_ids)
        )
        self.assertTrue(
            all(
                tag_id not in mapping_document["tag_ids"]
                for mapping_document in db_operations.get_all_mappings()
                for tag_id in tag_ids
            )
        )

    def test_get_tag_mappings(self):
        test_data = {
            1: {1, 4, 5},
            2: {2, 4, 5},
            3: {3, 4},
            4: set(),
        }
        for tag_id, exp_mapping_ids in test_data.items():
            with self.subTest(tag_id=tag_id):
                self.assertEqual(
                    {
                        mapping.doc_id
                        for mapping in db_operations.get_tag_mappings(tag_id)
                    },
                    exp_mapping_ids,
                )

    @parameterized.expand(
        (
            (1, True, "Music", "#a40000"),
            (2, True, "Videos", "#307895"),
            (3, True, "Documents", "#bca455"),
            (4, False, None, None),
        )
    )
    def test_get_tag_by_id(
        self, tag_id, exp_get_successful, exp_tag_name, exp_tag_color
    ):
        tag = db_operations.get_tag_by_id(tag_id)
        if exp_get_successful:
            self.assertEqual(tag.doc_id, tag_id)
            self.assertEqual(tag["name"], exp_tag_name)
            self.assertEqual(tag["color"], exp_tag_color)
        else:
            self.assertIsNone(tag)

    @parameterized.expand(
        (
            ("new tag name and new color", 2, "new tag name", "#ABCDEF"),
            ("new tag name and same color", 2, "new tag name", "#307895"),
            ("same tag name and new color", 2, "Videos", "#fedcba"),
            ("same tag name and same color", 2, "Videos", "#307895"),
        )
    )
    def test_update_tag(self, _, tag_id, tag_name_new, tag_color_new):
        # assume valid and existing tag_id
        db_operations.update_tag(tag_id, tag_name_new, tag_color_new)
        tag = db_operations.get_tag_by_id(tag_id)
        self.assertEqual(tag["name"], tag_name_new)
        self.assertEqual(tag["color"], tag_color_new)

    @parameterized.expand(
        (
            (1, True, "/home/dino/Music", ["1"]),
            (2, True, "/home/dino/Videos", ["2"]),
            (3, True, "/home/dino/Documents", ["3"]),
            (4, True, "/home/dino/Downloads", ["1", "2", "3"]),
            (5, True, "/media", ["1", "2"]),
            (6, True, "/home/dino/Pictures/wallpaper.jpg", []),
            (7, False, None, None),
        )
    )
    def test_get_mapping(self, mapping_id, exp_get_successful, exp_path, exp_tag_ids):
        mapping = db_operations.get_mapping(mapping_id)
        if exp_get_successful:
            self.assertEqual(mapping.doc_id, mapping_id)
            self.assertEqual(mapping["path"], exp_path)
            self.assertEqual(mapping["tag_ids"], exp_tag_ids)
        else:
            self.assertIsNone(mapping)

    def test_remove_tags_from_mappings(self):
        # assume all tag_ids are valid and exist
        # assume all mapping_ids are valid and exist
        tag_ids = [1, 3]
        mapping_ids = [1, 2, 4, 5, 6]
        mappings = [db_operations.get_mapping(mapping_id) for mapping_id in mapping_ids]
        self.assertEqual(len(db_operations.get_all_mappings()), 6)
        self.assertTrue(
            all(
                any(str(tag_id) in mapping["tag_ids"] for mapping in mappings)
                for tag_id in tag_ids
            )
        )
        db_operations.remove_tags_from_mappings(tag_ids, mapping_ids)
        self.assertEqual(len(db_operations.get_all_mappings()), 4)
        mappings = [
            mapping
            for mapping_id in mapping_ids
            if (mapping := db_operations.get_mapping(mapping_id))
        ]
        self.assertTrue(
            all(
                all(str(tag_id) not in mapping["tag_ids"] for mapping in mappings)
                for tag_id in tag_ids
            )
        )
        self.assertTrue("3" in db_operations.get_mapping(3)["tag_ids"])

    def test_remove_mappings_without_tags(self):
        self.assertEqual(len(db_operations.get_all_mappings()), 6)
        db_operations.remove_mappings_without_tags()
        self.assertEqual(len(db_operations.get_all_mappings()), 5)
        db_operations.remove_mappings_without_tags()
        self.assertEqual(len(db_operations.get_all_mappings()), 5)

    def test_get_all_mappings(self):
        mappings = db_operations.get_all_mappings()
        self.assertEqual(len(mappings), 6)
        self.assertEqual(mappings[0].doc_id, 1)
        self.assertEqual(mappings[0]["path"], "/home/dino/Music")
        self.assertEqual(set(mappings[0]["tag_ids"]), {"1"})
        self.assertEqual(mappings[1].doc_id, 2)
        self.assertEqual(mappings[1]["path"], "/home/dino/Videos")
        self.assertEqual(set(mappings[1]["tag_ids"]), {"2"})
        self.assertEqual(mappings[2].doc_id, 3)
        self.assertEqual(mappings[2]["path"], "/home/dino/Documents")
        self.assertEqual(set(mappings[2]["tag_ids"]), {"3"})
        self.assertEqual(mappings[3].doc_id, 4)
        self.assertEqual(mappings[3]["path"], "/home/dino/Downloads")
        self.assertEqual(set(mappings[3]["tag_ids"]), {"1", "2", "3"})
        self.assertEqual(mappings[4].doc_id, 5)
        self.assertEqual(mappings[4]["path"], "/media")
        self.assertEqual(set(mappings[4]["tag_ids"]), {"1", "2"})
        self.assertEqual(mappings[5].doc_id, 6)
        self.assertEqual(mappings[5]["path"], "/home/dino/Pictures/wallpaper.jpg")
        self.assertEqual(set(mappings[5]["tag_ids"]), set())

        db_operations.DB.purge_tables()
        self.assertEqual(len(db_operations.get_all_mappings()), 0)

    @parameterized.expand(
        (
            ("None path", None, False, None, None),
            ("empty path", "", False, None, None),
            ("tag_ids None", "/foo", True, None, []),
            ("tag_ids empty", "/foo", True, [], []),
            (
                "new path with valid tag_ids",
                "/foo",
                True,
                ["1", "3"],
                ["1", "3"],
            ),
            # TODO ("existing path", "/home/dino/Videos", False, None, None),
        )
    )
    def test_insert_mapping(
        self, _, path_str, exp_insert_successful, tag_ids, exp_tag_ids
    ):
        mapping_prev = db_operations.get_mapping_by_path(path_str)
        mappings_count_prev = len(db_operations.get_all_mappings())
        inserted_mapping_id = db_operations.insert_mapping(path_str, tag_ids)
        if exp_insert_successful:
            self.assertEqual(
                len(db_operations.get_all_mappings()), mappings_count_prev + 1
            )
            self.assertIsNone(mapping_prev)
            inserted_mapping = db_operations.get_mapping(inserted_mapping_id)
            self.assertEqual(inserted_mapping["path"], path_str)
            self.assertEqual(inserted_mapping["tag_ids"], exp_tag_ids)
        else:
            self.assertIsNone(inserted_mapping_id)
            self.assertEqual(len(db_operations.get_all_mappings()), mappings_count_prev)
            self.assertEqual(db_operations.get_mapping_by_path(path_str), mapping_prev)

    @parameterized.expand(
        (
            ("existing mapping path", "/home/dino/Downloads", True, 4, ["1", "2", "3"]),
            ("nonexistent mapping path", "/foo", False, None, None),
        )
    )
    def test_get_mapping_by_path(
        self, _, mapping_path, exp_mapping_found, exp_mapping_id, exp_mapping_tag_ids
    ):
        mapping = db_operations.get_mapping_by_path(mapping_path)
        if exp_mapping_found:
            self.assertEqual(mapping.doc_id, exp_mapping_id)
            self.assertEqual(mapping["path"], mapping_path)
            self.assertEqual(mapping["tag_ids"], exp_mapping_tag_ids)
        else:
            self.assertIsNone(mapping)

    @parameterized.expand(
        (
            ([2, 3, 4], 3),
            ([5], 5),
            ([6], 5),
        )
    )
    def test_delete_mappings(self, mapping_ids, exp_remaining_mappings_count):
        # assume all mapping_ids are valid and exist
        db_operations.delete_mappings(mapping_ids)
        self.assertEqual(
            len(db_operations.get_all_mappings()), exp_remaining_mappings_count
        )
        self.assertTrue(
            all(
                db_operations.get_mapping(mapping_id) is None
                for mapping_id in mapping_ids
            )
        )

    @parameterized.expand(
        (
            ("different path", 1, "/new/mapping/path"),
            ("same path", 1, "/home/dino/Music"),
        )
    )
    def test_update_mapping(self, _, mapping_id, path_str_new):
        # assume valid and existing mapping_id
        mapping_old = db_operations.get_mapping(mapping_id)
        db_operations.update_mapping(mapping_id, path_str_new)
        mapping_new = db_operations.get_mapping(mapping_id)
        self.assertEqual(mapping_new["path"], path_str_new)
        self.assertEqual(mapping_new["tag_ids"], mapping_old["tag_ids"])

    @parameterized.expand(
        (
            ([1], [], None, {1, 4, 5}),
            ([1], [], "media", {5}),
            ([1, 2], [], None, {4, 5}),
            ([1, 2], [], "MEDIA", {5}),
            ([], [1], None, {2, 3, 6}),
            ([], [1], "jpg", {6}),
            ([], [1], "jpeg", set()),
            ([], [1, 2], None, {3, 6}),
            ([], [1, 2], "jpg", {6}),
            ([1, 2], [3], None, {5}),
            ([1, 2], [3], "dino", set()),
            ([1], [2, 3], None, {1}),
            ([1], [2, 3], "Music", {1}),
            ([1], [1], None, set()),
            ([1], [1], "dino", set()),
        )
    )
    def test_get_filtered_mappings(
        self,
        tag_ids_to_include,
        tag_ids_to_exclude,
        mapping_path_like,
        exp_mapping_ids,
    ):
        self.assertEqual(
            {
                mapping.doc_id
                for mapping in db_operations.get_filtered_mappings(
                    tag_ids_to_include, tag_ids_to_exclude, mapping_path_like
                )
            },
            exp_mapping_ids,
        )

    def test_append_tags_to_mappings(
        self,
    ):
        # assume all valid and existing tag_ids
        # assume all valid and existing mapping_ids
        tag_ids = [1, 2]
        mapping_ids = [1, 3, 4, 6]
        db_operations.append_tags_to_mappings(tag_ids, mapping_ids)
        self.assertTrue(
            all(
                str(tag_id) in db_operations.get_mapping(mapping_id)["tag_ids"]
                for mapping_id in mapping_ids
                for tag_id in tag_ids
            )
        )
        self.assertTrue("1" not in db_operations.get_mapping(2)["tag_ids"])
