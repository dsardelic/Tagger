import os
import re
from pathlib import Path, PosixPath
from typing import List, Optional, Union

from Tagger import params


class MyPath:
    NT_ABS_PATH_STR_REGEX = r"^[A-Za-z]:[\\\/]?"

    def __init__(self, raw_path: Union[Path, str], is_abs_path: bool):
        self.raw_path = raw_path
        if any(
            (
                raw_path is None,
                os.name == "posix" and not str(raw_path).startswith("/"),
                os.name == "nt"
                and (
                    (
                        is_abs_path
                        and not re.match(self.NT_ABS_PATH_STR_REGEX, str(raw_path))
                    )
                    or (
                        not is_abs_path
                        and params.BASE_PATH
                        and not str(raw_path).startswith("/")
                    )
                ),
            )
        ):
            self.abs_path_str = None
        elif os.name == "nt" and re.fullmatch(
            self.NT_ABS_PATH_STR_REGEX, str(raw_path)
        ):
            self.abs_path_str = Path(raw_path).as_posix()[:2] + "/"
        else:
            formatted_raw_path_str = Path(raw_path).as_posix().strip("/")
            if isinstance(Path(raw_path), PosixPath):
                formatted_raw_path_str = "/" + formatted_raw_path_str
            if is_abs_path or not params.BASE_PATH:
                self.abs_path_str = formatted_raw_path_str
            else:
                self.abs_path_str = params.BASE_PATH.joinpath(
                    formatted_raw_path_str.lstrip("/")
                ).as_posix()

    @property
    def db_path_str(self) -> Optional[str]:
        if self.abs_path_str is None:
            return None
        abs_path = Path(self.abs_path_str)
        if not params.BASE_PATH:
            return abs_path.as_posix()
        if abs_path == params.BASE_PATH:
            return "/"
        if params.BASE_PATH in abs_path.parents:
            return "/" + "/".join(abs_path.parts[len(params.BASE_PATH.parts) :])
        return None

    @property
    def db_path(self) -> Optional[Path]:
        if self.db_path_str is None:
            return None
        return Path(self.db_path_str)

    @property
    def abs_path(self) -> Optional[Path]:
        if self.abs_path_str is None:
            return None
        return Path(self.abs_path_str)

    @property
    def is_valid_db_path_str(self) -> bool:
        return self.db_path_str not in (None, ".")

    def get_children(self) -> List["MyPath"]:
        return [
            self.__class__(child_raw_path, True)
            for child_raw_path in sorted(
                list(self.abs_path.glob("*")),
                key=lambda x: (1 - x.is_dir(), str(x).upper()),
            )
        ]
