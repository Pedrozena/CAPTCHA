import os

def envOverride(settings, path="", seprator="_"):
    '''
    Override dict values with environment variables sharing the same name of the key-path,
    separated by the **separator** value
    '''
    for k in settings:
        if type(settings[k]) is dict:
            settings[k] = envOverride(settings[k], path=k+seprator)
        else:
            settings[k] = os.environ.get((path+k).upper(), settings[k])
    return settings