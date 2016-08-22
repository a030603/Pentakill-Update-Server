
# MT-non-safe progress note
class ProgressNote(object):
    def __init__(self):
        self.cur_percentage = 0
        
    # Go to initial state
    def reset(self):
        self.current = 0
        
    def progress(self, percentage):
        self.cur_percentage += percentage
        if self.cur_percentage >= 100:
            self.cur_percentage = 100
    
    def complete(self):
        self.cur_percentage = 100
        
    def look(self):
        return self.cur_percentage
    
    def completed(self):
        return self.cur_percentage >= 100
    