import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import orjson


def check_verbose() -> bool:
    """Return if the verbose mode is active"""
    return "-v" in sys.argv or "--verbose" in sys.argv


def check_debug() -> bool:
    """Return if the debugger is currently active"""
    return "pydevd" in sys.modules or (hasattr(sys, "gettrace") and sys.gettrace() is not None)


class LockError(Exception):
    """An Exception which gets thrown if a Downloader is already running."""

    pass


def process_lock():
    """
    A very simple lock mechanism to prevent multiple downloaders being started.

    The functions are not resistant to high frequency calls.
    Raise conditions will occur!

    Test if a lock is already set in a directory, if not it creates the lock.
    """
    if not check_debug():
        path = PathTools.get_path_of_lock_file()
        if Path(path).exists():
            raise LockError(f"A downloader is already running. Delete {str(path)} if you think this is wrong.")
        Path(path).touch()


def process_unlock():
    """Remove a lock in a directory."""
    path = PathTools.get_path_of_lock_file()
    try:
        Path(path).unlink()
    except OSError:
        pass


def load_list_from_json(json_file_path: str) -> List[Dict]:
    """
    Return the list stored in a json file or an empty list
    """
    if os.path.exists(json_file_path):
        with open(json_file_path, "rb") as config_file:
            raw_json = config_file.read()
            return orjson.loads(raw_json)  # pylint: disable=maybe-no-member
    else:
        return []


def append_list_to_json(json_file_path: str, list_to_append: List[Dict]):
    """
    This appends a list of dictionaries to the end of a json file.
    If the json file does not exist a new json file is created.
    This functions makes strict assumptions about the file format.
    The format must be the same as from orjson output with the options orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2.
    Like:
    ```
    [
      {
        "test1": 1,
      },
      {
        "test2": "2",
        "test3": false
      }
    ]

    ```
    """
    # pylint: disable=maybe-no-member
    json_bytes = orjson.dumps(list_to_append, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
    try:
        if os.path.isfile(json_file_path):
            o_file = open(json_file_path, "r+b")
            o_file.seek(-3, os.SEEK_END)  # Remove \n]\n
            o_file.write(b",\n")
            o_file.write(json_bytes[2:])  # Remove [\n
        else:
            o_file = open(json_file_path, "wb")
            o_file.write(json_bytes)

    except (OSError, IOError) as err:
        logging.error("Error: Could not append List to json: %r Reason: %s", json_file_path, err)
        exit(-1)
    finally:
        if o_file is not None:
            o_file.close()


class PathTools:
    """A set of methods to create correct paths."""

    @staticmethod
    def get_user_config_directory():
        """Returns a platform-specific root directory for user config settings."""
        # On Windows, prefer %LOCALAPPDATA%, then %APPDATA%, since we can expect the
        # AppData directories to be ACLed to be visible only to the user and admin
        # users (https://stackoverflow.com/a/7617601/1179226). If neither is set,
        # return None instead of falling back to something that may be world-readable.
        if os.name == "nt":
            appdata = os.getenv("LOCALAPPDATA")
            if appdata:
                return appdata
            appdata = os.getenv("APPDATA")
            if appdata:
                return appdata
            return None
        # On non-windows, use XDG_CONFIG_HOME if set, else default to ~/.config.
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            return xdg_config_home
        return os.path.join(os.path.expanduser("~"), ".config")

    @staticmethod
    def get_user_data_directory():
        """Returns a platform-specific root directory for user application data."""
        if os.name == "nt":
            appdata = os.getenv("LOCALAPPDATA")
            if appdata:
                return appdata
            appdata = os.getenv("APPDATA")
            if appdata:
                return appdata
            return None
        # On non-windows, use XDG_DATA_HOME if set, else default to ~/.config.
        xdg_config_home = os.getenv("XDG_DATA_HOME")
        if xdg_config_home:
            return xdg_config_home
        return os.path.join(os.path.expanduser("~"), ".local/share")

    @staticmethod
    def get_project_data_directory():
        """
        Returns an Path object to the project config directory
        """
        data_dir = Path(PathTools.get_user_data_directory()) / "auto-ocr"
        if not data_dir.is_dir():
            data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    @staticmethod
    def get_project_config_directory():
        """
        Returns an Path object to the project config directory
        """
        config_dir = Path(PathTools.get_user_config_directory()) / "auto-ocr"
        if not config_dir.is_dir():
            config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir)

    @staticmethod
    def get_path_of_job_defs_json():
        return str(Path(PathTools.get_project_config_directory()) / "job_defs.json")

    @staticmethod
    def get_path_of_log_file():
        return str(Path(PathTools.get_project_data_directory()) / "AutoOcr.log")

    @staticmethod
    def get_path_of_lock_file():
        return str(Path(tempfile.gettempdir()) / "AutoOcr.running.lock")

    @staticmethod
    def get_path_of_done_files_json():
        return str(Path(PathTools.get_project_data_directory()) / "done_files.json")
