from .unit import Unit_base
from ...storage import genid
from ...utils.readable_index import question_index

question_index_counter = question_index()

class Question(Unit_base):
    """
    Question node representing application questions.
    Stores: question text, job_title, company_name, submission_date, embedding
    """
    
    def __init__(self, raw_context: str, question_id: str = None, 
                 job_title: str = None, company_name: str = None, 
                 submission_date: str = None, text_hash_id: str = None):
        self.raw_context = raw_context  # Question text
        self.question_id = question_id  # Database question ID
        self.job_title = job_title      # Job context
        self.company_name = company_name  # Company context
        self.submission_date = submission_date  # For recency filtering
        self.text_hash_id = text_hash_id
        self._hash_id = None
        self._human_readable_id = None
    
    @property
    def hash_id(self):
        if not self._hash_id:
            # Include question_id in hash to ensure uniqueness
            hash_input = [self.raw_context]
            if self.question_id:
                hash_input.append(str(self.question_id))
            self._hash_id = genid(hash_input, "sha256")
        return self._hash_id
    
    @property
    def human_readable_id(self):
        if not self._human_readable_id:
            self._human_readable_id = question_index_counter.increment()
        return self._human_readable_id

