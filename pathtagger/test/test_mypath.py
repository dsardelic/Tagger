import os
import unittest
from pathlib import PosixPath, WindowsPath

from pathtagger import views
from Tagger import params


@unittest.skip
class Test(unittest.TestCase):
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
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._is_allowed_path(PosixPath(path_str)), exp_rval)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_is_allowed_path_nt(self):
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
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._get_db_path_str(PosixPath(path_str)), exp_rval)

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
        for i, (_, base_path_str, path_str, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    WindowsPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(
                    views._get_db_path_str(WindowsPath(path_str)), exp_rval
                )

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
        for i, (_, base_path_str, path, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    PosixPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._join_with_base_path(path), exp_rval)

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
        for i, (_, base_path_str, path, exp_rval) in enumerate(test_data):
            with self.subTest(i=i):
                params.BASE_PATH = (
                    WindowsPath(base_path_str + os.sep) if base_path_str else None
                )
                self.assertEqual(views._join_with_base_path(path), exp_rval)
