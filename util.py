from difflib import ndiff
try:
    from constants import *
except ImportError:
    from .constants import *


class Dict2Class(object):

    def __init__(self, my_dict):
        self.dict = my_dict
        for key in my_dict:
            setattr(self, key, my_dict[key])

    def __str__(self):
        return '{' + ", ".join(f"{k}: " + ("list" if type(v) == list else v.__str__()) for k, v in self.dict.items()) + '}'


def is_director(update):
    return str(update.effective_chat.id) in DIRECTORS or update.effective_chat.username in DIRECTORS


def levenshtein_distance_gen(str1, str2):
    """Copied from
    https://codereview.stackexchange.com/questions/217065/calculate-levenshtein-distance-between-two-strings-in-python
    """
    counter = {"+": 0, "-": 0}
    for edit_code, *_ in ndiff(str1, str2):
        if edit_code == " ":
            yield max(counter.values())
            counter = {"+": 0, "-": 0}
        else:
            counter[edit_code] += 1
    yield max(counter.values())


def levenshtein(str1, str2):
    return sum(levenshtein_distance_gen(str1, str2))


def relative_levenshtein(str1, str2):
    return levenshtein(str1, str2)/max(len(str1), len(str2))


def escape_suits(string):
    for bad, good in zip(SUITS_UNICODE, SUITS):
        string = string.replace(bad, good)
    return string


def remove_suits(string):
    for bad in SUITS_UNICODE:
        string = string.replace(bad, "")
    return string
