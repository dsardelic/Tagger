import os
import unittest
from tempfile import NamedTemporaryFile

from django.apps import apps
from parameterized import parameterized

from pathtagger import db_operations, urls
from Tagger import params


# pylint: disable=too-many-public-methods,too-many-arguments,protected-access
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

    def test_get_all_favorites(self):
        favorites = db_operations.get_all_favorites()
        self.assertEqual(len(favorites), 2)
        self.assertEqual(favorites[0].doc_id, 1)
        self.assertEqual(favorites[0]["path"], "/home/dino/Music")
        self.assertEqual(favorites[1].doc_id, 2)
        self.assertEqual(favorites[1]["path"], "/")

        db_operations.DB.purge_tables()
        self.assertEqual(db_operations.get_all_favorites(), [])

    @parameterized.expand(
        [
            ("path is None", None, False, None),
            ("empty path", "", False, None),
            ("existing path", "/", True, 2),
            ("nonexistent path", "/foo", False, None),
        ]
    )
    def test_get_favorite(
        self, _, favorite_path, exp_get_successful, exp_favorite_doc_id
    ):
        favorite = db_operations.get_favorite(favorite_path)
        if exp_get_successful:
            self.assertEqual(favorite.doc_id, exp_favorite_doc_id)
            self.assertEqual(favorite["path"], favorite_path)
        else:
            self.assertIsNone(favorite)

    @parameterized.expand(
        [
            ("path is None", None, False),
            ("empty path", "", False),
            ("existing path", "/home/dino/Music", False),
            ("nonexistent path", "/new/favorite/path", True),
        ]
    )
    def test_insert_favorite(self, _, path_str, exp_insert_successful):
        favorite_prev = db_operations.get_favorite(path_str)
        favorites_count_prev = len(db_operations.get_all_favorites())
        inserted_favorite_id = db_operations.insert_favorite(path_str)
        if exp_insert_successful:
            self.assertEqual(
                len(db_operations.get_all_favorites()), favorites_count_prev + 1
            )
            self.assertIsNone(favorite_prev)
            inserted_favorite = db_operations.get_favorite(path_str)
            self.assertEqual(inserted_favorite["path"], path_str)
        else:
            self.assertIsNone(inserted_favorite_id)
            self.assertEqual(
                len(db_operations.get_all_favorites()), favorites_count_prev
            )
            self.assertEqual(db_operations.get_favorite(path_str), favorite_prev)

    @parameterized.expand(
        [
            ("path is None", None, 2),
            ("empty path", "", 2),
            ("existing path", "/home/dino/Music", 1),
            ("nonexistent path", "/foo", 2),
        ]
    )
    def test_delete_favorite(self, _, mapping_path, exp_remaining_favorites_count):
        db_operations.delete_favorite(mapping_path)
        self.assertEqual(
            len(db_operations.get_all_favorites()), exp_remaining_favorites_count
        )
        self.assertIsNone(db_operations.get_favorite(mapping_path))

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
            ("id is None, name is None", None, None, False, None, None, None),
            ("id is None, empty name ", None, "", False, None, None, None),
            ("id is None, existing name", None, "Videos", True, 2, "Videos", "#307895"),
            ("id is None, nonexistent name", None, "Movies", False, None, None, None),
            ("id exists, name is None", 1, None, True, 1, "Music", "#a40000"),
            ("id exists, empty name", 1, "", False, None, None, None),
            ("id exists, right name", 1, "Music", True, 1, "Music", "#a40000"),
            ("id exists, wrong name", 1, "Heavy metal", False, None, None, None),
            ("nonexisting id, name is None", 1001, None, False, None, None, None),
            ("nonexisting id, empty name", 1001, "", False, None, None, None),
            ("nonexisting id, existing name", 1001, "Music", False, None, None, None),
            ("nonexisting id, nonexisting name", 1001, "Jazz", False, None, None, None),
        ]
    )
    def test_get_tag(
        self,
        _,
        tag_id,
        tag_name,
        exp_get_successful,
        exp_tag_id,
        exp_tag_name,
        exp_tag_color,
    ):
        tag_id_variations = [{"tag_id": tag_id}]
        if tag_id is None:
            tag_id_variations.append({})
        tag_name_variations = [{"name": tag_name}]
        if tag_name is None:
            tag_name_variations.append({})

        for tag_id_variation in tag_id_variations:
            for tag_name_variation in tag_name_variations:
                with self.subTest({**tag_id_variation, **tag_name_variation}):
                    tag = db_operations.get_tag(
                        **{**tag_id_variation, **tag_name_variation}
                    )
                    if exp_get_successful:
                        self.assertEqual(tag.doc_id, exp_tag_id)
                        self.assertEqual(tag["name"], exp_tag_name)
                        self.assertEqual(tag["color"], exp_tag_color)
                    else:
                        self.assertIsNone(tag)

    @parameterized.expand(
        [
            ("None", None, False),
            ("empty", "", False),
            ("no leading hash sign", "ABCDEF", False),
            ("uppercase", "#ABCDEF", True),
            ("lowercase", "#fedcba", True),
            ("mixed case", "#1A2b3C", True),
            ("too short", "#1A2b3", False),
            ("too long", "#1A2b3C4", False),
            ("invalid char", "#1A2b3Z", False),
        ]
    )
    def test__is_valid_hex_color(self, _, color, exp_is_valid):
        self.assertEqual(db_operations._is_valid_hex_color(color), exp_is_valid)

    @parameterized.expand(
        [
            ("name is None, color is None", None, None, False),
            ("name is None, empty color", None, "", False),
            ("name is None, valid color", None, "#1A2b3C", False),
            ("name is None, invalid color", None, "#1A2b3Z", False),
            ("empty name, color is None", "", None, False),
            ("empty name, empty color", "", "", False),
            ("empty name, valid color", "", "#1A2b3C", False),
            ("empty name, invalid color", "", "#1A2b3Z", False),
            ("new name, color is None", "New tag", None, False),
            ("new name, empty color", "New tag", "", False),
            ("new name, valid color", "New tag", "#1A2b3C", True),
            ("new name, invalid color", "New tag", "#1A2b3Z", False),
            ("existing name, color is None", "Videos", None, False),
            ("existing name, empty color", "Videos", "", False),
            ("existing name, valid color", "Videos", "#974511", False),
            ("existing name, invalid color", "Videos", "#GGHHII", False),
        ]
    )
    def test_insert_tag(self, _, tag_name, tag_color, exp_insert_successful):
        tag_old = db_operations.get_tag(name=tag_name)
        tags_count_old = len(db_operations.get_all_tags())
        inserted_tag_id = db_operations.insert_tag(tag_name, tag_color)
        if exp_insert_successful:
            self.assertEqual(len(db_operations.get_all_tags()), tags_count_old + 1)
            self.assertIsNone(tag_old)
            inserted_tag = db_operations.get_tag(tag_id=inserted_tag_id)
            self.assertEqual(inserted_tag["name"], tag_name)
            self.assertEqual(inserted_tag["color"], tag_color)
        else:
            self.assertIsNone(inserted_tag_id)
            self.assertEqual(len(db_operations.get_all_tags()), tags_count_old)
            self.assertEqual(db_operations.get_tag(name=tag_name), tag_old)

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
            all(db_operations.get_tag(tag_id=tag_id) is None for tag_id in tag_ids)
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
            ("name is None", 2, None, "#fedcba", False),
            ("name empty", 2, "", "#fedcba", False),
            ("same name, new color", 2, "Videos", "#fedcba", True),
            ("same name, same color", 2, "Videos", "#307895", True),
            ("new name, new color", 2, "new tag name", "#ABCDEF", True),
            ("new name, same color", 2, "new tag name", "#307895", True),
            ("invalid color", 2, "Videos", "#zedcba", False),
            ("invalid tag_id", 1001, "new tag name", "#fedcba", False),
        )
    )
    def test_update_tag(
        self, _, tag_id, tag_name_new, tag_color_new, exp_update_successful
    ):
        tag_old = db_operations.get_tag(tag_id=tag_id)
        db_operations.update_tag(tag_id, tag_name_new, tag_color_new)
        tag_updated = db_operations.get_tag(tag_id=tag_id)
        if exp_update_successful:
            self.assertEqual(tag_updated["name"], tag_name_new)
            self.assertEqual(tag_updated["color"], tag_color_new)
        else:
            self.assertEqual(tag_updated, tag_old)

    @parameterized.expand(
        (
            ("id is None, path is None", None, None, False, None, None, None),
            ("id is None, empty path", None, "", False, None, None, None),
            (
                "id is None, path exists",
                None,
                "/home/dino/Documents",
                True,
                3,
                "/home/dino/Documents",
                ["3"],
            ),
            ("id is None, nonexistint path", None, "/foo", False, None, None, None),
            ("existing id, path is None", 1, None, True, 1, "/home/dino/Music", ["1"]),
            ("existing id, empty path", 1, "", False, None, None, None),
            (
                "existing id, correct path",
                1,
                "/home/dino/Music",
                True,
                1,
                "/home/dino/Music",
                ["1"],
            ),
            ("existing id, wrong path", 1, "/foo", False, None, None, None),
            ("nonexistent id, path is None", 1001, None, False, None, None, None),
            ("nonexistent id, empty path", 1001, "", False, None, None, None),
            ("nonexistent id, path exists", 1001, "/media", False, None, None, None),
            ("nonexistent id, nonexistent path", 1001, "/foo", False, None, None, None),
        )
    )
    def test_get_mapping(
        self,
        _,
        mapping_id,
        mapping_path,
        exp_get_successful,
        exp_mapping_id,
        exp_mapping_path,
        exp_tag_ids,
    ):
        mapping_id_variations = [{"mapping_id": mapping_id}]
        if mapping_id is None:
            mapping_id_variations.append({})
        mapping_path_variations = [{"db_path_str": mapping_path}]
        if mapping_path is None:
            mapping_path_variations.append({})

        for mapping_id_variation in mapping_id_variations:
            for mapping_path_variation in mapping_path_variations:
                with self.subTest({**mapping_id_variation, **mapping_path_variation}):
                    mapping = db_operations.get_mapping(
                        **{**mapping_id_variation, **mapping_path_variation}
                    )
                    if exp_get_successful:
                        self.assertEqual(mapping.doc_id, exp_mapping_id)
                        self.assertEqual(mapping["path"], exp_mapping_path)
                        self.assertEqual(mapping["tag_ids"], exp_tag_ids)
                    else:
                        self.assertIsNone(mapping)

    def test_remove_tags_from_mappings(self):
        # assume all tag_ids are valid and exist
        # assume all mapping_ids are valid and exist
        tag_ids = [1, 3]
        mapping_ids = [1, 2, 4, 5, 6]
        mappings = [
            db_operations.get_mapping(mapping_id=mapping_id)
            for mapping_id in mapping_ids
        ]
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
            if (mapping := db_operations.get_mapping(mapping_id=mapping_id))
        ]
        self.assertTrue(
            all(
                all(str(tag_id) not in mapping["tag_ids"] for mapping in mappings)
                for tag_id in tag_ids
            )
        )
        self.assertTrue("3" in db_operations.get_mapping(mapping_id=3)["tag_ids"])

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
            ("path is None, tag_ids is None", None, None, False, None),
            ("path is None, empty tag_ids", None, [], False, None),
            ("path is None, all valid tag_ids", None, [1, 2, 3], False, None),
            ("path is None, all invalid tag_ids", None, [11, 12], False, None),
            ("path is None, valid and invalid tag_ids", None, [1, 12], False, None),
            ("empty path, tag_ids is None", "", None, False, None),
            ("empty path, empty tag_ids", "", [], False, None),
            ("empty path, all valid tag_ids", "", [1, 2, 3], False, None),
            ("empty path, all invalid tag_ids", "", [11, 12], False, None),
            ("empty path, valid and invalid tag_ids", "", [1, 12], False, None),
            ("new path, tag_ids is None", "/foo", None, True, []),
            ("new path, empty tag_ids", "/foo", [], True, []),
            ("new path, all valid tag_ids", "/foo", [1, 3], True, ["1", "3"]),
            ("new path, all invalid tag_ids", "/foo", [11, 12], True, []),
            ("new path, valid and invalid tag_ids", "/foo", [1, 12], True, ["1"]),
            ("existing path, tag_ids is None", "/home/dino/Videos", None, False, None),
            ("existing path, empty tag_ids", "/home/dino/Videos", [], False, None),
            (
                "existing path, all valid tag_ids",
                "/home/dino/Videos",
                [1, 3],
                False,
                None,
            ),
            (
                "existing path, all invalid tag_ids",
                "/home/dino/Videos",
                [11, 12],
                False,
                None,
            ),
            (
                "existing path, valid and invalid tag_ids",
                "/home/dino/Videos",
                [1, 12],
                False,
                None,
            ),
        )
    )
    def test_insert_mapping(
        self, _, path_str, tag_ids, exp_insert_successful, exp_tag_ids
    ):
        mapping_old = db_operations.get_mapping(db_path_str=path_str)
        mappings_count_prev = len(db_operations.get_all_mappings())
        inserted_mapping_id = db_operations.insert_mapping(path_str, tag_ids)
        if exp_insert_successful:
            self.assertEqual(
                len(db_operations.get_all_mappings()), mappings_count_prev + 1
            )
            self.assertIsNone(mapping_old)
            inserted_mapping = db_operations.get_mapping(mapping_id=inserted_mapping_id)
            self.assertEqual(inserted_mapping["path"], path_str)
            self.assertEqual(inserted_mapping["tag_ids"], exp_tag_ids)
        else:
            self.assertIsNone(inserted_mapping_id)
            self.assertEqual(len(db_operations.get_all_mappings()), mappings_count_prev)
            self.assertEqual(
                db_operations.get_mapping(db_path_str=path_str), mapping_old
            )

    @parameterized.expand(
        (
            ([2, 3, 4], 2),
            ([5], 4),
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
                db_operations.get_mapping(mapping_id=mapping_id) is None
                for mapping_id in mapping_ids
            )
        )

    @parameterized.expand(
        (
            ("different path", 1, "/new/mapping/path"),
            ("same path", 1, "/home/dino/Music"),
        )
    )
    def test_update_mapping_path(self, _, mapping_id, path_str_new):
        # assume valid and existing mapping_id
        mapping_old = db_operations.get_mapping(mapping_id=mapping_id)
        db_operations.update_mapping_path(mapping_id, path_str_new)
        mapping_new = db_operations.get_mapping(mapping_id=mapping_id)
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
                str(tag_id)
                in db_operations.get_mapping(mapping_id=mapping_id)["tag_ids"]
                for mapping_id in mapping_ids
                for tag_id in tag_ids
            )
        )
        self.assertTrue("1" not in db_operations.get_mapping(mapping_id=2)["tag_ids"])
