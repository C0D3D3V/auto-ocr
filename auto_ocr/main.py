#!/usr/bin/env python3
# coding=utf-8

import argparse
import logging
import sys
import traceback

from logging.handlers import RotatingFileHandler


from colorama import just_fix_windows_console

from auto_ocr.jobs_processor import JobsProcessor

from auto_ocr.utils import (
    check_debug,
    check_verbose,
    LockError,
    Log,
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
        if hasattr(record, 'exception'):
            raise record.exception


def setup_logger():
    log_formatter = logging.Formatter('%(asctime)s  %(levelname)s  {%(module)s}  %(message)s', '%Y-%m-%d %H:%M:%S')
    log_file = PT.get_path_of_log_file()
    log_handler = RotatingFileHandler(
        log_file, mode='a', maxBytes=1 * 1024 * 1024, backupCount=2, encoding='utf-8', delay=0
    )

    log_handler.setFormatter(log_formatter)
    IS_VERBOSE = check_verbose()
    if IS_VERBOSE:
        log_handler.setLevel(logging.DEBUG)
    else:
        log_handler.setLevel(logging.INFO)

    app_log = logging.getLogger()
    if IS_VERBOSE:
        app_log.setLevel(logging.DEBUG)
    else:
        app_log.setLevel(logging.INFO)
    app_log.addHandler(log_handler)

    logging.info('--- auto-ocr started ---------------------')
    Log.info('Auto OCR starting...')
    if IS_VERBOSE:
        logging.debug('auto-ocr version: %s', __version__)
        logging.debug('python version: %s', ".".join(map(str, sys.version_info[:3])))

    if check_debug():
        logging.info('Debug-Mode detected. Errors will be re-risen.')
        app_log.addHandler(ReRaiseOnError())


def get_parser():
    """
    Creates a new argument parser.
    """
    parser = argparse.ArgumentParser(
        description=('Auto OCR - Tool to automatically OCR PDFs and copy them to a folder')
    )
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '-pj',
        '--process-jobs',
        action='store_true',
        help=(
            'Process all job definitions. Automatically OCR all PDFs in job directory and copy them to a defined folder'
        ),
    )

    parser.add_argument(
        '-v',
        '--verbose',
        default=False,
        action='store_true',
        help='Print various debugging information',
    )

    group.add_argument(
        '--version',
        action='version',
        version='auto-ocr ' + __version__,
        help='Print program version and exit',
    )

    return parser


# --- called at the program invocation: -------------------------------------
def main(args=None):
    """The main routine."""
    just_fix_windows_console()
    parser = get_parser()
    args = parser.parse_args(args)
    setup_logger()

    try:
        process_lock()
        if args.process_jobs:
            jobs_processor = JobsProcessor()
            jobs_processor.process()

        Log.success('All done. Exiting..')
        process_unlock()
    except BaseException as e:
        print('\n')
        if not isinstance(e, LockError):
            process_unlock()

        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': e})

        if check_verbose() or check_debug():
            Log.critical(f'{error_formatted}')
        else:
            Log.error(f'Exception: {e}')

        logging.debug('Exception-Handling completed. Exiting...')

        sys.exit(1)
