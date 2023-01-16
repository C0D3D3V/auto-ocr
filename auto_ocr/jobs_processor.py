from typing import Dict

from auto_ocr.utils import PathTools as PT, Log, append_list_to_json, load_list_from_json


class JobsProcessor:
    def __init__(self):
        path_of_job_defs_json = PT.get_path_of_job_defs_json()
        self.job_definitions = load_list_from_json(path_of_job_defs_json)

        if len(self.job_definitions) == 0:
            Log.warning(f'No Jobs are defined in {path_of_job_defs_json}')

        self.path_of_done_pdfs_json = PT.get_path_of_done_pdfs_json()
        self.done_pdfs = load_list_from_json(self.path_of_done_pdfs_json)

    def process_job(self, job: Dict):
        source_dir = job.get('source_dir', None)
        destination_dir = job.get('destination_dir', None)
        if source_dir is None or destination_dir is None:
            Log.error('source_dir or destination_dir not set for job')
            return

        source_dir = PT.get_abs_path(source_dir)
        destination_dir = PT.get_abs_path(destination_dir)

        finished_pdfs = []
        append_list_to_json(self.path_of_done_pdfs_json, finished_pdfs)

    def process(self):
        for job in self.job_definitions:
            self.process_job(job)
