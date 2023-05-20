from tourney_db import TourneyDB
from copy import deepcopy
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton
from constants import *
from util import is_director
from itertools import chain

NAVIGATION_KEYBOARD = [InlineKeyboardButton("back",  callback_data="bm:back"),
                       InlineKeyboardButton("restart",  callback_data="bm:restart")]
CONTRACTS_KEYBOARD = [[InlineKeyboardButton(text=str(i), callback_data=f"bm:{i}") for i in range(1, 8)],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list(reversed(SUITS_UNICODE)) + ["NT"]],
    [InlineKeyboardButton(text=x, callback_data=f"bm:{x}") for x in ["x", "xx", "pass"]],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list("NESW")]]


def contracts_keyboard(update, include_arbitral=False):
    lists = deepcopy(CONTRACTS_KEYBOARD)
    if is_director(update):
        adj_results = ['50/50', '60/40', '40/60'] if CONFIG["scoring"] == "MPs" else ['A/A', 'A+/A-', 'A-/A+']
        if include_arbitral:
            if CONFIG["scoring"] == "MPs":
                adj_results = [['60/60', '40/40', '50/40'], ['40/50', '60/50', '50/60']]
            else:
                adj_results = [['A+/A+', 'A-/A-', 'A/A-'], ['A-/A', 'A+/A', 'A/A+']]
            adjs = [[InlineKeyboardButton(text=r, callback_data=f"bm:{r}") for r in row] for row in adj_results]
            lists.extend(adjs + [NAVIGATION_KEYBOARD])

        else:
            adj_results.append('more')
            adjs = [InlineKeyboardButton(text=r, callback_data=f"bm:{r}") for r in adj_results]
            lists.append(adjs + NAVIGATION_KEYBOARD)
    else:
        lists.append(NAVIGATION_KEYBOARD)
    return InlineKeyboardMarkup(lists)


def lead_keyboard(update):
    rows = []

    for i, s in enumerate(SUITS_UNICODE):
        suit_cards = [InlineKeyboardButton(text, callback_data="bm:" + "shdc"[i] + text)
                      for text in [SUITS_UNICODE[i]] + CARDS_WITH_DIGIT_TEN]
        half = (len(suit_cards) + 1) // 2
        rows.extend([suit_cards[:half], suit_cards[half:]])
    rows.append(deepcopy(NAVIGATION_KEYBOARD))
    if is_director(update):
        rows[-1].append(InlineKeyboardButton("Unknown lead", callback_data="bm:nolead"))
    return InlineKeyboardMarkup(rows)


def pairs_keyboard(update, context, exclude=0, use_movement=True, reverted=False):
    pairs = context.bot_data["maxpair"]
    movement = context.bot_data["movement"] if use_movement else ''
    board = context.user_data["board"].number
    n_rounds = max(m[2] for m in movement) if movement else pairs - 1 + (pairs % 2)
    boards_per_round = int(context.bot_data["maxboard"]) // n_rounds
    board_set = (int(board) - 1) // boards_per_round + 1
    conn = TourneyDB.connect()
    cursor = conn.cursor()
    cursor.execute(f"Select ns,ew from protocols where number={board}")
    denied = list(set(chain(*[c for c in cursor.fetchall()])))
    conn.close()
    first_pair = 1 + (pairs % 2 and CONFIG.get('no_first_pair'))
    allowed = [b for b in range(first_pair, pairs + first_pair) if b not in denied and b != int(exclude)]
    rows = []
    if movement:
        allowed_tuples = [f"{ew if reverted else ns} vs {ns if reverted else ew}"
                          for (ns, ew, bs) in movement if bs == board_set and ns in allowed and ew in allowed]
        for i in range(len(allowed_tuples) // 3):
            rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}")
                         for p in allowed_tuples[3 * i:3 + 3 * i]])
        if len(allowed_tuples) % 3:
            rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}")
                         for p in allowed_tuples[len(allowed_tuples) // 3 * 3:]])

        if not is_director(update):
            rows.append(NAVIGATION_KEYBOARD)
            return InlineKeyboardMarkup(rows)
    else:
        for i in range(len(allowed) // 7):
            rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[7 * i:7 + 7 * i]])
        if len(allowed) % 7:
            rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[len(allowed) // 7 * 7:]])
    rows.append(NAVIGATION_KEYBOARD)
    if is_director(update):
        rows.append([InlineKeyboardButton("Remove all", callback_data=f"bm:rmall")])
        if movement:
            rows[-1].append(InlineKeyboardButton("Switch directions", callback_data="bm:wrongdirection"))

    return InlineKeyboardMarkup(rows)


def results_keyboard(context):
    result = context.user_data["result"]
    level = int(result.text.split("Contract: ")[1][0])

    rows = [[InlineKeyboardButton(text="=", callback_data=f"bm:=")] +
            [InlineKeyboardButton(text=f"+{i}", callback_data=f"bm:+{i}") for i in range(1, 8 - level)],

            [InlineKeyboardButton(text=f"-{i}", callback_data=f"bm:-{i}") for i in range(1, level + 7)],
            NAVIGATION_KEYBOARD
            ]
    return InlineKeyboardMarkup(rows)

