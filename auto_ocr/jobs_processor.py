import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, Optional, Union

from auto_ocr.utils import PathTools as PT
from auto_ocr.utils import append_list_to_json, load_list_from_json


class CopyMode(Enum):
    HARD_LINK = "hard_link"
    NO_COPY = "no_copy"
    COPY = "copy"


class OutputMode(Enum):
    MIRROR_TREE = "mirror_tree"
    SINGLE_FOLDER = "single_folder"


class InputMode(Enum):
    DEEP_TREE = "deep_tree"
    SINGLE_FOLDER = "single_folder"


@dataclass
class JobConfig:
    name: str
    sources: Union[str, List[str]]
    destinations: Optional[Union[str, List[str]]] = None
    copy_mode: CopyMode = CopyMode.HARD_LINK
    output_mode: OutputMode = OutputMode.MIRROR_TREE
    input_mode: InputMode = InputMode.DEEP_TREE
    do_ocr: bool = True
    use_done_file_names_list: bool = True
    delete_source_at_end: bool = False

    def __post_init__(self):
        # Convert single paths to lists
        if isinstance(self.sources, str):
            self.sources = [self.sources]
        if isinstance(self.destinations, str):
            self.destinations = [self.destinations]

        # Validate source paths
        if not self.sources:
            raise ValueError("At least one source directory must be provided.")
        absolute_src_paths = []
        for path in self.sources:
            path = Path(path).resolve()
            if not os.path.isdir(path):
                raise ValueError(f"Source directory does not exist: {path}")
            absolute_src_paths.append(path)
        self.sources = absolute_src_paths

        # Validate destination paths if provided
        absolute_dst_paths = []
        if self.destinations:
            for path in self.destinations:
                path = Path(path).resolve()
                if not os.path.isdir(path):
                    raise ValueError(f"Destination directory does not exist: {path}")
                absolute_dst_paths.append(path)
        self.destinations = absolute_dst_paths

        # Ensure do_ocr, use_file_name_done_list, delete_source_at_end are boolean
        if not isinstance(self.do_ocr, bool):
            raise ValueError("do_ocr must be a boolean.")
        if not isinstance(self.use_done_file_names_list, bool):
            raise ValueError("use_done_file_names_list must be a boolean.")
        if not isinstance(self.delete_source_at_end, bool):
            raise ValueError("delete_source_at_end must be a boolean.")

    @staticmethod
    def _parse_enum(enum_cls, value):
        if isinstance(value, enum_cls):
            return value
        if isinstance(value, str):
            try:
                return enum_cls(value.lower())
            except ValueError:
                raise ValueError(f"Invalid value '{value}' for {enum_cls.__name__}. Expected one of {list(enum_cls)}.")
        raise TypeError(f"Expected type {enum_cls.__name__} or str for {enum_cls.__name__}, got {type(value)}.")

    @classmethod
    def from_dict(cls, config_dict):
        return cls(
            name=config_dict['name'],
            sources=config_dict.get('sources', []),
            destinations=config_dict.get('destinations', None),
            copy_mode=cls._parse_enum(CopyMode, config_dict.get('copy_mode', 'hard_link')),
            output_mode=cls._parse_enum(OutputMode, config_dict.get('output_mode', 'mirror_tree')),
            input_mode=cls._parse_enum(InputMode, config_dict.get('input_mode', 'deep_tree')),
            do_ocr=config_dict.get('do_ocr', True),
            use_done_file_names_list=config_dict.get('use_done_file_names_list', True),
            delete_source_at_end=config_dict.get('delete_source_at_end', False),
        )


class JobsProcessor:
    def __init__(self):
        path_of_job_defs_json = PT.get_path_of_job_defs_json()
        self.job_definitions = load_list_from_json(path_of_job_defs_json)

        if len(self.job_definitions) == 0:
            logging.warning("No Jobs are defined in %s", path_of_job_defs_json)

        self.path_of_done_files_json = PT.get_path_of_done_files_json()
        self.all_done_files = load_list_from_json(self.path_of_done_files_json)

    def get_done_file_names_for(self, job_name: str) -> List[str]:
        already_done_file_names = []
        for done_file in self.all_done_files:
            done_file_job_name = done_file.get("job_name", None)
            if done_file_job_name is None or job_name != done_file_job_name:
                continue
            done_file_name = done_file.get("file_name", None)
            if done_file_name is not None:
                already_done_file_names.append(done_file_name)

        return already_done_file_names

    def copy_file(
        self,
        job: JobConfig,
        source_dir: Path,
        sub_source_dir: Path,
        file_name: str,
        destination_dir: Path,
    ) -> bool:

        if job.output_mode == OutputMode.MIRROR_TREE:
            destination_file_path = destination_dir / sub_source_dir / file_name
        elif job.output_mode == OutputMode.SINGLE_FOLDER:
            destination_file_path = destination_dir / file_name
        destination_file_path.mkdir(parents=True, exist_ok=True)

        source_file_path = source_dir / sub_source_dir / file_name

        logging.info("Copy %r to %r", file_name, destination_file_path)
        logging.info("Copy mode: %s", job.copy_mode.value)

        if job.copy_mode == CopyMode.COPY:
            try:
                shutil.copyfile(source_file_path, destination_file_path)
            except OSError as copy_err:
                logging.error("Error on copy: %r", copy_err)
                return False
        elif job.copy_mode == CopyMode.HARD_LINK:
            try:
                if os.path.isfile(destination_file_path) and not os.path.samefile(
                    source_file_path, destination_file_path
                ):
                    logging.warning("Destination file does already exist, file will be deleted")
                    destination_file_path.unlink()
            except OSError as remove_err:
                logging.error("Error while removing destination file: %s", remove_err)

            if not os.path.isfile(destination_file_path):
                try:
                    os.link(source_file_path, destination_file_path)
                except OSError as hardlink_err:
                    logging.error("Error while creating hardlink: %s", hardlink_err)
                    return False

            elif os.path.isfile(destination_file_path) and os.path.samefile(source_file_path, destination_file_path):
                logging.info("Destination file is already a hardlink of %r", file_name)
        return True

    def run_ocr(self, source_file_path: Path) -> bool:
        logging.info("Running OCR on %s", source_file_path.name)
        try:
            subprocess.run(
                [
                    "ocrmypdf",
                    "-l",
                    "deu",
                    str(source_file_path),
                    str(source_file_path),
                ],
                check=True,
            )
        except CalledProcessError as ocr_err:
            if ocr_err.returncode == 6:
                # The file already appears to contain text so it may not need OCR.
                logging.warning("%s already contains OCR", source_file_path.name)
            else:
                logging.error("ocrmypdf failed %s", ocr_err)
                return False
        return True

    def process_single_dir_job(
        self,
        job: JobConfig,
        source_dir: Path,
        sub_source_dir: Path,
        already_done_file_names: List[str],
    ):

        full_source_dir = source_dir / sub_source_dir
        for source_file_path in full_source_dir.iterdir():
            if source_file_path.is_file() and source_file_path.suffix.lower() == '.pdf':
                if job.use_done_file_names_list and source_file_path.name in already_done_file_names:
                    continue

                logging.info("Working on %s", source_file_path.name)

                if job.do_ocr:
                    if not self.run_ocr(source_file_path):
                        continue
                else:
                    logging.info("Skip ocr file!")

                if job.copy_mode != CopyMode.NO_COPY:
                    if any(
                        not self.copy_file(job, source_dir, sub_source_dir, source_file_path.name, dest_dir)
                        for dest_dir in job.destinations
                    ):
                        continue
                else:
                    logging.info("Skip copy file!")

                if job.delete_source_at_end:
                    try:
                        source_file_path.unlink()
                        logging.info("Source file deleted")
                    except OSError as delete_err:
                        logging.error("Error while removing source file: %s", delete_err)

                now_finished_file = [{"file_name": source_file_path.name, "job_name": job.name}]
                append_list_to_json(self.path_of_done_files_json, now_finished_file)

    def process_job(self, job: JobConfig):
        """Start a ocr process for each input path in that job"""
        already_done_file_names = self.get_done_file_names_for(job.name)

        for source_dir in job.sources:
            if job.input_mode is InputMode.SINGLE_FOLDER:
                self.process_single_dir_job(job, source_dir, Path('.'), already_done_file_names)
            elif job.input_mode is InputMode.DEEP_TREE:
                for root, _, _ in os.walk(source_dir):
                    relative_path = Path(root).relative_to(source_dir)
                    self.process_single_dir_job(job, source_dir, relative_path, already_done_file_names)

    def process(self):
        """Parse every job and start processing it"""
        for idx, job_dict in enumerate(self.job_definitions):
            try:
                job = JobConfig.from_dict(job_dict)
            except (ValueError, TypeError) as parse_error:
                raise RuntimeError(f"Could not parse job {idx}") from parse_error
            self.process_job(job)
