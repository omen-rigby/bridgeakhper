import os
from itertools import chain
from constants import CONFIG


def get_movement(max_pair):
    tables = (max_pair + 1) // 2
    movement_letter = "H" if CONFIG["movement"] == "howell" else "M"
    filename = f"{movement_letter}{tables:02d}{tables * 2 - 1:02d}.MOV"
    full_path = os.path.abspath(__file__).replace("parse_mov.py", filename)
    try:
        return parse(full_path)
    except Exception as e:
        print("Not found suitable movement for {} pairs, tried {}".format(max_pair, filename))
        return ""


def parse(file):
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


if __name__ == "__main__":
    arr = [[8, 1, 1], [8, 2, 2], [8, 3, 3], [8, 4, 4], [8, 5, 5], [8, 6, 6], [8, 7, 7],
           [6, 5, 1], [7, 6, 2], [1, 7, 3], [7, 5, 4], [4, 7, 5], [2, 7, 6], [6, 2, 7],
           [1, 4, 2], [2, 5, 3], [3, 6, 4], [6, 1, 5], [5, 1, 6], [7, 3, 1], [3, 1, 7],
           [6, 4, 3], [2, 1, 4], [3, 2, 5], [4, 3, 6], [4, 2, 1], [5, 3, 2], [5, 4, 7]]
    edit_mov("H0406.MOV", arr)
    print(parse("H0406_new.MOV"))
