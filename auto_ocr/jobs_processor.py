import os
import subprocess
import shutil

from typing import Dict, List
from subprocess import CalledProcessError

from auto_ocr.utils import PathTools as PT, Log, append_list_to_json, load_list_from_json


class JobsProcessor:
    def __init__(self):
        path_of_job_defs_json = PT.get_path_of_job_defs_json()
        self.job_definitions = load_list_from_json(path_of_job_defs_json)

        if len(self.job_definitions) == 0:
            Log.warning(f'No Jobs are defined in {path_of_job_defs_json}')

        self.path_of_done_pdfs_json = PT.get_path_of_done_pdfs_json()
        self.done_pdfs = load_list_from_json(self.path_of_done_pdfs_json)

    def get_done_pdfs_for_this_job(self, job_name) -> List[str]:
        that_job_done_pdfs = []
        for done_pdf in self.done_pdfs:
            done_pdf_job_name = done_pdf.get('job_name', None)
            if done_pdf_job_name is None or job_name != done_pdf_job_name:
                continue
            done_pdf_filename = done_pdf.get('filename', None)
            if done_pdf_filename is not None:
                that_job_done_pdfs.append(done_pdf_filename)

        return that_job_done_pdfs

    def job_settings_fine(self, job: Dict) -> bool:
        job_name = job.get('name', None)

        if job_name is None:
            Log.error('Please a job name (job_name) for this job')
            return False

        # Source options
        source_dir = job.get('source_dir', None)
        source_parent_dir = job.get('source_parent_dir', None)
        source_dirs = job.get('source_dirs', None)

        if source_dir is None and source_parent_dir is None and source_dirs is None:
            Log.error(
                'You have to define a single source directory using source_dir'
                + ' or multiple source directories with source_parent_dir and source_dirs'
            )
            return False
        if source_dir is not None and (source_parent_dir is not None or source_dirs is not None):
            Log.error('Please define only single or multiple source directories, not both.')
            return False

        if (source_parent_dir is not None and source_dirs is None) or (
            source_parent_dir is None and source_dirs is not None
        ):
            Log.error('Please define for multiple source directories both source_parent_dir and source_dirs')
            return False

        # Job options
        copy_mode = job.get('copy_mode', 'hardlink')

        if copy_mode != 'no_copy':
            # Destination options
            destination_parent_dir = job.get('destination_parent_dir', None)
            destination_dir = job.get('destination_dir', None)

            if source_dir is not None and destination_dir is None:
                Log.error('Please define for single source directory, also a single destination_dir')
                return False

            if source_parent_dir is not None and destination_parent_dir is None:
                Log.error('Please define for multiple source directories, also a destination_parent_dir')
                return False

        return True

    def copy_file(self, copy_mode: str, source_file_path: str, destination_dir: str, file_name: str) -> bool:
        file_copy_path = PT.make_path(destination_dir, file_name)
        Log.info(f'Copy {file_name} to {file_copy_path}')
        Log.info(f'Copy mode: {copy_mode}')
        if copy_mode == 'copy':
            try:
                shutil.copyfile(source_file_path, file_copy_path)
            except OSError as copy_err:
                Log.error(f'Error on copy: {copy_err}')
                return False
        elif copy_mode == 'hardlink':
            try:
                if os.path.isfile(file_copy_path) and not os.path.samefile(source_file_path, file_copy_path):
                    Log.warning('Destination file does already exist, file will be deleted')
                    os.remove(file_copy_path)
            except OSError as remove_err:
                Log.error(f'Error while removing destination file: {remove_err}')

            if not os.path.isfile(file_copy_path):
                try:
                    os.link(source_file_path, file_copy_path)
                except OSError as hardlink_err:
                    Log.error(f'Error while creating hardlink: {hardlink_err}')
                    return False

            elif os.path.isfile(file_copy_path) and os.path.samefile(source_file_path, file_copy_path):
                Log.info(f'Destination file is already a hardlink of {file_name}')
        return True

    def run_ocr(self, source_file_path: str, file_name: str) -> bool:
        Log.info(f'Running OCR on {file_name}')
        try:
            subprocess.run(
                [
                    'ocrmypdf',
                    '-l',
                    'deu',
                    source_file_path,
                    source_file_path,
                ],
                check=True,
            )
        except CalledProcessError as ocr_err:
            if ocr_err.returncode == 6:
                # The file already appears to contain text so it may not need OCR.
                Log.warning(f"{file_name} already contains OCR")
            else:
                Log.error(f"ocrmypdf failed {ocr_err}")
                return False
        return True

    def process_single_dir_job(self, job: Dict, source_dir: str, destination_dir: str, that_job_done_pdfs: List[str]):
        # Job options
        job_name = job.get('name')
        do_ocr = job.get('do_ocr', True)
        copy_mode = job.get('copy_mode', 'hardlink')

        source_dir = PT.get_abs_path(source_dir)
        if not os.path.isdir(source_dir):
            Log.error(f'{source_dir} does not exist!')
            return

        if destination_dir is not None:
            destination_dir = PT.get_abs_path(destination_dir)
            PT.make_dirs(destination_dir)

        source_file_names = os.listdir(source_dir)
        for source_file_name in source_file_names:
            if source_file_name not in that_job_done_pdfs:
                Log.info(f'Working on {source_file_name}')
                source_file_path = PT.make_path(source_dir, source_file_name)

                if do_ocr:
                    if not self.run_ocr(source_file_path, source_file_name):
                        continue
                else:
                    Log.info('Skip ocr file!')

                if copy_mode != 'no_copy':
                    if not self.copy_file(copy_mode, source_file_path, destination_dir, source_file_name):
                        continue
                else:
                    Log.info('Skip copy file!')

                now_finished_pdf = [{'filename': source_file_name, 'job_name': job_name}]
                append_list_to_json(self.path_of_done_pdfs_json, now_finished_pdf)

    def process_job(self, job: Dict):
        if not self.job_settings_fine(job):
            return

        source_mode = 'single'
        # Source options
        source_dir = job.get('source_dir', None)
        source_parent_dir = job.get('source_parent_dir', None)
        source_dirs = job.get('source_dirs', None)
        if source_parent_dir is not None:
            source_mode = 'multi'

        # Destination options
        destination_parent_dir = job.get('destination_parent_dir', None)
        destination_dir = job.get('destination_dir', None)

        job_name = job.get('name')
        that_job_done_pdfs = self.get_done_pdfs_for_this_job(job_name)

        if source_mode == 'single':
            self.process_single_dir_job(job, source_dir, destination_dir, that_job_done_pdfs)
        elif source_mode == 'multi':
            for source_dir_name in source_dirs:
                source_dir_path = PT.make_path(source_parent_dir, source_dir_name)
                destination_dir_path = None
                if destination_parent_dir is not None:
                    destination_dir_path = PT.make_path(destination_parent_dir, source_dir_name)
                self.process_single_dir_job(job, source_dir_path, destination_dir_path, that_job_done_pdfs)

    def process(self):
        for job in self.job_definitions:
            self.process_job(job)
