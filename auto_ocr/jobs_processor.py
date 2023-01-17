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

    def process_job(self, job: Dict):
        source_dir = job.get('source_dir', None)
        destination_dir = job.get('destination_dir', None)
        do_ocr = job.get('do_ocr', True)
        copy_mode = job.get('copy_mode', 'hardlink')
        job_name = job.get('name', None)
        if source_dir is None or job_name is None:
            Log.error('source_dir or job_name not set for job')
            return

        source_dir = PT.get_abs_path(source_dir)
        PT.make_dirs(source_dir)

        do_copy = False
        if destination_dir is None:
            Log.error('destination_dir is not set for job, files will not be copied')
            do_copy = False
        else:
            destination_dir = PT.get_abs_path(destination_dir)
            PT.make_dirs(destination_dir)
            do_copy = True

        that_job_done_pdfs = self.get_done_pdfs_for_this_job(job_name)

        pdf_names = os.listdir(source_dir)
        for pdf_name in pdf_names:
            if pdf_name not in that_job_done_pdfs:
                Log.info(f'Working on {pdf_name}')

                if do_ocr:
                    Log.info(f'Running OCR on {pdf_name}')
                    pdf_path = PT.make_path(source_dir, pdf_name)
                    try:
                        subprocess.run(
                            [
                                'ocrmypdf',
                                '-l',
                                'deu',
                                pdf_path,
                                pdf_path,
                            ],
                            check=True,
                        )
                    except CalledProcessError as err:
                        Log.info(f"ocrmypdf failed {err}")

                if do_copy:
                    pdf_copy_path = PT.make_path(destination_dir, pdf_name)
                    Log.info(f'Copy {pdf_name} to {pdf_copy_path}')
                    Log.info(f'Copy mode: {copy_mode}')
                    if copy_mode == 'copy':
                        try:
                            shutil.copyfile(pdf_path, pdf_copy_path)
                        except OSError as err:
                            Log.error(f'Error on copy: {err}')
                    elif copy_mode == 'hardlink':
                        try:
                            os.link(pdf_path, pdf_copy_path)
                        except OSError as err:
                            Log.error(f'Error on hardlink: {err}')

                now_finished_pdf = [{'filename': pdf_name, 'job_name': job_name}]
                append_list_to_json(self.path_of_done_pdfs_json, now_finished_pdf)

    def process(self):
        for job in self.job_definitions:
            self.process_job(job)
