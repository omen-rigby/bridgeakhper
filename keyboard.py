import sqlite3
from copy import deepcopy 
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton
from constants import *
from itertools import chain

NAVIGATION_KEYBOARD = [InlineKeyboardButton("back",  callback_data="bm:back"),
                       InlineKeyboardButton("restart",  callback_data="bm:restart")]
CONTRACTS_KEYBOARD = [[InlineKeyboardButton(text=str(i), callback_data=f"bm:{i}") for i in range(1, 8)],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list(reversed(SUITS_UNICODE)) + ["NT"]],
    [InlineKeyboardButton(text=x, callback_data=f"bm:{x}") for x in ["x", "xx", "pass"]],
    [InlineKeyboardButton(s, callback_data=f"bm:{s}") for s in list("NESW")]]


ADJS = [InlineKeyboardButton(text="50/50", callback_data="bm:50/50"),
        InlineKeyboardButton(text="60/40", callback_data="bm:60/40"),
        InlineKeyboardButton(text="60/40", callback_data="bm:40/60")]


def contracts_keyboard(update):
    lists = deepcopy(CONTRACTS_KEYBOARD)
    if update.effective_chat.username in DIRECTORS:
        lists.append(ADJS + NAVIGATION_KEYBOARD)
    else:
        lists.append(NAVIGATION_KEYBOARD)
    return InlineKeyboardMarkup(lists)


def lead_keyboard():
    rows = []

    for i, s in enumerate(SUITS_UNICODE):
        suit_cards = [InlineKeyboardButton(text, callback_data="bm:" + "shdc"[i] + text)
                      for text in [SUITS_UNICODE[i]] + CARDS_WITH_DIGIT_TEN]
        half = (len(suit_cards) + 1) // 2
        rows.extend([suit_cards[:half], suit_cards[half:]])
    rows.append(NAVIGATION_KEYBOARD)
    return InlineKeyboardMarkup(rows)


def pairs_keyboard(update, context, exclude=0):
    pairs = context.bot_data["maxpair"]
    board = context.user_data["board"].number
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"Select ns,ew from protocols where number={board}")
    denied = list(set(chain(*[c for c in cursor.fetchall()])))
    conn.close()
    allowed = [b for b in range(1, pairs + 1) if b not in denied and b != int(exclude)]
    rows = []
    for i in range(len(allowed) // 7):
        rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[7 * i:7 + 7 * i]])
    if len(allowed) % 7:
        rows.append([InlineKeyboardButton(text=str(p), callback_data=f"bm:{p}") for p in allowed[len(allowed) // 7 * 7:]])
    rows.append(NAVIGATION_KEYBOARD)
    if update.effective_chat.username in DIRECTORS:
        rows.append([InlineKeyboardButton("Remove all records", callback_data=f"bm:rmall")])

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

