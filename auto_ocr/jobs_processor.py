import os
from typing import Dict, List

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
        job_name = job.get('name', None)
        if source_dir is None or destination_dir is None or job_name is None:
            Log.error('source_dir or destination_dir not set for job')
            return

        source_dir = PT.get_abs_path(source_dir)
        PT.make_dirs(source_dir)
        destination_dir = PT.get_abs_path(destination_dir)
        PT.make_dirs(destination_dir)

        that_job_done_pdfs = self.get_done_pdfs_for_this_job(job_name)
        now_finished_pdfs = []

        pdf_names = os.listdir(source_dir)
        for pdf_name in pdf_names:
            if pdf_name not in that_job_done_pdfs:
                print(pdf_name)
                now_finished_pdfs.append({'filename': pdf_name, 'job_name': job_name})

        append_list_to_json(self.path_of_done_pdfs_json, now_finished_pdfs)

    def process(self):
        for job in self.job_definitions:
            self.process_job(job)
