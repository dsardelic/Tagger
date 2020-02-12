import configparser
import os
from pathlib import Path
from typing import Optional

from . import settings

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(settings.BASE_DIR, "Tagger.ini"))

DB_PATH = Path(settings.BASE_DIR).joinpath("TaggerDB.json")
if "DB_PATH" in CONFIG["DEFAULT"]:
    DB_PATH = Path(CONFIG["DEFAULT"]["DB_PATH"])

BASE_PATH: Optional[Path] = None
if base_path_str := CONFIG["DEFAULT"].get("BASE_PATH", None):
    BASE_PATH = Path(base_path_str + os.sep)

DEFAULT_TAG_COLOR: str = CONFIG["DEFAULT"].get("DEFAULT_TAG_COLOR", "#d9d9d9")
