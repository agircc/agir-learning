_episode = None

def set_episode(data):
    global _episode
    _episode = data

def get_episode():
    return _episode