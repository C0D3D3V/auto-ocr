#!/usr/bin/env python3
# coding=utf-8

import argparse
import logging
import sys
import traceback
import colorlog

from logging.handlers import RotatingFileHandler


from colorama import just_fix_windows_console

from auto_ocr.jobs_processor import JobsProcessor

from auto_ocr.utils import (
    check_debug,
    check_verbose,
    LockError,
    PathTools as PT,
    process_lock,
    process_unlock,
)
from auto_ocr.version import __version__


class ReRaiseOnError(logging.StreamHandler):
    """
    A logging-handler class which allows the exception-catcher of i.e. PyCharm
    to intervine
    """

    def emit(self, record):
        if hasattr(record, "exception"):
            raise record.exception


def setup_logger(args):
    file_log_handler = RotatingFileHandler(
        PT.make_path(args.log_file_path, "AutoOCR.log"),
        mode="a",
        maxBytes=1 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
        delay=0,
    )
    file_log_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)s  {%(module)s}  %(message)s", "%Y-%m-%d %H:%M:%S"
        )
    )
    stdout_log_handler = colorlog.StreamHandler()
    if sys.stdout.isatty() and not args.verbose:
        stdout_log_handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s %(message)s", "%H:%M:%S"
            )
        )
    else:
        stdout_log_handler.setFormatter(
            colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s  %(levelname)s  {%(module)s}  %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )

    app_log = logging.getLogger()
    if args.quiet:
        file_log_handler.setLevel(logging.ERROR)
        app_log.setLevel(logging.ERROR)
        stdout_log_handler.setLevel(logging.ERROR)
    elif args.verbose:
        file_log_handler.setLevel(logging.DEBUG)
        app_log.setLevel(logging.DEBUG)
        stdout_log_handler.setLevel(logging.DEBUG)
    else:
        file_log_handler.setLevel(logging.INFO)
        app_log.setLevel(logging.INFO)
        stdout_log_handler.setLevel(logging.INFO)

    app_log.addHandler(stdout_log_handler)
    if args.log_to_file:
        app_log.addHandler(file_log_handler)

    if args.verbose:
        logging.debug("auto-oct version: %s", __version__)
        logging.debug("python version: %s", ".".join(map(str, sys.version_info[:3])))

    if check_debug():
        logging.info("Debug-Mode detected. Errors will be re-risen.")
        app_log.addHandler(ReRaiseOnError())


def get_parser():
    """
    Creates a new argument parser.
    """

    def _dir_path(path):
        if os.path.isdir(path):
            return path
        raise argparse.ArgumentTypeError(
            f'"{str(path)}" is not a valid path. Make sure the directory exists.'
        )

    parser = argparse.ArgumentParser(
        description=(
            "Auto OCR - Tool to automatically OCR PDFs and copy them to a folder"
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-pj",
        "--process-jobs",
        dest="process_jobs",
        action="store_true",
        help=(
            "Process all job definitions. Automatically OCR all PDFs in job directory and copy them to a defined folder"
        ),
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        action="store_true",
        help="Print various debugging information",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        default=False,
        action="store_true",
        help="Sets the log level to error",
    )

    parser.add_argument(
        "-ltf",
        "--log-to-file",
        dest="log_to_file",
        default=False,
        action="store_true",
        help="Log all output additionally to a log file called MoodleDL.log",
    )

    parser.add_argument(
        "-lfp",
        "--log-file-path",
        dest="log_file_path",
        default=None,
        type=_dir_path,
        help=(
            "Sets the location of the log files created with --log-to-file. PATH must be an existing directory"
            + " in which you have read and write access. (default: same as --path)"
        ),
    )
    group.add_argument(
        "--version",
        action="version",
        version="auto-ocr " + __version__,
        help="Print program version and exit",
    )

    return parser


def post_process_args(args):
    if args.log_file_path is None:
        args.log_file_path = PT.get_project_data_directory()

    return args


# --- called at the program invocation: -------------------------------------
def main(args=None):
    """The main routine."""
    just_fix_windows_console()
    args = post_process_args(get_parser().parse_args(args))
    setup_logger(args)

    try:
        process_lock()
        if args.process_jobs:
            jobs_processor = JobsProcessor()
            jobs_processor.process()

        logging.info("All done. Exiting..")
        process_unlock()
    except BaseException as e:
        print("\n")
        if not isinstance(e, LockError):
            process_unlock()

        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={"exception": e})

        if check_verbose() or check_debug():
            logging.error("%s", error_formatted)
        else:
            logging.error("Exception: %s", e)

        logging.debug("Exception-Handling completed. Exiting...")

        sys.exit(1)
