import os
import tempfile
from bs4 import BeautifulSoup


def print_to_file(arg, name=None):
    if type(arg) == str and os.path.exists(arg):
        htm_path = arg
        htm_path = os.path.abspath(htm_path)
    elif type(arg) == str:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".htm") as f:
            f.write(arg)
        htm_path = os.path.abspath(f.name)
    elif type(arg) == BeautifulSoup:
        with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=".htm") as f:
            f.write(arg.prettify(encoding='UTF-8'))
        htm_path = os.path.abspath(f.name)
    if name:
        new_path = os.path.join(os.path.dirname(htm_path), f'{name}.htm')
        os.rename(htm_path, new_path)
        return new_path
    return htm_path
