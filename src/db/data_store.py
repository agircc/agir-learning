_learner = None
_process = None
_process_roles = None
_process_nodes = None
_process_transitions = None

def set_learner(data):
    global _learner
    _learner = data

def get_learner():
    return _learner

def set_process(data):
    global _process
    _process = data

def get_process():
    return _process
    
def set_process_roles(data):
    global _process_roles
    _process_roles = data

def get_process_roles():
    return _process_roles

def set_process_nodes(data):
    global _process_nodes
    _process_nodes = data

def get_process_nodes():
    return _process_nodes
    
def set_process_transitions(data):
    global _process_transitions
    _process_transitions = data

def get_process_transitions():
    return _process_transitions
