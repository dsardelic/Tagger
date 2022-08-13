import unittest.mock
from pathlib import Path

from pathtagger.views import MyPath
from Tagger import params


# pylint: disable=R0904
class TestMyPath(unittest.TestCase):
    # TODO: u svim metodama provjeriti da se poziva _to_formatted_posix_path_str!

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_no_base_path(self, mock__to_formatted_posix_path_str):
        test_data = [
            (
                None,
                False,
                None,
                None,
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
                None,
                None,
                False,
                False,
            ),
            (
                "",
                False,
                None,
                None,
                None,
                None,
                False,
                False,
            ),
            (
                "",
                True,
                ".",
                Path("."),
                ".",
                Path("."),
                False,
                False,
            ),
            (
                ".",
                False,
                None,
                None,
                None,
                None,
                False,
                False,
            ),
            (
                ".",
                True,
                ".",
                Path("."),
                ".",
                Path("."),
                False,
                False,
            ),
            (
                "/",
                False,
                "/",
                Path("/"),
                "/",
                Path("/"),
                True,
                True,
            ),
            (
                "/",
                True,
                "/",
                Path("/"),
                "/",
                Path("/"),
                True,
                True,
            ),
            (
                "/Videos",
                False,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/Videos"),
                True,
                True,
            ),
            (
                "/Videos",
                True,
                "/Videos",
                Path("/Videos"),
                "/Videos",
                Path("/Videos"),
                True,
                True,
            ),
            (
                "/Videos/movies/Tarantino",
                False,
                "/Videos/movies/Tarantino",
                Path("/Videos/movies/Tarantino"),
                "/Videos/movies/Tarantino",
                Path("/Videos/movies/Tarantino"),
                True,
                True,
            ),
            (
                "/Videos/movies/Tarantino",
                True,
                "/Videos/movies/Tarantino",
                Path("/Videos/movies/Tarantino"),
                "/Videos/movies/Tarantino",
                Path("/Videos/movies/Tarantino"),
                True,
                True,
            ),
        ]

        for (
            raw_path,
            is_abs_path,
            exp_abs_path_str,
            exp_abs_path,
            exp_db_path_str,
            exp_db_path,
            exp_is_taggable,
            exp_is_valid_db_path_str,
        ) in test_data:
            with self.subTest(raw_path=raw_path, is_abs_path=is_abs_path):
                params.BASE_PATH = None
                for raw_value in (
                    [raw_path, Path(raw_path)] if raw_path is not None else [raw_path]
                ):
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, exp_abs_path)
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.db_path, exp_db_path)
                    self.assertEqual(mypath.is_taggable(), exp_is_taggable)
                    self.assertEqual(
                        mypath.db_path_str_is_valid(), exp_is_valid_db_path_str
                    )

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_abs_path_is_ancestor_of_base_path(self, mock__to_formatted_posix_path_str):
        test_data = [
            ("/", Path("/home/user"), "/", Path("/")),
            ("/home", Path("/home/user"), "/home", Path("/home")),
        ]
        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_abs_path,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                mock__to_formatted_posix_path_str.reset_mock()
                mock__to_formatted_posix_path_str.return_value = Path(
                    raw_value
                ).as_posix()
                mypath = MyPath(raw_value, is_abs_path)
                if raw_path:
                    mock__to_formatted_posix_path_str.assert_called()
                for raw_value in [raw_path, Path(raw_path)]:
                    mypath = MyPath(raw_value, True)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, exp_abs_path)
                    self.assertIsNone(mypath.db_path_str)
                    self.assertIsNone(mypath.db_path)
                    self.assertFalse(mypath.is_taggable())
                    self.assertFalse(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_abs_path_is_base_path(self, mock__to_formatted_posix_path_str):
        base_path_strs = ["/", "/home", "/home/user"]
        for base_path_str in base_path_strs:
            with self.subTest(base_path_str=base_path_str):
                params.BASE_PATH = Path(base_path_str)
                for base_path_value in [base_path_str, Path(base_path_str)]:
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(base_path_value, True)
                    self.assertEqual(mypath.raw_path, base_path_value)
                    self.assertEqual(mypath.abs_path_str, base_path_str)
                    self.assertEqual(mypath.abs_path, Path(base_path_str))
                    self.assertEqual(mypath.db_path_str, "/")
                    self.assertEqual(mypath.db_path, Path("/"))
                    self.assertTrue(mypath.is_taggable())
                    self.assertTrue(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_abs_path_is_descendant_of_base_path(
        self, mock__to_formatted_posix_path_str
    ):
        test_data = [
            ("/home/user/Videos", Path("/home/user"), "/home/user/Videos", "/Videos"),
            (
                "/home/user/Videos/Tarantino",
                Path("/home/user"),
                "/home/user/Videos/Tarantino",
                "/Videos/Tarantino",
            ),
        ]
        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_db_path_str,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                for raw_value in [raw_path, Path(raw_path)]:
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(raw_value, True)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, Path(exp_abs_path_str))
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.db_path, Path(exp_db_path_str))
                    self.assertTrue(mypath.is_taggable())
                    self.assertTrue(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_abs_path_is_unrelated_to_base_path(
        self, mock__to_formatted_posix_path_str
    ):
        test_data = [
            (
                None,
                Path("/home/user"),
                None,
                None,
            ),
            (
                "",
                Path("/home/user"),
                ".",
                Path("."),
            ),
            (
                ".",
                Path("/home/user"),
                ".",
                Path("."),
            ),
            (
                "/usr",
                Path("/home/user"),
                "/usr",
                Path("/usr"),
            ),
            (
                "/usr/bin",
                Path("/home/user"),
                "/usr/bin",
                Path("/usr/bin"),
            ),
        ]

        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_abs_path,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                for raw_value in (
                    [raw_path, Path(raw_path)] if raw_path is not None else [raw_path]
                ):
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(raw_value, True)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, exp_abs_path)
                    self.assertIsNone(mypath.db_path_str)
                    self.assertIsNone(mypath.db_path)
                    self.assertFalse(mypath.is_taggable())
                    self.assertFalse(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_db_path_is_ancestor_of_base_path(self, mock__to_formatted_posix_path_str):
        test_data = [
            ("/", Path("/home/user"), "/home/user", Path("/home/user"), "/", Path("/")),
            (
                "/home",
                Path("/home/user"),
                "/home/user/home",
                Path("/home/user/home"),
                "/home",
                Path("/home"),
            ),
        ]
        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_abs_path,
            exp_db_path_str,
            exp_db_path,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                for raw_value in [raw_path, Path(raw_path)]:
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(raw_value, False)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, exp_abs_path)
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.db_path, exp_db_path)
                    self.assertTrue(mypath.is_taggable())
                    self.assertTrue(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_db_path_is_base_path(self, mock__to_formatted_posix_path_str):
        test_data = [
            ("/", "/"),
            ("/home", "/home/home"),
            ("/home/user", "/home/user/home/user"),
        ]
        for base_path_str, exp_abs_path_str in test_data:
            with self.subTest(base_path_str=base_path_str):
                params.BASE_PATH = Path(base_path_str)
                for base_path_value in [base_path_str, Path(base_path_str)]:
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(base_path_value, False)
                    self.assertEqual(mypath.raw_path, base_path_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, Path(exp_abs_path_str))
                    self.assertEqual(mypath.db_path_str, base_path_str)
                    self.assertEqual(mypath.db_path, Path(base_path_str))
                    self.assertTrue(mypath.is_taggable())
                    self.assertTrue(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_db_path_is_descendant_of_base_path(
        self, mock__to_formatted_posix_path_str
    ):
        test_data = [
            (
                "/home/user/Videos",
                Path("/home/user"),
                "/home/user/home/user/Videos",
                "/home/user/Videos",
            ),
            (
                "/home/user/Videos/Tarantino",
                Path("/home/user"),
                "/home/user/home/user/Videos/Tarantino",
                "/home/user/Videos/Tarantino",
            ),
        ]
        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_db_path_str,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                for raw_value in [raw_path, Path(raw_path)]:
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(raw_value, False)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, Path(exp_abs_path_str))
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.db_path, Path(exp_db_path_str))
                    self.assertTrue(mypath.is_taggable())
                    self.assertTrue(mypath.db_path_str_is_valid())

    @unittest.mock.patch.object(MyPath, "_to_formatted_posix_path_str", autospec=True)
    def test_db_path_is_unrelated_to_base_path(self, mock__to_formatted_posix_path_str):
        test_data = [
            (
                None,
                Path("/home/user"),
                None,
                None,
                None,
                None,
                False,
                False,
            ),
            (
                "",
                Path("/home/user"),
                None,
                None,
                None,
                None,
                False,
                False,
            ),
            (
                ".",
                Path("/home/user"),
                None,
                None,
                None,
                None,
                False,
                False,
            ),
            (
                "/usr",
                Path("/home/user"),
                "/home/user/usr",
                Path("/home/user/usr"),
                "/usr",
                Path("/usr"),
                True,
                True,
            ),
            (
                "/usr/bin",
                Path("/home/user"),
                "/home/user/usr/bin",
                Path("/home/user/usr/bin"),
                "/usr/bin",
                Path("/usr/bin"),
                True,
                True,
            ),
        ]

        for (
            raw_path,
            base_path,
            exp_abs_path_str,
            exp_abs_path,
            exp_db_path_str,
            exp_db_path,
            exp_is_taggable,
            exp_is_valid_db_path_str,
        ) in test_data:
            with self.subTest(raw_path=raw_path, base_path=base_path):
                params.BASE_PATH = base_path
                for raw_value in (
                    [raw_path, Path(raw_path)] if raw_path is not None else [raw_path]
                ):
                    mock__to_formatted_posix_path_str.reset_mock()
                    mock__to_formatted_posix_path_str.return_value = Path(
                        raw_value
                    ).as_posix()
                    mypath = MyPath(raw_value, is_abs_path)
                    if raw_path:
                        mock__to_formatted_posix_path_str.assert_called()
                    mypath = MyPath(raw_value, False)
                    self.assertEqual(mypath.raw_path, raw_value)
                    self.assertEqual(mypath.abs_path_str, exp_abs_path_str)
                    self.assertEqual(mypath.abs_path, exp_abs_path)
                    self.assertEqual(mypath.db_path_str, exp_db_path_str)
                    self.assertEqual(mypath.db_path, exp_db_path)
                    self.assertEqual(mypath.is_taggable(), exp_is_taggable)
                    self.assertEqual(
                        mypath.db_path_str_is_valid(), exp_is_valid_db_path_str
                    )

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
