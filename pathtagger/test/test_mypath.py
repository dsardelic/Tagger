import unittest
from pathlib import Path

from pathtagger.views import MyPath
from Tagger import params


class TestMyPath(unittest.TestCase):
    # TODO: u svim metodama provjeriti da se poziva _to_formatted_posix_path_str!

    def test_no_base_path(self):
        test_data = [
            (
                None,
                False,
                None,
                None,
                False,
                False,
            ),
            (
                None,
                True,
                None,
                None,
                False,
                False,
            ),
            (
                "",
                False,
                ".",
                ".",
                False,
                False,
            ),
            (
                "",
                True,
                ".",
                ".",
                False,
                False,
            ),
            (
                ".",
                False,
                ".",
                ".",
                False,
                False,
            ),
            (
                ".",
                True,
                ".",
                ".",
                False,
                False,
            ),
            (
                "/",
                False,
                "/",
                "/",
                True,
                True,
            ),
            (
                "/",
                True,
                "/",
                "/",
                True,
                True,
            ),
            (
                "/Videos",
                False,
                "/Videos",
                "/Videos",
                True,
                True,
            ),
            (
                "/Videos",
                True,
                "/Videos",
                "/Videos",
                True,
                True,
            ),
            (
                "/Videos/movies/Star Trek",
                False,
                "/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                True,
                True,
            ),
            (
                "/Videos/movies/Star Trek",
                True,
                "/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                True,
                True,
            ),
        ]

        for (
            raw_path,
            is_abs_path,
            exp_abs_path_str,
            exp_db_path_str,
            exp_is_taggable,
            exp_is_valid_db_path_str,
        ) in test_data:
            with self.subTest(raw_path=raw_path, is_abs_path=is_abs_path):
                params.BASE_PATH = None
                for raw_value in (
                    [raw_path, Path(raw_path)] if raw_path is not None else [raw_path]
                ):
                    mypath = MyPath(raw_value, is_abs_path)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.abs_path_str, mypath.db_path_str)
                    self.assertEqual(mypath.is_taggable(), exp_is_taggable)
                    self.assertEqual(
                        mypath.db_path_str_is_valid(), exp_is_valid_db_path_str
                    )

    def test_abs_path_is_ancestor_of_base_path(self):
        test_data = [
            (
                "/",
                True,
                Path("/home/user"),
                False,
                "/",
                None,
                False,
            ),
        ]

    def test_abs_path_is_base_path(self):
        test_data = []

    def test_abs_path_is_descendant_of_base_path(self):
        test_data = []

    def test_abs_path_is_unrelated_to_base_path(self):
        test_data = [
            (
                None,
                True,
                Path("/home/user"),
                False,
                None,
                None,
                False,
            ),
            (
                "",
                True,
                Path("/home/user"),
                False,
                ".",
                None,
                False,
            ),
            (
                ".",
                True,
                Path("/home/user"),
                False,
                ".",
                None,
                False,
            ),
            (
                "/Videos",
                True,
                Path("/home/user"),
                False,
                "/Videos",
                None,
                False,
            ),
            (
                "/Videos/movies/Star Trek",
                True,
                Path("/home/user"),
                False,
                "/Videos/movies/Star Trek",
                None,
                False,
            ),
        ]

    def test_db_path_is_ancestor_of_base_path(self):
        test_data = [
            (
                "/",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                "/",
                True,
            ),
        ]

    def test_db_path_is_base_path(self):
        test_data = []

    def test_db_path_is_descendant_of_base_path(self):
        test_data = []

    def test_db_path_is_unrelated_to_base_path(self):
        test_data = [
            (
                None,
                False,
                Path("/home/user"),
                False,
                None,
                None,
                False,
            ),
            (
                "",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                "/",
                True,
            ),
            (
                ".",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                "/",
                True,
            ),
            (
                "/Videos",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                "/Videos",
                True,
            ),
            (
                "/Videos/movies/Star Trek",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                True,
            ),
        ]

    def test__to_formatted_posix_path(self):
        # pylint: disable=W0212
        test_data = [
            ("empty", "", "."),
            ("dot str", ".", "."),
            ("root", "/", "/"),
            ("leading solidum", "/home/Videos", "/home/Videos"),
            ("multiple leading solida", "////home/Videos", "/home/Videos"),
            ("trailing solidum", "home/Videos/", "/home/Videos"),
            ("multiple trailing solida", "home/Videos///", "/home/Videos"),
            ("leading and trailing solidum", "/home/Videos/", "/home/Videos"),
            (
                "multiple leading and trailing solida",
                "///home/Videos///",
                "/home/Videos",
            ),
            ("intermediate solida", "/home//Videos", "/home/Videos"),
        ]
        for description, path, exp_rval in test_data:
            with self.subTest(description=description):
                self.assertEqual(MyPath._to_formatted_posix_path_str(path), exp_rval)
            path = Path(path)
            with self.subTest(description=description):
                self.assertEqual(MyPath._to_formatted_posix_path_str(path), exp_rval)
