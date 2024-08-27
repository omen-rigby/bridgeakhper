import time
import re
import json
import os

DEBUG = False

date = "2022-10-10" if DEBUG else time.strftime("%Y-%m-%d")
db_path = os.environ.get('CURRENT_TOURNEY')
PLAYERS_DB = os.environ.get('PLAYERS_DB')
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
ADJ_RE = re.compile("((\d\d)|(A[\+-]?))/((\d\d)|(A[\+-]?))")
CONTRACT_RE = re.compile(f"^([1-7]([{SUITS_UNICODE}]|(NT))x{{0,2}}[{hands}])|(pass)|((\d\d)|(A[\+-]?))/((\d\d)|(A[\+-]?))", re.IGNORECASE)
result_re = re.compile("=|([+-]\d\d?)")
OPPS_RE = re.compile("(\d+) vs (\d+)")
CARET = "_"  # □
CONFIG = json.load(open(os.path.abspath(__file__).replace(os.path.basename(__file__), "config.json")))
AM = CONFIG["city"] in ("Ереван",)
CITIES_LATIN = {"Ереван": "Yerevan"}
BITKIN_ID = 403784659
AGGREGATOR_COMMANDS = ['/simstart', '/venuelist', '/aggregate', '/startindex']
BOARDS_RE = re.compile('\d+ \(\d+\)')
global DIRECTORS
DIRECTORS = set(CONFIG["directors"])
