import time
import re
import json
import os

DEBUG = False

date = "2022-06-26" if DEBUG else time.strftime("%Y-%m-%d")
db_path = f"{date}/boards.db"
protocols_path = db_path.replace("boards", "protocols")
VULNERABILITY = ["e",
                 "-", "n", "e", "b",
                 "n", "e", "b", "-",
                 "e", "b", "-", "n",
                 "b", "-", "n"]
CARDS = "AKQJT98765432"
CARDS_WITH_DIGIT_TEN = [c.replace("T", "10") for c in CARDS]
SUITS = "shdc"
SUITS_UNICODE = "♠♥♦♣"
hands = "nesw"
DENOMINATIONS = "cdhsn"
CARD_RE = re.compile("[shdc][0-9AKQJT]", flags=re.IGNORECASE)
CONTRACT_RE = re.compile(f"^([1-7]([{SUITS_UNICODE}]|(NT))x{{0,2}}[{hands}])|(pass)|(\d\d/\d\d)$", re.IGNORECASE)
result_re = re.compile("=|([+-]\d\d?)")
ADJ_RE = re.compile("\d\d/\d\d")
CARET = "_"  # □
CONFIG = json.load(open("config.json"))
DIRECTORS = CONFIG["directors"]
if 'DYNO' in os.environ and os.environ.get("DIRECTOR"):
    DIRECTORS.append(os.environ.get("DIRECTOR"))

