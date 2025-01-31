import jaydebeapi
from difflib import ndiff
try:
    from constants import *
except ImportError:
    from .constants import *


DIRPATH = os.path.dirname(os.path.abspath(__file__))
UCANACCESS_JARS = [f'{DIRPATH}/access_driver/{path}' for path in
                   ['ucanaccess-5.0.1.jar', 'lib/commons-lang3-3.8.1.jar', 'lib/commons-logging-1.2.jar',
                    'lib/hsqldb-2.5.0.jar', 'lib/jackcess-3.0.1.jar']]


def connect_mdb(mdb_path):
    return jaydebeapi.connect(
        "net.ucanaccess.jdbc.UcanaccessDriver",
        f"jdbc:ucanaccess://{mdb_path};newDatabaseVersion=V2010",
        ["", ""],
        ":".join(UCANACCESS_JARS)
    )


class Dict2Class(object):

    def __init__(self, my_dict):
        self.dict = my_dict
        for key in my_dict:
            setattr(self, key, my_dict[key])

    def __str__(self):
        return '{' + ", ".join(f"{k}: " + ("list" if type(v) == list else v.__str__()) for k, v in self.dict.items()) + '}'


def is_director(update):
    return str(update.effective_user.id) in DIRECTORS or update.effective_user.username in DIRECTORS


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


def revert_name(name):
    """Converts full name to russian official style last_name first_name"""
    chunks = name.split()
    if len(chunks) == 2:
        return ' '.join(reversed(chunks))
    if len(chunks) == 3 and (len(chunks[1].strip('.')) == 1 or
                             any(chunks[1].endswith(a) for a in ("ич", "вна", "чна"))):
        # middle/patronymic initial: Alexander A. Ershov
        return f'{chunks[2]} {chunks[0]} {chunks[1]}'
    # last name prefix: Rafael van der Vaart
    last_name = ' '.join(chunks[1:])
    # TODO: handle asian & spanish names
    return f'{last_name} {chunks[0]}'.replace("ё", "е")


def decorate_all_functions(function_decorator):
    def decorator(cls):
        for name, obj in vars(cls).items():
            if callable(obj) and name not in ('end', 'start_round', 'restart_swiss', 'move_cards'):
                setattr(cls, name, function_decorator(obj))
        return cls
    return decorator
