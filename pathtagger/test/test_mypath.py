import os
import unittest
from pathlib import Path, PosixPath, WindowsPath

from pathtagger.views import MyPath
from Tagger import params


class TestMyPath(unittest.TestCase):
    def test_attribues_and_properties(self):
        test_data = [
            (
                "",
                False,
                None,
                False,
                ".",
                Path("."),
                ".",
                ".",
                Path("."),
                ".",
            ),
            (
                "",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                Path("/home/user"),
                "/home/user",
                "/",
                Path("/"),
                "/",
            ),
            (
                ".",
                False,
                None,
                False,
                ".",
                Path("."),
                ".",
                ".",
                Path("."),
                ".",
            ),
            (
                ".",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                Path("/home/user"),
                "/home/user",
                "/",
                Path("/"),
                "/",
            ),
            (
                "/",
                False,
                None,
                True,
                "/",
                Path("/"),
                "/",
                "/",
                Path("/"),
                "/",
            ),
            (
                "/",
                False,
                Path("/home/user"),
                True,
                "/home/user",
                Path("/home/user"),
                "/home/user",
                "/",
                Path("/"),
                "/",
            ),
            (
                "/Videos",
                False,
                None,
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "Videos/",
                False,
                None,
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "Videos/",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos/",
                False,
                None,
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos/",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "//Videos",
                False,
                None,
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "//Videos",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos//",
                False,
                None,
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos//",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                "/Videos",
                Path("/Videos"),
                "/Videos",
            ),
            (
                "/Videos/movies/Star Trek",
                False,
                None,
                True,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
            ),
            (
                "/Videos/movies/Star Trek",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos/movies/Star Trek",
                Path("/home/user/Videos/movies/Star Trek"),
                "/home/user/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
            ),
            (
                "/Videos//movies/Star Trek",
                False,
                None,
                True,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
            ),
            (
                "/Videos//movies/Star Trek",
                False,
                Path("/home/user"),
                True,
                "/home/user/Videos/movies/Star Trek",
                Path("/home/user/Videos/movies/Star Trek"),
                "/home/user/Videos/movies/Star Trek",
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
            ),
        ]

        for (
            raw_path,
            is_abs_path,
            base_path,
            exp_abs_path_is_taggable,
            exp_abs_path_str,
            exp_abs_path,
            exp_system_abs_path_str,
            exp_db_path_str,
            exp_db_path,
            exp_system_db_path_str,
        ) in test_data:
            with self.subTest(
                raw_path=raw_path, is_abs_path=is_abs_path, base_path=base_path
            ):
                params.BASE_PATH = base_path

                mypath = MyPath(raw_path, is_abs_path)
                self.assertEqual(mypath.db_path_str, exp_db_path_str)
                self.assertEqual(mypath.db_path, exp_db_path)
                self.assertEqual(mypath.system_db_path_str, exp_system_db_path_str)
                self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                self.assertEqual(mypath.abs_path, exp_abs_path)
                self.assertEqual(mypath.system_abs_path_str, exp_system_abs_path_str)
                self.assertEqual(mypath.abs_path_is_taggable, exp_abs_path_is_taggable)

                mypath = MyPath(Path(raw_path), is_abs_path)
                self.assertEqual(mypath.db_path_str, exp_db_path_str)
                self.assertEqual(mypath.db_path, exp_db_path)
                self.assertEqual(mypath.system_db_path_str, exp_system_db_path_str)
                self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                self.assertEqual(mypath.abs_path, exp_abs_path)
                self.assertEqual(mypath.system_abs_path_str, exp_system_abs_path_str)
                self.assertEqual(mypath.abs_path_is_taggable, exp_abs_path_is_taggable)

    def test__to_db_path_str(self):
        pass

    # pylint: disable=W0212
    def test__to_formatted_posix_path(self):
        test_data = [
            ("empty", "", "."),
            ("dot str", ".", "."),
            ("root", "/", "/"),
            ("leading solidum", "/home/Videos", "/home/Videos"),
            ("trailing solidum", "home/Videos/", "/home/Videos"),
            ("leading and trailing solidum", "/home/Videos/", "/home/Videos"),
        ]
        for description, path, exp_rval in test_data:
            with self.subTest(description=description):
                self.assertEqual(MyPath._to_formatted_posix_path(path), exp_rval)
            path = Path(path)
            with self.subTest(description=description):
                self.assertEqual(MyPath._to_formatted_posix_path(path), exp_rval)

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_is_allowed_path_posix(self):
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

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_is_allowed_path_nt(self):
        test_data = [
            ("no base path", None, r"C:\tools\eclipse", True),
            (
                "base path parent",
                r"C:\tools",
                r"C:\tools\eclipse",
                True,
            ),
            (
                "is base path",
                r"C:\tools\eclipse",
                r"C:\tools\eclipse",
                True,
            ),
            (
                "base path descendant",
                r"C:\tools\eclipse\plugins",
                r"C:\tools\eclipse",
                False,
            ),
            (
                "no relation with base path",
                r"C:\Windows",
                r"C:\tools\eclipse",
                False,
            ),
        ]

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_get_db_path_str_posix(self):
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

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_get_db_path_str_nt(self):
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

    @unittest.skipUnless(os.name == "posix", "requires Posix")
    def test_join_with_base_path_posix(self):
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

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_join_with_base_path_nt(self):
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
