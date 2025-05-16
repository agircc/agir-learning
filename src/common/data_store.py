_learner = None
_scenario = None
_agent_roles = None
_states = None
_state_transitions = None

def set_learner(data):
    global _learner
    _learner = data

def get_learner():
    return _learner

def set_scenario(data):
    global _scenario
    _scenario = data

def get_scenario():
    return _scenario
    
def set_agent_roles(data):
    global _agent_roles
    _agent_roles = data

def get_agent_roles():
    return _agent_roles

def set_states(data):
    global _states
    _states = data

def get_states():
    return _states
    
def set_state_transitions(data):
    global _state_transitions
    _state_transitions = data

def get_state_transitions():
    return _state_transitions

# Add backward compatibility functions
def set_process(data):
    set_scenario(data)

def get_process():
    return get_scenario()
    
def set_process_roles(data):
    set_agent_roles(data)

def get_process_roles():
    return get_agent_roles()

def set_process_nodes(data):
    set_states(data)

def get_process_nodes():
    return get_states()
    
def set_process_transitions(data):
    set_state_transitions(data)

def get_process_transitions():
    return get_state_transitions()

