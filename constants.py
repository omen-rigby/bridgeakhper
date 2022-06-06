import time
import re


DEBUG = True
date = "2022-06-05" if DEBUG else time.strftime("%Y-%m-%d")
db_path = f"{date}/boards.db"
protocols_path = db_path.replace("boards", "protocols")
VULNERABILITY = ["e",
                 "-", "n", "e", "b",
                 "n", "e", "b", "-",
                 "e", "b", "-", "n",
                 "b", "-", "n"]
CARDS = "AKQJT98765432"
SUITS = "shdc"
SUITS_UNICODE = "♠♥♦♣"
hands = "nesw"
DENOMINATIONS = "cdhsn"
CARD_RE = re.compile("[shdc][0-9AKQJT]", flags=re.IGNORECASE)
result_re = re.compile("=|([+-]\d\d?)")

CARET = "_"  # □
