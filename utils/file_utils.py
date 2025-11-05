import os

def cleanup(*filenames):
    for name in filenames:
        if os.path.exists(name):
            os.remove(name)
