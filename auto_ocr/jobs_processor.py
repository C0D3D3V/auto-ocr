import logging
import os
import shutil
import subprocess
from subprocess import CalledProcessError
from typing import Dict, List

from auto_ocr.utils import PathTools as PT
from auto_ocr.utils import append_list_to_json, load_list_from_json


class JobsProcessor:
    def __init__(self):
        path_of_job_defs_json = PT.get_path_of_job_defs_json()
        self.job_definitions = load_list_from_json(path_of_job_defs_json)

        if len(self.job_definitions) == 0:
            logging.warning("No Jobs are defined in %s", path_of_job_defs_json)

        self.path_of_done_files_json = PT.get_path_of_done_files_json()
        self.all_done_files = load_list_from_json(self.path_of_done_files_json)

    def get_done_filenames_for_this_job(self, job_name) -> List[str]:
        already_done_filenames = []
        for done_file in self.all_done_files:
            done_file_job_name = done_file.get("job_name", None)
            if done_file_job_name is None or job_name != done_file_job_name:
                continue
            done_filename = done_file.get("filename", None)
            if done_filename is not None:
                already_done_filenames.append(done_filename)

        return already_done_filenames

    def job_settings_fine(self, job: Dict) -> bool:
        job_name = job.get("name", None)

        if job_name is None:
            logging.error("Please a job name (job_name) for this job")
            return False

        # Source options
        source_dir = job.get("source_dir", None)
        source_parent_dir = job.get("source_parent_dir", None)
        source_dirs = job.get("source_dirs", None)

        if source_dir is None and source_parent_dir is None and source_dirs is None:
            logging.error(
                "You have to define a single source directory using source_dir"
                + " or multiple source directories with source_parent_dir and source_dirs"
            )
            return False
        if source_dir is not None and (source_parent_dir is not None or source_dirs is not None):
            logging.error("Please define only single or multiple source directories, not both.")
            return False

        if (source_parent_dir is not None and source_dirs is None) or (
            source_parent_dir is None and source_dirs is not None
        ):
            logging.error("Please define for multiple source directories both source_parent_dir and source_dirs")
            return False

        # Job options
        copy_mode = job.get("copy_mode", "hardlink")

        if copy_mode != "no_copy":
            # Destination options
            destination_parent_dir = job.get("destination_parent_dir", None)
            destination_dir = job.get("destination_dir", None)

            if source_dir is not None and destination_dir is None:
                logging.error("Please define for single source directory, also a single destination_dir")
                return False

            if source_parent_dir is not None and destination_parent_dir is None:
                logging.error("Please define for multiple source directories, also a destination_parent_dir")
                return False

        return True

    def copy_file(
        self,
        copy_mode: str,
        source_file_path: str,
        destination_dir: str,
        file_name: str,
    ) -> bool:
        file_copy_path = PT.make_path(destination_dir, file_name)
        logging.info("Copy %r to %r", file_name, file_copy_path)
        logging.info("Copy mode: %s", copy_mode)
        if copy_mode == "copy":
            try:
                shutil.copyfile(source_file_path, file_copy_path)
            except OSError as copy_err:
                logging.error("Error on copy: %r", copy_err)
                return False
        elif copy_mode == "hardlink":
            try:
                if os.path.isfile(file_copy_path) and not os.path.samefile(source_file_path, file_copy_path):
                    logging.warning("Destination file does already exist, file will be deleted")
                    os.remove(file_copy_path)
            except OSError as remove_err:
                logging.error("Error while removing destination file: %r", remove_err)

            if not os.path.isfile(file_copy_path):
                try:
                    os.link(source_file_path, file_copy_path)
                except OSError as hardlink_err:
                    logging.error("Error while creating hardlink: %r", hardlink_err)
                    return False

            elif os.path.isfile(file_copy_path) and os.path.samefile(source_file_path, file_copy_path):
                logging.info("Destination file is already a hardlink of %r", file_name)
        return True

    def run_ocr(self, source_file_path: str, file_name: str) -> bool:
        logging.info("Running OCR on %s", file_name)
        try:
            subprocess.run(
                [
                    "ocrmypdf",
                    "-l",
                    "deu",
                    source_file_path,
                    source_file_path,
                ],
                check=True,
            )
        except CalledProcessError as ocr_err:
            if ocr_err.returncode == 6:
                # The file already appears to contain text so it may not need OCR.
                logging.warning("%s already contains OCR", file_name)
            else:
                logging.error("ocrmypdf failed %s", ocr_err)
                return False
        return True

    def process_single_dir_job(
        self,
        job: Dict,
        source_dir: str,
        destination_dir: str,
        already_done_filenames: List[str],
    ):
        # Job options
        job_name = job.get("name")
        do_ocr = job.get("do_ocr", True)
        copy_mode = job.get("copy_mode", "hardlink")

        source_dir = PT.get_abs_path(source_dir)
        if not os.path.isdir(source_dir):
            logging.error("%s does not exist!", source_dir)
            return

        if destination_dir is not None:
            destination_dir = PT.get_abs_path(destination_dir)
            PT.make_dirs(destination_dir)

        source_file_names = os.listdir(source_dir)
        for source_file_name in source_file_names:
            if source_file_name not in already_done_filenames:
                logging.info("Working on %s", source_file_name)
                source_file_path = PT.make_path(source_dir, source_file_name)

                if do_ocr:
                    if not self.run_ocr(source_file_path, source_file_name):
                        continue
                else:
                    logging.info("Skip ocr file!")

                if copy_mode != "no_copy":
                    if not self.copy_file(copy_mode, source_file_path, destination_dir, source_file_name):
                        continue
                else:
                    logging.info("Skip copy file!")

                now_finished_file = [{"filename": source_file_name, "job_name": job_name}]
                append_list_to_json(self.path_of_done_files_json, now_finished_file)

    def process_job(self, job: Dict):
        if not self.job_settings_fine(job):
            return

        source_mode = "single"
        # Source options
        source_dir = job.get("source_dir", None)
        source_parent_dir = job.get("source_parent_dir", None)
        source_dirs = job.get("source_dirs", None)
        if source_parent_dir is not None:
            source_mode = "multi"

        # Destination options
        destination_parent_dir = job.get("destination_parent_dir", None)
        destination_dir = job.get("destination_dir", None)

        job_name = job.get("name")
        already_done_filenames = self.get_done_filenames_for_this_job(job_name)

        if source_mode == "single":
            self.process_single_dir_job(job, source_dir, destination_dir, already_done_filenames)
        elif source_mode == "multi":
            for source_dir_name in source_dirs:
                source_dir_path = PT.make_path(source_parent_dir, source_dir_name)
                destination_dir_path = None
                if destination_parent_dir is not None:
                    destination_dir_path = PT.make_path(destination_parent_dir, source_dir_name)
                self.process_single_dir_job(job, source_dir_path, destination_dir_path, already_done_filenames)

    def process(self):
        for job in self.job_definitions:
            self.process_job(job)
