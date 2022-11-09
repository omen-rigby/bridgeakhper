import sys
import os
from constants import date
from tourney_db import TourneyDB


def generate():
    date_folder = sys.argv[-1] if len(sys.argv) > 1 else date
    current_dir = __file__.replace("generate.py", "")
    new_dir = f"{current_dir}/{date_folder}"
    if not os.path.exists(new_dir):
        os.mkdir(new_dir)
        TourneyDB.create_tables()


if __name__ == "__main__":
    generate()


