import os
import unittest
from pathlib import Path, PosixPath, WindowsPath

from pathtagger.views import MyPath
from Tagger import params


class TestMyPath(unittest.TestCase):
    def test_to_formatted_path_str_valid(self):
        test_data = [
            (
                "empty path w/o BASE_PATH",
                "",
                False,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                None,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                False,
            ),
            (
                "empty path with BASE_PATH",
                "",
                False,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                Path("/home/user"),
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                False,
            ),
            (
                "dot w/o BASE_PATH",
                ".",
                False,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                None,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                False,
            ),
            (
                "dot with BASE_PATH",
                ".",
                False,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                Path("/home/user"),
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                MyPath.INVALID_PATH,
                False,
            ),
            (
                "root w/o BASE_PATH",
                "/",
                False,
                "/",
                Path("/"),
                "/",
                None,
                "/",
                Path("/"),
                "/",
                True,
            ),
            (
                "root with BASE_PATH",
                "/",
                False,
                "/",
                Path("/"),
                "/",
                Path("/home/user"),
                "/home/user",
                Path("/home/user"),
                "/home/user",
                True,
            ),
            (
                "single leading solidus w/o BASE_PATH",
                "/Videos",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                None,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                True,
            ),
            (
                "single leading solidus with BASE_PATH",
                "/Videos",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/home/user"),
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                True,
            ),
            (
                "single trailing solidus w/o BASE_PATH",
                "Videos/",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                None,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                True,
            ),
            (
                "single trailing solidus with BASE_PATH",
                "Videos/",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/home/user"),
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                True,
            ),
            (
                "single leading and single trailing solidus w/o BASE_PATH",
                "/Videos/",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                None,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                True,
            ),
            (
                "single leading and single trailing solidus with BASE_PATH",
                "/Videos/",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/home/user"),
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                True,
            ),
            (
                "multiple leading solidus w/o BASE_PATH",
                "//Videos",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                None,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                True,
            ),
            (
                "multiple leading solidus with BASE_PATH",
                "//Videos",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/home/user"),
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                True,
            ),
            (
                "multiple trailing solidus w/o BASE_PATH",
                "/Videos//",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                None,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                True,
            ),
            (
                "multiple trailing solidus with BASE_PATH",
                "/Videos//",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/home/user"),
                "/home/user/Videos",
                Path("/home/user/Videos"),
                "/home/user/Videos",
                True,
            ),
            (
                "intermediate single soliduses w/o BASE_PATH",
                "/Videos/movies/Star Trek",
                False,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                None,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                True,
            ),
            (
                "intermediate single soliduses with BASE_PATH",
                "/Videos/movies/Star Trek",
                False,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                Path("/home/user"),
                "/home/user/Videos/movies/Star Trek",
                Path("/home/user/Videos/movies/Star Trek"),
                "/home/user/Videos/movies/Star Trek",
                True,
            ),
            (
                "intermediate multiple soliduses w/o BASE_PATH",
                "/Videos//movies/Star Trek",
                False,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                None,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                True,
            ),
            (
                "intermediate multiple soliduses with BASE_PATH",
                "/Videos//movies/Star Trek",
                False,
                "/Videos/movies/Star Trek",
                Path("/Videos/movies/Star Trek"),
                "/Videos/movies/Star Trek",
                Path("/home/user"),
                "/home/user/Videos/movies/Star Trek",
                Path("/home/user/Videos/movies/Star Trek"),
                "/home/user/Videos/movies/Star Trek",
                True,
            ),
        ]

        for (
            description,
            path,
            is_abs_path,
            exp_db_path_str,
            exp_db_path,
            exp_system_db_path_str,
            base_path,
            exp_abs_path_str,
            exp_abs_path,
            exp_system_abs_path_str,
            exp_is_allowed,
        ) in test_data:
            with self.subTest(description=description):
                params.BASE_PATH = base_path

                mypath = MyPath(path, is_abs_path)
                self.assertEqual(mypath.db_path_str, exp_db_path_str)
                self.assertEqual(mypath.db_path, exp_db_path)
                self.assertEqual(mypath.system_db_path_str, exp_system_db_path_str)
                self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                self.assertEqual(mypath.abs_path, exp_abs_path)
                self.assertEqual(mypath.system_abs_path_str, exp_system_abs_path_str)
                self.assertEqual(mypath.is_allowed_db_path, exp_is_allowed)

                mypath = MyPath(Path(path), is_abs_path)
                self.assertEqual(mypath.db_path_str, exp_db_path_str)
                self.assertEqual(mypath.db_path, exp_db_path)
                self.assertEqual(mypath.system_db_path_str, exp_system_db_path_str)
                self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                self.assertEqual(mypath.abs_path, exp_abs_path)
                self.assertEqual(mypath.system_abs_path_str, exp_system_abs_path_str)
                self.assertEqual(mypath.is_allowed_db_path, exp_is_allowed)

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
