from .unit import Unit_base
from ...storage import genid
from ...utils.readable_index import answer_index

answer_index_counter = answer_index()

class Answer(Unit_base):
    """
    Answer node representing candidate's responses to questions.
    Stores: answer text only (job context inherited from Question node)
    """
    
    def __init__(self, raw_context: str, question_id: str = None, 
                 text_hash_id: str = None):
        self.raw_context = raw_context  # Answer text
        self.question_id = question_id  # Link back to Question
        self.text_hash_id = text_hash_id
        self._hash_id = None
        self._human_readable_id = None
    
    @property
    def hash_id(self):
        if not self._hash_id:
            hash_input = [self.raw_context]
            if self.question_id:
                hash_input.append(str(self.question_id))
            self._hash_id = genid(hash_input, "sha256")
        return self._hash_id
    
    @property
    def human_readable_id(self):
        if not self._human_readable_id:
            self._human_readable_id = answer_index_counter.increment()
        return self._human_readable_id

