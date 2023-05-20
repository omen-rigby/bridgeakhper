import os
import unittest
from urllib import parse
from constants import *

current_dir = "/".join(__file__.replace("\\", "/").split("/")[:-1])
for root, _, files in os.walk(current_dir):
    if "boards" in files:
        path = os.path.join(root, "boards")
        if "04-24" not in root:
            continue
        with open(path) as f:
            contents = f.read()
            if "s&e=s&s=s&w=s&" not in contents:
                boards = contents


class BoardTests(unittest.TestCase):
    def test_suites(self):
        for i, link in enumerate(boards.split("\n")):
            if not link:
                continue
            link = link.lower()
            hands = {}
            parsed = parse.urlparse(link)
            qs = parsed[4]
            qs = {chunk.split("=")[0]: chunk.split("=")[1] for chunk in qs.split("&")}
            for k, v in qs.items():
                if k in "nswe":
                    hands[k] = v
                    self.check_hand(v)
                elif k == "d":
                    expected_dealer = "wnes"[(i + 1) % 4]
                    self.assertEqual(v, expected_dealer, f"Board #{i+1}: expected dealer {expected_dealer}, got {v}")
                elif k == "v":
                    expected_vul = VULNERABILITY[(i + 1) % 16]
                    self.assertEqual(v, expected_vul, f"Board #{i+1}: expected vul {expected_vul}, got {v}")
                elif k == "b":
                    self.assertEqual(int(v), i + 1, f"Board #{i+1} has unexpected number {v}")
            self.check_distribution(hands, i + 1)

    def check_hand(self, hand):
        self.assertEqual(len(hand), 17, f"Hand {hand} has unexpected length")
        hand_set = {"2","3","4","5","6","7","8","9","t","j", "q", "k", "a","c","d","h","s"}
        extra_characters = set(hand).difference(hand_set)
        self.assertFalse(extra_characters, f"Extra characters {extra_characters} in {hand}")

        for suit in "shdc":
            self.assertEqual(hand.count(suit), 1, f"Found {suit} more than once in hand {hand}"
                                                  if hand.count(suit) else f"{suit} is missing from hand f{hand}")

    def check_distribution(self, hands, number):
        spades = "".join([h.split("s")[1].split("h")[0] for h in hands.values()])
        hearts = "".join([h.split("h")[1].split("d")[0] for h in hands.values()])
        diamonds = "".join([h.split("d")[1].split("c")[0] for h in hands.values()])
        clubs = "".join([h.split("c")[1] for h in hands.values()])
        for suit_name in ["spades", "hearts", "diamonds", "clubs"]:
            suit = eval(suit_name)
            self.assertEqual(13, len(suit), f"Wrong number of {suit_name} is entered for board #{number}")
            duplicates = "".join(set([card for card in suit if suit.count(card) > 1]))
            self.assertFalse(duplicates, f"{suit_name} {duplicates} appear more than once in board #{number}")








