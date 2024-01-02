from tourney_db import TourneyDB
from constants import *
from copy import deepcopy
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup, InlineKeyboardButton
from exceptions import *


class Board:
    _initial_layout = []

    def __init__(self, number=0):
        self.number = number
        self.n = self.w = self.s = self.e = ""

    def set_number(self, number):
        self.number = number

    @property
    def current_hand(self):
        for h in "nesw":
            if self.__getattribute__(h):
                continue
            return h

    @staticmethod
    def remove_suits(string):
        for s in SUITS_UNICODE:
            string = string.replace(s, "")
        return string

    def unset_hand(self):
        seat = self.current_hand
        self.__setattr__(seat.lower(), None)

    def set_hand(self, cards):
        seat = self.current_hand
        self.__setattr__(seat.lower(), cards)
        cards = self.remove_suits(cards.lower()).replace("\n", " ").replace("10", "t").split(" ")
        for suit, holding in zip("shdc", cards):
            self.__setattr__(seat.lower() + suit, holding.replace("-", ""))

    def get_w_hand(self):
        w = []
        cards_in_w = 0
        for i, suit in enumerate("shdc"):
            cards = "".join(CARDS).lower()
            for seat in "nes":
                for c in self.__getattribute__(f"{seat}{suit}"):
                    cards = cards.replace(c, "")
                    self.__setattr__(f"w{suit}", cards)
            cards_in_w += len(cards)
            w.append(SUITS_UNICODE[i] + (cards or "-"))
        if cards_in_w != 13:
            raise Exception(f"Wrong number of hands in W hand: {w}")
        return " ".join(w).upper()

    @property
    def initial_layout(self):
        if not self._initial_layout:
            for i, s in enumerate(SUITS_UNICODE):
                self._initial_layout.append([InlineKeyboardButton(text, callback_data="shdc"[i] + text)
                            for text in [SUITS_UNICODE[i]] + CARDS_WITH_DIGIT_TEN])
        return self._initial_layout

    def get_remaining_cards(self, lead=False):
        cards = deepcopy(self.initial_layout)
        for seat in "ne":
            if seat == self.current_hand or lead:
                break
            for i, suit in enumerate("shdc"):
                try:
                    holding = self.__getattribute__(f"{seat}{suit}").upper().replace("T", "10")
                except AttributeError:
                    holding = ""
                for card in CARDS_WITH_DIGIT_TEN:
                    if card in holding:
                        cards[i].pop([c.text for c in cards[i]].index(card))
        rows = []
        for suit_cards in cards:
            if len(suit_cards) < 8:
                rows.append(suit_cards)
            else:
                half = (len(suit_cards) + 1) // 2
                rows.extend([suit_cards[:half], suit_cards[half:]])
        return InlineKeyboardMarkup(rows)

    def is_vul(self, declarer):
        vul_text = VULNERABILITY[int(self.number) % 100 % 16]
        return declarer.lower() in {"n": "ns", "e": "ew", "b": "nsew", "-": ""}[vul_text.lower()]

    def sac_score(self, declarer, undertricks):
        if undertricks == 1:
            return 200 if self.is_vul(declarer) else 100
        elif undertricks == 2:
            return 500 if self.is_vul(declarer) else 300
        else:
            return -400 + 300 * (undertricks + self.is_vul(declarer))

    def get_total_points(self, declarer, denomination, tricks, result=None, multiplier=""):
        """
        Gets total points
        :param declarer: nsew
        :param denomination: cdhsn
        :param tricks: 7..13
        :param result: 7..13
        :param multiplier: "" or "x" or "xx"
        :return: total points
        """
        sign = (-1) ** (declarer in "ew")
        multiplier = 2 ** multiplier.count("x")
        vul = self.is_vul(declarer)
        if result is None:
            result = tricks
        level = tricks - 6
        if result < tricks:
            if multiplier == 1:
                return (50 + 50 * vul) * (result - tricks) * sign
            return -self.sac_score(declarer, tricks - result) * multiplier // 2 * sign
        trick_value = 20 if denomination in "cd♦♣" else 30
        base_cost = level * trick_value + 10 * (denomination[0] == "n")
        bonus = 50
        if base_cost * multiplier >= 100:

            bonus += [250, 450][vul]
            if level == 6:
                bonus += [500, 750][vul]
            elif level == 7:
                bonus += [1000, 1500][vul]
        if multiplier > 1:
            bonus += 25 * multiplier
        overtrick_value = [50, 100][vul] * multiplier if multiplier > 1 else trick_value
        return int((bonus + base_cost * multiplier + overtrick_value * (result - tricks)) * sign)

    def get_board_from_pbn(self, pbn, start_index=0):
        hands = pbn.split(' ')
        for hand in hands[4 - start_index:] + hands[:4 - start_index]:
            self.set_hand(hand.replace(".", "\n"))

    def is_valid(self):
        current_holding = {s: "" for s in SUITS}
        for position in hands:
            if position == self.current_hand:
                break
            for s in SUITS:
                holding = self.__getattribute__(position + s)
                repeating_cards = [c for c in holding if c in current_holding[s]]
                if repeating_cards:
                    raise RepeatingCardsException(f"{s}"+"".join(s.upper() for s in repeating_cards) + " is repeating more than once")
                else:
                    current_holding[s] += holding

    def save(self):
        conn = TourneyDB.connect()
        cursor = conn.cursor()

        statement = f"""
        INSERT INTO boards (number, ns, nh, nd, nc, es, eh, ed, ec, ss, sh, sd, sc, ws, wh, wd, wc)
        VALUES({self.number}, '{self.ns}', '{self.nh}', '{self.nd}', '{self.nc}', '{self.es}', '{self.eh}', 
            '{self.ed}', '{self.ec}', '{self.ss}', '{self.sh}', '{self.sd}', '{self.sc}', '{self.ws}', 
            '{self.wh}', '{self.wd}', '{self.wc}')
ON CONFLICT (number) DO UPDATE 
  SET ns = excluded.ns, nh = excluded.nh, nd = excluded.nd, nc = excluded.nc,
    es = excluded.es, eh = excluded.eh, ed = excluded.ed, ec = excluded.ec,
    ss = excluded.ss, sh = excluded.sh, sd = excluded.sd, sc = excluded.sc,
    ws = excluded.ws, wh = excluded.wh, wd = excluded.wd, wc = excluded.wc;"""
        cursor.execute(statement)
        conn.commit()
        conn.close()
