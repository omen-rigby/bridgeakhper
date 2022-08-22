from constants import *
from print import *

from deal import Deal
from result_getter import ResultGetter


class ConstDeal(Deal):
    def __init__(self, pbn, vul, dealer):
        self.data = {"v": vul, "d": dealer}

        if not isinstance(pbn, str):
            pbn = pbn.decode()
        pbn_first_seat, deck = pbn.split(":")
        n, e, s, w = deck.split(" ")
        assert pbn_first_seat.upper() == "N"

        for (cards, seat) in zip([n, e, s, w], hands):
            spades, hearts, diamonds, clubs = cards.split(".")
            self.data[f"{seat}s"] = spades
            self.data[f"{seat}h"] = hearts
            self.data[f"{seat}d"] = diamonds
            self.data[f"{seat}c"] = clubs

        self.get_minimax()


def main():
    deals = [
        ConstDeal(b"N:QJ6.K652.J85.T98 873.J97.AT764.Q4 K5.T83.KQ9.A7652 AT942.AQ4.32.KJ3", "NS", "N"),
        ConstDeal(b"N:T973.T852.AJ.JT5 Q.AQ.8764.AK7632 A654.7643.KT32.8 KJ82.KJ9.Q95.Q94", "-", "W"),
        ConstDeal(b"N:73.QJT.AQ54.T752 QT6.876.KJ9.AQ84 5.A95432.7632.K6 AKJ9842.K.T8.J93", "ALL", "S"),
    ]

    result_getter = ResultGetter(len(deals), None)
    result_getter.hands = deals

    path = f"./{date}"
    if not os.path.exists(path):
        os.makedirs(path)
    pdf_path = result_getter.pdf_travellers(True)
    print(f"Results are at: {pdf_path}")


if __name__ == '__main__':
    main()
