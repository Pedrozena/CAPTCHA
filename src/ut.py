import os

def envOverride(settings, path=""):
    for k in settings:
        if type(settings[k]) is dict:
            settings[k] = envOverride(settings[k], path=k+"_")
        else:
            settings[k] = os.environ.get((path+k).upper(), settings[k])
    return settings