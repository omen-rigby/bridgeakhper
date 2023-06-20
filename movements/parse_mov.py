import itertools
import os
from itertools import chain
from constants import CONFIG
from tourney_db import TourneyDB


def get_movement(max_pair):
    tables = (max_pair + 1) // 2
    conn = TourneyDB.connect()
    cursor = conn.cursor()
    is_mitchell = CONFIG.get("is_mitchell")
    cursor.execute(f"select movement from movements where tables={tables} and is_mitchell={is_mitchell}")
    movements = cursor.fetchall()
    conn.close()
    if movements:
        # list of [ns, ew, board_set (1...n_rounds)]
        return list(itertools.chain(*[[[int(r.split('-')[0]), int(r.split('-')[1]), round_num + 1] for r in rawnd.split(',')]
                                 for round_num, rawnd in enumerate(movements[0][0].split(';'))]))
    else:
        return ""


def parse(file):
    """Deprecated"""
    movement = []
    with open(file, "rb") as f:
        mojibake = f.read().split(b"#$")[-1]
        for round_n in range(len(mojibake) // 3):
            movement.append([mojibake[round_n * 3 + j] for j in range(3)])
    return movement


def edit_mov(file, new_pairs):
    with open(file, "rb") as f:
        mojibake = f.read().split(b"#$")[0] + b"#$"
        for r in chain(*new_pairs):
            mojibake += str(chr(r)).encode()
    with open(f"{file.split('.')[0]}_new.mov", "wb") as g:
        g.write(mojibake)
